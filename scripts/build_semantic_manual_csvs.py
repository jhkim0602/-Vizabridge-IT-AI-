#!/usr/bin/env python3
"""Build visa-consultation/RAG oriented semantic CSVs from parsed manuals.

This script treats the LlamaParse markdown as the structural source of truth.
The existing clean CSVs are kept as comparison/reference material, while the
final semantic rows are rebuilt around a single answerable knowledge unit:

    visa/status code + petition type + topic type + applicant context

No PDF page columns are emitted. Evidence is kept as section path, short quote,
and bounded raw text so review can happen without making raw parsing fragments
the primary retrieval surface.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
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
        "current_csv": "stay_manual_clean.csv",
        "output_csv": "stay_manual_semantic_clean.csv",
    },
    "visa": {
        "manual_type": "사증민원",
        "source_pdf": "260504 사증민원 자격별 안내 매뉴얼.pdf",
        "markdown_glob": "visa_manual_llamaparse_agentic_plus_*.md",
        "current_csv": "visa_manual_clean.csv",
        "output_csv": "visa_manual_semantic_clean.csv",
    },
}


SEMANTIC_COLUMNS = [
    "manual_type",
    "source_pdf",
    "source_section_path",
    "visa_code",
    "visa_name_ko",
    "petition_type",
    "topic_type",
    "applicant_context",
    "user_intents",
    "question_examples",
    "answer_summary",
    "conditions",
    "required_documents",
    "procedure",
    "restrictions",
    "exceptions",
    "ai_search_text",
    "evidence_quote",
    "source_raw_text",
    "needs_human_review",
    "review_notes",
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


INTENT_HINTS = {
    "D-8": [
        "한국에서 법인 설립",
        "외국인 투자",
        "한국에서 사업 운영",
        "스타트업 창업",
        "벤처기업 대표",
        "투자금 1억원",
    ],
    "E-7": [
        "한국 회사 취업",
        "전문인력 취업비자",
        "특정활동 직종",
        "고용추천서",
        "임금요건",
        "외국인 채용",
    ],
    "F-6": [
        "한국인 배우자",
        "결혼비자",
        "결혼이민",
        "자녀 양육",
        "이혼 또는 사망 후 체류",
        "배우자 비자 연장",
    ],
    "F-5": ["영주권", "한국 영주", "영주자격 변경", "장기체류 후 영주"],
    "F-4": ["재외동포", "동포비자", "외국국적동포", "동포 취업 제한"],
    "F-2": ["거주비자", "점수제 우수인재", "투자이민", "장기체류 거주"],
    "D-2": ["한국 대학 유학", "유학생 체류", "시간제 취업", "유학비자 연장"],
    "D-4": ["어학연수", "일반연수", "한국어 연수", "연수비자"],
    "D-10": ["구직비자", "졸업 후 취업 준비", "기술창업 준비", "첨단기술 인턴"],
    "C-3": ["단기방문", "관광비자", "상용방문", "가족 방문", "복수사증"],
    "C-4": ["단기취업", "90일 이하 취업", "단기 강연", "모델 공연"],
    "E-9": ["비전문취업", "고용허가제", "제조업 외국인 근로자"],
    "E-8": ["계절근로", "농어업 계절근로", "단기 계절근로"],
    "H-2": ["방문취업", "동포 취업", "방문취업 체류"],
    "COMMON": ["공통 제출서류", "서류 유효기간", "수수료", "결핵진단서", "공통 유의사항"],
}


CODE_RE = re.compile(
    r"\b[A-Z]-\d{1,2}(?:-(?:[A-Z]?\d{1,2}[A-Z]?|[A-Z]\d*))?[A-Z]?\b"
)
SPACED_CODE_RE = re.compile(
    r"\b([A-Z])\s*-\s*(\d{1,2})(?:\s*-\s*([A-Z]?\d{1,2}[A-Z]?|[A-Z]\d*))?([A-Z]?)\b"
)
PAGE_RE = re.compile(r"<!--\s*PDF_PAGE:(\d+)\s+SUCCESS:(True|False)\s*-->")
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")
IMAGE_RE = re.compile(r"!\[[^\]]*]\([^)]+\)")
HTML_TAG_RE = re.compile(r"<[^>]+>")
PIPE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)+\|?\s*$")
ENUM_PREFIX_RE = re.compile(
    r"^\s*(?:[-*•▶➡➠▪▸○◯ㅇ□■▣◇◆☞✓✔]|\(?\d{1,2}[).-]?|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]|[가-하]\.)\s*"
)


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
    "사증발급내용",
    "발급 내용",
    "발급내용",
    "체류기간의 상한",
    "체류기간 상한",
    "체류허가기간",
    "신청기관",
    "신청 장소",
    "신청장소",
    "발급 절차",
    "발급절차",
    "신청절차",
    "제출서류",
    "제출 서류",
    "필수서류",
    "추가서류",
    "서류 목록",
    "첨부서류",
    "첨부 서류",
    "신청서류",
    "구비서류",
    "공관장 재량으로 발급할 수 있는 사증",
    "사증발급인정서 발급대상",
    "사증발급인정서발급대상",
    "전자사증",
    "체류자격외 활동",
    "체류자격외활동",
    "근무처의 변경·추가",
    "근무처 변경",
    "체류자격 부여",
    "체류자격 변경허가",
    "체류기간 연장허가",
    "재입국허가",
    "외국인등록",
    "등록사항 변경신고",
    "참고사항",
    "제한",
    "적용 제외",
    "예외",
    "면제",
    "특례",
    "수수료",
    "점수표",
    "배점표",
    "고용추천서",
]


TOPIC_PRIORITY = [
    ("제출서류", ["제출서류", "제출 서류", "필수서류", "추가서류", "서류 목록", "첨부서류", "첨부 서류", "신청서류", "구비서류"]),
    ("요건", ["기본요건", "허가요건", "자격요건", "요건", "심사기준", "기준"]),
    ("대상", ["해당자", "신청대상", "신청 대상", "적용대상", "대상자", "발급대상", "발급 대상", "대상"]),
    ("활동범위", ["활동범위"]),
    ("절차", ["신청기관", "신청 장소", "신청장소", "발급절차", "신청절차", "절차", "접수"]),
    ("기간", ["체류기간", "유효기간", "허가기간", "기간의 상한", "체류허가기간"]),
    ("제한", ["제한", "불허", "금지", "결격", "제외", "억제"]),
    ("예외", ["예외", "면제", "특례", "완화"]),
    ("수수료", ["수수료"]),
    ("점수", ["점수표", "배점표", "점수제", "배점"]),
    ("추천", ["고용추천서", "추천서", "추천기관"]),
    ("참고", ["참고사항", "판례", "주의"]),
]


PETITION_PRIORITY = [
    ("체류자격외활동", ["체류자격외 활동", "체류자격외활동", "자격외 활동"]),
    ("근무처 변경·추가", ["근무처의 변경·추가", "근무처 변경", "근무처 추가"]),
    ("체류자격 부여", ["체류자격 부여"]),
    ("체류자격 변경", ["체류자격 변경허가", "체류자격 변경", "자격변경"]),
    ("체류기간 연장", ["체류기간 연장허가", "체류기간연장", "기간연장"]),
    ("재입국허가", ["재입국허가"]),
    ("외국인등록", ["외국인등록", "등록사항 변경신고", "체류지변경신고"]),
    ("사증발급인정서", ["사증발급인정서", "비자발급인정서"]),
    ("전자사증", ["전자사증", "전자비자"]),
    ("사증발급", ["공관장 재량", "사증발급", "사증 발급", "비자발급", "복수사증", "단수사증"]),
]


GENERIC_TITLES = {
    "",
    "목차",
    "▶ 목차",
    "▣ 목차",
    "공관장 재량으로",
    "공관장 재량으로 발급할 수 있는 사증",
    "사증발급인정서 발급대상",
    "사증발급인정서발급대상",
}


@dataclass
class Element:
    line_no: int
    page_no: int
    kind: str
    title: str
    raw: str
    is_table: bool = False


def normalize_code_text(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        head = f"{match.group(1)}-{match.group(2)}"
        middle = match.group(3)
        suffix = match.group(4) or ""
        if middle:
            return f"{head}-{middle}{suffix}"
        return f"{head}{suffix}"

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


def compact(text: str, max_chars: int = 800) -> str:
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
    normalized = normalize_code_text(text)
    codes = CODE_RE.findall(normalized)
    out: list[str] = []
    for code in codes:
        code = code.strip("-")
        if code not in out:
            out.append(code)
    return out


def base_code(code: str) -> str:
    parts = (code or "").split("-")
    if len(parts) >= 2:
        return "-".join(parts[:2])
    return code


def code_name(code: str) -> str:
    return BASE_CODE_NAMES.get(base_code(code), "")


def title_has_main_name(title: str, code: str) -> bool:
    name = code_name(code)
    if not name:
        return False
    normalized_title = re.sub(r"\s+", "", title)
    normalized_name = re.sub(r"\s+", "", name)
    code_pos = normalized_title.find(base_code(code))
    name_pos = normalized_title.find(normalized_name)
    return name_pos >= 0 and (code_pos < 0 or name_pos < code_pos)


def is_main_section_title(title: str) -> bool:
    codes = detect_codes(title)
    if not codes:
        return False
    code = base_code(codes[0])
    name = code_name(code)
    if not name:
        return False
    title_no_markup = re.sub(r"^\d+[\).]?\s*", "", title).strip()
    title_norm = re.sub(r"\s+", "", title_no_markup)
    name_norm = re.sub(r"\s+", "", name)
    starts_with_name = title_norm.startswith(name_norm)
    is_short_name_heading = len(title_no_markup) <= len(name) + len(code) + 8
    return starts_with_name and (is_short_name_heading or title_has_main_name(title, code))


def parse_pipe_row(line: str) -> list[str]:
    row = line.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    cells = [strip_markup(cell).strip() for cell in re.split(r"(?<!\\)\|", row)]
    return [cell for cell in cells if cell]


def table_elements(lines: list[str], line_no: int, page_no: int) -> list[Element]:
    elements: list[Element] = []
    for raw_line in lines:
        if PIPE_SEPARATOR_RE.match(raw_line):
            continue
        cells = parse_pipe_row(raw_line)
        if len(cells) < 2:
            continue
        label = clean_title(cells[0])
        value = "\n".join(cells[1:])
        if not label or len(compact(value, 2000)) < 20:
            continue
        title = label
        raw = f"{label}\n{value}"
        elements.append(Element(line_no=line_no, page_no=page_no, kind="table_row", title=title, raw=raw, is_table=True))
    return elements


def is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.count("|") >= 2


def is_topic_marker_line(line: str) -> bool:
    title = clean_title(line)
    if not title or len(title) > 90:
        return False
    if title in GENERIC_TITLES:
        return True
    return any(marker in title for marker in TOPIC_MARKERS)


def flush_text_element(buffer: list[str], title: str, line_no: int, page_no: int, out: list[Element]) -> None:
    raw = "\n".join(buffer).strip()
    plain = compact(raw, 2000)
    clean = clean_title(title) or clean_title(buffer[0])
    if is_main_section_title(clean) and len(plain) < 45:
        out.append(Element(line_no=line_no, page_no=page_no, kind="context", title=clean, raw=raw))
        return
    if len(plain) < 45:
        return
    if clean in {"목차", "▶ 목차", "▣ 목차"} and len(plain) < 120:
        return
    out.append(Element(line_no=line_no, page_no=page_no, kind="text", title=clean, raw=raw))


def iter_elements(markdown: str) -> list[Element]:
    elements: list[Element] = []
    buffer: list[str] = []
    buffer_title = ""
    buffer_line_no = 1
    page_no = 0
    lines = markdown.splitlines()
    i = 0
    while i < len(lines):
        line_no = i + 1
        line = lines[i]
        page_match = PAGE_RE.search(line)
        if page_match:
            if buffer:
                flush_text_element(buffer, buffer_title, buffer_line_no, page_no, elements)
                buffer = []
                buffer_title = ""
            page_no = int(page_match.group(1))
            i += 1
            continue

        if "<page_footer>" in line:
            while i < len(lines) and "</page_footer>" not in lines[i]:
                i += 1
            i += 1
            continue

        if is_table_line(line):
            if buffer:
                flush_text_element(buffer, buffer_title, buffer_line_no, page_no, elements)
                buffer = []
                buffer_title = ""
            table_lines: list[str] = []
            table_line_no = line_no
            while i < len(lines) and is_table_line(lines[i]):
                table_lines.append(lines[i])
                i += 1
            elements.extend(table_elements(table_lines, table_line_no, page_no))
            continue

        heading = HEADING_RE.match(line)
        if heading:
            if buffer:
                flush_text_element(buffer, buffer_title, buffer_line_no, page_no, elements)
            buffer = [line]
            buffer_title = heading.group(2)
            buffer_line_no = line_no
            i += 1
            continue

        if is_topic_marker_line(line) and buffer:
            flush_text_element(buffer, buffer_title, buffer_line_no, page_no, elements)
            buffer = [line]
            buffer_title = line
            buffer_line_no = line_no
            i += 1
            continue

        buffer.append(line)
        if not buffer_title and compact(line, 120):
            buffer_title = line
            buffer_line_no = line_no
        i += 1

    if buffer:
        flush_text_element(buffer, buffer_title, buffer_line_no, page_no, elements)
    return elements


def detect_petition_type(title: str, raw: str, manual_key: str, inherited: str) -> str:
    # Petition context should be driven by structural labels/headings. Full raw
    # text often mentions other petitions as exceptions or after-arrival notes.
    title_haystack = title
    for label, keywords in PETITION_PRIORITY:
        if any(keyword in title_haystack for keyword in keywords):
            return label
    raw_head = raw[:260]
    for label, keywords in PETITION_PRIORITY:
        if label in {"외국인등록", "재입국허가"} and manual_key == "visa":
            continue
        if any(keyword in raw_head for keyword in keywords):
            return label
    if inherited:
        return inherited
    return "사증발급" if manual_key == "visa" else ""


def detect_topic_type(title: str, raw: str) -> str:
    title_priority = [
        ("제출서류", ["제출서류", "제출 서류", "필수서류", "추가서류", "서류 목록", "첨부서류", "첨부 서류", "신청서류", "구비서류"]),
        ("활동범위", ["활동범위"]),
        ("대상", ["해당자", "신청대상", "신청 대상", "적용대상", "대상자", "발급대상", "발급 대상", "대상"]),
        ("요건", ["기본요건", "허가요건", "자격요건", "요건", "심사기준", "기준"]),
        ("절차", ["신청기관", "신청 장소", "신청장소", "발급절차", "신청절차", "절차", "접수"]),
        ("기간", ["체류기간", "유효기간", "허가기간", "기간의 상한", "체류허가기간", "사증발급 내용", "발급 내용"]),
        ("제한", ["제한", "불허", "금지", "결격", "제외", "억제"]),
        ("예외", ["예외", "면제", "특례", "완화"]),
        ("수수료", ["수수료"]),
        ("점수", ["점수표", "배점표", "점수제", "배점"]),
        ("추천", ["고용추천서", "추천서", "추천기관"]),
        ("참고", ["참고사항", "판례", "주의"]),
    ]
    for label, keywords in title_priority:
        if any(keyword in title for keyword in keywords):
            return label
    haystack = raw[:1000]
    doc_words = [
        "신청서",
        "여권",
        "사진",
        "수수료",
        "증명서",
        "등본",
        "계약서",
        "등록증",
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
        "혼인관계",
        "주민등록",
    ]
    if sum(1 for word in doc_words if word in haystack) >= 3:
        return "제출서류"
    if re.match(r"^\d+(?:-\d+)?\b", title) and any(word in haystack for word in doc_words):
        return "제출서류"
    for label, keywords in TOPIC_PRIORITY:
        if any(keyword in haystack for keyword in keywords):
            return label
    if detect_codes(haystack):
        return "개요"
    return "일반"


def looks_like_context(title: str) -> bool:
    if not title or title in GENERIC_TITLES:
        return False
    if any(marker == title for marker in TOPIC_MARKERS):
        return False
    if detect_codes(title):
        return True
    if re.match(r"^\d+[\).-]\s+", title) and len(title) > 12:
        return True
    if re.match(r"^[가-하]\.\s+", title) and len(title) > 12:
        return True
    return False


def meaningful_lines(raw: str) -> list[str]:
    text = strip_markup(raw)
    lines: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        if line in {"목차", "▶ 목차", "▣ 목차"}:
            continue
        if line.lower().startswith("image_url_placeholder"):
            continue
        if PIPE_SEPARATOR_RE.match(line):
            continue
        lines.append(line)
    return lines


def key_text(raw: str, max_lines: int = 8, max_chars: int = 1300) -> str:
    lines = meaningful_lines(raw)
    selected: list[str] = []
    for line in lines:
        stripped = ENUM_PREFIX_RE.sub("", line).strip()
        if not stripped:
            continue
        if stripped not in selected:
            selected.append(stripped)
        if len(selected) >= max_lines:
            break
    return compact("; ".join(selected), max_chars)


def extract_documents(raw: str) -> str:
    lines = meaningful_lines(raw)
    doc_words = [
        "신청서",
        "여권",
        "사진",
        "수수료",
        "증명서",
        "등본",
        "계약서",
        "등록증",
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
        "혼인관계",
        "주민등록",
    ]
    selected: list[str] = []
    for line in lines:
        stripped = ENUM_PREFIX_RE.sub("", line).strip()
        if any(word in stripped for word in doc_words):
            selected.append(stripped)
        if len(selected) >= 12:
            break
    return compact("; ".join(selected), 1700)


def answer_summary(code: str, name: str, petition: str, topic: str, context: str, raw: str) -> str:
    subject = f"{name}({code})" if code and name else (code or name or "공통사항")
    parts = [f"{subject}"]
    if context and context not in subject:
        parts.append(context)
    if petition:
        parts.append(petition)
    parts.append(topic)
    lead = " / ".join(part for part in parts if part)

    docs = extract_documents(raw) if topic == "제출서류" else ""
    body = docs or key_text(raw, max_lines=5, max_chars=650)
    if body:
        return compact(f"{lead}에 관한 정리입니다. {body}", 900)
    return compact(f"{lead}에 관한 정리입니다.", 300)


def evidence_quote(raw: str) -> str:
    for line in meaningful_lines(raw):
        if len(line) >= 25:
            return compact(line, 500)
    return compact(raw, 500)


def user_intents_for(code: str, topic: str, petition: str, name: str) -> str:
    hints = INTENT_HINTS.get(base_code(code), INTENT_HINTS["COMMON"] if not code else [])
    base = [f"{name} {topic}", f"{name} {petition}".strip()] if name else []
    if topic == "제출서류":
        base.extend(["필요서류", "어떤 서류를 준비해야 하나", "구비서류"])
    if topic in {"요건", "대상"}:
        base.extend(["자격요건", "대상 여부", "신청 가능 여부"])
    if topic == "절차":
        base.extend(["신청 방법", "어디에 신청", "절차"])
    if topic == "제한":
        base.extend(["불허 사유", "제한 업종", "신청 제한"])
    joined = []
    for value in [*hints, *base]:
        value = value.strip()
        if value and value not in joined:
            joined.append(value)
    return " | ".join(joined[:10])


def question_examples_for(code: str, name: str, topic: str, petition: str, context: str) -> str:
    subject = name or "공통사항"
    examples = [
        f"{subject} {petition} {topic}이 어떻게 되나요?".strip(),
        f"{subject} 신청할 때 {topic}을 알려주세요.",
    ]
    if context:
        examples.append(f"{context}의 {topic}은 무엇인가요?")
    if base_code(code) == "D-8":
        examples.append("외국인이 한국에서 법인을 만들고 살려면 어떤 비자가 맞나요?")
    elif base_code(code) == "E-7":
        examples.append("한국 회사가 외국 전문인력을 채용하려면 어떤 요건이 필요한가요?")
    elif base_code(code) == "F-6":
        examples.append("한국인과 결혼한 외국인은 어떤 서류와 절차가 필요한가요?")
    return " | ".join(dict.fromkeys(compact(example, 180) for example in examples if example))


def review_flags(element: Element, code: str, topic: str, raw: str) -> list[str]:
    notes: list[str] = []
    codes = detect_codes(raw)
    raw_len = len(strip_markup(raw))
    if element.is_table:
        notes.append("표 구조에서 추출: 열/행 의미 검수 필요")
    if len({base_code(c) for c in codes}) >= 3:
        notes.append("복수 코드 포함: 코드-규칙 연결 검수 필요")
    if not code and "공통" not in raw[:200] and "유의" not in raw[:200]:
        notes.append("대표 코드 없음: 공통/부록 여부 검수 필요")
    if raw_len > 4500:
        notes.append("긴 원문 블록: 추가 분할 또는 요약 검수 필요")
    if "image_url_placeholder" in raw or "![" in raw:
        notes.append("이미지/양식 포함: 원문 대조 필요")
    mixed_topics = sum(1 for label, keys in TOPIC_PRIORITY[:7] if any(key in raw[:1600] for key in keys))
    if mixed_topics >= 4:
        notes.append("여러 주제가 한 블록에 섞임: 분할 검수 필요")
    if topic == "일반":
        notes.append("주제 자동분류 약함: 검수 필요")
    return notes


def is_low_value_fragment(title: str, raw: str, code: str) -> bool:
    text = f"{title}\n{raw}"
    if code:
        return False
    low_value_markers = [
        "FOREIGNER OCCUPATION REPORT FORM",
        "OCCUPATION ( )",
        "Elementary Workers",
        "신청일 (Date of Application)",
        "신청인 (Applicant)",
        "대리인 ( By proxy )",
        "서명 또는 인",
        "외국인등록번호 Alien Registration No.",
    ]
    return any(marker in text for marker in low_value_markers)


def assign_topic_fields(topic: str, raw: str) -> dict[str, str]:
    content = key_text(raw)
    docs = extract_documents(raw)
    fields = {
        "conditions": "",
        "required_documents": "",
        "procedure": "",
        "restrictions": "",
        "exceptions": "",
    }
    if topic == "제출서류":
        fields["required_documents"] = docs or content
    elif topic in {"대상", "활동범위", "요건", "기간", "점수", "추천"}:
        fields["conditions"] = content
        if docs and topic in {"요건", "추천"}:
            fields["required_documents"] = docs
    elif topic == "절차":
        fields["procedure"] = content
        if docs:
            fields["required_documents"] = docs
    elif topic == "제한":
        fields["restrictions"] = content
    elif topic == "예외":
        fields["exceptions"] = content
    elif topic == "수수료":
        fields["procedure"] = content
    else:
        fields["conditions"] = content
    return fields


def build_semantic_rows(manual_key: str, markdown: str) -> list[dict[str, str]]:
    manual = MANUALS[manual_key]
    elements = iter_elements(markdown)
    rows: list[dict[str, str]] = []

    current_code = ""
    current_name = "공통사항"
    current_section = "공통사항"
    current_petition = "사증발급" if manual_key == "visa" else ""
    current_context = ""

    for element in elements:
        title = clean_title(element.title)
        raw_plain = strip_markup(element.raw)
        title_codes = detect_codes(title)

        # Cover pages and table-of-contents rows are navigation, not knowledge.
        if element.page_no == 1 and not title_codes:
            continue
        if element.page_no <= 2 and element.is_table:
            continue
        if element.page_no <= 2 and title_codes and re.match(r"^\d+\.\s+", title):
            continue

        if element.kind == "context":
            if is_main_section_title(title):
                detected = detect_codes(title)
                current_code = base_code(detected[0])
                current_name = code_name(current_code) or current_name
                current_section = f"{current_name}({current_code})"
                current_petition = "사증발급" if manual_key == "visa" else ""
                current_context = ""
            continue

        if len(raw_plain) < 45:
            continue
        if title in {"목차", "▶ 목차", "▣ 목차"} and len(raw_plain) < 180:
            continue
        if is_low_value_fragment(title, raw_plain, current_code):
            continue

        if is_main_section_title(title):
            detected = detect_codes(title)
            current_code = base_code(detected[0])
            current_name = code_name(current_code) or current_name
            current_section = f"{current_name}({current_code})"
            current_petition = "사증발급" if manual_key == "visa" else ""
            current_context = ""

        raw_codes = detect_codes(raw_plain[:1400])
        row_code = current_code
        for candidate in title_codes:
            if current_code and base_code(candidate) == base_code(current_code):
                row_code = candidate
                break
        if not row_code and title_codes and title_has_main_name(title, title_codes[0]):
            row_code = base_code(title_codes[0])
            current_code = row_code
            current_name = code_name(row_code) or current_name
            current_section = f"{current_name}({row_code})"

        row_name = code_name(row_code) if row_code else "공통사항"
        if title in {"유 의 사 항", "유의사항", "공 통 사 항", "공통사항"}:
            current_section = clean_title(title)
            row_name = "공통사항"
            row_code = ""
            current_code = ""
            current_name = "공통사항"

        detected_petition = detect_petition_type(title, raw_plain, manual_key, current_petition)
        if detected_petition:
            current_petition = detected_petition
        petition = detected_petition or current_petition
        topic = detect_topic_type(title, raw_plain)

        if looks_like_context(title) and not is_main_section_title(title):
            current_context = title
        context = current_context
        if topic in {"대상", "활동범위"} and not context:
            context = title if title not in GENERIC_TITLES else ""

        fields = assign_topic_fields(topic, raw_plain)
        summary = answer_summary(row_code, row_name, petition, topic, context, raw_plain)
        intents = user_intents_for(row_code, topic, petition, row_name)
        questions = question_examples_for(row_code, row_name, topic, petition, context)
        source_path_parts = [current_section]
        if petition:
            source_path_parts.append(petition)
        if context and context not in source_path_parts:
            source_path_parts.append(context)
        if title and title not in source_path_parts:
            source_path_parts.append(title)
        source_section_path = " > ".join(part for part in source_path_parts if part)

        notes = review_flags(element, row_code, topic, raw_plain)
        ai_search_text = compact(
            " ".join(
                part
                for part in [
                    manual["manual_type"],
                    row_code,
                    row_name,
                    petition,
                    topic,
                    context,
                    intents,
                    questions,
                    summary,
                    fields["conditions"],
                    fields["required_documents"],
                    fields["procedure"],
                    fields["restrictions"],
                    fields["exceptions"],
                ]
                if part
            ),
            3500,
        )

        row = {
            "manual_type": manual["manual_type"],
            "source_pdf": manual["source_pdf"],
            "source_section_path": compact(source_section_path, 600),
            "visa_code": row_code,
            "visa_name_ko": row_name,
            "petition_type": petition,
            "topic_type": topic,
            "applicant_context": compact(context, 500),
            "user_intents": intents,
            "question_examples": questions,
            "answer_summary": summary,
            "conditions": fields["conditions"],
            "required_documents": fields["required_documents"],
            "procedure": fields["procedure"],
            "restrictions": fields["restrictions"],
            "exceptions": fields["exceptions"],
            "ai_search_text": ai_search_text,
            "evidence_quote": evidence_quote(raw_plain),
            "source_raw_text": compact(raw_plain, 5000),
            "needs_human_review": "true" if notes else "false",
            "review_notes": "; ".join(notes),
        }

        # Drop obvious parse navigation fragments after their context was used.
        if row["answer_summary"].count("목차") >= 2 and len(row["source_raw_text"]) < 220:
            continue
        if title in GENERIC_TITLES and topic == "일반" and len(row["source_raw_text"]) < 180:
            continue

        rows.append(row)

    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str, str, str]] = set()
    out: list[dict[str, str]] = []
    for row in rows:
        key = (
            row["manual_type"],
            row["visa_code"],
            row["petition_type"],
            row["topic_type"],
            compact(row["source_raw_text"], 260),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def latest_markdown_path(manual_key: str) -> Path:
    paths = sorted(PARSED_DIR.glob(MANUALS[manual_key]["markdown_glob"]), key=lambda p: p.stat().st_mtime, reverse=True)
    if not paths:
        raise FileNotFoundError(f"No markdown file found for {manual_key}")
    return paths[0]


def write_csv(path: Path, rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SEMANTIC_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in SEMANTIC_COLUMNS})


def summarize_rows(rows: list[dict[str, str]]) -> dict[str, object]:
    return {
        "rows": len(rows),
        "review_rows": sum(row["needs_human_review"] == "true" for row in rows),
        "topic_counts": Counter(row["topic_type"] for row in rows).most_common(),
        "petition_counts": Counter(row["petition_type"] for row in rows).most_common(),
        "top_code_counts": Counter(row["visa_code"] or "COMMON" for row in rows).most_common(20),
    }


def main() -> None:
    summary: dict[str, object] = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "schema": SEMANTIC_COLUMNS,
        "manuals": {},
    }
    for manual_key in ["stay", "visa"]:
        source_path = latest_markdown_path(manual_key)
        markdown = source_path.read_text(encoding="utf-8")
        rows = build_semantic_rows(manual_key, markdown)
        output_path = PROCESSED_DIR / MANUALS[manual_key]["output_csv"]
        write_csv(output_path, rows)
        summary["manuals"][manual_key] = {
            "markdown": str(source_path.relative_to(PROJECT_ROOT)),
            "output_csv": str(output_path.relative_to(PROJECT_ROOT)),
            **summarize_rows(rows),
        }

    summary_path = PROCESSED_DIR / "semantic_build_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
