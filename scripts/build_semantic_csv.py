#!/usr/bin/env python3
"""Stage 6: build final semantic CSVs from normalized intermediate Markdown.

Reads ``data/parsed/normalized/{manual_key}_manual.md`` and writes
``data/processed/{manual_key}_manual_semantic_clean.csv``. No LLM call,
no fuzzy heuristics — strictly a deterministic parse of the canonical
Markdown format documented in
``.claude/skills/vizabridge-normalize/references/output_format.md``.

Schema is enforced: STAY_COLUMNS / VISA_COLUMNS lists below define the
output columns and their order. Missing fields become empty strings.
Unknown fields in the normalized file are dropped silently (forward
compatibility — the normalize skill can carry extra metadata without
breaking the CSV writer).

Usage:
    .venv/bin/python scripts/build_semantic_csv.py
    .venv/bin/python scripts/build_semantic_csv.py stay
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NORMALIZED_DIR = PROJECT_ROOT / "data" / "parsed" / "normalized"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


OPEN_MARKER_RE = re.compile(
    r"<!--\s*vizabridge-normalize v1 chunk:\s*([^\s]+)\s+hash:\s*([^\s]+)\s+lines:\s*(\d+)-(\d+)\s*-->"
)
CLOSE_MARKER_RE = re.compile(r"<!--\s*end chunk:\s*([^\s]+)\s*-->")
ROW_HEADER_RE = re.compile(r"^###\s+row\s+.*$", re.MULTILINE)
FIELD_LINE_RE = re.compile(r"^-\s+([a-z_]+):\s*(.*)$", re.MULTILINE)
MULTILINE_VALUE_START_RE = re.compile(r"^-\s+([a-z_]+):\s*\|\s*$")


COMMON_COLUMNS = [
    "manual_type",
    "source_pdf",
    "item_type",
    "section_title",
    "subtype_or_program",
    "petition_type",
    "subsection_type",
    "applicant_context",
    "eligibility",
    "target_persons",
    "common_documents",
    "mandatory_documents",
    "other_documents",
    "requirements",
    "procedure",
    "restrictions",
    "exceptions",
    "fees",
    "duration_or_validity",
    "quota_or_limit",
    "score_criteria",
    "table_summary",
    "table_rows",
    "normalized_text",
]

STAY_COLUMNS = [
    "stay_status_code",
    "stay_status_name_ko",
    *COMMON_COLUMNS,
    "obligations",
]

VISA_COLUMNS = [
    "visa_code",
    "visa_name_ko",
    *COMMON_COLUMNS,
    "inviter_context",
    "recommendation_or_approval",
]

SCHEMAS = {"stay": STAY_COLUMNS, "visa": VISA_COLUMNS}
SOURCE_PDF = {
    "stay": "260504 체류민원 자격별 안내 매뉴얼.hwp",
    "visa": "260504 사증민원 자격별 안내 매뉴얼.hwp",
}


def parse_row_body(body: str) -> dict[str, str]:
    """Parse ``- field: value`` lines and ``- field: |`` blocks."""
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
    """Yield (chunk_id, row_body_text) for every ### row block inside chunks."""
    opens = list(OPEN_MARKER_RE.finditer(normalized_text))
    close_by_id = {m.group(1): m for m in CLOSE_MARKER_RE.finditer(normalized_text)}
    for open_m in opens:
        chunk_id = open_m.group(1)
        close_m = close_by_id.get(chunk_id)
        if not close_m or close_m.start() < open_m.end():
            continue
        chunk_body = normalized_text[open_m.end() : close_m.start()]
        # Split on ### row headers
        positions = [m.start() for m in ROW_HEADER_RE.finditer(chunk_body)]
        if not positions:
            continue
        positions.append(len(chunk_body))
        for i in range(len(positions) - 1):
            row_text = chunk_body[positions[i] : positions[i + 1]]
            # Drop the header line itself
            row_lines = row_text.splitlines()
            yield chunk_id, "\n".join(row_lines[1:])


def build_csv(manual_key: str) -> tuple[Path, int]:
    schema = SCHEMAS[manual_key]
    norm_path = NORMALIZED_DIR / f"{manual_key}_manual.md"
    if not norm_path.exists():
        raise SystemExit(f"정규화 출력 없음: {norm_path}")
    text = norm_path.read_text(encoding="utf-8")

    rows: list[dict[str, str]] = []
    for chunk_id, body in iter_row_blocks(text):
        fields = parse_row_body(body)
        # Always set source_pdf from manual_key
        fields.setdefault("source_pdf", SOURCE_PDF[manual_key])
        # manual_type fallback
        fields.setdefault(
            "manual_type", "체류민원" if manual_key == "stay" else "사증민원"
        )
        rows.append(fields)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / f"{manual_key}_manual_semantic_clean.csv"
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=schema, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in schema})

    return out_path, len(rows)


def main() -> int:
    args = sys.argv[1:]
    manuals = args if args else ["stay", "visa"]
    for manual_key in manuals:
        if manual_key not in SCHEMAS:
            raise SystemExit(f"unknown manual_key: {manual_key}")
        try:
            out_path, n = build_csv(manual_key)
        except SystemExit as e:
            print(f"  {manual_key}: skipped ({e})")
            continue
        print(f"  {manual_key}: {n} rows → {out_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
