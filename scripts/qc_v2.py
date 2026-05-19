#!/usr/bin/env python3
"""v2 검수용 CSV 품질 점검 스크립트.

체크 항목:
  1. 32컬럼 모두 존재
  2. enum 컬럼 위반 (사증·체류 / 신청종류 / 검수상태) — ``schema.validate_row``
  3. 빈 셀 정책 — NaN / null / "-" / "내용없음" 등 금지 토큰 검출
  4. 채움률 by column
  5. 행 수, 비자코드 종류, 신청종류 분포

산출물:
- output/quality/v2/{stay,visa}_fill_rates.csv
- output/quality/v2/{stay,visa}_enum_violations.csv  (위반이 있을 때만)
- output/quality/v2/{stay,visa}_blank_violations.csv (위반이 있을 때만)
- output/quality/v2/v2_quality_report.md
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from schema import (  # noqa: E402
    COLUMNS,
    MANUAL_KIND,
    PETITION_TYPES,
    REVIEW_STATUS,
    SchemaError,
    _BLANK_ALIASES,
    validate_row,
)

SRC_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "output" / "quality" / "v2"

INPUT_FILES = {
    "stay": "체류매뉴얼_검수용_v2.csv",
    "visa": "사증매뉴얼_검수용_v2.csv",
}

# 빈 셀 정책 위반 후보. schema._BLANK_ALIASES 에서 BLANK("") 자체는 제외.
FORBIDDEN_BLANK_TOKENS = {t for t in _BLANK_ALIASES if t != ""}


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def check_columns(rows: list[dict[str, str]]) -> tuple[bool, list[str], list[str]]:
    if not rows:
        return False, COLUMNS, []
    keys = list(rows[0].keys())
    missing = [c for c in COLUMNS if c not in keys]
    extra = [c for c in keys if c not in COLUMNS]
    return (not missing and not extra), missing, extra


def fill_rates(rows: list[dict[str, str]]) -> list[tuple[str, int, int, float]]:
    n = len(rows)
    out: list[tuple[str, int, int, float]] = []
    for col in COLUMNS:
        filled = sum(1 for r in rows if (r.get(col) or "").strip() != "")
        rate = (filled / n) if n else 0.0
        out.append((col, filled, n, rate))
    return out


def enum_violations(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """schema.validate_row 가 잡는 enum / 필수값 위반을 모두 수집."""
    violations: list[dict[str, str]] = []
    for i, raw in enumerate(rows):
        row = {col: raw.get(col, "") for col in COLUMNS}
        try:
            validate_row(row)
        except SchemaError as exc:
            violations.append(
                {
                    "행번호": str(i + 2),  # CSV 1행은 header
                    "비자코드": row.get("비자코드", ""),
                    "사증·체류": row.get("사증·체류", ""),
                    "신청종류": row.get("신청종류", ""),
                    "검수상태": row.get("검수상태", ""),
                    "오류": str(exc),
                }
            )
    return violations


def blank_violations(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """금지된 빈 셀 토큰(``-``, ``없음`` 등)이 그대로 들어 있는 셀 검출."""
    out: list[dict[str, str]] = []
    for i, r in enumerate(rows):
        for col in COLUMNS:
            v = (r.get(col) or "").strip().lower()
            if v in FORBIDDEN_BLANK_TOKENS:
                out.append(
                    {
                        "행번호": str(i + 2),
                        "비자코드": r.get("비자코드", ""),
                        "컬럼": col,
                        "값": r.get(col, ""),
                    }
                )
    return out


def distribution(rows: list[dict[str, str]], col: str) -> list[tuple[str, int]]:
    return Counter(r.get(col, "") for r in rows).most_common()


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def write_dictcsv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def report_section(label: str, rows: list[dict[str, str]]) -> list[str]:
    lines: list[str] = []
    n = len(rows)
    visa_codes = sorted({r.get("비자코드", "") for r in rows})
    petitions = distribution(rows, "신청종류")
    manuals = distribution(rows, "사증·체류")

    lines.append(f"## {label}")
    lines.append("")
    lines.append(f"- 행 수: **{n}**")
    lines.append(f"- 비자코드 종류 수: **{len(visa_codes)}**")
    lines.append(f"- 사증·체류 분포: {manuals}")
    lines.append(f"- 신청종류 분포: {petitions}")
    lines.append("")

    # 컬럼 체크
    ok, missing, extra = check_columns(rows)
    lines.append(f"- 32컬럼 정합성: {'OK' if ok else 'FAIL'}")
    if missing:
        lines.append(f"  - 누락 컬럼: {missing}")
    if extra:
        lines.append(f"  - 잉여 컬럼: {extra}")
    lines.append("")

    # enum / blank 위반
    enums = enum_violations(rows)
    blanks = blank_violations(rows)
    lines.append(f"- enum 위반: **{len(enums)}**건")
    lines.append(f"- 금지된 빈 셀 토큰 위반: **{len(blanks)}**건")
    lines.append("")

    # 채움률
    rates = fill_rates(rows)
    lines.append("### 채움률 (상위 + 하위)")
    lines.append("")
    lines.append("| 컬럼 | 채움 | 전체 | 채움률 |")
    lines.append("|---|---:|---:|---:|")
    for col, filled, total, rate in rates:
        lines.append(f"| {col} | {filled} | {total} | {rate*100:.1f}% |")
    lines.append("")

    return lines


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report_lines: list[str] = ["# v2 검수용 CSV 품질 점검 보고서", ""]
    report_lines.append(f"- 매뉴얼 사전: {MANUAL_KIND}")
    report_lines.append(f"- 신청종류 사전: {PETITION_TYPES}")
    report_lines.append(f"- 검수상태 사전: {REVIEW_STATUS}")
    report_lines.append("")

    for key, fname in INPUT_FILES.items():
        rows = load_rows(SRC_DIR / fname)

        # 채움률 CSV
        rates = fill_rates(rows)
        write_csv(
            OUT_DIR / f"{key}_fill_rates.csv",
            ["컬럼", "채움", "전체", "채움률"],
            [[c, str(f), str(t), f"{r*100:.2f}%"] for c, f, t, r in rates],
        )

        # enum 위반 CSV (위반이 있을 때만 파일 생성)
        enums = enum_violations(rows)
        if enums:
            write_dictcsv(
                OUT_DIR / f"{key}_enum_violations.csv",
                ["행번호", "비자코드", "사증·체류", "신청종류", "검수상태", "오류"],
                enums,
            )

        # blank 위반 CSV
        blanks = blank_violations(rows)
        if blanks:
            write_dictcsv(
                OUT_DIR / f"{key}_blank_violations.csv",
                ["행번호", "비자코드", "컬럼", "값"],
                blanks,
            )

        label = "체류매뉴얼" if key == "stay" else "사증매뉴얼"
        report_lines.extend(report_section(label, rows))

    (OUT_DIR / "v2_quality_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    print(f"  보고서: {OUT_DIR / 'v2_quality_report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
