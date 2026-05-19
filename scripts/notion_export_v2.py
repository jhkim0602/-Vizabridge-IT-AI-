#!/usr/bin/env python3
"""v2 검수용 CSV → Notion import 친화 CSV.

입력은 32컬럼 v2 CSV (``data/processed/{체류,사증}매뉴얼_검수용_v2.csv``).
출력은 컬럼 구성·순서는 동일하되 Notion import 친화 변환을 가한다:

- 첫 컬럼은 ``비자코드`` (Notion에서 Title 컬럼이 됨)
- ``검수상태`` 빈 값은 사전값 ``미검수`` 로 보정
- ``검수메모`` 는 빈 셀로 유지
- 줄바꿈은 그대로 보존하되 ``\\r\\n`` → ``\\n`` 통일
- 인코딩 utf-8-sig

산출물:
- data/processed/체류매뉴얼_노션검수용_v2.csv
- data/processed/사증매뉴얼_노션검수용_v2.csv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from schema import COLUMNS, validate_row  # noqa: E402

SRC_DIR = ROOT / "data" / "processed"

INPUT_FILES = {
    "stay": "체류매뉴얼_검수용_v2.csv",
    "visa": "사증매뉴얼_검수용_v2.csv",
}
OUTPUT_FILES = {
    "stay": "체류매뉴얼_노션검수용_v2.csv",
    "visa": "사증매뉴얼_노션검수용_v2.csv",
}


def normalize_newlines(value: str) -> str:
    """``\\r\\n`` / ``\\r`` 를 ``\\n`` 으로 통일."""
    if not isinstance(value, str):
        return value
    return value.replace("\r\n", "\n").replace("\r", "\n")


def convert(manual_key: str) -> tuple[Path, int]:
    src_path = SRC_DIR / INPUT_FILES[manual_key]
    out_path = SRC_DIR / OUTPUT_FILES[manual_key]
    if not src_path.exists():
        raise SystemExit(f"입력 CSV 없음: {src_path}")

    with src_path.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    converted: list[dict[str, str]] = []
    for r in rows:
        # 컬럼 정합성 확인 — 누락 컬럼이 있으면 빈 문자열로 채워서 schema에 맞춤.
        row = {col: r.get(col, "") for col in COLUMNS}
        # 줄바꿈 통일 + 빈 값 정규화는 schema.validate_row 가 처리.
        row = {col: normalize_newlines(v) for col, v in row.items()}
        validated = validate_row(row)
        converted.append(validated)

    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
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
