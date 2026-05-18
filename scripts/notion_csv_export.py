#!/usr/bin/env python3
"""검수용 CSV → Notion import 친화 CSV.

기존 7컬럼 CSV에서:
- '문서유형'을 '신청종류 + 구획'으로 분리 (Notion Select 필터링 용이)
- 부모 비자코드(상위코드) 컬럼 추가 ("F-6 (F-6-1)" → "F-6")
- 검수상태(기본 '미검수'), 검수메모 컬럼 추가

산출물:
- data/processed/체류매뉴얼_노션검수용.csv
- data/processed/사증매뉴얼_노션검수용.csv

Notion UI에서 `+ Import → CSV`로 가져온 뒤 검수상태 컬럼을 Status type으로,
나머지 select 컬럼들을 Select type으로 전환만 하면 검수 시작 가능.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "data" / "processed"

INPUT_FILES = {
    "stay": "체류매뉴얼_검수용_최종.csv",
    "visa": "사증매뉴얼_검수용_최종.csv",
}
OUTPUT_FILES = {
    "stay": "체류매뉴얼_노션검수용.csv",
    "visa": "사증매뉴얼_노션검수용.csv",
}

OUTPUT_COLUMNS = [
    "비자코드",
    "상위코드",
    "사증·체류",
    "신청종류",
    "구획",
    "핵심내용",
    "제출서류",
    "예상질문",
    "출처",
    "검수상태",
    "검수메모",
]


PARENT_CODE_RE = re.compile(r"^([A-Z]-\d+(?:-[A-Z0-9]+)?)")


def parent_code(visa_code: str) -> str:
    """비자코드에서 상위코드 추출.

    예:
        "F-6 (F-6-1)" → "F-6"
        "E-7 (E-7-4)" → "E-7"
        "E-7-4"       → "E-7-4"
        "공통"        → "공통"
    """
    s = visa_code.strip()
    if not s:
        return ""
    # 괄호 앞부분이 있으면 우선
    head = s.split("(", 1)[0].strip()
    m = PARENT_CODE_RE.match(head)
    if m:
        return m.group(1)
    return head


def split_doctype(doc_type: str) -> tuple[str, str]:
    """'사증발급 / 제출서류' → ('사증발급', '제출서류')."""
    if " / " in doc_type:
        a, b = doc_type.split(" / ", 1)
        return a.strip(), b.strip()
    return doc_type.strip(), ""


def convert(manual_key: str) -> tuple[Path, int]:
    src_path = SRC_DIR / INPUT_FILES[manual_key]
    out_path = SRC_DIR / OUTPUT_FILES[manual_key]
    if not src_path.exists():
        raise SystemExit(f"입력 CSV 없음: {src_path}")

    with src_path.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    converted: list[dict[str, str]] = []
    for r in rows:
        sinchung, kuhwak = split_doctype(r.get("문서유형", ""))
        converted.append({
            "비자코드": r.get("비자코드", ""),
            "상위코드": parent_code(r.get("비자코드", "")),
            "사증·체류": r.get("사증·체류", ""),
            "신청종류": sinchung,
            "구획": kuhwak,
            "핵심내용": r.get("핵심내용", ""),
            "제출서류": r.get("제출서류", ""),
            "예상질문": r.get("예상질문", ""),
            "출처": r.get("출처", ""),
            "검수상태": "미검수",
            "검수메모": "",
        })

    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(converted)

    return out_path, len(converted)


def main() -> int:
    args = sys.argv[1:]
    manuals = args if args else ["stay", "visa"]
    for manual_key in manuals:
        if manual_key not in INPUT_FILES:
            raise SystemExit(f"unknown manual_key: {manual_key}")
        out_path, n = convert(manual_key)
        print(f"  {manual_key}: {n}행 → {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
