#!/usr/bin/env python3
"""Stage 6 — 사람 검수용 한국어 CSV 빌더.

`data/parsed/normalized/{stay,visa}_manual.md`(정규화 중간 산출물)을 읽어
`data/processed/{체류,사증}매뉴얼_검수용.csv` 두 파일을 생성합니다.

이 단계는 LLM 없이 결정적으로 동작합니다. 정규화 MD의 한 `### row` 블록이
검수용 CSV 한 행이 됩니다.

출력 컬럼 (7개, 한국어):
    비자코드, 사증·체류, 문서유형, 핵심내용, 제출서류, 예상질문, 출처

기존의 27개 세분화 컬럼은 다음과 같이 통합/한국어화됩니다:
    비자코드   ← stay_status_code 또는 visa_code (+subtype_or_program)
    사증·체류  ← manual_type을 "체류"/"사증"으로 축약
    문서유형   ← petition_type / subsection_type
    핵심내용   ← applicant_context~obligations 등 내용 필드를 라벨링해 통합
    제출서류   ← common_documents + mandatory_documents + other_documents
    예상질문   ← expected_questions (정규화 스킬이 LLM으로 생성)
    출처       ← section_title | source_pdf

용법:
    .venv/bin/python scripts/build_semantic_csv.py
    .venv/bin/python scripts/build_semantic_csv.py stay
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NORMALIZED_DIR = PROJECT_ROOT / "data" / "parsed" / "normalized"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


OPEN_MARKER_RE = re.compile(
    r"<!--\s*vizabridge-normalize v1 chunk:\s*([^\s]+)\s+hash:\s*([^\s]+)\s+lines:\s*(\d+)-(\d+)\s*-->"
)
CLOSE_MARKER_RE = re.compile(r"<!--\s*end chunk:\s*([^\s]+)\s*-->")
ROW_HEADER_RE = re.compile(r"^###\s+row\s+.*$", re.MULTILINE)
FIELD_LINE_RE = re.compile(r"^-\s+([a-z_]+):\s*(.*)$", re.MULTILINE)
MULTILINE_VALUE_START_RE = re.compile(r"^-\s+([a-z_]+):\s*\|\s*$")


SOURCE_PDF = {
    "stay": "260504 체류민원 자격별 안내 매뉴얼.hwp",
    "visa": "260504 사증민원 자격별 안내 매뉴얼.hwp",
}

OUTPUT_FILENAME = {
    "stay": "체류매뉴얼_검수용.csv",
    "visa": "사증매뉴얼_검수용.csv",
}

OUTPUT_COLUMNS = [
    "비자코드",
    "사증·체류",
    "문서유형",
    "핵심내용",
    "제출서류",
    "예상질문",
    "출처",
]

# QC 도구(quality_report)가 소비하는 중간 산출물.
# 1차 검수 단계에서는 사용자 대상이 아닙니다.
INTERMEDIATE_COMMON = [
    "manual_type",
    "source_pdf",
    "item_type",
    "section_title",
    "subtype_or_program",
    "petition_type",
    "subsection_type",
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
    "expected_questions",
]
INTERMEDIATE_STAY = ["stay_status_code", "stay_status_name_ko", *INTERMEDIATE_COMMON, "obligations"]
INTERMEDIATE_VISA = ["visa_code", "visa_name_ko", *INTERMEDIATE_COMMON, "inviter_context", "recommendation_or_approval"]
INTERMEDIATE_SCHEMA = {"stay": INTERMEDIATE_STAY, "visa": INTERMEDIATE_VISA}
INTERMEDIATE_FILENAME = {
    "stay": "stay_manual_semantic_clean.csv",
    "visa": "visa_manual_semantic_clean.csv",
}


# 핵심내용에 들어갈 필드와 한국어 라벨 (출현 순서대로)
CONTENT_FIELDS = [
    ("applicant_context", "신청 상황"),
    ("target_persons", "대상자"),
    ("eligibility", "자격요건"),
    ("requirements", "요건"),
    ("procedure", "절차"),
    ("duration_or_validity", "체류기간/유효기간"),
    ("fees", "수수료"),
    ("restrictions", "제한"),
    ("exceptions", "예외"),
    ("quota_or_limit", "쿼터/허용인원"),
    ("score_criteria", "점수표"),
    ("obligations", "의무사항"),
    ("inviter_context", "초청자"),
    ("recommendation_or_approval", "추천/승인기관"),
    ("table_summary", "표 요약"),
    ("table_rows", "표 항목"),
]

# 제출서류에 들어갈 필드
DOCUMENT_FIELDS = [
    ("common_documents", "공통서류"),
    ("mandatory_documents", "필수서류"),
    ("other_documents", "기타서류"),
]


def parse_row_body(body: str) -> dict[str, str]:
    """`- field: value` 라인과 `- field: |` 멀티라인 블록을 파싱."""
    fields: dict[str, str] = {}
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        multi = MULTILINE_VALUE_START_RE.match(line)
        if multi:
            name = multi.group(1)
            collected: list[str] = []
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.startswith("    "):
                    collected.append(nxt[4:])
                    i += 1
                elif nxt.strip() == "" and i + 1 < len(lines) and lines[i + 1].startswith("    "):
                    collected.append("")
                    i += 1
                else:
                    break
            fields[name] = "\n".join(collected).rstrip()
            continue
        single = FIELD_LINE_RE.match(line)
        if single:
            fields[single.group(1)] = single.group(2).strip()
        i += 1
    return fields


def iter_row_blocks(normalized_text: str):
    """청크 마커 안의 모든 `### row` 블록을 (chunk_id, body)로 yield."""
    opens = list(OPEN_MARKER_RE.finditer(normalized_text))
    close_by_id = {m.group(1): m for m in CLOSE_MARKER_RE.finditer(normalized_text)}
    for open_m in opens:
        chunk_id = open_m.group(1)
        close_m = close_by_id.get(chunk_id)
        if not close_m or close_m.start() < open_m.end():
            continue
        chunk_body = normalized_text[open_m.end() : close_m.start()]
        positions = [m.start() for m in ROW_HEADER_RE.finditer(chunk_body)]
        if not positions:
            continue
        positions.append(len(chunk_body))
        for i in range(len(positions) - 1):
            row_text = chunk_body[positions[i] : positions[i + 1]]
            row_lines = row_text.splitlines()
            yield chunk_id, "\n".join(row_lines[1:])


def code_with_subtype(fields: dict[str, str], manual_key: str) -> str:
    code_field = "stay_status_code" if manual_key == "stay" else "visa_code"
    code = fields.get(code_field, "").strip()
    subtype = fields.get("subtype_or_program", "").strip()
    if subtype and subtype != code:
        return f"{code} ({subtype})" if code else subtype
    return code


def manual_label(manual_type: str) -> str:
    """`체류민원`/`사증민원` → `체류`/`사증` 축약."""
    if "체류" in manual_type:
        return "체류"
    if "사증" in manual_type:
        return "사증"
    return manual_type


def document_type(fields: dict[str, str]) -> str:
    petition = fields.get("petition_type", "").strip()
    subsection = fields.get("subsection_type", "").strip()
    if petition and subsection:
        return f"{petition} / {subsection}"
    return petition or subsection


def join_labeled(fields: dict[str, str], spec: list[tuple[str, str]]) -> str:
    """spec에 명시된 필드 중 비어있지 않은 값을 [라벨] 본문 형식으로 합침."""
    parts: list[str] = []
    for key, label in spec:
        value = fields.get(key, "").strip()
        if not value:
            continue
        # 라벨 + 본문. 본문이 여러 줄이면 그대로 보존.
        parts.append(f"[{label}]\n{value}")
    return "\n\n".join(parts)


def source_text(fields: dict[str, str], manual_key: str) -> str:
    section = fields.get("section_title", "").strip()
    pdf = fields.get("source_pdf", "").strip() or SOURCE_PDF[manual_key]
    if section:
        return f"{section} | {pdf}"
    return pdf


def to_review_row(fields: dict[str, str], manual_key: str) -> dict[str, str]:
    return {
        "비자코드": code_with_subtype(fields, manual_key),
        "사증·체류": manual_label(
            fields.get("manual_type")
            or ("체류민원" if manual_key == "stay" else "사증민원")
        ),
        "문서유형": document_type(fields),
        "핵심내용": join_labeled(fields, CONTENT_FIELDS),
        "제출서류": join_labeled(fields, DOCUMENT_FIELDS),
        "예상질문": fields.get("expected_questions", "").strip(),
        "출처": source_text(fields, manual_key),
    }


def build_csv(manual_key: str) -> tuple[Path, int]:
    norm_path = NORMALIZED_DIR / f"{manual_key}_manual.md"
    if not norm_path.exists():
        raise SystemExit(f"정규화 출력 없음: {norm_path}")
    text = norm_path.read_text(encoding="utf-8")

    review_rows: list[dict[str, str]] = []
    raw_rows: list[dict[str, str]] = []
    for _chunk_id, body in iter_row_blocks(text):
        fields = parse_row_body(body)
        fields.setdefault("source_pdf", SOURCE_PDF[manual_key])
        fields.setdefault(
            "manual_type", "체류민원" if manual_key == "stay" else "사증민원"
        )
        raw_rows.append(fields)
        review_rows.append(to_review_row(fields, manual_key))

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # 1차 정리 CSV — 한국어, 사람 검수용
    out_path = PROCESSED_DIR / OUTPUT_FILENAME[manual_key]
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        # utf-8-sig: Excel에서 한글 깨짐 방지
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(review_rows)

    # 중간 산출물 — QC 도구(quality_report)용
    intermediate_path = PROCESSED_DIR / INTERMEDIATE_FILENAME[manual_key]
    schema = INTERMEDIATE_SCHEMA[manual_key]
    with intermediate_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=schema, extrasaction="ignore")
        writer.writeheader()
        for row in raw_rows:
            writer.writerow({col: row.get(col, "") for col in schema})

    return out_path, len(review_rows)


def main() -> int:
    args = sys.argv[1:]
    manuals = args if args else ["stay", "visa"]
    for manual_key in manuals:
        if manual_key not in OUTPUT_FILENAME:
            raise SystemExit(f"unknown manual_key: {manual_key}")
        try:
            out_path, n = build_csv(manual_key)
        except SystemExit as e:
            print(f"  {manual_key}: skipped ({e})")
            continue
        print(f"  {manual_key}: {n}행 → {out_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
