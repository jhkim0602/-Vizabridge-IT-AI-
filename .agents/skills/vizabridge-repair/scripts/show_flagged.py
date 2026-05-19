#!/usr/bin/env python3
"""Skill helper: list chunks with validator-reported issues.

Reads ``data/parsed/validation/{manual_key}_validation.json`` (produced
by scripts/validate_normalization.py) and prints each flagged chunk's
issues, ordered by severity (more rows-with-issues first).

Usage:
    python .claude/skills/vizabridge-repair/scripts/show_flagged.py {stay|visa}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
VALIDATION_DIR = PROJECT_ROOT / "data" / "parsed" / "validation"


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"stay", "visa"}:
        raise SystemExit("Usage: show_flagged.py {stay|visa}")
    manual_key = sys.argv[1]
    path = VALIDATION_DIR / f"{manual_key}_validation.json"
    if not path.exists():
        raise SystemExit(
            f"validation report not found: {path}\n"
            f"먼저 'python scripts/validate_normalization.py {manual_key}'을 실행하세요."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    chunks = data.get("chunks", [])
    flagged = [c for c in chunks if c.get("rows_with_issues") or c.get("chunk_level_issues")]
    flagged.sort(
        key=lambda c: (-c.get("rows_with_issues", 0), -len(c.get("chunk_level_issues", []))),
    )

    print(f"manual:               {manual_key}")
    print(f"normalized chunks:    {data.get('normalized_chunks', 0)}")
    print(f"flagged chunks:       {len(flagged)}")
    print(f"total rows:           {data.get('total_rows', 0)}")
    print(f"rows with issues:     {data.get('rows_with_issues', 0)}")

    if not flagged:
        print()
        print("clean. nothing to repair.")
        return 1

    print()
    print("NEXT CHUNK TO REPAIR:")
    nxt = flagged[0]
    print(f"  chunk_id:          {nxt['chunk_id']}")
    print(f"  hash_drift:        {nxt.get('hash_drift', False)}")
    print(f"  rows total:        {nxt['row_count']}")
    print(f"  rows with issues:  {nxt['rows_with_issues']}")
    if nxt.get("chunk_level_issues"):
        print(f"  chunk-level issues:")
        for issue in nxt["chunk_level_issues"]:
            print(f"    - {issue}")
    for row in nxt["rows"]:
        if not row.get("issues"):
            continue
        title = row.get("section_title") or "(no section title)"
        pt = row.get("petition_type") or ""
        sst = row.get("subsection_type") or ""
        print(f"  row #{row['row_index']} ({title} / {pt} / {sst}):")
        for issue in row["issues"]:
            print(f"    - {issue}")

    if len(flagged) > 1:
        print()
        print(f"OTHER FLAGGED ({len(flagged)-1} more):")
        for c in flagged[1:11]:
            print(
                f"  - {c['chunk_id']}: {c['rows_with_issues']}/{c['row_count']} rows flagged"
                + (" (hash drift)" if c.get("hash_drift") else "")
            )
        if len(flagged) > 11:
            print(f"  ... +{len(flagged)-11} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
