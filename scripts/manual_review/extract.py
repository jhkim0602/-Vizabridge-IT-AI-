from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .schema import (
    BASE_CODE_NAMES,
    MANUALS,
    PARSED_DIR,
    PETITION_KEYWORDS,
    RAW_DIR,
    SUBSECTION_KEYWORDS,
    empty_item,
)


CODE_RE = re.compile(r"\b[A-Z]-\d{1,2}(?:-[A-Z]?\d{1,2}[A-Z]?|-[A-Z])?[A-Z]?\b")
SPACED_CODE_RE = re.compile(r"\b([A-Z])\s*-\s*(\d{1,2})(?:\s*-\s*([A-Z]?\d{1,2}[A-Z]?|[A-Z]))?([A-Z]?)\b")
PRINTED_PAGE_RE = re.compile(r"[-–]\s*(\d{1,4})\s*[-–]")
NUMBERED_HEADING_RE = re.compile(r"^\s*(?:\d{1,2}|[가-하])[\).]?\s+\S")
CODE_HEADING_RE = re.compile(r"^\s*[가-힣A-Za-zㆍ· ]{1,24}\([A-Z]\s*-\s*\d")
MARKDOWN_PAGE_RE = re.compile(r"<!--\s*PDF_PAGE:(\d+)\s+SUCCESS:(True|False)\s*-->")


@dataclass
class Block:
    title: str
    text: str


