from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PARSED_DIR = PROJECT_ROOT / "data" / "parsed"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


COMMON_FIELDS = [
    "item_id",
    "manual_type",
    "source_pdf",
    "pdf_page_start",
    "pdf_page_end",
    "printed_page_start",
    "printed_page_end",
    "section_path",
    "item_type",
    "section_title",
    "subsection_type",
    "raw_text",
    "normalized_text",
    "table_summary",
    "table_rows",
    "evidence_quote",
    "extraction_source",
    "confidence",
    "needs_human_review",
    "review_notes",
]

STAY_FIELDS = [
    "stay_status_code",
    "stay_status_name_ko",
    "subtype_or_program",
    "petition_type",
    "eligibility",
    "requirements",
    "required_documents",
    "procedure",
    "restrictions",
    "exceptions",
    "obligations",
    "fees",
    "quota_or_limit",
    "score_criteria",
]

VISA_FIELDS = [
    "visa_code",
    "visa_name_ko",
    "subtype_or_program",
    "petition_type",
    "applicant_context",
    "inviter_context",
    "eligibility",
    "requirements",
    "required_documents",
    "procedure",
    "restrictions",
    "exceptions",
    "duration_or_validity",
    "recommendation_or_approval",
]

ALL_FIELDS = list(dict.fromkeys(COMMON_FIELDS + STAY_FIELDS + VISA_FIELDS))

MANUALS = {
    "stay": {
        "manual_type": "체류민원",
        "source_pdf": "260504 체류민원 자격별 안내 매뉴얼.pdf",
        "id_prefix": "stay",
        "markdown_glob": "stay_manual_llamaparse_agentic_plus_*.md",
        "critical_terms": ["D-2", "E-7", "E-7-4", "지역특화형", "점수표", "쿼터"],
        "sample_pages": {1, 2, 3, 4, 5, 6, 7, 8, 18, 59, 107, 147, 292},
    },
    "visa": {
        "manual_type": "사증민원",
        "source_pdf": "260504 사증민원 자격별 안내 매뉴얼.pdf",
        "id_prefix": "visa",
        "markdown_glob": "visa_manual_llamaparse_agentic_plus_*.md",
        "critical_terms": ["C-3", "D-8", "E-7", "F-6", "사증발급인정서", "복수사증"],
        "sample_pages": {1, 2, 3, 4, 5, 6, 7, 8, 12, 28, 93, 169, 180},
    },
}

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

SUSPICIOUS_TERMS = {"제목자격", "제목관리과", "제목족적"}

SUBSECTION_KEYWORDS = [
    ("제출서류", ["제출서류", "제출 서류", "첨부서류", "구비서류", "신청서류"]),
    ("수수료", ["수수료", "심사수수료"]),
    ("점수표", ["점수표", "배점", "점수제"]),
    ("쿼터", ["쿼터", "선발인원", "허용인원"]),
    ("신고의무", ["신고의무", "신고하여야", "제출 의무", "교육의무", "거주의무"]),
    ("절차", ["절차", "신청방법", "신청기관", "재외공관", "온라인", "하이코리아"]),
    ("제한", ["제한", "불허", "제외", "금지", "결격"]),
    ("예외", ["예외", "특례", "면제", "완화"]),
    ("요건", ["요건", "자격요건", "심사기준", "기준"]),
    ("대상", ["대상", "해당자", "신청대상", "발급대상", "적용대상"]),
]

PETITION_KEYWORDS = [
    ("체류자격외 활동허가", ["체류자격외 활동", "체류자격외활동", "자격외 활동"]),
    ("근무처 변경/추가", ["근무처의 변경", "근무처 변경", "근무처 추가"]),
    ("체류자격 변경", ["체류자격 변경허가", "체류자격 변경", "자격변경"]),
    ("체류기간 연장", ["체류기간 연장허가", "체류기간 연장", "기간연장"]),
    ("체류자격 부여", ["체류자격 부여"]),
    ("재입국허가", ["재입국허가"]),
    ("외국인등록", ["외국인등록", "등록사항 변경", "거소신고"]),
    ("사증발급인정서", ["사증발급인정서", "비자발급인정서"]),
    ("사증발급", ["사증발급", "사증 발급", "비자발급"]),
    ("초청", ["초청"]),
    ("전자사증", ["전자사증", "전자비자"]),
]


def empty_item() -> dict[str, str]:
    item = {field: "" for field in ALL_FIELDS}
    item["confidence"] = "0.00"
    item["needs_human_review"] = "false"
    return item
