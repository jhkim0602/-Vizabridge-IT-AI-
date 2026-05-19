"""Fill the 페이지 column of inspection CSVs by matching 원문발췌/섹션 against
HWP-derived PDF text.

Usage::

    .venv/bin/python scripts/fill_page_numbers.py stay
    .venv/bin/python scripts/fill_page_numbers.py visa
    .venv/bin/python scripts/fill_page_numbers.py both

PDF paths default to ``/tmp/hwp2pdf/...``; override with ``--stay-pdf`` /
``--visa-pdf`` or env vars ``STAY_PDF`` / ``VISA_PDF``.

The page index is cached as JSON under ``/tmp/hwp2pdf/cache/`` so repeated runs
do not re-extract text from the (large) PDFs.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pdfplumber


# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
CACHE_DIR = Path("/tmp/hwp2pdf/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PDFS = {
    "stay": Path(os.environ.get("STAY_PDF", "/tmp/hwp2pdf/260504 체류민원 자격별 안내 매뉴얼.pdf")),
    "visa": Path(os.environ.get("VISA_PDF", "/tmp/hwp2pdf/260504 사증민원 자격별 안내 매뉴얼.pdf")),
}

CSV_PATHS = {
    "stay": {
        "review": PROCESSED / "체류매뉴얼_검수용_v2.csv",
        "notion": PROCESSED / "체류매뉴얼_노션검수용_v2.csv",
    },
    "visa": {
        "review": PROCESSED / "사증매뉴얼_검수용_v2.csv",
        "notion": PROCESSED / "사증매뉴얼_노션검수용_v2.csv",
    },
}


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

# HWP -> PDF conversion duplicates many Korean syllables (외외 국국 인인 ...). We
# collapse consecutive duplicate characters before matching so excerpts written
# in plain Korean still align.
DUP_RE = re.compile(r"([가-힣])\1")
WS_RE = re.compile(r"\s+")
# Strip punctuation that gets rendered inconsistently between HWP and PDF.
STRIP_RE = re.compile(r"[\s​　 ·•▣◯○□■◇◆☆★※→←↑↓\-‐‑‒–—―•◦.·,()\[\]{}<>「」『』《》〈〉【】\"'`~!@#$%^&*+=|/\\?:;]")


def _collapse_dups(text: str) -> str:
    prev = None
    while prev != text:
        prev = text
        text = DUP_RE.sub(r"\1", text)
    return text


def normalize(text: str) -> str:
    """Aggressively normalize a chunk of Korean text for matching.

    - NFC normalize
    - collapse HWP-PDF duplicate Hangul syllables (외외 -> 외)
    - drop whitespace and punctuation entirely
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = _collapse_dups(text)
    text = STRIP_RE.sub("", text)
    return text


# ---------------------------------------------------------------------------
# PDF page index (cached)
# ---------------------------------------------------------------------------

def build_page_index(pdf_path: Path, cache_key: str, force: bool = False) -> List[str]:
    """Return a list where index i holds the normalized text of page i+1."""

    cache_path = CACHE_DIR / f"{cache_key}_pages.json"
    if cache_path.exists() and not force:
        with cache_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data["pages"]

    print(f"[{cache_key}] extracting text from {pdf_path}…", flush=True)
    pages: List[str] = []
    t0 = time.time()
    with pdfplumber.open(str(pdf_path)) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            raw = page.extract_text() or ""
            pages.append(normalize(raw))
            if i % 50 == 0 or i == total:
                print(f"  page {i}/{total} ({time.time()-t0:.1f}s)", flush=True)
    cache_path.write_text(json.dumps({"pages": pages}, ensure_ascii=False), encoding="utf-8")
    print(f"[{cache_key}] cached -> {cache_path}", flush=True)
    return pages


# ---------------------------------------------------------------------------
# Excerpt -> candidate substrings
# ---------------------------------------------------------------------------

def excerpt_candidates(excerpt: str) -> List[str]:
    """Pick a few 'characteristic' substrings from the excerpt to search for.

    Returns at most a handful of candidates of varying length so we can
    fall back from very specific to more general.
    """
    if not excerpt:
        return []
    norm = normalize(excerpt)
    if not norm:
        return []

    cands: List[str] = []
    L = len(norm)

    # 1. The most unique slice tends to live near the middle.
    if L >= 60:
        mid = L // 2
        cands.append(norm[max(0, mid - 30) : mid + 30])
    # 2. A long head slice.
    if L >= 60:
        cands.append(norm[: 60])
    else:
        cands.append(norm[: max(20, L)])
    # 3. A long tail slice.
    if L >= 60:
        cands.append(norm[L - 60 :])
    # 4. Sliding 25-char windows across the whole excerpt — catches cases
    #    where the editor reordered fragments and middle/head/tail straddle a
    #    boundary that doesn't exist in the PDF. Step is small so the windows
    #    overlap heavily.
    if L >= 25:
        win = 25
        step = 8
        for start in range(0, max(1, L - win + 1), step):
            cands.append(norm[start : start + win])
    # 5. Short head fallback.
    cands.append(norm[: 20])

    # De-dup while preserving order.
    seen = set()
    out: List[str] = []
    for c in cands:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


