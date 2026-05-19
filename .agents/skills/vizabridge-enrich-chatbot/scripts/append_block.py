#!/usr/bin/env python3
"""Skill helper: validate and atomically append one chatbot block.

Usage:
    python .claude/skills/vizabridge-enrich-chatbot/scripts/append_block.py \
        {stay|visa} {record_id} /tmp/vizabridge_chatbot_block.md

Validations:
- record_id format matches `{manual_key}-{row_index:05d}-{primary_code}`
- corresponding semantic row exists at row_index
- open marker present, record_id and source_hash match
- close marker present
- required fields present
- record_id not already in the output

Atomic append via temp file + os.replace.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
NORMALIZED_CHATBOT_DIR = PROJECT_ROOT / "data" / "parsed" / "normalized_chatbot"


OPEN_MARKER_RE = re.compile(
    r"<!--\s*vizabridge-chatbot v1 source_row:\s*([^\s]+)\s+source_hash:\s*([^\s]+)\s*-->"
)
CLOSE_MARKER_RE = re.compile(r"<!--\s*end chatbot:\s*([^\s]+)\s*-->")
FIELD_LINE_RE = re.compile(r"^-\s+([a-z_]+):", re.MULTILINE)
RECORD_ID_RE = re.compile(r"^([a-z]+)-(\d{5})-(.+)$")

REQUIRED_FIELDS = {
    "record_id",
    "source_dataset",
    "code_type",
    "primary_code",
    "primary_name_ko",
    "source_section_title",
    "user_situation_tags",
    "intent_keywords",
    "applicant_profile",
    "current_location_context",
    "current_status_context",
    "plain_language_summary",
    "required_user_info",
    "routing_hint",
    "answer_focus",
    "search_text",
}


def fail(msg: str) -> "no return":
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(2)


def parse_record_id(record_id: str) -> tuple[str, int, str]:
    m = RECORD_ID_RE.match(record_id)
    if not m:
        fail(f"record_id malformed: {record_id} (expected manual-NNNNN-CODE)")
    return m.group(1), int(m.group(2)), m.group(3)


def hash_semantic_row(row: dict[str, str]) -> str:
    serialized = "|".join(f"{k}={row.get(k, '')}" for k in sorted(row))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def load_semantic_rows(manual_key: str) -> list[dict[str, str]]:
    path = PROCESSED_DIR / f"{manual_key}_manual_semantic_clean.csv"
    if not path.exists():
        fail(f"semantic CSV not found: {path}")
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def chunk_already_present(manual_key: str, record_id: str) -> bool:
    path = NORMALIZED_CHATBOT_DIR / f"{manual_key}_manual.md"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return any(m.group(1) == record_id for m in OPEN_MARKER_RE.finditer(text))


def validate_block(text: str, record_id: str, expected_hash: str) -> None:
    open_match = OPEN_MARKER_RE.search(text)
    if not open_match:
        fail("missing open marker (vizabridge-chatbot v1 source_row: ...)")
    if open_match.group(1) != record_id:
        fail(f"open marker record_id mismatch: {open_match.group(1)} != {record_id}")
    if open_match.group(2) != expected_hash:
        fail(f"open marker source_hash mismatch: {open_match.group(2)} != {expected_hash}")

    close_match = CLOSE_MARKER_RE.search(text)
    if not close_match:
        fail("missing close marker (end chatbot: ...)")
    if close_match.group(1) != record_id:
        fail(f"close marker record_id mismatch: {close_match.group(1)} != {record_id}")
    if close_match.start() < open_match.end():
        fail("close marker appears before open marker")

    body = text[open_match.end() : close_match.start()]
    fields_seen = set(FIELD_LINE_RE.findall(body))
    missing = REQUIRED_FIELDS - fields_seen
    if missing:
        fail(f"missing required fields: {sorted(missing)}")


def atomic_append(target: Path, block_text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    separator = "\n\n" if existing and not existing.endswith("\n\n") else ""
    new_text = existing + separator + block_text.rstrip() + "\n"
    fd, tmp_path = tempfile.mkstemp(dir=str(target.parent), prefix=".chatbot.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_text)
        os.replace(tmp_path, target)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manual_key", choices=["stay", "visa"])
    parser.add_argument("record_id")
    parser.add_argument("block_file", type=Path)
    args = parser.parse_args()

    parsed_mk, row_idx, primary_code = parse_record_id(args.record_id)
    if parsed_mk != args.manual_key:
        fail(f"record_id prefix '{parsed_mk}' does not match manual_key '{args.manual_key}'")

    rows = load_semantic_rows(args.manual_key)
    if row_idx >= len(rows):
        fail(f"row_index {row_idx} out of range (only {len(rows)} rows)")
    semantic_row = rows[row_idx]
    code_field = "stay_status_code" if args.manual_key == "stay" else "visa_code"
    if (semantic_row.get(code_field) or "").strip() != primary_code:
        fail(
            f"primary_code mismatch: record_id has '{primary_code}', semantic row has "
            f"'{semantic_row.get(code_field)}'"
        )

    expected_hash = hash_semantic_row(semantic_row)

    if chunk_already_present(args.manual_key, args.record_id):
        fail(f"record_id already present: {args.record_id}. Skill should have detected this.")

    if not args.block_file.exists():
        fail(f"block file not found: {args.block_file}")
    block_text = args.block_file.read_text(encoding="utf-8")
    validate_block(block_text, args.record_id, expected_hash)

    target = NORMALIZED_CHATBOT_DIR / f"{args.manual_key}_manual.md"
    atomic_append(target, block_text)
    print(f"OK: appended {args.record_id} → {target.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
