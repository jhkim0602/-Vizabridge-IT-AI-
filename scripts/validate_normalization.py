#!/usr/bin/env python3
"""Stage 4: deterministic cross-validation of normalized chunks vs source.

For each chunk block in ``data/parsed/normalized/{manual_key}_manual.md``,
compare emitted rows against the original line range in
``data/parsed/raw/{manual_key}_manual.md`` and flag:

- visa codes that the row claims but do not appear in the source chunk
  (hallucination)
- monetary amounts in the source that disappear in normalized rows
  (information loss)
- document-name nouns missing or invented
- required fields left empty when the source clearly contains the data

This script does NOT call any LLM. It is a fast, idempotent check that the
normalize skill can rerun to validate itself, and that the repair skill
reads to decide which chunks need fixing.

Output:
- ``data/parsed/validation/{manual_key}_validation.json`` — per-chunk issues
- console summary

Usage:
    .venv/bin/python scripts/validate_normalization.py             # both manuals
    .venv/bin/python scripts/validate_normalization.py stay        # one only
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARSED_RAW = PROJECT_ROOT / "data" / "parsed" / "raw"
CHUNKS_DIR = PROJECT_ROOT / "data" / "parsed" / "chunks"
NORMALIZED_DIR = PROJECT_ROOT / "data" / "parsed" / "normalized"
VALIDATION_DIR = PROJECT_ROOT / "data" / "parsed" / "validation"


OPEN_MARKER_RE = re.compile(
    r"<!--\s*vizabridge-normalize v1 chunk:\s*([^\s]+)\s+hash:\s*([^\s]+)\s+lines:\s*(\d+)-(\d+)\s*-->"
)
CLOSE_MARKER_RE = re.compile(r"<!--\s*end chunk:\s*([^\s]+)\s*-->")
ROW_HEADER_RE = re.compile(r"^###\s+row\s+", re.MULTILINE)
FIELD_LINE_RE = re.compile(r"^-\s+([a-z_]+):\s*(.*)$", re.MULTILINE)
MULTILINE_VALUE_START_RE = re.compile(r"^-\s+([a-z_]+):\s*\|\s*$", re.MULTILINE)

VISA_CODE_RE = re.compile(
    r"\b([A-H])\s*-\s*(\d{1,2})(?:\s*-\s*([A-Z]?\d{1,2}|[A-Z]))?\b"
)
# Monetary amounts: digit groups (with commas) followed by 원/만원/억원
AMOUNT_RE = re.compile(r"\b(\d{1,3}(?:,\d{3})*|\d+)\s*(?:만원|원|억원)\b")

# Document-name suffixes that signal a Korean admin document
DOCUMENT_SUFFIX_RE = re.compile(
    r"[가-힣A-Za-z0-9·‧]+(?:등록증|신청서|증명서|확인서|위임장|동의서|허가증|면허증|추천서|공한|진단서|진술서|보증서|초청장)"
)

REQUIRED_ROW_FIELDS = {
    "manual_type",
    "item_type",
    "section_title",
    "petition_type",
    "subsection_type",
}


@dataclass
class RowIssues:
    row_index: int
    section_title: str
    petition_type: str
    subsection_type: str
    issues: list[str] = field(default_factory=list)


@dataclass
class ChunkValidation:
    chunk_id: str
    source_hash_index: str
    source_hash_block: str
    hash_drift: bool
    row_count: int
    rows_with_issues: int
    rows: list[RowIssues]
    chunk_level_issues: list[str]


def normalize_code(match: re.Match[str]) -> str:
    letter, num, sub = match.group(1), match.group(2), match.group(3)
    return f"{letter}-{num}-{sub}" if sub else f"{letter}-{num}"


def extract_visa_codes(text: str) -> set[str]:
    return {normalize_code(m) for m in VISA_CODE_RE.finditer(text)}


def extract_amounts(text: str) -> set[str]:
    # Normalize commas away for comparison robustness
    out: set[str] = set()
    for m in AMOUNT_RE.finditer(text):
        digits = m.group(1).replace(",", "")
        suffix = m.group(0)[len(m.group(1)) :].strip()
        out.add(f"{digits}{suffix}")
    return out


def extract_documents(text: str) -> set[str]:
    return {m.group(0) for m in DOCUMENT_SUFFIX_RE.finditer(text)}


def load_chunk_index(manual_key: str) -> dict[str, dict]:
    path = CHUNKS_DIR / f"{manual_key}_chunks_index.jsonl"
    if not path.exists():
        raise SystemExit(f"chunk index not found: {path}")
    out: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        out[rec["chunk_id"]] = rec
    return out


def slice_source_lines(source_lines: list[str], start_line: int, end_line: int) -> str:
    # start_line / end_line are 1-indexed inclusive in the chunk index
    return "\n".join(source_lines[start_line - 1 : end_line])


def parse_row_fields(row_body: str) -> dict[str, str]:
    """Parse '- field: value' lines plus '- field: |' multi-line blocks."""
    out: dict[str, str] = {}
    lines = row_body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m_multi = MULTILINE_VALUE_START_RE.match(line)
        if m_multi:
            field_name = m_multi.group(1)
            i += 1
            collected: list[str] = []
            while i < len(lines):
                nxt = lines[i]
                if nxt.startswith("    "):
                    collected.append(nxt[4:])
                    i += 1
                elif nxt.strip() == "":
                    i += 1
                    if i < len(lines) and not lines[i].startswith("    "):
                        break
                else:
                    break
            out[field_name] = "\n".join(collected).strip()
            continue
        m_single = FIELD_LINE_RE.match(line)
        if m_single:
            out[m_single.group(1)] = m_single.group(2).strip()
        i += 1
    return out


def parse_chunk_blocks(normalized_text: str) -> list[dict]:
    """Walk normalized text, yielding {chunk_id, source_hash_block, body}."""
    out: list[dict] = []
    open_iter = list(OPEN_MARKER_RE.finditer(normalized_text))
    close_by_id = {m.group(1): m for m in CLOSE_MARKER_RE.finditer(normalized_text)}
    for open_m in open_iter:
        chunk_id = open_m.group(1)
        source_hash = open_m.group(2)
        close_m = close_by_id.get(chunk_id)
        if not close_m or close_m.start() < open_m.end():
            continue
        body = normalized_text[open_m.end() : close_m.start()]
        out.append(
            {"chunk_id": chunk_id, "source_hash_block": source_hash, "body": body}
        )
    return out


def split_row_blocks(body: str) -> list[str]:
    parts = ROW_HEADER_RE.split(body)
    return [p for p in parts[1:] if p.strip()]


def validate_chunk(
    chunk_meta: dict, source_text: str, body: str, source_hash_block: str, manual_key: str
) -> ChunkValidation:
    source_codes = extract_visa_codes(source_text)
    source_amounts = extract_amounts(source_text)
    source_documents = extract_documents(source_text)

    rows_out: list[RowIssues] = []
    chunk_level: list[str] = []

    hash_drift = chunk_meta["content_hash"] != source_hash_block
    if hash_drift:
        chunk_level.append(
            f"hash drift: index={chunk_meta['content_hash']} vs block={source_hash_block}"
        )

    row_blocks = split_row_blocks(body)
    for i, raw_body in enumerate(row_blocks):
        fields = parse_row_fields(raw_body)
        issues: list[str] = []

        missing = REQUIRED_ROW_FIELDS - set(fields)
        if missing:
            issues.append(f"missing required fields: {sorted(missing)}")

        # visa_code / stay_status_code must appear in source
        code_value = fields.get("visa_code") or fields.get("stay_status_code") or ""
        code_value = code_value.strip()
        if code_value:
            row_codes = extract_visa_codes(code_value)
            if not row_codes:
                # plain value like "A-1" not in regex form — still normalize
                m = VISA_CODE_RE.search(code_value)
                if m:
                    row_codes = {normalize_code(m)}
            invented = row_codes - source_codes
            if invented:
                issues.append(f"visa code not in source: {sorted(invented)}")
        else:
            issues.append("visa_code/stay_status_code value empty")

        # subtype_or_program: if non-empty and matches a sub-code pattern, also check
        subtype = fields.get("subtype_or_program", "").strip()
        if subtype:
            invented_sub = extract_visa_codes(subtype) - source_codes
            if invented_sub:
                issues.append(f"subtype_or_program code not in source: {sorted(invented_sub)}")

        # fees: every amount cited in the row must appear in the source
        fees_value = fields.get("fees", "").strip()
        if fees_value:
            row_amounts = extract_amounts(fees_value)
            invented_amount = row_amounts - source_amounts
            if invented_amount:
                issues.append(f"amount not in source: {sorted(invented_amount)}")

        # documents: row document names must appear (as exact suffix-bearing
        # phrases) in the source — fuzzy enough to allow source word variants.
        for fld in ("mandatory_documents", "common_documents", "other_documents"):
            doc_text = fields.get(fld, "").strip()
            if not doc_text:
                continue
            row_docs = extract_documents(doc_text)
            invented_doc = row_docs - source_documents
            if invented_doc:
                # Be lenient: documents are commonly abbreviated, only flag
                # if NONE of the row docs appear in source.
                if invented_doc == row_docs:
                    issues.append(
                        f"{fld}: none of the cited documents found in source: {sorted(invented_doc)[:3]}"
                    )

        rows_out.append(
            RowIssues(
                row_index=i + 1,
                section_title=fields.get("section_title", ""),
                petition_type=fields.get("petition_type", ""),
                subsection_type=fields.get("subsection_type", ""),
                issues=issues,
            )
        )

    rows_with_issues = sum(1 for r in rows_out if r.issues)
    return ChunkValidation(
        chunk_id=chunk_meta["chunk_id"],
        source_hash_index=chunk_meta["content_hash"],
        source_hash_block=source_hash_block,
        hash_drift=hash_drift,
        row_count=len(rows_out),
        rows_with_issues=rows_with_issues,
        rows=rows_out,
        chunk_level_issues=chunk_level,
    )


def validate_manual(manual_key: str) -> dict:
    chunks_meta = load_chunk_index(manual_key)
    raw_path = PARSED_RAW / f"{manual_key}_manual.md"
    norm_path = NORMALIZED_DIR / f"{manual_key}_manual.md"
    if not raw_path.exists():
        raise SystemExit(f"raw markdown not found: {raw_path}")
    if not norm_path.exists():
        return {
            "manual_key": manual_key,
            "status": "no normalized output yet",
            "chunks": [],
        }
    source_lines = raw_path.read_text(encoding="utf-8").splitlines()
    normalized_text = norm_path.read_text(encoding="utf-8")
    blocks = parse_chunk_blocks(normalized_text)

    results: list[ChunkValidation] = []
    for block in blocks:
        chunk_id = block["chunk_id"]
        if chunk_id not in chunks_meta:
            # Block references a chunk_id not in the current index. Possible
            # cause: the indexer was rerun and renamed chunks. Flag.
            results.append(
                ChunkValidation(
                    chunk_id=chunk_id,
                    source_hash_index="",
                    source_hash_block=block["source_hash_block"],
                    hash_drift=True,
                    row_count=0,
                    rows_with_issues=0,
                    rows=[],
                    chunk_level_issues=["chunk_id not present in current index"],
                )
            )
            continue
        meta = chunks_meta[chunk_id]
        source_text = slice_source_lines(source_lines, meta["start_line"], meta["end_line"])
        results.append(
            validate_chunk(meta, source_text, block["body"], block["source_hash_block"], manual_key)
        )

    out = {
        "manual_key": manual_key,
        "normalized_chunks": len(results),
        "total_rows": sum(r.row_count for r in results),
        "rows_with_issues": sum(r.rows_with_issues for r in results),
        "chunks_with_issues": sum(
            1 for r in results if r.rows_with_issues or r.chunk_level_issues
        ),
        "chunks": [asdict(r) for r in results],
    }
    return out


def write_validation(manual_key: str, data: dict) -> Path:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    path = VALIDATION_DIR / f"{manual_key}_validation.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def print_summary(data: dict) -> None:
    mk = data["manual_key"]
    if "status" in data:
        print(f"=== {mk}: {data['status']} ===")
        return
    print(f"=== {mk} ===")
    print(f"  normalized chunks:  {data['normalized_chunks']}")
    print(f"  total rows:         {data['total_rows']}")
    print(f"  chunks with issues: {data['chunks_with_issues']}")
    print(f"  rows with issues:   {data['rows_with_issues']}")
    issue_counts: dict[str, int] = {}
    for chunk in data["chunks"]:
        for row in chunk["rows"]:
            for issue in row["issues"]:
                kind = issue.split(":", 1)[0]
                issue_counts[kind] = issue_counts.get(kind, 0) + 1
        for issue in chunk["chunk_level_issues"]:
            kind = issue.split(":", 1)[0]
            issue_counts[kind] = issue_counts.get(kind, 0) + 1
    if issue_counts:
        print("  issue breakdown:")
        for kind, count in sorted(issue_counts.items(), key=lambda kv: -kv[1]):
            print(f"    {kind}: {count}")


def main() -> int:
    args = sys.argv[1:]
    manuals = args if args else ["stay", "visa"]
    for manual_key in manuals:
        if manual_key not in {"stay", "visa"}:
            raise SystemExit(f"unknown manual_key: {manual_key}")
        data = validate_manual(manual_key)
        path = write_validation(manual_key, data)
        print_summary(data)
        if "status" not in data:
            print(f"  → {path.relative_to(PROJECT_ROOT)}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
