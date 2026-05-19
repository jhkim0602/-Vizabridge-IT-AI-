"""검수용 CSV v2 스키마 — Single Source of Truth.

이 모듈은 Vizabridge 비자/체류 매뉴얼 검수용 CSV v2의 컬럼 순서,
Enum 사전, 빈 셀 정책, 그리고 행 단위 검증 함수를 한 곳에 모은
표준 정의 파일입니다. 모든 빌더·정규화·검수 스크립트는 본 모듈을
import 해서 컬럼명을 직접 참조해야 하며, 본 모듈을 거치지 않은
컬럼 추가/변경은 허용하지 않습니다.

상세 사양: docs/data_schema_v2.md
(저장소 루트 기준 상대경로. GitHub 점프 시 같은 commit 기준 문서 참조.)

규약:
- 빈 셀은 빈 문자열 ``""`` 로 통일한다. ``None`` / ``NaN`` / ``"-"`` /
  ``"내용없음"`` / ``"없음"`` 은 허용하지 않는다.
- 한 행 = (비자코드 × 신청종류) 1조합. 한 비자코드가 여러 신청종류를
  가지면 신청종류 수만큼 행이 펼쳐진다.
- ``MANUAL_KIND`` / ``PETITION_TYPES`` / ``REVIEW_STATUS`` 는 Enum
  집합이며 ``validate_row()`` 가 위반을 강제한다.
- CSV 파일 인코딩은 utf-8-sig 로 통일한다 (BOM 보존).
"""

from __future__ import annotations

from typing import Iterable


# ---------------------------------------------------------------------------
# 컬럼 정의 — 32개, 순서 확정 (v2, 2026-05-18)
# ---------------------------------------------------------------------------
#
# 그룹별 인덱스:
#   [0:5]   식별·분류     (5)
#   [5:22]  행정 내용     (17)
#   [22:26] 출처·추적     (4)
#   [26:29] 관계·검색     (3)
#   [29:32] 검수          (3)
#
# 컬럼명은 한국어. CSV header 그대로 사용된다.
COLUMNS: list[str] = [
    # 식별·분류 (5)
    "비자코드",
    "상위코드",
    "사증·체류",
    "신청종류",
    "하위프로그램",
    # 행정 내용 (17)
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
    # 출처·추적 (4)
    "원본파일",
    "섹션",
    "페이지",
    "원본 라인범위",
    # 관계·검색 (3)
    "연계비자",
    "키워드",
    "원문발췌",
    # 검수 (3)
    "예상질문",
    "검수상태",
    "검수메모",
]


# ---------------------------------------------------------------------------
# Enum 사전
# ---------------------------------------------------------------------------

#: 매뉴얼 구분. 2종으로 고정.
MANUAL_KIND: tuple[str, ...] = (
    "사증",
    "체류",
)

#: 신청종류. 13종 (Phase 2 audit 결과에 따라 추가 가능 — 추가 시 본 상수만
#: 갱신하고 호출처는 자동으로 동기화된다).
PETITION_TYPES: tuple[str, ...] = (
    # 사증 매뉴얼 측
    "사증발급",
    "사증발급인정서",
    "전자사증",
    # 체류 매뉴얼 측
    "체류자격 변경",
    "체류자격 부여",
    "체류기간 연장",
    "외국인등록",
    "거소신고",
    "재입국허가",
    "근무처 변경/추가",
    "체류자격외 활동허가",
    "고용변동 신고",
    # 매뉴얼 양쪽 공통 / 기타
    "공통사항",
)

#: 검수 상태. 사전값 "미검수" 로 초기화하고 사람이 단계적으로 갱신한다.
REVIEW_STATUS: tuple[str, ...] = (
    "미검수",
    "검수중",
    "검수완료",
    "이슈있음",
)


# ---------------------------------------------------------------------------
# 빈 셀 정책
# ---------------------------------------------------------------------------

#: 빈 셀의 표준 표현. None / NaN / "-" / "없음" 모두 BLANK 로 정규화한다.
BLANK: str = ""

#: 빈 셀로 강제 변환되어야 하는 후보 값들 (대소문자 무시 + strip 후 비교).
_BLANK_ALIASES: frozenset[str] = frozenset(
    {
        "",
        "-",
        "nan",
        "none",
        "null",
        "없음",
        "내용없음",
        "해당없음",
        "n/a",
        "na",
    }
)


def is_blank(value: object) -> bool:
    """값이 빈 셀로 간주되어야 하는지 판단한다.

    ``None`` 도 빈 셀로 본다. 검증 함수는 호출 전에 ``BLANK`` 로
    치환하는 것을 권장한다.
    """
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return value.strip().lower() in _BLANK_ALIASES


def normalize_blank(value: object) -> str:
    """ 빈 셀 후보 값을 ``BLANK`` 으로, 그 외는 ``str()`` 캐스팅 결과로 반환."""
    if is_blank(value):
        return BLANK
    return str(value)


# ---------------------------------------------------------------------------
# 검증
# ---------------------------------------------------------------------------


