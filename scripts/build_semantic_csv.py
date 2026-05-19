#!/usr/bin/env python3
"""Stage 6 — 검수용 CSV v2 빌더 (32컬럼).

`data/parsed/normalized/{stay,visa}_manual.md`(정규화 중간 산출물)을 읽어
v2 스키마(32컬럼)에 맞는 검수용 CSV 두 개를 생성한다.

산출물:
    data/processed/체류매뉴얼_검수용_v2.csv
    data/processed/사증매뉴얼_검수용_v2.csv

행 단위:
    한 행 = (비자코드 × 신청종류) 1조합. 같은 묶음의 여러 normalized row
    (subsection_type 단위로 쪼개진 단편들)는 한 v2 행에 합쳐진다.

컬럼은 ``scripts/schema.py`` 의 ``COLUMNS`` 를 single source of truth 로
참조하고, 매 행마다 ``validate_row`` 로 enum 위반을 검증한다.

용법:
    .venv/bin/python scripts/build_semantic_csv.py
    .venv/bin/python scripts/build_semantic_csv.py stay
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

# 패키지 import 를 위해 프로젝트 루트를 sys.path 에 추가.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_helpers.aggregate import GroupAggregator  # noqa: E402
from scripts.build_helpers.sources import load_chunk_lines  # noqa: E402
from scripts.schema import COLUMNS, validate_rows  # noqa: E402


NORMALIZED_DIR = PROJECT_ROOT / "data" / "parsed" / "normalized"
CHUNKS_DIR = PROJECT_ROOT / "data" / "parsed" / "chunks"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


OPEN_MARKER_RE = re.compile(
    r"<!--\s*vizabridge-normalize v1 chunk:\s*([^\s]+)\s+hash:\s*([^\s]+)\s+lines:\s*(\d+)-(\d+)\s*-->"
)
CLOSE_MARKER_RE = re.compile(r"<!--\s*end chunk:\s*([^\s]+)\s*-->")
ROW_HEADER_RE = re.compile(r"^###\s+row\s+.*$", re.MULTILINE)
FIELD_LINE_RE = re.compile(r"^-\s+([a-z_]+):\s*(.*)$", re.MULTILINE)
MULTILINE_VALUE_START_RE = re.compile(r"^-\s+([a-z_]+):\s*\|\s*$")


OUTPUT_FILENAME = {
    "stay": "체류매뉴얼_검수용_v2.csv",
    "visa": "사증매뉴얼_검수용_v2.csv",
}


def parse_row_body(body: str) -> dict[str, str]:
    """`- field: value` 라인과 `- field: |` 멀티라인 블록을 파싱."""
    fields: dict[str, str] = {}
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        multi = MULTILINE_VALUE_START_RE.match(line)
        if multi:
            name = multi.group(1)
            collected: list[str] = []
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.startswith("    "):
                    collected.append(nxt[4:])
                    i += 1
                elif nxt.strip() == "" and i + 1 < len(lines) and lines[i + 1].startswith("    "):
                    collected.append("")
                    i += 1
                else:
                    break
            fields[name] = "\n".join(collected).rstrip()
            continue
        single = FIELD_LINE_RE.match(line)
        if single:
            fields[single.group(1)] = single.group(2).strip()
        i += 1
    return fields


def iter_row_blocks(normalized_text: str):
    """청크 마커 안의 모든 `### row` 블록을 (chunk_id, body) 로 yield."""
    opens = list(OPEN_MARKER_RE.finditer(normalized_text))
    close_by_id = {m.group(1): m for m in CLOSE_MARKER_RE.finditer(normalized_text)}
    for open_m in opens:
        chunk_id = open_m.group(1)
        close_m = close_by_id.get(chunk_id)
        if not close_m or close_m.start() < open_m.end():
            continue
        chunk_body = normalized_text[open_m.end() : close_m.start()]
        positions = [m.start() for m in ROW_HEADER_RE.finditer(chunk_body)]
        if not positions:
            continue
        positions.append(len(chunk_body))
        for i in range(len(positions) - 1):
            row_text = chunk_body[positions[i] : positions[i + 1]]
            row_lines = row_text.splitlines()
            yield chunk_id, "\n".join(row_lines[1:])


def build_csv(manual_key: str) -> tuple[Path, int, int]:
    norm_path = NORMALIZED_DIR / f"{manual_key}_manual.md"
    if not norm_path.exists():
        raise SystemExit(f"정규화 출력 없음: {norm_path}")
    text = norm_path.read_text(encoding="utf-8")

    chunk_lines = load_chunk_lines(CHUNKS_DIR / f"{manual_key}_chunks_index.jsonl")

    aggregator = GroupAggregator(manual_key)
    row_count = 0
    for chunk_id, body in iter_row_blocks(text):
        fields = parse_row_body(body)
        aggregator.add(fields, chunk_id)
        row_count += 1

    raw_rows = aggregator.finalize_rows(chunk_lines)

    # schema 검증 — enum 위반 시 SchemaError 가 즉시 raise 된다.
    validated = validate_rows(raw_rows)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / OUTPUT_FILENAME[manual_key]
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="raise")
        writer.writeheader()
        writer.writerows(validated)

    return out_path, len(validated), row_count


def _fill_stats(rows: list[dict[str, str]]) -> dict[str, float]:
    """각 컬럼의 채움률 (%, 0~100) 을 계산."""
    if not rows:
        return {col: 0.0 for col in COLUMNS}
    total = len(rows)
    out: dict[str, float] = {}
    for col in COLUMNS:
        filled = sum(1 for r in rows if r.get(col, "").strip())
        out[col] = 100.0 * filled / total
    return out


def main() -> int:
    args = sys.argv[1:]
    manuals = args if args else ["stay", "visa"]
    summary: list[str] = []
    for manual_key in manuals:
        if manual_key not in OUTPUT_FILENAME:
            raise SystemExit(f"unknown manual_key: {manual_key}")
        out_path, n_rows, n_src = build_csv(manual_key)
        # 채움률 리포트 (요약 컬럼만)
        with out_path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        stats = _fill_stats(rows)
        watched = ["키워드", "원문발췌", "예상질문", "참고사항"]
        rel = out_path.relative_to(PROJECT_ROOT)
        summary.append(
            f"  {manual_key}: src_rows={n_src} → groups={n_rows} cols={len(COLUMNS)} → {rel}"
        )
        summary.append(
            "    채움률: "
            + ", ".join(f"{k}={stats[k]:.1f}%" for k in watched)
        )
    print("\n".join(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
