#!/usr/bin/env python3
"""Stage 2: split kordoc Markdown into LLM-digestible chunks.

Design (intentionally simple):

- The only deterministic structural anchor in kordoc output is the
  top-level ``<table>`` boundary. Headings and visa-code header cells are
  not consistently preserved (e.g. F-2 in 체류 manual lacks a clean
  ``<th>`` anchor; H-2 appears only in supplementary tables). So we do
  not try to map "one chunk = one visa code".

- Instead: accumulate sequential lines into a chunk; when the accumulated
  size hits a target (~15K chars) and we are at a top-level ``<table>``
  boundary, close the chunk and start a new one. Inter-table free text
  (headings, paragraphs) is appended to the chunk in flight.

- For each chunk, scan its text with a permissive visa-code regex and
  record every code that appears (e.g. ``["D-2", "D-2-1", "F-1-3"]``).
  The normalize skill uses this list to know which codes might need rows,
  but it is free to emit rows for codes it discovers itself.

- A chunk's ``content_hash`` is the cache key: re-running the indexer
  after a kordoc rerun only invalidates chunks whose content actually
  changed.

The indexer writes:

    data/parsed/chunks/{manual_key}_chunks_index.jsonl

each line a chunk record. Empty preamble/tail chunks are emitted only if
they carry real text (e.g. cover / 유의사항 / 공통사항 before the first
table; appendix forms after the last).

Usage:
    .venv/bin/python scripts/index_markdown_chunks.py
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARSED_RAW = PROJECT_ROOT / "data" / "parsed" / "raw"
CHUNKS_DIR = PROJECT_ROOT / "data" / "parsed" / "chunks"


# Target chunk size in characters. Calibrated so each chunk fits comfortably
# in a single normalize-skill prompt round with the schema + instructions.
TARGET_CHUNK_CHARS = 15_000
# Hard cap: never let a single chunk exceed this. If a single table is larger,
# we still emit it but mark it ``oversized`` for the skill to handle carefully.
MAX_CHUNK_CHARS = 30_000


TABLE_OPEN_RE = re.compile(r"<table\b", re.IGNORECASE)
TABLE_CLOSE_RE = re.compile(r"</table>", re.IGNORECASE)

# Permissive visa-code regex covering: A-1, D-10, E-7-4, F-2-R, etc.
# We deliberately accept spaces around the hyphen because Korean typography
# sometimes inserts thin spaces ("D - 8") that survive parsing.
VISA_CODE_RE = re.compile(
    r"\b([A-H])\s*-\s*(\d{1,2})(?:\s*-\s*([A-Z]?\d{1,2}|[A-Z]))?\b"
)


@dataclass
class Chunk:
    chunk_id: str
    manual_key: str
    start_line: int  # 1-indexed inclusive
    end_line: int  # 1-indexed inclusive
    char_count: int
    table_count: int
    visa_codes: list[str] = field(default_factory=list)
    oversized: bool = False
    content_hash: str = ""


def find_top_level_table_ranges(lines: list[str]) -> list[tuple[int, int]]:
    """Return (open_idx, close_idx) 0-based inclusive for every top-level table.

    Tracks nested tables via open/close depth counting.
    """
    spans: list[tuple[int, int]] = []
    depth = 0
    start: int | None = None
    for i, line in enumerate(lines):
        opens = len(TABLE_OPEN_RE.findall(line))
        closes = len(TABLE_CLOSE_RE.findall(line))
        if opens > 0 and depth == 0 and start is None:
            start = i
        depth += opens - closes
        if depth <= 0 and start is not None:
            spans.append((start, i))
            start = None
            depth = 0
    return spans


def normalize_code(match: re.Match[str]) -> str:
    letter, num, sub = match.group(1), match.group(2), match.group(3)
    if sub:
        return f"{letter}-{num}-{sub}"
    return f"{letter}-{num}"


def extract_visa_codes(text: str) -> list[str]:
    """Return de-duplicated list of visa codes appearing in text, sorted by
    first appearance order.
    """
    seen: dict[str, None] = {}
    for m in VISA_CODE_RE.finditer(text):
        code = normalize_code(m)
        if code not in seen:
            seen[code] = None
    return list(seen.keys())


def content_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def build_chunks(lines: list[str], manual_key: str) -> list[Chunk]:
    """Greedy chunker.

    Walk the file line by line. Open a new chunk at line 0 or just after a
    chunk close. Inside a chunk: accumulate lines. When the chunk exceeds
    ``TARGET_CHUNK_CHARS`` AND the previous line closed a top-level table,
    cut. If a single table by itself exceeds ``MAX_CHUNK_CHARS`` the chunk is
    emitted as ``oversized``.
    """
    table_spans = find_top_level_table_ranges(lines)
    # Map close-line -> True so we can ask "did this line close a top-level table?"
    table_closes: set[int] = {end for _start, end in table_spans}
    # Map open-line -> True so we can avoid cutting mid-table
    in_table_open: set[int] = set()
    for start, end in table_spans:
        for i in range(start, end + 1):
            in_table_open.add(i)

    chunks: list[Chunk] = []
    chunk_start = 0
    chunk_size = 0
    chunk_tables = 0

    def emit(end_idx: int) -> None:
        nonlocal chunk_start, chunk_size, chunk_tables
        if end_idx < chunk_start:
            return
        text = "\n".join(lines[chunk_start : end_idx + 1])
        stripped = text.strip()
        if not stripped:
            chunk_start = end_idx + 1
            chunk_size = 0
            chunk_tables = 0
            return
        idx_str = f"{len(chunks)+1:03d}"
        chunks.append(
            Chunk(
                chunk_id=f"{manual_key}_{idx_str}",
                manual_key=manual_key,
                start_line=chunk_start + 1,
                end_line=end_idx + 1,
                char_count=len(text),
                table_count=chunk_tables,
                visa_codes=extract_visa_codes(text),
                oversized=len(text) > MAX_CHUNK_CHARS,
                content_hash=content_hash(text),
            )
        )
        chunk_start = end_idx + 1
        chunk_size = 0
        chunk_tables = 0

    for i, line in enumerate(lines):
        chunk_size += len(line) + 1  # +1 for newline
        if i in table_closes:
            chunk_tables += 1
        # Cut points: at a top-level table close AND chunk is big enough,
        # AND we are not currently inside an open nested situation.
        if chunk_size >= TARGET_CHUNK_CHARS and i in table_closes:
            emit(i)

    # Flush remaining
    if chunk_start <= len(lines) - 1:
        emit(len(lines) - 1)

    return chunks


def summarize(manual_key: str, chunks: list[Chunk]) -> None:
    sizes = [c.char_count for c in chunks]
    table_counts = [c.table_count for c in chunks]
    codes_per_chunk = [len(c.visa_codes) for c in chunks]
    all_codes: set[str] = set()
    for c in chunks:
        all_codes.update(c.visa_codes)

    print(f"\n=== {manual_key} ===")
    print(f"  청크 수:      {len(chunks)}")
    if sizes:
        print(f"  청크 크기:    min={min(sizes):,} / max={max(sizes):,} / avg={sum(sizes)//len(sizes):,} chars")
        print(f"  표 수/청크:   min={min(table_counts)} / max={max(table_counts)} / avg={sum(table_counts)//len(table_counts):.1f}")
        print(f"  코드/청크:    min={min(codes_per_chunk)} / max={max(codes_per_chunk)} / avg={sum(codes_per_chunk)//len(codes_per_chunk)}")
    oversized = [c for c in chunks if c.oversized]
    if oversized:
        print(f"  오버사이즈 청크 ({MAX_CHUNK_CHARS:,} chars 초과): {len(oversized)}")
        for c in sorted(oversized, key=lambda c: -c.char_count)[:5]:
            preview_codes = ", ".join(c.visa_codes[:6]) + ("..." if len(c.visa_codes) > 6 else "")
            print(f"    - {c.chunk_id}: {c.char_count:,} chars, codes=[{preview_codes}]")
    print(f"  총 비자코드 종류: {len(all_codes)}")
    print(f"  발견된 코드 (정렬): {', '.join(sorted(all_codes))}")


def write_chunks(chunks: list[Chunk], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")


def main() -> int:
    md_paths = sorted(PARSED_RAW.glob("*_manual.md"))
    if not md_paths:
        raise SystemExit(
            f"파싱된 Markdown 없음: {PARSED_RAW}. 먼저 parse_hwp_to_markdown.py 실행하세요."
        )
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    for md_path in md_paths:
        manual_key = md_path.stem.replace("_manual", "")
        text = md_path.read_text(encoding="utf-8")
        chunks = build_chunks(text.splitlines(), manual_key)
        out_path = CHUNKS_DIR / f"{manual_key}_chunks_index.jsonl"
        write_chunks(chunks, out_path)
        summarize(manual_key, chunks)
        print(f"  → {out_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
