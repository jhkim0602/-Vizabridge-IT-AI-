#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from manual_review.extract import build_items
from manual_review.quality import quality_summary, validate_items
from manual_review.schema import ALL_FIELDS, MANUALS, PROCESSED_DIR


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def append_review_notes(items: list[dict[str, str]], errors: list[dict[str, str]]) -> None:
    by_id: dict[str, list[str]] = {}
    for error in errors:
        by_id.setdefault(error.get("item_id", ""), []).append(error["message"])
    for item in items:
        notes = by_id.get(item["item_id"], [])
        if notes:
            item["needs_human_review"] = "true"
            existing = item.get("review_notes", "")
            merged = [existing] if existing else []
            merged.extend(note for note in notes if note not in merged)
            item["review_notes"] = "; ".join(merged)


def assert_critical_coverage(items: list[dict[str, str]], sample: bool) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if sample:
        return errors
    for manual_key, meta in MANUALS.items():
        manual_name = meta["manual_type"]
        manual_items = [item for item in items if item.get("manual_type") == manual_name]
        for term in meta["critical_terms"]:
            found = any(term in "\n".join([item.get("raw_text", ""), item.get("normalized_text", ""), item.get("subtype_or_program", "")]) for item in manual_items)
            if not found:
                errors.append({"item_id": "", "severity": "error", "message": f"critical coverage missing: {manual_name} {term}"})
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Build human-reviewable manual review datasets.")
    parser.add_argument("--sample", action="store_true", help="Run only critical sample pages.")
    args = parser.parse_args()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    items = build_items(sample=args.sample)
    errors = validate_items(items)
    errors.extend(assert_critical_coverage(items, args.sample))
    append_review_notes(items, errors)
    # Re-run after notes are attached so suspicious-term findings with notes do not remain stale.
    errors = validate_items(items) + assert_critical_coverage(items, args.sample)

    suffix = "_sample" if args.sample else ""
    items_jsonl = PROCESSED_DIR / f"manual_review_items{suffix}.jsonl"
    items_csv = PROCESSED_DIR / f"manual_review_items{suffix}.csv"
    samples_csv = PROCESSED_DIR / "manual_review_samples.csv"
    errors_jsonl = PROCESSED_DIR / f"manual_review_validation_errors{suffix}.jsonl"
    report_md = PROCESSED_DIR / f"manual_review_quality_report{suffix}.md"

    write_jsonl(items_jsonl, items)
    write_csv(items_csv, items, ALL_FIELDS)
    write_csv(samples_csv, items[:200], ALL_FIELDS)
    write_jsonl(errors_jsonl, errors)
    report_md.write_text(quality_summary(items, errors, sample=args.sample), encoding="utf-8")

    if not args.sample:
        # Stable final filenames required by the design.
        write_jsonl(PROCESSED_DIR / "manual_review_items.jsonl", items)
        write_csv(PROCESSED_DIR / "manual_review_items.csv", items, ALL_FIELDS)
        write_jsonl(PROCESSED_DIR / "manual_review_validation_errors.jsonl", errors)
        (PROCESSED_DIR / "manual_review_quality_report.md").write_text(quality_summary(items, errors), encoding="utf-8")

    print(f"items={len(items)} errors={len(errors)} sample={args.sample}")
    print(items_jsonl)
    print(items_csv)
    print(report_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
