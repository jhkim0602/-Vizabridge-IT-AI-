"""정규화 row 의 subsection_type / 필드를 32컬럼 v2 스키마의 17 행정구획에 매핑.

매핑 규칙 (사양):
  subsection_type → 기본 행정구획 컬럼
    "대상"      → "대상"
    "요건"      → "자격요건"
    "제출서류"  → "제출서류"
    "절차"      → "절차"
    "수수료"    → "수수료"
    "기간"      → "기간"
    "제한"      → "제한"
    "예외"      → "예외"
    "점수표"    → "점수표"
    "쿼터"      → "쿼터"
  그 외 (예: 공통사항/의무사항/표 데이터 자체) → "참고사항"

  필드 단위 (subsection_type 과 별개로 항상 적용):
    applicant_context        → "신청상황"
    target_persons           → "대상"  (subsection 매핑과 합쳐짐)
    eligibility              → "자격요건"  (subsection 매핑과 합쳐짐)
    common/mandatory/other
      _documents             → "제출서류"  (라벨 없이 합쳐 한 셀로)
    requirements             → "자격요건"
    procedure                → "절차"
    fees                     → "수수료"
    duration_or_validity     → "기간"
    restrictions             → "제한"
    exceptions               → "예외"
    score_criteria           → "점수표"
    quota_or_limit           → "쿼터"
    obligations              → "의무사항"
    inviter_context          → "초청자"           (사증 전용)
    recommendation_or_approval → "추천·승인기관"  (사증 전용)
    table_summary, table_rows → "표 데이터"

  분류 안 되는 자유 텍스트는 "참고사항" 으로.
"""

from __future__ import annotations


# subsection_type → 컬럼 (참고사항 폴백)
SUBSECTION_TO_COLUMN: dict[str, str] = {
    "대상": "대상",
    "요건": "자격요건",
    "제출서류": "제출서류",
    "절차": "절차",
    "수수료": "수수료",
    "기간": "기간",
    "제한": "제한",
    "예외": "예외",
    "점수표": "점수표",
    "쿼터": "쿼터",
    # 사양상 명시 매핑은 위 10개. 미스이면 참고사항으로 보냄.
}

#: 17 행정구획 컬럼 (검증/초기화 용).
ADMIN_COLUMNS: tuple[str, ...] = (
    "신청상황",
    "대상",
    "자격요건",
    "제출서류",
    "절차",
    "수수료",
    "기간",
    "제한",
    "예외",
    "의무사항",
    "공통사항",
    "점수표",
    "쿼터",
    "초청자",
    "추천·승인기관",
    "표 데이터",
    "참고사항",
)


def subsection_to_column(subsection: str) -> str:
    """subsection_type 문자열을 행정구획 컬럼명으로 변환. 미스 시 '참고사항'."""
    return SUBSECTION_TO_COLUMN.get(subsection.strip(), "참고사항")


def documents_blob(common: str, mandatory: str, other: str) -> str:
    """공통/필수/기타 서류를 라벨 없이 한 셀로 합친다.

    셋 모두 빈 값이면 빈 문자열. 비어있지 않은 것끼리만 줄바꿈으로 합침.
    """
    parts = [s.strip() for s in (common, mandatory, other) if s and s.strip()]
    return "\n".join(parts)


def table_blob(summary: str, rows: str) -> str:
    """표 요약/행을 한 셀로 합친다. 둘 다 비면 빈 문자열."""
    bits: list[str] = []
    if summary and summary.strip():
        bits.append(summary.strip())
    if rows and rows.strip():
        bits.append(rows.strip())
    return "\n".join(bits)