def normalize_code_text(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        code = f"{match.group(1)}-{match.group(2)}"
        if match.group(3):
            code = f"{code}-{match.group(3)}"
        return f"{code}{match.group(4) or ''}"

    return SPACED_CODE_RE.sub(repl, text or "")


def compact(text: str, max_chars: int = 1200) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"


def detect_codes(text: str) -> list[str]:
    codes: list[str] = []
    for code in CODE_RE.findall(normalize_code_text(text)):
        if code not in codes:
            codes.append(code)
    return codes


def base_code(code: str) -> str:
    parts = (code or "").split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else code


def code_name(code: str) -> str:
    return BASE_CODE_NAMES.get(base_code(code), "")


def normalize_korean_name(text: str, code: str) -> str:
    name = code_name(code)
    if name:
        return name
    match = re.search(r"([가-힣ㆍ· ]{2,24})\(\s*" + re.escape(code).replace(r"\-", r"\s*-\s*") + r"\s*\)", text)
    return re.sub(r"\s+", "", match.group(1)) if match else ""


def is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if NUMBERED_HEADING_RE.match(stripped):
        return True
    if CODE_HEADING_RE.match(stripped):
        return True
    if stripped.startswith(("▣", "□", "■", "▶")) and len(stripped) < 90:
        return True
    if any(keyword in stripped for keyword in ["첨부서류", "제출서류", "사증발급인정서", "근무처의 변경", "체류자격 변경"]):
        return len(stripped) < 110
    return False


def split_page_blocks(text: str) -> list[Block]:
    lines = [line.rstrip() for line in (text or "").splitlines()]
    blocks: list[Block] = []
    title = ""
    buf: list[str] = []

    def flush() -> None:
        nonlocal title, buf
        raw = "\n".join(line for line in buf if line.strip()).strip()
        if raw:
            blocks.append(Block(title=title or raw.splitlines()[0].strip(), text=raw))
        title = ""
        buf = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if is_heading(stripped) and buf:
            flush()
        if not buf:
            title = stripped
        buf.append(stripped)
    flush()
    return blocks


def first_evidence_line(text: str) -> str:
    for line in (text or "").splitlines():
        line = compact(line, 240)
        if len(line) >= 8 and not PRINTED_PAGE_RE.fullmatch(line):
            return line
    return compact(text, 240)


def extract_documents(text: str) -> str:
    if not any(keyword in text for keyword in ["첨부서류", "제출서류", "구비서류", "신청서류", "사증발급신청서", "여권"]):
        return ""
    lines = [compact(line, 400) for line in text.splitlines() if line.strip()]
    selected = [line for line in lines if any(keyword in line for keyword in ["서류", "신청서", "여권", "사진", "수수료", "증명서", "추천서", "계약서", "사업자등록증"])]
    return "; ".join(dict.fromkeys(selected[:8]))


def classify_text(text: str, manual_key: str) -> dict[str, str]:
    result = {
        "item_type": "stay_status_rule" if manual_key == "stay" else "visa_rule",
        "subsection_type": "기타",
        "petition_type": "",
    }
    haystack = compact(text, 3000)
    for subsection, keywords in SUBSECTION_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            result["subsection_type"] = subsection
            break

    if result["subsection_type"] == "수수료":
        result["item_type"] = "fee"
    elif result["subsection_type"] == "점수표":
        result["item_type"] = "score_table"
    elif result["subsection_type"] == "쿼터":
        result["item_type"] = "quota"
    elif result["subsection_type"] == "제출서류":
        result["item_type"] = "required_documents"
    elif result["subsection_type"] == "제한":
        result["item_type"] = "restriction"
    elif result["subsection_type"] == "예외":
        result["item_type"] = "exception"
    elif "공통" in haystack[:120] or "유 의 사 항" in haystack[:120]:
        result["item_type"] = "common_rule"

    for petition, keywords in PETITION_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            result["petition_type"] = petition
            break
    if manual_key == "visa" and not result["petition_type"]:
        result["petition_type"] = "사증발급"
    return result


def assign_content_fields(item: dict[str, str], text: str) -> None:
    subsection = item["subsection_type"]
    docs = extract_documents(text)
    if docs:
        item["required_documents"] = docs
    if subsection == "대상":
        item["eligibility"] = compact(text)
    elif subsection == "요건":
        item["requirements"] = compact(text)
    elif subsection == "절차":
        item["procedure"] = compact(text)
    elif subsection == "제한":
        item["restrictions"] = compact(text)
    elif subsection == "예외":
        item["exceptions"] = compact(text)
    elif subsection == "신고의무":
        item["obligations"] = compact(text)
    elif subsection == "수수료":
        item["fees"] = compact(text)
    elif subsection == "쿼터":
        item["quota_or_limit"] = compact(text)
    elif subsection == "점수표":
        item["score_criteria"] = compact(text)
    if any(word in text for word in ["체류기간", "유효기간", "단수사증", "복수사증"]):
        item["duration_or_validity"] = compact(text)
    if any(word in text for word in ["추천서", "고용추천", "관계기관", "승인"]):
        item["recommendation_or_approval"] = compact(text)


def item_from_block(manual_key: str, page_no: int, title: str, text: str, sequence: int) -> dict[str, str]:
    meta = MANUALS[manual_key]
    normalized = normalize_code_text(text)
    item = empty_item()
    item["item_id"] = f"{meta['id_prefix']}-{sequence:06d}"
    item["manual_type"] = meta["manual_type"]
    item["source_pdf"] = meta["source_pdf"]
    item["pdf_page_start"] = str(page_no)
    item["pdf_page_end"] = str(page_no)
    printed_pages = PRINTED_PAGE_RE.findall(text)
    if printed_pages:
        item["printed_page_start"] = printed_pages[-1]
        item["printed_page_end"] = printed_pages[-1]
    item["section_title"] = compact(normalize_code_text(title), 240)
    item["section_path"] = item["section_title"]
    item["raw_text"] = text.strip()
    item["normalized_text"] = compact(normalized, 1800)
    item["evidence_quote"] = first_evidence_line(text)
    item["extraction_source"] = "pdf_text"
    item["confidence"] = "0.72"

    classification = classify_text(normalized, manual_key)
    item.update(classification)
    codes = detect_codes(normalized)
    if codes:
        code = codes[0]
        if manual_key == "stay":
            item["stay_status_code"] = code
            item["stay_status_name_ko"] = normalize_korean_name(title + "\n" + text, code)
        else:
            item["visa_code"] = code
            item["visa_name_ko"] = normalize_korean_name(title + "\n" + text, code)
    else:
        item["needs_human_review"] = "true"
        item["review_notes"] = "대표 코드 없음: 공통/부록 여부 검수 필요"

    if any(marker in normalized for marker in ["E-7-4", "지역특화형", "K-point", "Top-Tier", "복수사증", "단수사증"]):
        matches = [marker for marker in ["E-7-4", "지역특화형", "K-point", "Top-Tier", "복수사증", "단수사증"] if marker in normalized]
        item["subtype_or_program"] = "; ".join(matches)

    if "|" in text or "\t" in text:
        item["table_summary"] = compact(title, 300)
        rows = [compact(line, 600) for line in text.splitlines() if "|" in line or "\t" in line]
        item["table_rows"] = "\n".join(rows[:20])

    assign_content_fields(item, normalized)
    return item


def extract_pdf_pages(pdf_path: Path) -> list[str]:
    completed = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.split("\f")


def load_markdown_pages(manual_key: str) -> dict[int, str]:
    files = sorted(PARSED_DIR.glob(MANUALS[manual_key]["markdown_glob"]))
    if not files:
        return {}
    current_page = 0
    pages: dict[int, list[str]] = {}
    for line in files[-1].read_text(encoding="utf-8", errors="ignore").splitlines():
        match = MARKDOWN_PAGE_RE.search(line)
        if match:
            current_page = int(match.group(1))
            pages.setdefault(current_page, [])
            continue
        if current_page:
            pages.setdefault(current_page, []).append(line)
    return {page: "\n".join(lines) for page, lines in pages.items()}


def build_items(sample: bool = False) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    sequence = 1
    for manual_key, meta in MANUALS.items():
        pdf_path = RAW_DIR / meta["source_pdf"]
        pages = extract_pdf_pages(pdf_path)
        markdown_pages = load_markdown_pages(manual_key)
        for page_no, page_text in enumerate(pages, start=1):
            if sample and page_no not in meta["sample_pages"]:
                continue
            source_text = page_text.strip()
            if not source_text and page_no in markdown_pages:
                source_text = markdown_pages[page_no]
            for block in split_page_blocks(source_text):
                if len(compact(block.text, 1000)) < 25:
                    continue
                items.append(item_from_block(manual_key, page_no, block.title, block.text, sequence))
                sequence += 1
    return items