class SchemaError(ValueError):
    """행 단위 schema 위반."""


def _require_columns(row: dict[str, object]) -> None:
    missing = [c for c in COLUMNS if c not in row]
    if missing:
        raise SchemaError(f"누락된 컬럼: {missing}")
    extra = [k for k in row.keys() if k not in COLUMNS]
    if extra:
        raise SchemaError(f"허용되지 않은 컬럼: {extra}")


def _require_enum(name: str, value: str, allowed: Iterable[str]) -> None:
    if value == BLANK:
        # 빈 값 허용 여부는 컬럼별 정책. validate_row 에서 직접 강제한다.
        return
    if value not in tuple(allowed):
        raise SchemaError(
            f"'{name}' 값 {value!r} 은 enum 사전에 없습니다. "
            f"허용: {tuple(allowed)}"
        )


def validate_row(row: dict[str, object]) -> dict[str, str]:
    """행 dict 1건을 검증하고 정규화된 dict 를 돌려준다.

    검증 항목:
      1. 컬럼 집합이 :data:`COLUMNS` 와 정확히 일치하는가
      2. 빈 셀 후보 값 (``None`` / ``"-"`` / ``"없음"`` 등) 이 모두
         :data:`BLANK` 으로 치환되는가
      3. ``사증·체류`` 가 :data:`MANUAL_KIND` 안에 있는가 (필수)
      4. ``신청종류`` 가 :data:`PETITION_TYPES` 안에 있는가 (필수)
      5. ``검수상태`` 가 :data:`REVIEW_STATUS` 안에 있는가 (필수, 기본
         ``"미검수"`` 자동 보정)

    위반 시 :class:`SchemaError` 발생. 정상 시 모든 값이 ``str`` 으로
    정규화된 새 dict 를 반환한다.
    """
    _require_columns(row)

    out: dict[str, str] = {col: normalize_blank(row[col]) for col in COLUMNS}

    # 검수상태: 빈 값은 사전값 "미검수" 로 자동 보정
    if out["검수상태"] == BLANK:
        out["검수상태"] = "미검수"

    # 필수 enum 컬럼
    if out["사증·체류"] == BLANK:
        raise SchemaError("'사증·체류' 컬럼은 비울 수 없습니다.")
    if out["신청종류"] == BLANK:
        raise SchemaError("'신청종류' 컬럼은 비울 수 없습니다.")

    _require_enum("사증·체류", out["사증·체류"], MANUAL_KIND)
    _require_enum("신청종류", out["신청종류"], PETITION_TYPES)
    _require_enum("검수상태", out["검수상태"], REVIEW_STATUS)

    # 비자코드는 검수 행의 식별자. 공통/총칙 행은 "공통" 같은 명시 토큰을
    # 쓰도록 권장하되 enum 으로 묶지 않는다 (자유 텍스트 + 비어있지만 않음).
    if out["비자코드"] == BLANK:
        raise SchemaError("'비자코드' 컬럼은 비울 수 없습니다 (공통 행도 '공통' 등으로 명시).")

    return out


def validate_rows(rows: Iterable[dict[str, object]]) -> list[dict[str, str]]:
    """행 시퀀스 전체를 검증·정규화한다.

    위반 시 첫 위반에서 ``SchemaError`` 가 던져진다. 에러 메시지에
    행 인덱스를 부착한다.
    """
    normalized: list[dict[str, str]] = []
    for i, row in enumerate(rows):
        try:
            normalized.append(validate_row(row))
        except SchemaError as exc:
            raise SchemaError(f"[행 {i}] {exc}") from exc
    return normalized


# ---------------------------------------------------------------------------
# 데코레이터
# ---------------------------------------------------------------------------


def enforce_schema(func):
    """행 dict 를 반환하는 함수에 schema 검증을 부착한다.

    예::

        @enforce_schema
        def build_row(...): -> dict:
            return {...}

    반환값이 dict 면 :func:`validate_row`, list[dict] 면
    :func:`validate_rows` 를 자동 적용한다.
    """

    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, dict):
            return validate_row(result)
        if isinstance(result, list):
            return validate_rows(result)
        raise TypeError(
            f"enforce_schema: 함수 {func.__name__} 의 반환 타입이 "
            f"dict / list[dict] 가 아닙니다 ({type(result).__name__})."
        )

    wrapper.__wrapped__ = func  # type: ignore[attr-defined]
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


# ---------------------------------------------------------------------------
# 헤더 추출 (CSV writer 용)
# ---------------------------------------------------------------------------


def empty_row() -> dict[str, str]:
    """모든 컬럼이 :data:`BLANK` 인 빈 행을 만든다 (테스트·템플릿 용)."""
    return {col: BLANK for col in COLUMNS}


__all__ = [
    "BLANK",
    "COLUMNS",
    "MANUAL_KIND",
    "PETITION_TYPES",
    "REVIEW_STATUS",
    "SchemaError",
    "empty_row",
    "enforce_schema",
    "is_blank",
    "normalize_blank",
    "validate_row",
    "validate_rows",
]
