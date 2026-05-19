#!/usr/bin/env python3
"""Skill helper: validate and atomically append one chunk block.

The skill writes a candidate block to a temp file (e.g. /tmp/vizabridge_block.md)
and then calls:

    python .claude/skills/vizabridge-normalize/scripts/append_block.py \
        {stay|visa} {chunk_id} /tmp/vizabridge_block.md

Validations:
- chunk_id exists in the chunk index
- the block opens with the correct vizabridge-normalize v1 marker
- open marker hash matches the index's content_hash
- block closes with the matching end marker
- chunk is not already present in the normalized file
- every ### row has the required fields per column_schema.md

On success: append (atomic via temp file + os.replace) and report a one-line
summary. Exit 0.

On failure: print the specific check that failed, do not touch the
normalized file, exit non-zero.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
CHUNKS_DIR = PROJECT_ROOT / "data" / "parsed" / "chunks"
NORMALIZED_DIR = PROJECT_ROOT / "data" / "parsed" / "normalized"


OPEN_MARKER_RE = re.compile(
    r"<!--\s*vizabridge-normalize v1 chunk:\s*([^\s]+)\s+hash:\s*([^\s]+)\s+lines:\s*(\d+)-(\d+)\s*-->"
)
CLOSE_MARKER_RE = re.compile(r"<!--\s*end chunk:\s*([^\s]+)\s*-->")
ROW_HEADER_RE = re.compile(r"^###\s+row\s+", re.MULTILINE)
FIELD_LINE_RE = re.compile(r"^-\s+([a-z_]+):", re.MULTILINE)

REQUIRED_ROW_FIELDS = {
    "manual_type",
    "item_type",
    "section_title",
    "petition_type",
    "subsection_type",
}
REQUIRED_STAY_FIELDS = {"stay_status_code", "stay_status_name_ko"}
REQUIRED_VISA_FIELDS = {"visa_code", "visa_name_ko"}

# Optional v2 enrichment fields. Not required, but the validator must not
# reject blocks that include them. The current FIELD_LINE_RE + subset check
# (REQUIRED_ROW_FIELDS - fields) already permits unknown extras; this set is
# kept here as a reference / documentation aid only.
OPTIONAL_V2_FIELDS = {
    "keywords",
    "source_page",
    "source_excerpt",
    "related_visa_codes",
    "expected_questions",
}


def fail(msg: str) -> "no return":
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(2)


def load_chunk_meta(manual_key: str, chunk_id: str) -> dict:
    path = CHUNKS_DIR / f"{manual_key}_chunks_index.jsonl"
    if not path.exists():
        fail(f"chunk index not found: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record["chunk_id"] == chunk_id:
            return record
    fail(f"chunk_id not in index: {chunk_id}")


def chunk_already_present(manual_key: str, chunk_id: str) -> bool:
    path = NORMALIZED_DIR / f"{manual_key}_manual.md"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return any(m.group(1) == chunk_id for m in OPEN_MARKER_RE.finditer(text))


def validate_block(text: str, manual_key: str, expected_chunk_id: str, expected_hash: str) -> None:
    open_match = OPEN_MARKER_RE.search(text)
    if not open_match:
        fail("missing open marker (vizabridge-normalize v1 chunk: ...)")
    if open_match.group(1) != expected_chunk_id:
        fail(f"open marker chunk_id mismatch: {open_match.group(1)} != {expected_chunk_id}")
    if open_match.group(2) != expected_hash:
        fail(f"open marker hash mismatch: {open_match.group(2)} != {expected_hash}")

    close_match = CLOSE_MARKER_RE.search(text)
    if not close_match:
        fail("missing close marker (end chunk: ...)")
    if close_match.group(1) != expected_chunk_id:
        fail(f"close marker chunk_id mismatch: {close_match.group(1)} != {expected_chunk_id}")

    if close_match.start() < open_match.end():
        fail("close marker appears before open marker")

    # Validate each row block has required fields.
    body = text[open_match.end() : close_match.start()]
    rows = ROW_HEADER_RE.split(body)
    # First element before the first ### row is allowed pre-row whitespace.
    row_bodies = rows[1:]
    for i, row_body in enumerate(row_bodies):
        fields = set(FIELD_LINE_RE.findall(row_body))
        missing = REQUIRED_ROW_FIELDS - fields
        if missing:
            fail(f"row {i+1}: missing required fields: {sorted(missing)}")
        if manual_key == "stay":
            missing_stay = REQUIRED_STAY_FIELDS - fields
            if missing_stay:
                fail(f"row {i+1}: missing stay-specific fields: {sorted(missing_stay)}")
        elif manual_key == "visa":
            missing_visa = REQUIRED_VISA_FIELDS - fields
            if missing_visa:
                fail(f"row {i+1}: missing visa-specific fields: {sorted(missing_visa)}")

    return None


def atomic_append(target: Path, block_text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    # Two blank lines between chunks for readability.
    separator = "\n\n" if existing and not existing.endswith("\n\n") else ""
    new_text = existing + separator + block_text.rstrip() + "\n"
    fd, tmp_path = tempfile.mkstemp(dir=str(target.parent), prefix=".normalized.", suffix=".tmp")
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
    parser.add_argument("chunk_id")
    parser.add_argument("block_file", type=Path)
    args = parser.parse_args()

    meta = load_chunk_meta(args.manual_key, args.chunk_id)

    if chunk_already_present(args.manual_key, args.chunk_id):
        fail(f"chunk already present in normalized file: {args.chunk_id}. Use repair skill instead.")

    if not args.block_file.exists():
        fail(f"block file not found: {args.block_file}")
    block_text = args.block_file.read_text(encoding="utf-8")
    validate_block(block_text, args.manual_key, args.chunk_id, meta["content_hash"])

    target = NORMALIZED_DIR / f"{args.manual_key}_manual.md"
    atomic_append(target, block_text)

    row_count = len(ROW_HEADER_RE.findall(block_text))
    print(f"OK: appended {args.chunk_id} → {target.relative_to(PROJECT_ROOT)} ({row_count} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
