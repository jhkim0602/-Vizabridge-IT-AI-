#!/usr/bin/env python3
"""Skill helper: report chatbot-enrichment progress for one manual.

Reads the semantic CSV and the normalized_chatbot Markdown, prints:
- total semantic rows
- already-enriched record_ids
- next pending row (row_index, primary_code, primary_name_ko, source_section_title)
- summary of the source row's semantic fields the LLM may want at hand

Exit code 0 if more work remains, 1 if everything is done.

Usage:
    python .claude/skills/vizabridge-enrich-chatbot/scripts/show_progress.py {stay|visa}
"""

from __future__ import annotations

import csv
import hashlib
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
NORMALIZED_CHATBOT_DIR = PROJECT_ROOT / "data" / "parsed" / "normalized_chatbot"


OPEN_MARKER_RE = re.compile(
    r"<!--\s*vizabridge-chatbot v1 source_row:\s*([^\s]+)\s+source_hash:\s*([^\s]+)\s*-->"
)
CLOSE_MARKER_RE = re.compile(r"<!--\s*end chatbot:\s*([^\s]+)\s*-->")


def derive_record_id(manual_key: str, row_index: int, primary_code: str) -> str:
    return f"{manual_key}-{row_index:05d}-{primary_code}"


def hash_semantic_row(row: dict[str, str]) -> str:
    serialized = "|".join(f"{k}={row.get(k, '')}" for k in sorted(row))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def load_semantic_rows(manual_key: str) -> list[dict[str, str]]:
    path = PROCESSED_DIR / f"{manual_key}_manual_semantic_clean.csv"
    if not path.exists():
        raise SystemExit(
            f"semantic CSV not found: {path}\n"
            f"먼저 normalize 스킬과 scripts/build_semantic_csv.py를 실행하세요."
        )
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_completed(manual_key: str) -> set[str]:
    path = NORMALIZED_CHATBOT_DIR / f"{manual_key}_manual.md"
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    opens = {m.group(1) for m in OPEN_MARKER_RE.finditer(text)}
    closes = {m.group(1) for m in CLOSE_MARKER_RE.finditer(text)}
    return opens & closes


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"stay", "visa"}:
        raise SystemExit("Usage: show_progress.py {stay|visa}")
    manual_key = sys.argv[1]
    code_field = "stay_status_code" if manual_key == "stay" else "visa_code"
    name_field = "stay_status_name_ko" if manual_key == "stay" else "visa_name_ko"

    rows = load_semantic_rows(manual_key)
    completed = load_completed(manual_key)

    pending: list[tuple[int, dict[str, str]]] = []
    for idx, row in enumerate(rows):
        primary_code = (row.get(code_field) or "").strip()
        if not primary_code:
            continue
        rid = derive_record_id(manual_key, idx, primary_code)
        if rid not in completed:
            pending.append((idx, row))

    print(f"manual:    {manual_key}")
    print(f"total:     {len(rows)} semantic rows")
    print(f"completed: {len(completed)}")
    print(f"pending:   {len(pending)}")

    if not pending:
        print()
        print("done. no pending rows.")
        return 1

    row_idx, row = pending[0]
    primary_code = (row.get(code_field) or "").strip()
    primary_name = (row.get(name_field) or "").strip()
    record_id = derive_record_id(manual_key, row_idx, primary_code)
    src_hash = hash_semantic_row(row)

    print()
    print("NEXT ROW:")
    print(f"  row_index:           {row_idx}")
    print(f"  record_id:           {record_id}")
    print(f"  source_hash:         {src_hash}")
    print(f"  primary_code:        {primary_code}")
    print(f"  primary_name_ko:     {primary_name}")
    print(f"  source_section_title: {row.get('section_title', '')}")
    print(f"  petition_type:       {row.get('petition_type', '')}")
    print(f"  subsection_type:     {row.get('subsection_type', '')}")
    print(f"  item_type:           {row.get('item_type', '')}")
    print()
    print("  Source row content (truncated):")
    for k in (
        "applicant_context",
        "eligibility",
        "target_persons",
        "mandatory_documents",
        "requirements",
        "restrictions",
        "fees",
        "duration_or_validity",
        "score_criteria",
        "quota_or_limit",
        "obligations",
        "recommendation_or_approval",
    ):
        v = (row.get(k) or "").strip()
        if not v:
            continue
        if len(v) > 120:
            v = v[:117] + "..."
        v = v.replace("\n", " / ")
        print(f"    {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
