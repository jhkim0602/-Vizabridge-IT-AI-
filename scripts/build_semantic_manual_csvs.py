#!/usr/bin/env python3
"""Build the two final semantic CSV files from parsed immigration manuals.

This script is the main "PDF manual -> clean CSV" converter.

It does not try to copy the PDF page layout into a spreadsheet. Instead it
turns the manual into rows that match the administrative meaning of the text:
visa/stay code, petition type, 대상, 요건, 제출서류, 절차, 제한, 예외,
수수료, 점수표, 쿼터, and similar fields.

The final artifact contract is intentionally strict:

- one CSV per PDF
  - data/processed/stay_manual_semantic_clean.csv
  - data/processed/visa_manual_semantic_clean.csv
- no PDF page columns
- no evidence quote, raw source text, review flags, or debug columns
- no cover page, table-of-contents, blank form, or broken table-header rows

Maintenance guide:

1. Add or adjust schema columns in STAY_COLUMNS/VISA_COLUMNS.
2. Add domain keywords in SUBSECTION_RULES or PETITION_RULES.
3. Add OCR/noise cleanup in is_noise_row() or is_low_value_semantic_row().
4. Run tests, rebuild CSVs, then run the quality report script.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARSED_DIR = PROJECT_ROOT / "data" / "parsed"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


MANUALS = {
    "stay": {
        "manual_type": "체류민원",
        "source_pdf": "260504 체류민원 자격별 안내 매뉴얼.pdf",
        "markdown_glob": "stay_manual_llamaparse_agentic_plus_*.md",
        "output_csv": "stay_manual_semantic_clean.csv",
    },
    "visa": {
        "manual_type": "사증민원",
        "source_pdf": "260504 사증민원 자격별 안내 매뉴얼.pdf",
        "markdown_glob": "visa_manual_llamaparse_agentic_plus_*.md",
        "output_csv": "visa_manual_semantic_clean.csv",
    },
}

# Final CSV schema. The two manuals share most columns, but stay manuals have
# stay_status_* and obligations while visa manuals have visa_* and inviter /
# recommendation fields.
COMMON_COLUMNS = [
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
    "normalized_text",
]

STAY_COLUMNS = [
    "stay_status_code",
    "stay_status_name_ko",
    *COMMON_COLUMNS,
    "obligations",
]

VISA_COLUMNS = [
    "visa_code",
    "visa_name_ko",
    *COMMON_COLUMNS,
    "inviter_context",
    "recommendation_or_approval",
]


BASE_CODE_NAMES = {
    "A-1": "외교",
    "A-2": "공무",
    "A-3": "협정",
    "B-1": "사증면제",
    "B-2": "관광통과",
    "C-1": "일시취재",
    "C-3": "단기방문",
    "C-4": "단기취업",
    "D-1": "문화예술",
    "D-2": "유학",
    "D-3": "기술연수",
    "D-4": "일반연수",
    "D-5": "취재",
    "D-6": "종교",
    "D-7": "주재",
    "D-8": "기업투자",
    "D-9": "무역경영",
    "D-10": "구직",
    "E-1": "교수",
    "E-2": "회화지도",
    "E-3": "연구",
    "E-4": "기술지도",
    "E-5": "전문직업",
    "E-6": "예술흥행",
    "E-7": "특정활동",
    "E-8": "계절근로",
    "E-9": "비전문취업",
    "E-10": "선원취업",
    "F-1": "방문동거",
    "F-2": "거주",
    "F-3": "동반",
    "F-4": "재외동포",
    "F-5": "영주",
    "F-6": "결혼이민",
    "G-1": "기타",
    "H-1": "관광취업",
    "H-2": "방문취업",
}

# Regular expressions used while reading the LlamaParse Markdown. These are
# intentionally centralized because OCR often changes spaces around code values
# such as "E - 7" or "F - 2 - R".
CODE_RE = re.compile(r"\b[A-Z]-\d{1,2}(?:-[A-Z]?\d{1,2}[A-Z]?|-[A-Z]\d*|-[A-Z])?[A-Z]?\b")
SPACED_CODE_RE = re.compile(r"\b([A-Z])\s*-\s*(\d{1,2})(?:\s*-\s*([A-Z]?\d{1,2}[A-Z]?|[A-Z]\d*|[A-Z]))?([A-Z]?)\b")
PAGE_RE = re.compile(r"<!--\s*PDF_PAGE:(\d+)\s+SUCCESS:(True|False)\s*-->")
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")
IMAGE_RE = re.compile(r"!\[[^\]]*]\([^)]+\)")
HTML_TAG_RE = re.compile(r"<[^>]+>")
PIPE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)+\|?\s*$")
ENUM_PREFIX_RE = re.compile(r"^\s*(?:[-*•▶➡➠▪▸○◯ㅇ□■▣◇◆☞✓✔]|\(?\d{1,2}[).-]?|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]|[가-하]\.)\s*")


TOPIC_MARKERS = [
    "활동범위 및 해당자",
    "자격 해당자 및 활동범위",
    "활동범위",
    "해당자",
    "발급 대상",
    "발급대상",
    "신청 대상",
    "신청대상",
    "적용대상",
    "대상자",
    "기본요건",
    "허가요건",
    "자격요건",
    "심사기준",
    "사증발급 내용",
    "체류기간의 상한",
    "체류기간 상한",
    "신청기관",
    "신청 장소",
    "발급 절차",
    "신청절차",
    "제출서류",
    "제출 서류",
    "필수서류",
    "추가서류",
    "첨부서류",
    "구비서류",
    "체류자격외 활동",
    "근무처의 변경·추가",
    "근무처 변경",
    "체류자격 변경허가",
    "체류기간 연장허가",
    "재입국허가",
    "외국인등록",
    "신고의무",
    "제한",
    "예외",
    "면제",
    "특례",
    "수수료",
    "점수표",
    "배점표",
    "쿼터",
    "고용추천서",
]

# Blank attachment/form titles are usually not useful as RAG records by
# themselves. If the form text contains real requirements/documents elsewhere,
# those meaningful rows should remain; this list filters title-only fragments.
FORM_TITLE_NOISE_MARKERS = [
    "확인서",
    "계획서",
    "카드(예시)",
    "신상 기술서",
    "signature/seal",
    "검 사 내 용",
]

FORM_ATTACHMENT_NOISE_MARKERS = [
    "ROWSPANCONTINUE",
    "근로계약서 견본",
    "Labor Contract(Sample)",
    "Employment Permit",
    "Payment methods",
]

SHORT_TABLE_FRAGMENT_TITLES = {
    "구분",
    "구 분",
    "내용",
    "일반",
    "일반식당",
    "소득",
    "쿼터",
}

# These rules map Korean administrative headings to the output fields. The
# first matching rule wins, so put more specific document/target rules before
# broader requirement/default rules.
SUBSECTION_RULES = [
    ("common_documents", "제출서류", ["공통서류", "공통 제출서류"]),
    ("mandatory_documents", "제출서류", ["제출서류", "제출 서류", "필수서류", "첨부서류", "구비서류", "신청서류", "사증발급신청서", "사증발급인정신청서", "여권사본", "표준규격사진"]),
    ("eligibility", "대상", ["해당자", "신청대상", "신청 대상", "적용대상", "대상자", "발급대상", "발급 대상", "대상"]),
    ("requirements", "요건", ["기본요건", "허가요건", "자격요건", "요건", "심사기준", "기준"]),
    ("procedure", "절차", ["신청기관", "신청 장소", "발급절차", "신청절차", "절차", "접수", "하이코리아"]),
    ("duration_or_validity", "기간", ["체류기간", "유효기간", "허가기간", "기간의 상한", "체류허가기간", "단수사증", "복수사증"]),
    ("restrictions", "제한", ["제한", "불허", "금지", "결격", "제외", "억제"]),
    ("exceptions", "예외", ["예외", "면제", "특례", "완화"]),
    ("fees", "수수료", ["수수료", "수입인지", "납부금"]),
    ("score_criteria", "점수표", ["점수표", "배점표", "점수제", "배점"]),
    ("quota_or_limit", "쿼터", ["쿼터", "선발인원", "허용인원", "상한"]),
    ("obligations", "신고의무", ["신고의무", "신고하여야", "제출 의무", "교육의무", "거주의무"]),
    ("recommendation_or_approval", "추천/승인", ["고용추천서", "추천서", "추천기관", "관계기관", "승인"]),
]

DOCUMENT_WORDS = [
    "신청서",
    "여권",
    "사진",
    "수수료",
    "증명서",
    "등본",
    "계약서",
    "등록증",
    "허가증",
    "면허증",
    "추천서",
    "공한",
    "입증서류",
    "확인서",
    "사본",
    "초청장",
    "신원보증서",
    "진술서",
    "건강진단서",
    "범죄경력",
    "가족관계",
    "사업자등록증",
    "준비서류",
    "첨부서류",
    "구비서류",
    "제출서류",
]

DOCUMENT_CONTEXT_WORDS = [
    "제출",
    "서류",
    "준비서류",
    "첨부",
    "구비",
    "해당자",
    "필요시",
    "신청 시",
]

SCORE_WORDS = ["점수", "배점", "평가항목", "총점", "득점", "가점", "감점", "만점", "점 이상"]
QUOTA_WORDS = ["쿼터", "선발인원", "허용인원", "허용 인원", "배정인원", "명 이내", "명 이하", "인원"]
EXCEPTION_WORDS = ["예외", "면제", "특례", "완화", "제출할 필요가 없", "제출 불요"]
RESTRICTION_WORDS = ["제외", "제한", "불허", "금지", "불가", "억제", "결격"]

PETITION_RULES = [
    ("체류자격외 활동허가", ["체류자격외 활동", "체류자격외활동", "자격외 활동"]),
    ("근무처 변경/추가", ["근무처의 변경·추가", "근무처 변경", "근무처 추가"]),
    ("체류자격 부여", ["체류자격 부여"]),
    ("체류자격 변경", ["체류자격 변경허가", "체류자격 변경", "자격변경"]),
    ("체류기간 연장", ["체류기간 연장허가", "체류기간 연장", "체류기간연장", "기간연장"]),
    ("재입국허가", ["재입국허가"]),
    ("외국인등록", ["외국인등록", "등록사항 변경신고", "체류지변경신고", "거소신고"]),
    ("사증발급인정서", ["사증발급인정서", "비자발급인정서"]),
    ("전자사증", ["전자사증", "전자비자"]),
    ("사증발급", ["사증발급", "사증 발급", "비자발급", "공관장 재량", "단수사증", "복수사증"]),
    ("초청", ["초청"]),
]

STAY_PETITION_TYPES = {
    "체류자격외 활동허가",
    "근무처 변경/추가",
    "체류자격 부여",
    "체류자격 변경",
    "체류기간 연장",
    "재입국허가",
    "외국인등록",
}

VISA_PETITION_TYPES = {
    "사증발급인정서",
    "전자사증",
    "사증발급",
    "초청",
}


@dataclass
class Element:
    """One extracted Markdown block before it becomes a final CSV row."""

    title: str
    raw: str
    is_table: bool = False
    section_code: str = ""
    section_title: str = ""


def normalize_code_text(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        code = f"{match.group(1)}-{match.group(2)}"
        if match.group(3):
            code = f"{code}-{match.group(3)}"
        return f"{code}{match.group(4) or ''}"

    return SPACED_CODE_RE.sub(repl, text or "")


def strip_markup(text: str) -> str:
    text = normalize_code_text(text or "")
    text = text.replace("<br/>", "\n").replace("<br>", "\n").replace("<br />", "\n")
    text = re.sub(r"<page_footer>[\s\S]*?</page_footer>", " ", text)
    text = IMAGE_RE.sub(" ", text)
    text = HTML_TAG_RE.sub(" ", text)
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    text = re.sub(r"[*_`~\\]", "", text)
    text = re.sub(r"\[(.*?)\]\([^)]+\)", r"\1", text)
    text = text.replace("|", " / ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compact(text: str, max_chars: int = 1000) -> str:
    text = re.sub(r"\s+", " ", strip_markup(text)).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def clean_title(text: str) -> str:
    title = compact(text, 220)
    title = re.sub(r"^#+\s*", "", title)
    title = re.sub(r"^(?:[▶▣□■◇◆]\s*)+", "", title).strip()
    return title


def detect_codes(text: str) -> list[str]:
    out: list[str] = []
    for code in CODE_RE.findall(normalize_code_text(text or "")):
        code = code.strip("-")
        if code not in out:
            out.append(code)
    return out


def base_code(code: str) -> str:
    parts = (code or "").split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else code


def code_name(code: str) -> str:
    return BASE_CODE_NAMES.get(base_code(code), "")


def default_petition(manual_key: str) -> str:
    return "사증발급" if manual_key == "visa" else ""


def is_reference_code_context(text: str) -> bool:
    reference_terms = ["제외", "참조", "준용", "가능", "불가", "내지", "부터", "까지", "관련", "소지자", "해당하지"]
    return any(term in text for term in reference_terms)


def primary_section_code(title: str) -> str:
    """Return a section code only for real code headings, not references."""
    clean = clean_title(title)
    if clean in {"유 의 사 항", "유의사항", "공 통 사 항", "공통사항"}:
        return ""
    codes = detect_codes(clean)
    if len(codes) != 1:
        return ""
    code = codes[0]
    if not code_name(code):
        return ""
    if is_reference_code_context(clean) and not re.search(rf"\({re.escape(code)}\)\s*$", clean):
        return ""
    if len(clean) > 100 and not re.search(rf"\({re.escape(code)}\)\s*$", clean):
        return ""
    return code


def should_promote_title_code(title: str, raw: str, section_code: str, is_table: bool) -> bool:
    """Decide whether a code inside the current row is its primary code.

    Section context usually wins. Row-level codes are promoted only when the row
    itself is a code-bearing table/heading and the wording is not just a
    reference, exception, or exclusion.
    """
    title_codes = detect_codes(title)
    if len(title_codes) != 1 or not code_name(title_codes[0]):
        return False
    haystack = compact(f"{title} {raw[:300]}", 600)
    if "제외" in haystack or "참조" in haystack or "해당하지" in haystack:
        return False
    if section_code and base_code(title_codes[0]) == base_code(section_code):
        return True
    return is_table or bool(primary_section_code(title))


def parse_pipe_row(line: str) -> list[str]:
    row = line.strip().strip("|")
    cells = [strip_markup(cell).strip() for cell in re.split(r"(?<!\\)\|", row)]
    return [cell for cell in cells if cell]


def is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.count("|") >= 2


def table_elements(lines: list[str], section_code: str = "", section_title: str = "") -> list[Element]:
    elements: list[Element] = []
    for raw_line in lines:
        if PIPE_SEPARATOR_RE.match(raw_line):
            continue
        cells = parse_pipe_row(raw_line)
        if len(cells) < 2:
            continue
        label = clean_title(cells[0])
        value = "\n".join(cells[1:])
        if label and len(compact(value, 1600)) >= 20:
            elements.append(Element(title=label, raw=f"{label}\n{value}", is_table=True, section_code=section_code, section_title=section_title))
    return elements


def is_topic_marker_line(line: str) -> bool:
    title = clean_title(line)
    return bool(title) and len(title) <= 90 and any(marker in title for marker in TOPIC_MARKERS)


def flush_text_element(buffer: list[str], title: str, out: list[Element], section_code: str = "", section_title: str = "") -> None:
    raw = "\n".join(buffer).strip()
    plain = compact(raw, 2000)
    clean = clean_title(title) or clean_title(buffer[0] if buffer else "")
    if len(plain) < 35:
        return
    out.append(Element(title=clean, raw=raw, section_code=section_code, section_title=section_title))


def iter_elements(markdown: str) -> list[Element]:
    """Split parsed Markdown into candidate semantic blocks.

    A block can come from a Markdown heading, a topic marker line such as
    "제출서류", or a table row. Later functions decide whether the block is
    useful enough to keep.
    """
    elements: list[Element] = []
    buffer: list[str] = []
    buffer_title = ""
    current_section_code = ""
    current_section_title = ""
    lines = markdown.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if PAGE_RE.search(line):
            if buffer:
                flush_text_element(buffer, buffer_title, elements, current_section_code, current_section_title)
                buffer = []
                buffer_title = ""
            i += 1
            continue
        if "<page_footer>" in line:
            while i < len(lines) and "</page_footer>" not in lines[i]:
                i += 1
            i += 1
            continue
        if is_table_line(line):
            if buffer:
                flush_text_element(buffer, buffer_title, elements, current_section_code, current_section_title)
                buffer = []
                buffer_title = ""
            table_lines: list[str] = []
            while i < len(lines) and is_table_line(lines[i]):
                table_lines.append(lines[i])
                i += 1
            elements.extend(table_elements(table_lines, current_section_code, current_section_title))
            continue
        heading = HEADING_RE.match(line)
        if heading:
            if buffer:
                flush_text_element(buffer, buffer_title, elements, current_section_code, current_section_title)
            heading_title = heading.group(2)
            heading_code = primary_section_code(heading_title)
            if heading_code:
                current_section_code = heading_code
                current_section_title = clean_title(heading_title)
            elif clean_title(heading_title) in {"유 의 사 항", "유의사항", "공 통 사 항", "공통사항"}:
                current_section_code = ""
                current_section_title = clean_title(heading_title)
            buffer = [line]
            buffer_title = heading_title
            i += 1
            continue
        if is_topic_marker_line(line) and buffer:
            flush_text_element(buffer, buffer_title, elements, current_section_code, current_section_title)
            buffer = [line]
            buffer_title = line
            i += 1
            continue
        buffer.append(line)
        if not buffer_title and compact(line, 120):
            buffer_title = line
        i += 1
    if buffer:
        flush_text_element(buffer, buffer_title, elements, current_section_code, current_section_title)
    return elements


def meaningful_lines(raw: str) -> list[str]:
    lines = []
    for line in strip_markup(raw).splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not line or line.lower().startswith("image_url_placeholder"):
            continue
        if PIPE_SEPARATOR_RE.match(line):
            continue
        lines.append(line)
    return lines


def key_text(raw: str, max_lines: int = 8, max_chars: int = 1300) -> str:
    selected: list[str] = []
    for line in meaningful_lines(raw):
        stripped = ENUM_PREFIX_RE.sub("", line).strip()
        if stripped and stripped not in selected:
            selected.append(stripped)
        if len(selected) >= max_lines:
            break
    return compact("; ".join(selected), max_chars)


def looks_like_document_text(title: str, raw: str) -> bool:
    """True when a block is mostly a 제출서류/document list.

    Administrative manuals often list documents as numbered lines without a
    nearby "제출서류" heading. A short title such as "근로자파견사업허가증(해당자)"
    should therefore be treated as a document row, not as 대상/요건.
    """
    text = compact(f"{title}\n{raw}", 1600)
    if not any(word in text for word in DOCUMENT_WORDS):
        return False
    if any(word in text for word in DOCUMENT_CONTEXT_WORDS):
        return True

    lines = meaningful_lines(raw)
    if not lines:
        return False
    doc_like_lines = sum(1 for line in lines if any(word in line for word in DOCUMENT_WORDS))
    return doc_like_lines >= 2 or len(text) <= 180


def looks_like_score_text(title: str, raw: str) -> bool:
    text = compact(f"{title}\n{raw}", 1200)
    if any(word in text for word in SCORE_WORDS):
        return True
    has_point_value = bool(re.search(r"\(\s*\d{1,3}\s*\)", title))
    has_score_context = any(word in text for word in ["우수 재능", "연령", "소득", "학력", "한국어", "사회통합"])
    has_quota_context = any(word in text for word in QUOTA_WORDS)
    return has_point_value and has_score_context and not has_quota_context


def looks_like_quota_text(title: str, raw: str) -> bool:
    text = compact(f"{title}\n{raw}", 1200)
    return any(word in text for word in QUOTA_WORDS)


def looks_like_strong_restriction_title(title: str) -> bool:
    title = clean_title(title)
    if any(word in title for word in ["제출서류", "준비서류", "첨부서류", "구비서류"]):
        return False
    return any(
        word in title
        for word in ["취업제한", "발급 제한", "발급제한", "제한 대상", "제한대상", "제한 업종", "불허", "금지", "결격", "불가"]
    )


def classify_subsection(title: str, raw: str) -> tuple[str, str]:
    """Return the output field and Korean subsection label for one block."""
    title_first = title + "\n" + raw[:1200]
    if any(keyword in title_first for keyword in ["제출할 필요가 없", "제출 불요", "면제 대상자는"]):
        return "exceptions", "예외"
    if looks_like_strong_restriction_title(title):
        return "restrictions", "제한"
    if looks_like_document_text(title, raw):
        return "mandatory_documents", "제출서류"
    if looks_like_score_text(title, raw):
        return "score_criteria", "점수표"
    if looks_like_quota_text(title, raw):
        return "quota_or_limit", "쿼터"
    if any(keyword in title_first for keyword in RESTRICTION_WORDS):
        return "restrictions", "제한"
    if any(keyword in title_first for keyword in EXCEPTION_WORDS):
        return "exceptions", "예외"
    for field, label, keywords in SUBSECTION_RULES:
        if any(keyword in title_first for keyword in keywords):
            return field, label
    return "normalized_text", "기타"


def classify_petition(title: str, raw: str, manual_key: str, inherited: str) -> str:
    """Detect the 민원유형 and inherit the previous one when the PDF omits it."""
    haystacks = [title, raw[:350]]
    allowed = VISA_PETITION_TYPES if manual_key == "visa" else STAY_PETITION_TYPES
    for label, keywords in PETITION_RULES:
        if label not in allowed:
            continue
        if any(any(keyword in haystack for keyword in keywords) for haystack in haystacks):
            return label
    return inherited or default_petition(manual_key)


def classify_item_type(manual_key: str, subsection: str, raw: str) -> str:
    """Reduce a subsection into the machine-friendly item_type enum."""
    if subsection == "제출서류":
        return "required_documents"
    if subsection == "수수료":
        return "fee"
    if subsection == "점수표":
        return "score_table"
    if subsection == "쿼터":
        return "quota"
    if subsection == "제한":
        return "restriction"
    if subsection == "예외":
        return "exception"
    if "공통" in raw[:160] or "유 의 사 항" in raw[:160] or "유의사항" in raw[:160]:
        return "common_rule"
    return "stay_status_rule" if manual_key == "stay" else "visa_rule"


def document_buckets(raw: str) -> tuple[str, str, str]:
    """Split document-looking lines into common, mandatory, and other buckets."""
    common_terms = ["통합신청서", "사증발급신청서", "여권", "사진", "수수료", "외국인등록증"]
    common: list[str] = []
    mandatory: list[str] = []
    other: list[str] = []
    for line in meaningful_lines(raw):
        stripped = ENUM_PREFIX_RE.sub("", line).strip()
        if not any(word in stripped for word in DOCUMENT_WORDS):
            continue
        target = common if any(term in stripped for term in common_terms) else mandatory
        if any(term in stripped for term in ["필요시", "해당자", "추가", "입증", "심사"]):
            target = other
        if stripped not in target:
            target.append(stripped)
    return (
        compact("; ".join(common), 1200),
        compact("; ".join(mandatory), 1700),
        compact("; ".join(other), 1700),
    )


def detect_context(title: str, raw: str, current_context: str) -> str:
    if any(word in title for word in ["대상", "해당자", "초청", "투자", "유학생", "배우자", "근로자", "전문인력"]):
        return compact(title, 300)
    first = compact(raw, 300)
    if any(word in first for word in ["신청하는 경우", "대상", "해당자", "초청"]):
        return first
    return current_context


def subtype_or_program(raw: str) -> str:
    markers = ["E-7-4", "K-point", "지역특화형", "지역우수인재", "Top-Tier", "K-STAR", "복수사증", "단수사증", "사증발급인정서"]
    found = [marker for marker in markers if marker in raw]
    return "; ".join(dict.fromkeys(found))


def is_noise_row(title: str, raw: str) -> bool:
    """Return True for rows that should never reach the final clean CSV."""
    text = compact(f"{title} {raw}", 1400)
    title_clean = clean_title(title)
    if any(marker in text for marker in FORM_ATTACHMENT_NOISE_MARKERS):
        return True
    if title_clean in {"目 次", "次", "목차", "▶ 목차", "▣ 목차"}:
        return True
    if is_cover_or_manual_title_noise(title_clean, text):
        return True
    if is_stray_toc_entry(title_clean, text):
        return True
    if is_blank_form_title_noise(title_clean, text):
        return True
    if is_short_table_fragment_noise(title_clean, text):
        return True
    if is_blank_bilingual_form_noise(text):
        return True
    if "目 次" in text and len(text) < 1500:
        return True
    if text.count(")") >= 8 and sum(1 for code in detect_codes(text) if code) >= 8:
        return True
    noise_markers = [
        "FOREIGNER OCCUPATION REPORT FORM",
        "OCCUPATION ( )",
        "서명 또는 인",
        "신청일 (Date of Application)",
        "Alien Registration No.",
    ]
    return any(marker in text for marker in noise_markers)


def is_cover_or_manual_title_noise(title: str, text: str) -> bool:
    """Detect cover-page titles, not valid cross-references to another manual."""
    if "참조" in text:
        return False
    title_markers = ["안내매뉴얼", "안 내 매 뉴 얼"]
    org_markers = ["법무부", "출입국", "외국인정책본부"]
    if any(marker in title for marker in title_markers) and (
        any(marker in text for marker in org_markers) or len(text) <= 180
    ):
        return True
    return False


def is_stray_toc_entry(title: str, text: str) -> bool:
    """Detect short table-of-contents fragments that only name a code/section."""
    if len(text) > 180:
        return False
    if not re.match(r"^\d{1,2}\.\s*", title):
        return False
    codes = detect_codes(text)
    if not codes:
        return False
    toc_only_markers = ["관련", "체류제도", "국내 성장 기반", "외국국적동포"]
    return any(marker in text for marker in toc_only_markers) or len(meaningful_lines(text)) <= 3


def is_blank_form_title_noise(title: str, text: str) -> bool:
    """Drop standalone blank form titles when no actual requirement/document content follows."""
    if len(text) > 120:
        return False
    title_joined = re.sub(r"\s+", "", title)
    return any(marker in title or marker in title_joined for marker in FORM_TITLE_NOISE_MARKERS)


def is_short_table_fragment_noise(title: str, text: str) -> bool:
    """Drop table headers or broken numeric fragments that are not meaningful alone."""
    if len(text) > 90:
        return False
    if title in SHORT_TABLE_FRAGMENT_TITLES:
        return True
    table_header_markers = ["사업장 면적", "허용 인원", "허용인원", "인 가구", "종 류", "상 세 설 명"]
    return any(marker in text for marker in table_header_markers)


def is_blank_bilingual_form_noise(text: str) -> bool:
    """Drop blank bilingual contract/form templates extracted as long pseudo-rules."""
    form_markers = [
        "Monthly Normal wages",
        "Accommo-dations and Meals",
        "Both employees and employers shall comply",
        "Payment methods",
    ]
    return sum(1 for marker in form_markers if marker in text) >= 2


def is_low_value_semantic_row(row: dict[str, str]) -> bool:
    """Drop rows that only repeat a blank form title or a broken table header.

    This runs after row classification because some fragments look non-empty in
    raw Markdown but collapse to a title-only row after normalization.
    """
    title = clean_title(row.get("section_title", ""))
    title_joined = re.sub(r"\s+", "", title)
    normalized = compact(row.get("normalized_text", ""), 300)
    table_rows = compact(row.get("table_rows", ""), 300)
    text = compact("; ".join(part for part in [title, normalized, table_rows] if part), 500)

    if "참조" in text and "안내매뉴얼" in text:
        return False
    if any(marker in text for marker in FORM_ATTACHMENT_NOISE_MARKERS):
        return True
    if normalized and len(normalized) > 90:
        return False
    if any(marker in title or marker in title_joined for marker in FORM_TITLE_NOISE_MARKERS):
        return True
    if title in SHORT_TABLE_FRAGMENT_TITLES and (
        len(normalized) < 80 or any(marker in normalized for marker in ["허용 인원", "허용인원", "인 가구"])
    ):
        return True
    if any(marker in normalized for marker in ["허용 인원", "허용인원", "종 류; 상 세 설 명"]):
        return True
    if re.fullmatch(r"[,0-9]+만원(?:; [,0-9]+만원)+", normalized):
        return True
    return False


def clean_row_values(row: dict[str, str]) -> dict[str, str]:
    enum_fields = {
        "item_type",
        "manual_type",
        "source_pdf",
        "stay_status_code",
        "stay_status_name_ko",
        "visa_code",
        "visa_name_ko",
        "petition_type",
        "subsection_type",
    }
    cleaned = {}
    for key, value in row.items():
        if key in enum_fields:
            value = re.sub(r"\s+", " ", value or "").strip()
        else:
            value = compact(value, 2400 if key in {"normalized_text", "mandatory_documents", "other_documents", "requirements"} else 1400)
        value = value.replace("제목자격", "체류자격").replace("제목관리과", "체류관리과").replace("제목족적", "체류목적")
        cleaned[key] = value
    return cleaned


def empty_row(manual_key: str) -> dict[str, str]:
    columns = STAY_COLUMNS if manual_key == "stay" else VISA_COLUMNS
    return {column: "" for column in columns}


def build_semantic_rows(manual_key: str, markdown: str) -> list[dict[str, str]]:
    """Convert one parsed manual Markdown file into final CSV row dictionaries."""
    manual = MANUALS[manual_key]
    elements = iter_elements(markdown)
    rows: list[dict[str, str]] = []
    current_code = ""
    current_name = "공통사항"
    current_context = ""
    current_petition = default_petition(manual_key)

    for element in elements:
        title = clean_title(element.title)
        raw = strip_markup(element.raw)
        if len(compact(raw, 2000)) < 35 or is_noise_row(title, raw):
            continue

        if element.section_code != current_code:
            current_code = element.section_code
            current_name = code_name(current_code) if current_code else "공통사항"
            current_context = ""
            current_petition = default_petition(manual_key)

        title_codes = detect_codes(title)
        raw_codes = detect_codes(raw[:1200])
        row_code = current_code
        if should_promote_title_code(title, raw, current_code, element.is_table):
            row_code = title_codes[0]
        elif not row_code and raw_codes and code_name(raw_codes[0]):
            raw_context = compact(raw[:500], 700)
            if not is_reference_code_context(raw_context):
                row_code = base_code(raw_codes[0])

        row_name = code_name(row_code) if row_code else "공통사항"
        if title in {"유 의 사 항", "유의사항", "공 통 사 항", "공통사항"}:
            row_code = ""
            row_name = "공통사항"
            current_code = ""
            current_name = "공통사항"
            current_petition = default_petition(manual_key)

        current_petition = classify_petition(title, raw, manual_key, current_petition)
        field, subsection = classify_subsection(title, raw)
        item_type = classify_item_type(manual_key, subsection, raw)
        current_context = detect_context(title, raw, current_context)
        common_docs, mandatory_docs, other_docs = document_buckets(raw)

        row = empty_row(manual_key)
        row.update(
            {
                "manual_type": manual["manual_type"],
                "source_pdf": manual["source_pdf"],
                "item_type": item_type,
                "section_title": title,
                "subtype_or_program": subtype_or_program(raw),
                "petition_type": current_petition,
                "subsection_type": subsection,
                "applicant_context": current_context,
                "common_documents": common_docs,
                "mandatory_documents": mandatory_docs,
                "other_documents": other_docs,
                "table_summary": title if element.is_table else "",
                "table_rows": key_text(raw, max_lines=12, max_chars=1600) if element.is_table else "",
                "normalized_text": key_text(raw, max_lines=10, max_chars=2200),
            }
        )
        if manual_key == "stay":
            row["stay_status_code"] = row_code
            row["stay_status_name_ko"] = row_name
        else:
            row["visa_code"] = row_code
            row["visa_name_ko"] = row_name

        if field in row:
            row[field] = key_text(raw, max_lines=10, max_chars=1800)
        if subsection == "대상":
            row["target_persons"] = row[field]
        if manual_key == "visa" and any(word in raw for word in ["초청인", "고용주", "유치기관", "초청자"]):
            row["inviter_context"] = key_text(raw, max_lines=6, max_chars=1200)

        cleaned_row = clean_row_values(row)
        if is_low_value_semantic_row(cleaned_row):
            continue
        rows.append(cleaned_row)

    return dedupe_rows(rows, manual_key)


def dedupe_rows(rows: list[dict[str, str]], manual_key: str) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str, str, str]] = set()
    out: list[dict[str, str]] = []
    code_field = "stay_status_code" if manual_key == "stay" else "visa_code"
    for row in rows:
        key = (
            row.get(code_field, ""),
            row.get("petition_type", ""),
            row.get("subsection_type", ""),
            row.get("section_title", ""),
            compact(row.get("normalized_text", ""), 260),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def latest_markdown_path(manual_key: str) -> Path:
    paths = sorted(PARSED_DIR.glob(MANUALS[manual_key]["markdown_glob"]), key=lambda p: p.stat().st_mtime, reverse=True)
    if not paths:
        raise FileNotFoundError(f"No parsed markdown file found for {manual_key}")
    return paths[0]


def write_csv(path: Path, rows: Iterable[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def build_all() -> dict[str, int]:
    counts: dict[str, int] = {}
    for manual_key in ["stay", "visa"]:
        source_path = latest_markdown_path(manual_key)
        markdown = source_path.read_text(encoding="utf-8")
        rows = build_semantic_rows(manual_key, markdown)
        columns = STAY_COLUMNS if manual_key == "stay" else VISA_COLUMNS
        output_path = PROCESSED_DIR / MANUALS[manual_key]["output_csv"]
        write_csv(output_path, rows, columns)
        counts[manual_key] = len(rows)
    return counts


def main() -> None:
    counts = build_all()
    for manual_key, count in counts.items():
        print(f"{manual_key}: {count} rows")


if __name__ == "__main__":
    main()
