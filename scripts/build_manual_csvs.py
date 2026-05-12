#!/usr/bin/env python3
"""Parse the raw immigration manuals with LlamaParse and build clean CSVs.

The current contract is intentionally narrow:

- parse each raw PDF again with LlamaParse `agentic_plus`
- keep local markdown/metadata parse artifacts for traceability
- write exactly one clean CSV per PDF under data/processed
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from llama_cloud import LlamaCloud


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PARSED_DIR = PROJECT_ROOT / "data" / "parsed"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


MANUALS = {
    "stay": {
        "manual_type": "체류민원",
        "source_pdf": "260504 체류민원 자격별 안내 매뉴얼.pdf",
        "code_field": "stay_status_code",
        "name_field": "stay_status_name_ko",
        "output_csv": "stay_manual_clean.csv",
    },
    "visa": {
        "manual_type": "사증민원",
        "source_pdf": "260504 사증민원 자격별 안내 매뉴얼.pdf",
        "code_field": "visa_code",
        "name_field": "visa_name_ko",
        "output_csv": "visa_manual_clean.csv",
    },
}


CLEAN_COLUMNS = [
    "manual_type",
    "source_pdf",
    "parse_job_id",
    "parse_tier",
    "pdf_page_start",
    "pdf_page_end",
    "printed_page_start",
    "printed_page_end",
    "item_type",
    "section_title",
    "stay_status_code",
    "stay_status_name_ko",
    "visa_code",
    "visa_name_ko",
    "subtype_or_program",
    "petition_type",
    "subsection_type",
    "applicant_context",
    "eligibility",
    "requirements",
    "required_documents",
    "procedure",
    "restrictions",
    "exceptions",
    "obligations",
    "duration_or_validity",
    "fees",
    "quota_or_limit",
    "score_criteria",
    "table_count",
    "evidence_quote",
    "normalized_text",
    "source_raw_text",
    "needs_human_review",
    "review_notes",
    "extraction_method",
]


CODE_RE = re.compile(r"\b[A-Z]-\d{1,2}(?:-\d{1,2})?[A-Z]?\b")
PRINTED_PAGE_RE = re.compile(r"[-–]\s*(\d{1,4})\s*[-–]")
HEADING_RE = re.compile(r"(?m)^(#{1,6})\s+(.+?)\s*$")
HTML_TABLE_RE = re.compile(r"<table[\s\S]*?</table>", re.IGNORECASE)
MD_TABLE_BLOCK_RE = re.compile(
    r"(?m)(?:^\|.+\|\s*$\n^\|[\s:\-|]+\|\s*$\n(?:^\|.*\|\s*$\n?)+)"
)

PETITION_PATTERNS = [
    "체류자격외 활동허가",
    "근무처 변경",
    "근무처 추가",
    "체류자격 부여",
    "체류자격 변경",
    "체류기간 연장",
    "재입국허가",
    "외국인등록",
    "거소신고",
    "체류지 변경",
    "사증발급인정서",
    "사증발급",
    "비자발급",
    "초청",
]

SUBSECTION_PATTERNS = [
    ("제출서류", ["제출서류", "첨부서류", "구비서류", "신청서류"]),
    ("대상", ["대상", "적용대상", "신청대상", "해당자"]),
    ("요건", ["요건", "자격요건", "심사기준", "기준"]),
    ("절차", ["절차", "신청방법", "방법", "처리절차"]),
    ("제한", ["제한", "불허", "제외", "금지", "결격"]),
    ("예외", ["예외", "특례", "면제", "완화"]),
    ("신고의무", ["신고의무", "제출 의무", "교육의무", "거주의무"]),
    ("수수료", ["수수료"]),
    ("체류기간", ["체류기간", "허가기간", "유효기간"]),
    ("점수표", ["점수표", "배점", "점수"]),
    ("쿼터", ["쿼터", "선발인원", "허용인원", "상한"]),
    ("표", ["<table", "| ---", "|---"]),
]

ITEM_KEYWORDS = [
    ("fee", ["수수료"]),
    ("score_table", ["점수표", "배점"]),
    ("quota", ["쿼터", "선발인원", "허용인원", "상한"]),
    ("required_documents", ["제출서류", "첨부서류", "구비서류", "신청서류"]),
    ("reporting_obligation", ["신고의무", "제출 의무", "교육의무", "거주의무"]),
    ("employment_rule", ["근무처", "고용", "취업", "직업"]),
    ("family_rule", ["동반가족", "배우자", "자녀", "초청"]),
    ("procedure", ["절차", "신청방법", "온라인 접수", "하이코리아"]),
    ("restriction", ["제한", "불허", "제외", "금지", "결격"]),
    ("exception", ["예외", "특례", "면제", "완화"]),
]

FIELD_KEYWORDS = {
    "eligibility": ["대상", "적용대상", "신청대상", "해당자"],
    "requirements": ["요건", "자격요건", "심사기준", "기준", "소득", "학력", "경력"],
    "required_documents": ["제출서류", "첨부서류", "구비서류", "신청서류"],
    "procedure": ["절차", "신청방법", "방법", "접수", "하이코리아"],
    "restrictions": ["제한", "불허", "제외", "금지", "결격"],
    "exceptions": ["예외", "특례", "면제", "완화"],
    "obligations": ["신고의무", "제출 의무", "교육의무", "거주의무", "준수"],
    "duration_or_validity": ["체류기간", "허가기간", "유효기간", "연장기간"],
    "fees": ["수수료", "만원", "천원"],
    "quota_or_limit": ["쿼터", "선발인원", "허용인원", "상한", "최대"],
    "score_criteria": ["점수표", "배점", "점수"],
}


@dataclass
class Page:
    page_number: int
    markdown: str
    success: bool


def clean_text(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text or "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compact_line(text: str, max_chars: int = 420) -> str:
    line = re.sub(r"\s+", " ", text or "").strip()
    return line[: max_chars - 1] + "..." if len(line) > max_chars else line


def unique_join(values: list[str], sep: str = " | ") -> str:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        value = compact_line(value, 700)
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return sep.join(out)


def strip_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text or "")
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`#>|]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def markdown_to_plain(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    text = re.sub(r"</?u\s*", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"</?mark\s*", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?\s*>?", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(td|th|tr|p|li|div|h[1-6])>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    plain_lines: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)
        line = re.sub(r"^\s*[-*+]\s+", "- ", line)
        line = re.sub(r"^\s*>+\s*", "", line)
        line = re.sub(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$", "", line)
        line = line.replace("|", " / ")
        line = re.sub(r"[*_`~]", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            plain_lines.append(line)
    return "\n".join(plain_lines).strip()


def clean_delimited_field(text: str) -> str:
    parts = re.split(r"\s+\|\s+", text or "")
    cleaned = [markdown_to_plain(part) for part in parts]
    return unique_join([part for part in cleaned if part], sep="; ")


def first_heading(markdown: str) -> str:
    match = HEADING_RE.search(markdown or "")
    if match:
        return compact_line(strip_markdown(match.group(2)), 240)
    for line in (markdown or "").splitlines():
        plain = compact_line(strip_markdown(line), 240)
        if plain:
            return plain
    return ""


def detect_printed_page(markdown: str) -> str:
    matches = PRINTED_PAGE_RE.findall(markdown or "")
    return matches[-1] if matches else ""


def detect_codes(text: str) -> list[str]:
    return sorted(set(CODE_RE.findall(text or "")))


def detect_code_and_name(text: str) -> tuple[str, str]:
    code_match = CODE_RE.search(text or "")
    if not code_match:
        return "", ""
    code = code_match.group(0)
    prefix = text[max(0, code_match.start() - 30) : code_match.start()]
    name_match = re.search(r"([가-힣A-Za-zㆍ·\s]{2,20})\($", prefix)
    if name_match:
        return code, compact_line(name_match.group(1), 80)
    inline = re.search(rf"([가-힣A-Za-zㆍ·\s]{{2,20}})\({re.escape(code)}\)", text)
    if inline:
        return code, compact_line(inline.group(1), 80)
    return code, ""


def detect_subtype_or_program(text: str) -> str:
    programs = [
        "지역우수인재",
        "지역특화형",
        "광역형 비자",
        "K-STAR",
        "Top-Tier",
        "탑티어",
        "숙련기능인력",
        "K-point E74",
        "네거티브 방식",
        "동반가족",
        "외국국적동포",
    ]
    lower_text = text.lower()
    return unique_join([program for program in programs if program.lower() in lower_text])


def detect_petition_type(text: str) -> str:
    return unique_join([pattern for pattern in PETITION_PATTERNS if pattern in text])


def detect_subsection_type(text: str) -> str:
    found: list[str] = []
    for label, keywords in SUBSECTION_PATTERNS:
        if any(keyword in text for keyword in keywords):
            found.append(label)
    return unique_join(found)


def detect_item_type(text: str, manual_key: str) -> str:
    found = [label for label, keys in ITEM_KEYWORDS if any(key in text for key in keys)]
    if found:
        return found[0]
    if detect_codes(text):
        return "stay_status_rule" if manual_key == "stay" else "visa_rule"
    return "common_rule"


def extract_keyword_lines(text: str, keywords: list[str], max_lines: int = 12) -> list[str]:
    lines = [strip_markdown(line) for line in (text or "").splitlines()]
    lines = [line for line in lines if line]
    selected: list[str] = []
    for i, line in enumerate(lines):
        if any(keyword in line for keyword in keywords):
            selected.append(line)
            for next_line in lines[i + 1 : i + 4]:
                if len(selected) >= max_lines:
                    break
                if next_line.startswith(("①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "-", "•", "◦", "❍")):
                    selected.append(next_line)
    return selected[:max_lines]


def evidence_quote(text: str) -> str:
    for line in (text or "").splitlines():
        plain = strip_markdown(line)
        if len(plain) >= 25 and not plain.startswith("|"):
            return compact_line(plain, 300)
    return compact_line(strip_markdown(text), 300)


def find_tables(markdown: str) -> list[tuple[str, str]]:
    tables: list[tuple[str, str]] = []
    for match in HTML_TABLE_RE.finditer(markdown or ""):
        tables.append(("html", match.group(0).strip()))
    for match in MD_TABLE_BLOCK_RE.finditer(markdown or ""):
        tables.append(("markdown", match.group(0).strip()))
    return tables


def split_chunks(page: Page) -> list[tuple[str, str]]:
    markdown = clean_text(page.markdown)
    if not markdown:
        return []

    matches = list(HEADING_RE.finditer(markdown))
    if not matches:
        return [(first_heading(markdown), markdown)]

    chunks: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        prefix = markdown[: matches[0].start()].strip()
        if prefix:
            chunks.append((first_heading(prefix), prefix))

    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        title = strip_markdown(match.group(2))
        chunk = markdown[start:end].strip()
        if chunk:
            chunks.append((title, chunk))

    merged: list[tuple[str, str]] = []
    for title, chunk in chunks:
        if merged and len(strip_markdown(chunk)) < 160:
            prev_title, prev_chunk = merged[-1]
            merged[-1] = (prev_title, prev_chunk + "\n\n" + chunk)
        else:
            merged.append((title, chunk))
    return merged


def to_plain_dict(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    return value


def parse_job_id(result: Any) -> str:
    job = getattr(result, "job", None)
    for attr in ("id", "job_id"):
        value = getattr(job, attr, None)
        if value:
            return str(value)
    value = getattr(result, "id", None)
    return str(value or "")


def parse_tier(result: Any, requested_tier: str) -> str:
    job = getattr(result, "job", None)
    return str(getattr(job, "tier", None) or requested_tier)


def pages_from_result(result: Any) -> list[Page]:
    pages: list[Page] = []
    markdown = getattr(result, "markdown", None)
    for page in getattr(markdown, "pages", []) or []:
        pages.append(
            Page(
                page_number=int(getattr(page, "page_number", len(pages) + 1)),
                markdown=getattr(page, "markdown", None) or getattr(page, "text", "") or "",
                success=bool(getattr(page, "success", True)),
            )
        )
    return pages


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CLEAN_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in CLEAN_COLUMNS})


def save_parse_artifacts(
    manual_key: str,
    manual: dict[str, str],
    result: Any,
    pages: list[Page],
    tier: str,
) -> None:
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    job_id = parse_job_id(result)
    stem = f"{manual_key}_manual_llamaparse_{tier}_{job_id or 'unknown_job'}"

    metadata = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "manual_type": manual["manual_type"],
        "source_pdf": manual["source_pdf"],
        "parse_job_id": job_id,
        "parse_tier": parse_tier(result, tier),
        "job": to_plain_dict(getattr(result, "job", {})),
        "job_metadata": to_plain_dict(getattr(result, "job_metadata", {})),
    }
    (PARSED_DIR / f"{stem}.metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (PARSED_DIR / f"{stem}.md").open("w", encoding="utf-8") as f:
        for page in pages:
            f.write(f"\n\n<!-- PDF_PAGE:{page.page_number} SUCCESS:{page.success} -->\n\n")
            f.write(page.markdown.strip())
            f.write("\n")


def build_rows(
    manual_key: str,
    manual: dict[str, str],
    result: Any,
    pages: list[Page],
    requested_tier: str,
) -> list[dict[str, Any]]:
    job_id = parse_job_id(result)
    tier = parse_tier(result, requested_tier)
    rows: list[dict[str, Any]] = []

    for page in pages:
        page_md = clean_text(page.markdown)
        printed_page = detect_printed_page(page_md)
        page_heading = first_heading(page_md)

        for chunk_title, chunk in split_chunks(page):
            plain = strip_markdown(chunk)
            if len(plain) < 40:
                continue

            code, name = detect_code_and_name(chunk_title + "\n" + chunk[:1200])
            tables = find_tables(chunk)
            review_notes: list[str] = []
            if tables:
                review_notes.append("표 포함: 열/행 의미 검수 필요")
            if len(detect_codes(chunk)) > 3:
                review_notes.append("복수 코드 포함: 코드-규칙 연결 검수 필요")
            if not page.success:
                review_notes.append("LlamaParse page_success=false")
            if len(plain) > 6000:
                review_notes.append("긴 섹션: 필요 시 더 작은 RAG 단위로 수동 분할")

            row = {
                "manual_type": manual["manual_type"],
                "source_pdf": manual["source_pdf"],
                "parse_job_id": job_id,
                "parse_tier": tier,
                "pdf_page_start": page.page_number,
                "pdf_page_end": page.page_number,
                "printed_page_start": printed_page,
                "printed_page_end": printed_page,
                "item_type": detect_item_type(chunk, manual_key),
                "section_title": clean_delimited_field(compact_line(chunk_title or page_heading, 240)),
                "stay_status_code": code if manual_key == "stay" else "",
                "stay_status_name_ko": clean_delimited_field(name if manual_key == "stay" else ""),
                "visa_code": code if manual_key == "visa" else "",
                "visa_name_ko": clean_delimited_field(name if manual_key == "visa" else ""),
                "subtype_or_program": clean_delimited_field(detect_subtype_or_program(chunk)),
                "petition_type": clean_delimited_field(detect_petition_type(chunk)),
                "subsection_type": clean_delimited_field(detect_subsection_type(chunk)),
                "applicant_context": "",
                "eligibility": clean_delimited_field(unique_join(extract_keyword_lines(chunk, FIELD_KEYWORDS["eligibility"]))),
                "requirements": clean_delimited_field(unique_join(extract_keyword_lines(chunk, FIELD_KEYWORDS["requirements"]))),
                "required_documents": clean_delimited_field(unique_join(extract_keyword_lines(chunk, FIELD_KEYWORDS["required_documents"]))),
                "procedure": clean_delimited_field(unique_join(extract_keyword_lines(chunk, FIELD_KEYWORDS["procedure"]))),
                "restrictions": clean_delimited_field(unique_join(extract_keyword_lines(chunk, FIELD_KEYWORDS["restrictions"]))),
                "exceptions": clean_delimited_field(unique_join(extract_keyword_lines(chunk, FIELD_KEYWORDS["exceptions"]))),
                "obligations": clean_delimited_field(unique_join(extract_keyword_lines(chunk, FIELD_KEYWORDS["obligations"]))),
                "duration_or_validity": clean_delimited_field(unique_join(extract_keyword_lines(chunk, FIELD_KEYWORDS["duration_or_validity"]))),
                "fees": clean_delimited_field(unique_join(extract_keyword_lines(chunk, FIELD_KEYWORDS["fees"]))),
                "quota_or_limit": clean_delimited_field(unique_join(extract_keyword_lines(chunk, FIELD_KEYWORDS["quota_or_limit"]))),
                "score_criteria": clean_delimited_field(unique_join(extract_keyword_lines(chunk, FIELD_KEYWORDS["score_criteria"]))),
                "table_count": len(tables),
                "evidence_quote": markdown_to_plain(evidence_quote(chunk)),
                "normalized_text": markdown_to_plain(chunk),
                "source_raw_text": chunk,
                "needs_human_review": "true" if review_notes else "false",
                "review_notes": clean_delimited_field(unique_join(review_notes)),
                "extraction_method": "llamaparse_agentic_plus_markdown_conservative_regex",
            }
            rows.append(row)

    return rows


def parse_manual(client: LlamaCloud, manual_key: str, manual: dict[str, str], tier: str) -> dict[str, Any]:
    pdf_path = RAW_DIR / manual["source_pdf"]
    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing source PDF: {pdf_path}")

    print(f"uploading: {pdf_path.name}")
    uploaded_file = client.files.create(file=str(pdf_path), purpose="parse")

    print(f"parsing: {pdf_path.name} / tier={tier}")
    result = client.parsing.parse(
        file_id=uploaded_file.id,
        tier=tier,  # type: ignore[arg-type]
        version="latest",
        disable_cache=True,
        expand=["markdown", "job_metadata"],
        output_options={
            "markdown": {
                "tables": {"output_tables_as_markdown": True},
            },
        },
        timeout=7200,
        verbose=True,
    )

    pages = pages_from_result(result)
    if not pages:
        raise RuntimeError(f"No markdown pages returned for {manual_key}")

    save_parse_artifacts(manual_key, manual, result, pages, tier)
    rows = build_rows(manual_key, manual, result, pages, tier)
    output_path = PROCESSED_DIR / manual["output_csv"]
    write_csv(output_path, rows)

    return {
        "manual_key": manual_key,
        "source_pdf": manual["source_pdf"],
        "output_csv": str(output_path.relative_to(PROJECT_ROOT)),
        "parse_job_id": parse_job_id(result),
        "parse_tier": parse_tier(result, tier),
        "pages": len(pages),
        "rows": len(rows),
        "page_success_false": sum(1 for page in pages if not page.success),
        "needs_human_review_rows": sum(1 for row in rows if row["needs_human_review"] == "true"),
    }


def remove_existing_processed_outputs(selected: list[str]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    if set(selected) == set(MANUALS):
        for path in PROCESSED_DIR.glob("*.csv"):
            path.unlink()
    else:
        for key in selected:
            for path in PROCESSED_DIR.glob(f"{key}_manual*.csv"):
                path.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual", choices=["stay", "visa", "all"], default="all")
    parser.add_argument("--tier", default="agentic_plus", choices=["fast", "cost_effective", "agentic", "agentic_plus"])
    parser.add_argument(
        "--keep-existing-csv",
        action="store_true",
        help="Do not delete old data/processed CSV files before writing the requested outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    if not os.getenv("LLAMA_CLOUD_API_KEY") and not os.getenv("LLAMA_PARSE_API_KEY"):
        raise RuntimeError("LLAMA_CLOUD_API_KEY 또는 LLAMA_PARSE_API_KEY가 필요합니다.")

    selected = ["stay", "visa"] if args.manual == "all" else [args.manual]
    if not args.keep_existing_csv:
        remove_existing_processed_outputs(selected)

    client = LlamaCloud()
    summary = [parse_manual(client, key, MANUALS[key], args.tier) for key in selected]

    (PROCESSED_DIR / "build_summary.json").write_text(
        json.dumps(
            {
                "built_at": datetime.now(timezone.utc).isoformat(),
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
