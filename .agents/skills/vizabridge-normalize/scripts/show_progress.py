#!/usr/bin/env python3
"""Skill helper: report normalize-stage progress for one manual.

Reads the chunk index and the normalized output, prints:
- total chunks
- already-normalized chunk_ids
- next pending chunk (with its line range, char_count, visa_codes)
- last 3 completed (for quick spot-check)

Exit code 0 if more work remains, 1 if everything is done.

Usage:
    python .claude/skills/vizabridge-normalize/scripts/show_progress.py {stay|visa}
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
CHUNKS_DIR = PROJECT_ROOT / "data" / "parsed" / "chunks"
NORMALIZED_DIR = PROJECT_ROOT / "data" / "parsed" / "normalized"


OPEN_MARKER_RE = re.compile(
    r"<!--\s*vizabridge-normalize v1 chunk:\s*([^\s]+)\s+hash:\s*([^\s]+)\s+lines:\s*(\d+)-(\d+)\s*-->"
)
CLOSE_MARKER_RE = re.compile(r"<!--\s*end chunk:\s*([^\s]+)\s*-->")


def load_chunks(manual_key: str) -> list[dict]:
    path = CHUNKS_DIR / f"{manual_key}_chunks_index.jsonl"
    if not path.exists():
        raise SystemExit(f"청크 인덱스 없음: {path}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_completed(manual_key: str) -> tuple[set[str], dict[str, str]]:
    """Return (completed_chunk_ids, hash_by_chunk_id_from_normalized)."""
    path = NORMALIZED_DIR / f"{manual_key}_manual.md"
    if not path.exists():
        return set(), {}
    text = path.read_text(encoding="utf-8")
    opens = {m.group(1): m.group(2) for m in OPEN_MARKER_RE.finditer(text)}
    closes = {m.group(1) for m in CLOSE_MARKER_RE.finditer(text)}
    # Only chunks with both open AND close markers count as completed.
    completed = set(opens) & closes
    return completed, {cid: opens[cid] for cid in completed}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"stay", "visa"}:
        raise SystemExit("Usage: show_progress.py {stay|visa}")
    manual_key = sys.argv[1]

    chunks = load_chunks(manual_key)
    chunks_by_id = {c["chunk_id"]: c for c in chunks}
    completed_ids, completed_hashes = load_completed(manual_key)

    # Hash drift check: warn if a completed chunk's source hash no longer
    # matches the index (means source MD changed since normalization).
    drifted = [
        cid for cid in completed_ids
        if cid in chunks_by_id and chunks_by_id[cid]["content_hash"] != completed_hashes[cid]
    ]

    pending = [c for c in chunks if c["chunk_id"] not in completed_ids]

    print(f"manual:    {manual_key}")
    print(f"total:     {len(chunks)}")
    print(f"completed: {len(completed_ids)}")
    print(f"pending:   {len(pending)}")
    if drifted:
        print(f"drifted (source changed, repair needed): {len(drifted)}")
        for cid in drifted[:5]:
            print(f"  - {cid}")

    if completed_ids:
        recent = [c for c in chunks if c["chunk_id"] in completed_ids][-3:]
        print()
        print("recent completed:")
        for c in recent:
            print(f"  - {c['chunk_id']} (lines {c['start_line']}-{c['end_line']}, {c['char_count']:,} chars)")

    if not pending:
        print()
        print("done. no pending chunks.")
        return 1

    nxt = pending[0]
    print()
    print("NEXT CHUNK:")
    print(f"  chunk_id:    {nxt['chunk_id']}")
    print(f"  lines:       {nxt['start_line']}-{nxt['end_line']}")
    print(f"  char_count:  {nxt['char_count']:,}")
    print(f"  table_count: {nxt['table_count']}")
    print(f"  oversized:   {nxt['oversized']}")
    print(f"  hash:        {nxt['content_hash']}")
    visa_preview = ", ".join(nxt["visa_codes"][:10])
    if len(nxt["visa_codes"]) > 10:
        visa_preview += f", ... (+{len(nxt['visa_codes'])-10} more)"
    print(f"  visa_codes:  [{visa_preview}]")
    print()
    print(f"  read source: data/parsed/raw/{manual_key}_manual.md")
    print(f"               offset={nxt['start_line']}, limit={nxt['end_line']-nxt['start_line']+1}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
