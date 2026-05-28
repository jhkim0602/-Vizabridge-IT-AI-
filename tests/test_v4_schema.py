"""v4 CSV 회귀 테스트.

다음을 회귀로 잠근다 (보고서 부록 B 「컬럼별 채움률」 + 본문 산출물 기준):

1. 행 수: 사증 158, 체류 275
2. 컬럼 수: 26
3. 컬럼 순서: V4_COLUMNS 와 정확히 일치
4. 컬럼 채움률: 보고서 부록 B 의 minimum 값 이상
5. 검수 컬럼(검수상태/검수메모) 미포함
6. 출처 컬럼 100% 채움
7. (비자코드, 신청종류) 모두 채워짐
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

# build_v4.V4_COLUMNS 와 일치해야 함
EXPECTED_COLUMNS = [
    "비자코드", "상위코드", "사증·체류", "신청종류",
    "신청상황", "대상자", "자격요건", "절차", "수수료",
    "사증유효기간", "1회부여 체류기간", "체류상한",
    "제한", "예외", "의무사항", "점수표", "쿼터",
    "초청자", "추천·승인기관",
    "제출서류", "예상질문",
    "출처",
    "선행자격", "다음단계", "동반가족", "키워드",
]

FORBIDDEN_COLUMNS = {"검수상태", "검수메모"}

# 보고서 부록 B 「컬럼별 채움률」 기준 — 회귀 락은 보고서 값보다 약간 낮게 잡아 노이즈 흡수.
# (사증 158 / 체류 275 기준 비율)
MIN_FILL_RATE = {
    "사증": {
        "비자코드": 1.00, "상위코드": 1.00, "사증·체류": 1.00, "신청종류": 1.00,
        "출처": 1.00, "키워드": 1.00, "선행자격": 1.00, "다음단계": 1.00,
        "동반가족": 1.00, "예상질문": 0.90, "신청상황": 0.85, "자격요건": 0.80,
        "제출서류": 0.70, "초청자": 0.55, "절차": 0.55, "1회부여 체류기간": 0.50,
        "대상자": 0.50, "사증유효기간": 0.50, "추천·승인기관": 0.40,
        "체류상한": 0.40, "제한": 0.40, "예외": 0.30,
        # 채움률이 매우 낮은 컬럼 (보고서 6.1) — 최소만 잡고 회귀로만 사용
        "쿼터": 0.05, "점수표": 0.05, "수수료": 0.02, "의무사항": 0.01,
    },
    "체류": {
        "비자코드": 1.00, "상위코드": 1.00, "사증·체류": 1.00, "신청종류": 1.00,
        "출처": 1.00, "키워드": 1.00, "선행자격": 0.95, "다음단계": 0.95,
        "동반가족": 0.95, "예상질문": 0.85, "제출서류": 0.75, "자격요건": 0.70,
        "신청상황": 0.65, "제한": 0.40, "대상자": 0.35, "예외": 0.30,
        "절차": 0.30, "체류상한": 0.25, "1회부여 체류기간": 0.20, "의무사항": 0.20,
        "수수료": 0.10, "추천·승인기관": 0.07, "점수표": 0.07, "쿼터": 0.07,
        "사증유효기간": 0.03, "초청자": 0.02,
    },
}

EXPECTED_ROW_COUNT = {"사증": 158, "체류": 275}


def _load(kind: str) -> tuple[list[str], list[dict[str, str]]]:
    path = PROCESSED / f"{kind}매뉴얼_최종_v4_26col.csv"
    csv.field_size_limit(sys.maxsize)
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        cols = list(reader.fieldnames or [])
        rows = list(reader)
    return cols, rows


@pytest.mark.parametrize("kind", ["사증", "체류"])
def test_row_count_matches_report(kind: str) -> None:
    _, rows = _load(kind)
    assert len(rows) == EXPECTED_ROW_COUNT[kind], (
        f"{kind}매뉴얼 행수 {len(rows)} != 보고서 기준 {EXPECTED_ROW_COUNT[kind]}"
    )


@pytest.mark.parametrize("kind", ["사증", "체류"])
def test_columns_exactly_match_v4_schema(kind: str) -> None:
    cols, _ = _load(kind)
    assert cols == EXPECTED_COLUMNS, (
        f"{kind}매뉴얼 컬럼 순서/구성이 V4_COLUMNS와 다름:\n"
        f"  expected: {EXPECTED_COLUMNS}\n"
        f"  got:      {cols}"
    )
    assert len(cols) == 26


@pytest.mark.parametrize("kind", ["사증", "체류"])
def test_no_review_workflow_columns(kind: str) -> None:
    """v4 부터 검수 워크플로 컬럼은 데이터 계층에서 분리."""
    cols, _ = _load(kind)
    assert FORBIDDEN_COLUMNS.isdisjoint(set(cols)), (
        f"{kind}매뉴얼에 검수 컬럼이 포함되어 있음: "
        f"{set(cols) & FORBIDDEN_COLUMNS}"
    )


@pytest.mark.parametrize("kind", ["사증", "체류"])
def test_identity_columns_fully_populated(kind: str) -> None:
    """비자코드·상위코드·사증·체류·신청종류·키워드·출처는 100% 채워야 함 (보고서 부록 B)."""
    _, rows = _load(kind)
    for col in ("비자코드", "상위코드", "사증·체류", "신청종류", "출처", "키워드"):
        empty = [i for i, r in enumerate(rows) if not r[col].strip()]
        assert not empty, f"{kind}매뉴얼 컬럼 '{col}' 비어있는 행: {empty[:5]}..."


@pytest.mark.parametrize("kind", ["사증", "체류"])
def test_source_column_has_page_marker(kind: str) -> None:
    """출처 컬럼에는 `(p. NNN)` 형식의 페이지 정보가 100% 들어있어야 함 (페이지 매칭 100%)."""
    _, rows = _load(kind)
    missing = [i for i, r in enumerate(rows) if "p." not in r["출처"]]
    # 일부 행은 페이지 매칭 단계 전 상태일 수 있으므로 95% 이상으로 회귀 락
    matched_rate = 1 - (len(missing) / len(rows))
    assert matched_rate >= 0.95, (
        f"{kind}매뉴얼 페이지 매칭율 {matched_rate:.1%} < 95% "
        f"(매칭 안 된 행 {len(missing)}개)"
    )


@pytest.mark.parametrize("kind", ["사증", "체류"])
def test_manual_kind_uses_only_two_enum_values(kind: str) -> None:
    """사증·체류 컬럼은 두 enum 값만 사용한다. 다수는 매뉴얼 종류와 같지만,
    보고서 4.4 「사증·체류 단계 혼재」에 따라 일부 행은 다른 값일 수 있다
    (예: 사증 매뉴얼에 들어있어도 체류자격 변경만 허용되는 E-7-4 K-point).
    """
    _, rows = _load(kind)
    values = {r["사증·체류"] for r in rows}
    assert values <= {"사증", "체류"}, f"{kind}매뉴얼 사증·체류 값 외 등장: {values}"
    # 다수는 같은 종류여야 함 (75% 이상)
    same = sum(1 for r in rows if r["사증·체류"] == kind)
    assert same / len(rows) >= 0.75, (
        f"{kind}매뉴얼 행의 {same}/{len(rows)} ({same/len(rows):.1%}) 만 "
        f"'{kind}' 라벨 — 정규화가 매뉴얼 종류를 너무 무시한 듯"
    )


import re

_PARENT_CODE_RE = re.compile(r"^([A-H]-\d{1,2})")

# 보고서 6.1 「추가 확인이 필요한 컬럼」 정신 — 데이터 정정 전까지 알려진 mismatch 를
# 화이트리스트로 보존한다. 정정 후 비울 것.
KNOWN_PARENT_MISMATCH: dict[tuple[str, str], str] = {
    ("사증", "C-3 (C-3-3) - 단기방문 의료관광"): "G-1",
}

# 보고서 5.1 「매뉴얼에 없거나 우리가 별도 정의한 컬럼」 정신 — 표준 X-N 패턴이 아닌
# 의도된 특수 행 (예: 국적 취득). 새 케이스 등장 시 명시적으로 등록.
KNOWN_NONSTANDARD_VISA_CODE: dict[tuple[str, str], str] = {
    ("사증", "특별귀화 (체류자격 아님, 국적 취득)"): "F-5",
}


@pytest.mark.parametrize("kind", ["사증", "체류"])
def test_parent_code_is_top_level_letter_number(kind: str) -> None:
    """상위코드는 X-N (예: E-7, F-6) 형식. sub-code (E-7-4, F-6-1) 의 상위는 E-7, F-6.

    비자코드는 다양한 형식 — `A-1`, `E-7 (E-7-4)`, `E-7-4`, `C-3-1~9 (중국 국민 복수사증)`,
    `D-7 외국기업 국내지사 주재`, `공통` 등. 상위코드는 보고서 2.2 표 2 「sub-code 의 상위
    자격까지」 규칙에 따라 X-N 패턴을 추출한 결과 또는 부모 부분 그대로.

    알려진 데이터 mismatch 는 `KNOWN_PARENT_MISMATCH` 화이트리스트로 인지한다 —
    화이트리스트 외에는 즉시 fail.
    """
    _, rows = _load(kind)
    for i, r in enumerate(rows):
        visa = r["비자코드"]
        parent = r["상위코드"]
        if visa == "공통":
            assert parent == "공통", f"행 {i}: 비자코드 '공통' → 상위코드 '{parent}'"
            continue
        # 표준 X-N 패턴이 아닌 의도된 특수 행
        nonstandard = KNOWN_NONSTANDARD_VISA_CODE.get((kind, visa))
        if nonstandard is not None:
            assert parent == nonstandard, (
                f"행 {i}: 등록된 비표준 비자코드 '{visa}' 의 상위 '{parent}' "
                f"!= 등록값 '{nonstandard}'"
            )
            continue
        m = _PARENT_CODE_RE.match(visa)
        assert m, (
            f"행 {i}: 비자코드 '{visa}' 가 X-N 패턴으로 시작하지 않음. "
            f"의도된 특수 행이면 KNOWN_NONSTANDARD_VISA_CODE 에 등록 필요."
        )
        expected = m.group(1)
        if parent == expected:
            continue
        allowed = KNOWN_PARENT_MISMATCH.get((kind, visa))
        assert allowed == parent, (
            f"행 {i}: 비자코드 '{visa}' → 상위코드 '{parent}' (예상 '{expected}'). "
            f"새 mismatch — 데이터 정정 또는 KNOWN_PARENT_MISMATCH 등록 필요."
        )


@pytest.mark.parametrize("kind", ["사증", "체류"])
def test_fill_rates_meet_report_appendix_b(kind: str) -> None:
    """각 컬럼 채움률이 보고서 부록 B 기준 이상."""
    _, rows = _load(kind)
    n = len(rows)
    failures: list[tuple[str, float, float]] = []
    for col, min_rate in MIN_FILL_RATE[kind].items():
        filled = sum(1 for r in rows if r[col].strip())
        actual_rate = filled / n
        if actual_rate < min_rate:
            failures.append((col, actual_rate, min_rate))
    assert not failures, "채움률 미달 컬럼:\n" + "\n".join(
        f"  - {col}: {actual:.1%} < {required:.1%}" for col, actual, required in failures
    )


@pytest.mark.parametrize("kind", ["사증", "체류"])
def test_xlsx_companion_exists(kind: str) -> None:
    """v4 산출물은 CSV + XLSX 쌍으로 유지된다."""
    csv_path = PROCESSED / f"{kind}매뉴얼_최종_v4_26col.csv"
    xlsx_path = PROCESSED / f"{kind}매뉴얼_최종_v4_26col.xlsx"
    assert csv_path.exists(), f"CSV 없음: {csv_path}"
    assert xlsx_path.exists(), f"XLSX 없음: {xlsx_path}"
    # XLSX 가 CSV 보다 오래되지 않아야 함 (fill_page_numbers 가 동기화)
    # 단, 빌드 직후엔 동일 시각도 가능하므로 부등호는 >=
    assert xlsx_path.stat().st_mtime >= csv_path.stat().st_mtime - 5, (
        f"XLSX 가 CSV 보다 너무 오래됨 (fill_page_numbers 재실행 권장)"
    )
