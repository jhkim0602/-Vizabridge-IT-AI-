#!/usr/bin/env python3
"""검수용 v2 CSV의 시스템적 품질 이슈를 일괄 보정한다.

처리 대상:
1. 키워드 컬럼: 비자코드 형태(D-2, F-6-1)·중복·빈 항목 제거 → 최대 8개로 cap
2. 수수료 컬럼: 빈 값/`수수료` 플레이스홀더 → 신청종류·상위코드에 따른 표준 수수료
   (공통 / 공통사항 행의 수수료 표를 단일 진실 원천으로 사용)
3. 연계비자 컬럼: 본인 비자코드(전체 또는 상위)가 들어가 있으면 제거 + 중복 제거
4. 예상질문 컬럼: 비자코드(F-6, E-7-4 등) 직접 노출 → 한글 자격명으로 치환
   (자주 등장하는 매핑 사용; 불가능하면 검수메모에 플래그)
5. 검수메모: 합본 행·F-2-71 부등호 반전 의심 같은 사람 검토 필요 케이스 플래그

CSV 위치:
- data/processed/체류매뉴얼_검수용_v2.csv
- data/processed/사증매뉴얼_검수용_v2.csv

용법::

    .venv/bin/python scripts/fixup_v2_csv.py

스키마는 그대로 유지(32컬럼). enum/blank 정책도 그대로.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.schema import COLUMNS  # noqa: E402


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FILES = {
    "stay": PROCESSED_DIR / "체류매뉴얼_검수용_v2.csv",
    "visa": PROCESSED_DIR / "사증매뉴얼_검수용_v2.csv",
}


# ---------------------------------------------------------------------------
# 1. 키워드 정리
# ---------------------------------------------------------------------------

# 비자코드 형식: A-1, F-6, E-7-4, F-2-7S, D-10-T 등
VISA_CODE_RE = re.compile(r"^[A-H]-\d+(?:-[0-9A-Z]+)*$")
KEYWORD_CAP = 8


def clean_keywords(value: str) -> str:
    """비자코드형 토큰을 제거하고 최대 8개로 cap. dedup."""
    if not value.strip():
        return ""
    tokens = [t.strip() for t in value.split(",") if t.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if VISA_CODE_RE.match(t):
            continue  # 비자코드는 별도 컬럼이 있음
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
        if len(out) >= KEYWORD_CAP:
            break
    return ", ".join(out)


# ---------------------------------------------------------------------------
# 2. 수수료 자동 채움 (체류 매뉴얼만)
# ---------------------------------------------------------------------------

# 공통 / 공통사항 행에서 가져온 표준 수수료. 출입국관리법 시행규칙 별표.
STAY_FEE_BASE = {
    "체류자격외 활동허가": "12만원",
    "근무처 변경/추가": "12만원",
    "체류자격 부여": "8만원",
    "체류자격 변경": "10만원",
    "체류기간 연장": "6만원",
    "재입국허가": "단수 3만원 / 복수 5만원",
    "외국인등록": "외국인등록증 발급·재발급 3만 5천원",
    "거소신고": "거소등록증 발급·재발급 3만 5천원",
}

# 상위코드별 특례 수수료 (F-5 영주, F-6 결혼이민)
STAY_FEE_EXCEPTIONS = {
    ("F-5", "체류자격 변경"): "20만원",
    ("F-6", "체류자격 부여"): "4만원",
    ("F-6", "체류기간 연장"): "3만원",
}


FEE_PLACEHOLDERS = {"수수료", "수 수 료", "심사수수료", "심사 수수료"}


def autofill_fee_stay(row: dict[str, str]) -> Optional[str]:
    """체류 매뉴얼 행의 수수료를 표준표로 자동 채움. 변경할 경우 새 값을 리턴, 아니면 None."""
    current = row["수수료"].strip()
    if current and current not in FEE_PLACEHOLDERS:
        return None  # 이미 의미 있는 값
    petition = row["신청종류"].strip()
    parent = row["상위코드"].strip()
    if not petition:
        return None
    # 특례 먼저
    if (parent, petition) in STAY_FEE_EXCEPTIONS:
        return STAY_FEE_EXCEPTIONS[(parent, petition)]
    # 일반 표
    if petition in STAY_FEE_BASE:
        return STAY_FEE_BASE[petition]
    return None


# 사증 매뉴얼 수수료는 비자별·국가별 편차가 커서 자동 채움 부적절.
# (영사관 비자신청 수수료는 30USD/40USD/면제 등 국적·체류기간별 달라짐)


# ---------------------------------------------------------------------------
# 3. 연계비자 자기참조 제거
# ---------------------------------------------------------------------------


def clean_related_visa(row: dict[str, str]) -> str:
    """연계비자에서 본인 비자코드(전체 또는 상위) 제거 + dedup."""
    if not row["연계비자"].strip():
        return ""
    own_codes = {row["상위코드"].strip()}
    # "F-6 (F-6-1)" 같이 sub-code가 있으면 그것도 own에 추가
    sub = re.search(r"\(([^)]+)\)", row["비자코드"])
    if sub:
        own_codes.add(sub.group(1).strip())
    own_codes.discard("")

    tokens = [t.strip() for t in row["연계비자"].split(",") if t.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t in own_codes:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return ", ".join(out)


# ---------------------------------------------------------------------------
# 4. 예상질문 비자코드 노출 자연어화
# ---------------------------------------------------------------------------

VISA_TO_KOREAN = {
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

# E-7-4, F-6-1 등 sub-code는 부모 코드 한글명 + sub 식별자
SUBCODE_RE = re.compile(r"\b([A-H]-\d+)-([0-9A-Z]+)\b")
# 단일 코드 (E-7, F-6 등)
CODE_RE = re.compile(r"\b([A-H]-\d+)\b")


def dehumanize_question(q: str) -> str:
    """질문에서 비자코드 노출을 한글 자격명으로 치환."""
    # sub-code 먼저 (longer match)
    def sub_replacer(m: re.Match) -> str:
        parent, sub = m.group(1), m.group(2)
        ko = VISA_TO_KOREAN.get(parent)
        if ko:
            return f"{ko}({parent}-{sub})"  # 한글명(원코드)
        return m.group(0)

    q = SUBCODE_RE.sub(sub_replacer, q)

    def code_replacer(m: re.Match) -> str:
        code = m.group(1)
        ko = VISA_TO_KOREAN.get(code)
        if ko:
            return f"{ko}"  # 한글명만 (자연어 톤)
        return code

    q = CODE_RE.sub(code_replacer, q)
    return q


def clean_expected_questions(value: str) -> str:
    if not value.strip():
        return ""
    lines = [l.strip() for l in value.split("\n") if l.strip()]
    cleaned = [dehumanize_question(l) for l in lines]
    # dedup (case-insensitive)
    seen: set[str] = set()
    out: list[str] = []
    for q in cleaned:
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
        if len(out) >= 4:
            break
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 5. 검수메모 자동 플래그 (사람 검토 필요)
# ---------------------------------------------------------------------------

MULTI_SUBCODE_PATTERN = re.compile(
    r"(?:F-5-\d+.*F-5-\d+.*F-5-\d+|G-1-\d+.*G-1-\d+.*G-1-\d+|D-3-\d+.*D-3-\d+.*D-3-\d+)"
)


def add_review_note(row: dict[str, str], stay: bool) -> str:
    """검수메모에 추가할 플래그 (없으면 빈 문자열). 기존 메모 prepend 형태."""
    notes: list[str] = []
    # 합본 행 — 자격요건/대상에 여러 sub-code가 동시에 나오는지
    combined_text = (row.get("자격요건", "") + " " + row.get("대상", "")
                     + " " + row.get("절차", ""))
    if MULTI_SUBCODE_PATTERN.search(combined_text):
        notes.append("[자동 플래그] 다수 sub-code 합본 행 — 분리 검토 필요")
    # F-2-71 부등호 반전 의심
    if "F-2-71" in row.get("비자코드", "") and "이상" in row.get("자격요건", ""):
        if "주체류자" in row.get("자격요건", "") and "국민소득" in row.get("자격요건", ""):
            notes.append("[자동 플래그] F-2-71 자격요건 부등호 검토 (raw: 주체류자 소득 '미만'일 때 자녀 부여)")
    # 수수료가 placeholder만 있고 자동 채움 못 한 경우
    if stay and row["수수료"].strip() in FEE_PLACEHOLDERS:
        notes.append("[자동 플래그] 수수료 컬럼 placeholder — 원본 대조 필요")

    new = " | ".join(notes)
    existing = row.get("검수메모", "").strip()
    if not new:
        return existing
    if existing:
        return f"{new} | {existing}"
    return new


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------


def fix_manual(manual_key: str) -> dict[str, int]:
    path = FILES[manual_key]
    stay = manual_key == "stay"
    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    stats = {
        "keyword_trimmed": 0,
        "fee_autofilled": 0,
        "related_visa_self_removed": 0,
        "expected_q_dehumanized": 0,
        "review_notes_added": 0,
    }

    for row in rows:
        # 1. 키워드
        new_kw = clean_keywords(row["키워드"])
        if new_kw != row["키워드"]:
            row["키워드"] = new_kw
            stats["keyword_trimmed"] += 1

        # 2. 수수료 (체류만)
        if stay:
            new_fee = autofill_fee_stay(row)
            if new_fee:
                row["수수료"] = new_fee
                stats["fee_autofilled"] += 1

        # 3. 연계비자
        new_rel = clean_related_visa(row)
        if new_rel != row["연계비자"]:
            row["연계비자"] = new_rel
            stats["related_visa_self_removed"] += 1

        # 4. 예상질문
        new_q = clean_expected_questions(row["예상질문"])
        if new_q != row["예상질문"]:
            row["예상질문"] = new_q
            stats["expected_q_dehumanized"] += 1

        # 5. 검수메모 자동 플래그
        new_note = add_review_note(row, stay)
        if new_note != row["검수메모"]:
            row["검수메모"] = new_note
            stats["review_notes_added"] += 1

    # 저장
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return stats


def main() -> int:
    args = sys.argv[1:]
    manuals = args if args else ["stay", "visa"]
    for m in manuals:
        if m not in FILES:
            raise SystemExit(f"unknown manual: {m}")
        s = fix_manual(m)
        print(f"  {m}: {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
