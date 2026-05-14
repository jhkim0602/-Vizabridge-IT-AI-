#!/usr/bin/env python3
"""Create quality reports and human-review workbooks for semantic CSVs.

This script does not change the final CSV files. It reads them, looks for rows
that a human should inspect first, and writes separate review outputs under
output/. The final CSVs remain clean; review flags live only in the Excel files.

What the report checks:

- required fields that are unexpectedly empty
- mismatches such as item_type=restriction but empty restrictions
- possible OCR or table-of-contents noise
- duplicate semantic rows
- very short/long rows that may need splitting or removal

The goal is not to prove that every immigration rule is legally perfect. The
goal is to make manual review efficient by shrinking thousands of rows to a
small, prioritized candidate list.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.legacy import build_semantic_manual_csvs as builder  # constants + classifier helpers

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
QUALITY_DIR = PROJECT_ROOT / "output" / "quality"
REVIEW_DIR = PROJECT_ROOT / "output" / "review"


MANUAL_CONFIGS = {
    "stay": {
        "label": "체류민원",
        "csv": PROCESSED_DIR / "stay_manual_semantic_clean.csv",
        "code_col": "stay_status_code",
        "name_col": "stay_status_name_ko",
    },
    "visa": {
        "label": "사증민원",
        "csv": PROCESSED_DIR / "visa_manual_semantic_clean.csv",
        "code_col": "visa_code",
        "name_col": "visa_name_ko",
    },
}

# Columns added only to review outputs. They are intentionally not part of the
# final data/processed CSV contract.
REVIEW_COLUMNS = [
    "source_row_number",
    "review_priority",
    "review_reason",
    "suggested_action",
]

CORE_REVIEW_COLUMNS = [
    "item_type",
    "section_title",
    "petition_type",
    "subsection_type",
    "subtype_or_program",
    "applicant_context",
    "eligibility",
    "target_persons",
    "common_documents",
    "mandatory_documents",
    "other_documents",
    "requirements",
    "procedure",
    "restrictions",
    "exceptions",
    "fees",
    "duration_or_validity",
    "quota_or_limit",
    "score_criteria",
    "table_summary",
    "table_rows",
    "normalized_text",
]


SUSPICIOUS_TERMS = [
    "제목자격",
    "제목관리과",
    "제목족적",
    "目 次",
    "OCCUPATION REPORT FORM",
    "Alien Registration No.",
]

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def compact_text(value: object, max_chars: int = 600) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def filled(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().ne("")


def manual_columns(manual_key: str) -> list[str]:
    return builder.STAY_COLUMNS if manual_key == "stay" else builder.VISA_COLUMNS


def load_manual_csv(manual_key: str) -> pd.DataFrame:
    """Read one final CSV and normalize its column order for consistent reports."""
    config = MANUAL_CONFIGS[manual_key]
    df = pd.read_csv(config["csv"], dtype=str).fillna("")
    for column in manual_columns(manual_key):
        if column not in df.columns:
            df[column] = ""
    return df[manual_columns(manual_key)]


def priority_for(reasons: Iterable[tuple[str, str, str]]) -> str:
    priorities = [priority for _, priority, _ in reasons]
    return min(priorities, key=lambda priority: PRIORITY_RANK[priority])


def issue_actions(issue_keys: list[str]) -> str:
    """Translate machine issue keys into short review instructions."""
    actions = []
    if any("without" in key for key in issue_keys):
        actions.append("item_type/subsection_type과 실제 채움 필드가 맞는지 확인")
    if any("document" in key for key in issue_keys):
        actions.append("공통/필수/기타서류 버킷 재분류")
    if any("score" in key for key in issue_keys):
        actions.append("점수표/배점 행인지 확인")
    if any("quota" in key for key in issue_keys):
        actions.append("쿼터/인원 제한 행인지 확인")
    if any("noise" in key for key in issue_keys):
        actions.append("목차/양식/페이지 노이즈 여부 확인 후 제거")
    if any("ocr" in key for key in issue_keys):
        actions.append("OCR 오타 사전 보정 후보에 추가")
    if any("missing_code" in key for key in issue_keys):
        actions.append("공통사항인지 코드 누락인지 확인")
    if any("duplicate" in key for key in issue_keys):
        actions.append("동일 의미 행 병합 또는 중복 제거 검토")
    if any("long_text" in key for key in issue_keys):
        actions.append("한 행에 여러 의미가 섞였는지 분할 검토")
    if any("short_text" in key for key in issue_keys):
        actions.append("맥락 없는 짧은 행인지 확인")
    return "; ".join(dict.fromkeys(actions)) or "행 내용을 확인"


def row_issues(row: pd.Series, manual_key: str, is_duplicate: bool) -> list[tuple[str, str, str]]:
    """Return quality issues for one CSV row.

    Each issue is a tuple of:

    - issue key: stable machine-readable reason
    - priority: high, medium, or low
    - Korean explanation: useful when reading the code or extending rules
    """
    config = MANUAL_CONFIGS[manual_key]
    code_col = config["code_col"]
    name_col = config["name_col"]
    text = " ".join(str(row.get(column, "")) for column in row.index)
    normalized = str(row.get("normalized_text", "")).strip()
    item_type = str(row.get("item_type", "")).strip()
    subsection = str(row.get("subsection_type", "")).strip()
    section_title = str(row.get("section_title", "")).strip()
    status_name = str(row.get(name_col, "")).strip()
    issues: list[tuple[str, str, str]] = []

    if not str(row.get(code_col, "")).strip() and item_type not in {"common_rule"} and status_name != "공통사항":
        issues.append(("missing_code_on_non_common_row", "high", "공통사항이 아닌 행에 코드가 비어 있음"))
    if not subsection:
        issues.append(("missing_subsection_type", "high", "subsection_type이 비어 있음"))
    if item_type == "required_documents" and not any(
        str(row.get(column, "")).strip()
        for column in ["common_documents", "mandatory_documents", "other_documents"]
    ):
        issues.append(("required_documents_without_document_bucket", "high", "제출서류 행인데 서류 버킷이 모두 비어 있음"))
    if item_type == "restriction" and not str(row.get("restrictions", "")).strip():
        issues.append(("restriction_without_restrictions", "high", "제한 행인데 restrictions가 비어 있음"))
    if item_type == "exception" and not str(row.get("exceptions", "")).strip():
        issues.append(("exception_without_exceptions", "high", "예외 행인데 exceptions가 비어 있음"))
    if item_type == "fee" and not str(row.get("fees", "")).strip():
        issues.append(("fee_without_fees", "high", "수수료 행인데 fees가 비어 있음"))
    if item_type == "score_table" and not any(
        str(row.get(column, "")).strip() for column in ["score_criteria", "table_rows"]
    ):
        issues.append(("score_table_without_score_or_table_rows", "high", "점수표 행인데 점수/표 필드가 비어 있음"))
    if item_type == "quota" and not any(
        str(row.get(column, "")).strip() for column in ["quota_or_limit", "table_rows"]
    ):
        issues.append(("quota_without_limit_or_table_rows", "high", "쿼터 행인데 제한/표 필드가 비어 있음"))
    if any(marker in text for marker in builder.FORM_ATTACHMENT_NOISE_MARKERS):
        issues.append(("form_attachment_noise", "high", "양식/붙임/표 병합 노이즈로 보임"))
    if (
        item_type not in {"required_documents", "exception"}
        and subsection not in {"추천/승인", "수수료"}
        and builder.looks_like_document_text(section_title, normalized or text)
    ):
        issues.append(("document_like_row_outside_required_documents", "high", "제출서류처럼 보이나 제출서류 행이 아님"))
    if item_type not in {"score_table", "required_documents"} and builder.looks_like_score_text(section_title, normalized or text):
        issues.append(("score_like_row_outside_score_table", "high", "점수표처럼 보이나 점수표 행이 아님"))
    if item_type == "quota" and builder.looks_like_score_text(section_title, normalized or text):
        issues.append(("score_like_quota_row", "high", "점수표 행이 쿼터로 분류된 것으로 보임"))
    if section_title in {"목차", "目 次", "次", "▶ 목차", "▣ 목차"}:
        issues.append(("noise_like_title", "high", "목차성 제목이 남아 있음"))
    if (
        "참조" not in text
        and any(marker in section_title for marker in ["안내매뉴얼", "안 내 매 뉴 얼"])
        and len(section_title) < 80
    ):
        issues.append(("manual_cover_or_title_noise", "high", "표지 또는 매뉴얼 제목 행으로 보임"))
    if any(term in text for term in SUSPICIOUS_TERMS):
        issues.append(("ocr_or_form_noise_suspect", "high", "OCR 오타 또는 양식 노이즈 의심어가 남아 있음"))
    if is_duplicate:
        issues.append(("duplicate_semantic_key", "medium", "코드/민원유형/소분류/제목/본문이 중복됨"))
    if subsection == "기타" and any(keyword in normalized for keyword in ["제출서류", "요건", "제한", "예외", "수수료"]):
        issues.append(("unclassified_keyword_in_misc_subsection", "medium", "기타로 분류됐지만 구조 키워드가 포함됨"))
    if normalized and len(normalized) < 25:
        issues.append(("short_text", "medium", "본문이 지나치게 짧음"))
    if len(normalized) > 1800:
        issues.append(("long_text", "low", "본문이 길어 행 분할 후보"))

    return issues


def duplicate_mask(df: pd.DataFrame, manual_key: str) -> pd.Series:
    code_col = MANUAL_CONFIGS[manual_key]["code_col"]
    key_columns = [code_col, "petition_type", "subsection_type", "section_title", "normalized_text"]
    present_columns = [column for column in key_columns if column in df.columns]
    return df.duplicated(subset=present_columns, keep=False) if present_columns else pd.Series(False, index=df.index)


def collect_review_candidates(df: pd.DataFrame, manual_key: str) -> pd.DataFrame:
    """Build the smaller table of rows that deserve human attention first."""
    dupes = duplicate_mask(df, manual_key)
    rows: list[dict[str, str]] = []
    code_col = MANUAL_CONFIGS[manual_key]["code_col"]
    name_col = MANUAL_CONFIGS[manual_key]["name_col"]
    ordered_source_columns = [
        code_col,
        name_col,
        *[column for column in CORE_REVIEW_COLUMNS if column in df.columns],
    ]

    for idx, row in df.iterrows():
        issues = row_issues(row, manual_key, bool(dupes.loc[idx]))
        if not issues:
            continue
        issue_keys = [key for key, _, _ in issues]
        out = {
            "source_row_number": str(idx + 2),
            "review_priority": priority_for(issues),
            "review_reason": "; ".join(issue_keys),
            "suggested_action": issue_actions(issue_keys),
        }
        for column in ordered_source_columns:
            out[column] = compact_text(row.get(column, ""), 1200)
        rows.append(out)

    output_columns = [
        *REVIEW_COLUMNS,
        *ordered_source_columns,
    ]
    return pd.DataFrame(rows, columns=output_columns)


def annotate_review_flags(df: pd.DataFrame, candidates: pd.DataFrame, manual_key: str) -> pd.DataFrame:
    """Return every source row with review columns inserted at the front."""
    annotated = df.copy()
    annotated.insert(0, "source_row_number", [str(i + 2) for i in range(len(annotated))])
    annotated.insert(1, "needs_review", "False")
    annotated.insert(2, "review_priority", "")
    annotated.insert(3, "review_reason", "")
    annotated.insert(4, "suggested_action", "")
    if candidates.empty:
        return annotated

    by_row = candidates.set_index("source_row_number")
    for idx, source_row_number in enumerate(annotated["source_row_number"]):
        if source_row_number not in by_row.index:
            continue
        candidate = by_row.loc[source_row_number]
        annotated.at[idx, "needs_review"] = "True"
        annotated.at[idx, "review_priority"] = candidate["review_priority"]
        annotated.at[idx, "review_reason"] = candidate["review_reason"]
        annotated.at[idx, "suggested_action"] = candidate["suggested_action"]
    return annotated


def field_fill_rates(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in df.columns:
        fill_count = int(filled(df[column]).sum())
        rows.append(
            {
                "field": column,
                "fill_count": fill_count,
                "row_count": len(df),
                "fill_rate": round(fill_count / len(df), 4) if len(df) else 0,
            }
        )
    return pd.DataFrame(rows).sort_values(["fill_rate", "field"], ascending=[True, True])


def value_counts_frame(df: pd.DataFrame, column: str, limit: int = 30) -> pd.DataFrame:
    if column not in df.columns:
        return pd.DataFrame(columns=[column, "count"])
    counts = df[column].replace("", "미분류").value_counts().head(limit)
    return counts.rename_axis(column).reset_index(name="count")


def build_quality_summary(df: pd.DataFrame, candidates: pd.DataFrame, manual_key: str) -> pd.DataFrame:
    fill_rates = field_fill_rates(df)
    candidate_rate = len(candidates) / len(df) if len(df) else 0
    priority_counts = candidates["review_priority"].value_counts().to_dict() if len(candidates) else {}
    lowest_fields = "; ".join(
        f"{row.field}:{row.fill_rate:.0%}" for row in fill_rates.itertuples(index=False)
    )
    metrics = [
        ("manual_key", manual_key),
        ("manual_label", MANUAL_CONFIGS[manual_key]["label"]),
        ("row_count", str(len(df))),
        ("column_count", str(len(df.columns))),
        ("review_candidate_count", str(len(candidates))),
        ("review_candidate_rate", f"{candidate_rate:.2%}"),
        ("high_priority_count", str(priority_counts.get("high", 0))),
        ("medium_priority_count", str(priority_counts.get("medium", 0))),
        ("low_priority_count", str(priority_counts.get("low", 0))),
        ("lowest_fill_rate_fields", lowest_fields),
    ]
    return pd.DataFrame(metrics, columns=["metric", "value"])


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def autosize_worksheet_columns(worksheet, max_width: int = 72) -> None:
    for column_cells in worksheet.columns:
        header = column_cells[0]
        max_length = max(
            len(str(cell.value or "")) for cell in column_cells[: min(len(column_cells), 300)]
        )
        worksheet.column_dimensions[header.column_letter].width = min(max(max_length + 2, 12), max_width)


def write_review_workbook(
    manual_key: str,
    df: pd.DataFrame,
    candidates: pd.DataFrame,
    summary: pd.DataFrame,
    fill_rates: pd.DataFrame,
) -> Path:
    """Write the Excel workbook used for nontechnical row-by-row review."""
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    path = REVIEW_DIR / f"{manual_key}_manual_review.xlsx"
    code_col = MANUAL_CONFIGS[manual_key]["code_col"]
    annotated = annotate_review_flags(df, candidates, manual_key)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        annotated.to_excel(writer, sheet_name="all_rows_with_flags", index=False)
        candidates.to_excel(writer, sheet_name="review_candidates", index=False)
        summary.to_excel(writer, sheet_name="summary", index=False)
        fill_rates.to_excel(writer, sheet_name="field_fill_rates", index=False)
        value_counts_frame(df, "item_type").to_excel(writer, sheet_name="item_type_counts", index=False)
        value_counts_frame(df, "subsection_type").to_excel(writer, sheet_name="subsection_counts", index=False)
        value_counts_frame(df, "petition_type").to_excel(writer, sheet_name="petition_counts", index=False)
        value_counts_frame(df, code_col).to_excel(writer, sheet_name="code_counts", index=False)

        for worksheet in writer.book.worksheets:
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            autosize_worksheet_columns(worksheet)

    return path


def markdown_report(summary_by_manual: dict[str, pd.DataFrame], output_paths: dict[str, dict[str, Path]]) -> str:
    lines = [
        "# Semantic Manual CSV Quality Report",
        "",
        "최종 semantic CSV를 사람이 검수하기 쉽게 자동 점검한 결과입니다.",
        "",
    ]
    for manual_key, summary in summary_by_manual.items():
        metrics = dict(zip(summary["metric"], summary["value"]))
        paths = output_paths[manual_key]
        lines.extend(
            [
                f"## {metrics['manual_label']} ({manual_key})",
                "",
                f"- rows: {metrics['row_count']}",
                f"- review candidates: {metrics['review_candidate_count']} ({metrics['review_candidate_rate']})",
                f"- high priority: {metrics['high_priority_count']}",
                f"- medium priority: {metrics['medium_priority_count']}",
                f"- low priority: {metrics['low_priority_count']}",
                f"- review workbook: `{paths['workbook'].relative_to(PROJECT_ROOT)}`",
                f"- candidate CSV: `{paths['candidates_csv'].relative_to(PROJECT_ROOT)}`",
                f"- summary CSV: `{paths['summary_csv'].relative_to(PROJECT_ROOT)}`",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def build_quality_outputs() -> dict[str, dict[str, Path]]:
    """Generate every quality CSV, workbook, and Markdown summary."""
    QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    output_paths: dict[str, dict[str, Path]] = {}
    summaries: dict[str, pd.DataFrame] = {}

    for manual_key in ["stay", "visa"]:
        df = load_manual_csv(manual_key)
        candidates = collect_review_candidates(df, manual_key)
        summary = build_quality_summary(df, candidates, manual_key)
        fill_rates = field_fill_rates(df)

        summary_csv = QUALITY_DIR / f"{manual_key}_manual_quality_summary.csv"
        fill_rates_csv = QUALITY_DIR / f"{manual_key}_manual_field_fill_rates.csv"
        candidates_csv = QUALITY_DIR / f"{manual_key}_manual_review_candidates.csv"
        write_csv(summary_csv, summary)
        write_csv(fill_rates_csv, fill_rates)
        write_csv(candidates_csv, candidates)
        workbook = write_review_workbook(manual_key, df, candidates, summary, fill_rates)

        summaries[manual_key] = summary
        output_paths[manual_key] = {
            "summary_csv": summary_csv,
            "field_fill_rates_csv": fill_rates_csv,
            "candidates_csv": candidates_csv,
            "workbook": workbook,
        }

    report_path = QUALITY_DIR / "semantic_manual_quality_report.md"
    report_path.write_text(markdown_report(summaries, output_paths), encoding="utf-8")
    for paths in output_paths.values():
        paths["report_md"] = report_path
    return output_paths


def main() -> None:
    outputs = build_quality_outputs()
    for manual_key, paths in outputs.items():
        print(f"{manual_key}:")
        for label, path in paths.items():
            print(f"  {label}: {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