# ---------------------------------------------------------------------------
# Section fallback candidates
# ---------------------------------------------------------------------------

# Strip pieces like "F-6-1 외국인" from the section title and use a clean form
# for fallback search.
SECTION_LINE_RE = re.compile(r"\n+")


def section_candidates(section: str) -> List[str]:
    if not section:
        return []
    cands: List[str] = []
    for line in SECTION_LINE_RE.split(section):
        line = line.strip()
        if not line:
            continue
        # Looks like e.g. "F-6-1 외국인배우자 / 체류자격 변경허가"
        # Try the full normalized line, plus the prefix before " / ".
        cands.append(normalize(line))
        if " / " in line:
            head, _, tail = line.partition(" / ")
            cands.append(normalize(head))
            cands.append(normalize(tail))
    # De-dup
    seen = set()
    out = []
    for c in cands:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def find_pages(needle: str, pages: List[str], start_hint: Optional[int] = None) -> List[int]:
    """Return 1-based page numbers whose normalized text contains *needle*."""
    if not needle:
        return []
    hits: List[int] = []
    # Prefer pages from start_hint onwards so we tend to pick the in-section
    # occurrence rather than a stale table-of-contents listing.
    order = list(range(len(pages)))
    if start_hint is not None and 0 <= start_hint < len(pages):
        order = list(range(start_hint, len(pages))) + list(range(0, start_hint))
    for i in order:
        if needle in pages[i]:
            hits.append(i + 1)
    return hits


def collapse_range(hits: List[int], window: int = 4) -> str:
    """Turn page hits into a compact 'p. 142' or 'p. 142~145' style string."""
    if not hits:
        return ""
    hits = sorted(set(hits))
    start = hits[0]
    end = start
    for p in hits[1:]:
        if p - end <= window:
            end = p
        else:
            break
    if end == start:
        return f"p. {start}"
    return f"p. {start}~{end}"


# ---------------------------------------------------------------------------
# CSV processing
# ---------------------------------------------------------------------------

