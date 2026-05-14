#!/usr/bin/env python3
"""Stage 8: build chatbot-ready CSVs from normalized chatbot Markdown.

Reads ``data/parsed/normalized_chatbot/{manual_key}_manual.md`` produced
by the enrich-chatbot skill and writes
``data/processed/{manual_key}_manual_chatbot_ready.csv``.

Deterministic, no LLM call. Schema is enforced.

Usage:
    .venv/bin/python scripts/build_chatbot_csv.py
    .venv/bin/python scripts/build_chatbot_csv.py stay
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NORMALIZED_CHATBOT_DIR = PROJECT_ROOT / "data" / "parsed" / "normalized_chatbot"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


OPEN_MARKER_RE = re.compile(
    r"<!--\s*vizabridge-chatbot v1 source_row:\s*([^\s]+)\s+source_hash:\s*([^\s]+)\s*-->"
)
CLOSE_MARKER_RE = re.compile(r"<!--\s*end chatbot:\s*([^\s]+)\s*-->")
HEADER_RE = re.compile(r"^###\s+chatbot\s+.*$", re.MULTILINE)
FIELD_LINE_RE = re.compile(r"^-\s+([a-z_]+):\s*(.*)$", re.MULTILINE)
MULTILINE_VALUE_START_RE = re.compile(r"^-\s+([a-z_]+):\s*\|\s*$")


CHATBOT_COLUMNS = [
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
]


def parse_block_fields(body: str) -> dict[str, str]:
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


def iter_blocks(normalized_text: str):
    opens = list(OPEN_MARKER_RE.finditer(normalized_text))
    close_by_id = {m.group(1): m for m in CLOSE_MARKER_RE.finditer(normalized_text)}
    for open_m in opens:
        rid = open_m.group(1)
        close_m = close_by_id.get(rid)
        if not close_m or close_m.start() < open_m.end():
            continue
        body = normalized_text[open_m.end() : close_m.start()]
        # Drop the header line
        body_after_header = HEADER_RE.sub("", body, count=1)
        yield rid, body_after_header


def build_csv(manual_key: str) -> tuple[Path, int]:
    norm_path = NORMALIZED_CHATBOT_DIR / f"{manual_key}_manual.md"
    if not norm_path.exists():
        raise SystemExit(f"정규화 chatbot 출력 없음: {norm_path}")
    text = norm_path.read_text(encoding="utf-8")

    rows: list[dict[str, str]] = []
    for _rid, body in iter_blocks(text):
        rows.append(parse_block_fields(body))

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / f"{manual_key}_manual_chatbot_ready.csv"
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CHATBOT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in CHATBOT_COLUMNS})
    return out_path, len(rows)


def main() -> int:
    args = sys.argv[1:]
    manuals = args if args else ["stay", "visa"]
    for manual_key in manuals:
        if manual_key not in {"stay", "visa"}:
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
