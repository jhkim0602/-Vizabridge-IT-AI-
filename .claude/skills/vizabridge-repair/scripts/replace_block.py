#!/usr/bin/env python3
"""Skill helper: atomically replace one chunk block in the normalized file.

The repair skill writes a corrected block to a temp file, then calls:

    python .claude/skills/vizabridge-repair/scripts/replace_block.py \
        {stay|visa} {chunk_id} /tmp/vizabridge_repair_block.md

Validations:
- chunk_id exists in the index AND in the existing normalized file
- new block's open marker chunk_id matches
- new block's source_hash matches the index (no drift)
- new block has both open and close markers
- each ### row has the required fields

On success: replace the old (open..close) span with the new block.
Atomic via temp file + os.replace.
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
        rec = json.loads(line)
        if rec["chunk_id"] == chunk_id:
            return rec
    fail(f"chunk_id not in index: {chunk_id}")


def find_existing_block(normalized_text: str, chunk_id: str) -> tuple[int, int]:
    """Return (start, end) absolute char offsets in normalized_text covering the
    entire old block (from its open marker's start to its close marker's end).
    """
    open_iter = list(OPEN_MARKER_RE.finditer(normalized_text))
    for open_m in open_iter:
        if open_m.group(1) != chunk_id:
            continue
        # Find matching close
        close_m = None
        for cand in CLOSE_MARKER_RE.finditer(normalized_text, pos=open_m.end()):
            if cand.group(1) == chunk_id:
                close_m = cand
                break
        if not close_m:
            fail(f"existing block for {chunk_id} has no close marker")
        return open_m.start(), close_m.end()
    fail(f"chunk_id {chunk_id} not present in normalized file")


def validate_new_block(text: str, chunk_id: str, expected_hash: str) -> None:
    open_match = OPEN_MARKER_RE.search(text)
    if not open_match:
        fail("missing open marker")
    if open_match.group(1) != chunk_id:
        fail(f"open marker chunk_id mismatch: {open_match.group(1)} != {chunk_id}")
    if open_match.group(2) != expected_hash:
        fail(
            f"source_hash drift: new block has {open_match.group(2)}, index has {expected_hash}. "
            f"This is a re-normalize, not a repair."
        )
    close_match = CLOSE_MARKER_RE.search(text)
    if not close_match:
        fail("missing close marker")
    if close_match.group(1) != chunk_id:
        fail(f"close marker chunk_id mismatch: {close_match.group(1)} != {chunk_id}")
    if close_match.start() < open_match.end():
        fail("close marker before open marker")

    body = text[open_match.end() : close_match.start()]
    row_bodies = ROW_HEADER_RE.split(body)[1:]
    for i, row_body in enumerate(row_bodies):
        fields = set(FIELD_LINE_RE.findall(row_body))
        missing = REQUIRED_ROW_FIELDS - fields
        if missing:
            fail(f"row {i+1}: missing required fields: {sorted(missing)}")


def atomic_replace(target: Path, old_span: tuple[int, int], new_text: str) -> None:
    existing = target.read_text(encoding="utf-8")
    start, end = old_span
    # Trim trailing blank lines on either side for clean spacing
    new_text = new_text.strip() + "\n"
    rebuilt = existing[:start].rstrip() + "\n\n" + new_text + existing[end:].lstrip()
    fd, tmp_path = tempfile.mkstemp(dir=str(target.parent), prefix=".repair.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(rebuilt)
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

    target = NORMALIZED_DIR / f"{args.manual_key}_manual.md"
    if not target.exists():
        fail(f"normalized file does not exist: {target}")

    if not args.block_file.exists():
        fail(f"block file not found: {args.block_file}")
    new_block = args.block_file.read_text(encoding="utf-8")
    validate_new_block(new_block, args.chunk_id, meta["content_hash"])

    existing_text = target.read_text(encoding="utf-8")
    old_span = find_existing_block(existing_text, args.chunk_id)

    atomic_replace(target, old_span, new_block)
    print(f"OK: replaced {args.chunk_id} in {target.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