def process_csv(
    manual: str,
    csv_path: Path,
    notion_path: Path,
    pages: List[str],
) -> Dict[str, object]:
    """Fill 페이지 column in-place. Returns stats dict."""

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    n = len(rows)
    matched_excerpt = 0
    matched_section = 0
    no_match = 0
    no_match_samples: List[Tuple[int, str, str]] = []

    last_page_hint: Optional[int] = None

    for idx, row in enumerate(rows):
        excerpt = row.get("원문발췌", "") or ""
        section = row.get("섹션", "") or ""

        # Collect a vote tally across ALL candidates instead of stopping at
        # the first match — the first candidate isn't always the best one
        # when excerpts splice together fragments from several sub-sections.
        excerpt_votes: Dict[int, int] = {}
        for cand in excerpt_candidates(excerpt):
            for p in find_pages(cand, pages):
                excerpt_votes[p] = excerpt_votes.get(p, 0) + 1
        section_votes: Dict[int, int] = {}
        for cand in section_candidates(section):
            for p in find_pages(cand, pages):
                section_votes[p] = section_votes.get(p, 0) + 1

        # Combine: an excerpt match is worth 3x a section match for raw
        # votes. Also, pages within +/- 30 of a section-anchor hit get a
        # multiplicative bonus on their excerpt score — section anchors are
        # the most reliable signal for "what section am I in".
        section_anchor_pages = set(section_votes.keys())
        combined: Dict[int, float] = {}
        for p, v in excerpt_votes.items():
            base = v * 3.0
            # Within +/- 30 of a section anchor: bump the score
            if any(abs(p - a) <= 30 for a in section_anchor_pages):
                base *= 1.5
            combined[p] = combined.get(p, 0.0) + base
        for p, v in section_votes.items():
            combined[p] = combined.get(p, 0.0) + v * 1.5

        if combined:
            # Bias toward the last hint: heavily down-weight pages that are
            # far from the previous row's page, because excerpts often
            # contain template text that appears throughout the document.
            # The closer to last_page_hint (going forward), the bigger the
            # multiplier — this beats boilerplate matches deeper in the doc.
            if last_page_hint is not None:
                for p in list(combined.keys()):
                    dist = p - last_page_hint
                    if 0 <= dist <= 8:
                        combined[p] *= 2.5  # almost certainly the right page
                    elif 8 < dist <= 25:
                        combined[p] *= 1.6
                    elif 25 < dist <= 80:
                        combined[p] *= 1.15
                    elif 80 < dist <= 200:
                        combined[p] *= 1.0
                    elif dist > 200:
                        combined[p] *= 0.7
                    elif -8 <= dist < 0:
                        combined[p] *= 1.2  # same section reference
                    elif -25 <= dist < -8:
                        combined[p] *= 0.7
                    elif -80 <= dist < -25:
                        combined[p] *= 0.4
                    else:
                        # very far backward (boilerplate match elsewhere)
                        combined[p] *= 0.15

            # Pick the page with the highest score; tiebreak by proximity to
            # last_page_hint (forward preferred), then by page number.
            def _key(p: int) -> Tuple[float, float, int]:
                score = combined[p]
                if last_page_hint is None:
                    return (-score, 0.0, p)
                dist = p - last_page_hint
                # forward distance is cheaper than backward
                if dist >= 0:
                    proximity = dist
                else:
                    proximity = -dist * 2 + 1000  # heavy penalty for going back
                return (-score, proximity, p)

            primary = min(combined.keys(), key=_key)

            # Build a span: walk forward from primary while consecutive pages
            # are still scored. Only chain pages that are actually contiguous
            # (gap <= 2) and score at least half of primary's score.
            top_score = combined[primary]
            span_hits = [primary]
            # extend forward
            cur = primary
            for p in sorted(p for p in combined.keys() if p > primary):
                if p - cur <= 2 and combined[p] >= top_score * 0.5:
                    span_hits.append(p)
                    cur = p
                else:
                    break
            # extend backward (rare — usually primary IS the start)
            cur = primary
            for p in sorted((p for p in combined.keys() if p < primary), reverse=True):
                if cur - p <= 2 and combined[p] >= top_score * 0.5:
                    span_hits.append(p)
                    cur = p
                else:
                    break
            row["페이지"] = collapse_range(span_hits)

            if excerpt_votes:
                matched_excerpt += 1
                method = "excerpt"
            else:
                matched_section += 1
                method = "section"
            last_page_hint = primary
        else:
            no_match += 1
            if len(no_match_samples) < 5:
                no_match_samples.append((idx, section.split("\n", 1)[0][:60], excerpt[:60]))

    # Write back
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "manual": manual,
        "total": n,
        "matched_excerpt": matched_excerpt,
        "matched_section": matched_section,
        "no_match": no_match,
        "no_match_samples": no_match_samples,
        "csv_path": str(csv_path),
        "notion_path": str(notion_path),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(manual: str, args) -> Dict[str, object]:
    pdf_path = Path(args.stay_pdf if manual == "stay" else args.visa_pdf)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    pages = build_page_index(pdf_path, cache_key=manual, force=args.force)
    return process_csv(
        manual=manual,
        csv_path=CSV_PATHS[manual]["review"],
        notion_path=CSV_PATHS[manual]["notion"],
        pages=pages,
    )


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Fill 페이지 column from HWP-derived PDFs.")
    ap.add_argument("manual", choices=["stay", "visa", "both"], help="which manual(s) to process")
    ap.add_argument("--stay-pdf", default=str(DEFAULT_PDFS["stay"]))
    ap.add_argument("--visa-pdf", default=str(DEFAULT_PDFS["visa"]))
    ap.add_argument("--force", action="store_true", help="ignore the page-text cache")
    args = ap.parse_args(argv)

    manuals = ["stay", "visa"] if args.manual == "both" else [args.manual]
    results: List[Dict[str, object]] = []
    for m in manuals:
        results.append(run(m, args))

    print()
    print("=== Page-fill results ===")
    for r in results:
        total = r["total"]
        me = r["matched_excerpt"]
        ms = r["matched_section"]
        nm = r["no_match"]
        rate = (me + ms) * 100.0 / total if total else 0.0
        print(
            f"[{r['manual']}] total={total}  "
            f"excerpt={me}  section={ms}  no_match={nm}  "
            f"match_rate={rate:.1f}%"
        )
        for idx, sec, exc in r["no_match_samples"]:
            print(f"    miss row {idx}: section={sec!r} excerpt={exc!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
