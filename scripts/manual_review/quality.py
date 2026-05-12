from __future__ import annotations

from collections import Counter

from .schema import MANUALS, SUSPICIOUS_TERMS


def _norm(text: str) -> str:
    return " ".join((text or "").split())


def _text_for_suspicious_scan(item: dict[str, str]) -> str:
    fields = [
        "section_title",
        "normalized_text",
        "stay_status_name_ko",
        "visa_name_ko",
        "petition_type",
        "subsection_type",
        "eligibility",
        "requirements",
        "required_documents",
        "procedure",
        "restrictions",
        "exceptions",
        "obligations",
    ]
    return "\n".join(item.get(field, "") for field in fields)


def validate_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for item in items:
        item_id = item.get("item_id", "")
        raw_text = item.get("raw_text", "")
        evidence = item.get("evidence_quote", "")
        if not raw_text.strip():
            errors.append({"item_id": item_id, "severity": "error", "message": "empty raw_text"})
        if evidence and raw_text and _norm(evidence) not in _norm(raw_text):
            errors.append({"item_id": item_id, "severity": "warning", "message": "evidence quote not found in raw_text"})

        scan_text = _text_for_suspicious_scan(item)
        for term in sorted(SUSPICIOUS_TERMS):
            if term in scan_text and not item.get("review_notes"):
                errors.append({"item_id": item_id, "severity": "warning", "message": f"suspicious term without review note: {term}"})

        if item.get("manual_type") == "체류민원" and (item.get("visa_code") or item.get("visa_name_ko")):
            errors.append({"item_id": item_id, "severity": "warning", "message": "stay row has visa-only fields"})
        if item.get("manual_type") == "사증민원" and (item.get("stay_status_code") or item.get("stay_status_name_ko")):
            errors.append({"item_id": item_id, "severity": "warning", "message": "visa row has stay-only fields"})
        if item.get("table_summary") and not item.get("table_rows"):
            errors.append({"item_id": item_id, "severity": "warning", "message": "table summary without table_rows"})
    return errors


def _counter_table(title: str, counter: Counter[str]) -> list[str]:
    lines = [f"## {title}", "", "| Value | Count |", "| --- | ---: |"]
    for value, count in counter.most_common():
        lines.append(f"| {value or '(blank)'} | {count} |")
    lines.append("")
    return lines


def _coverage(items: list[dict[str, str]], manual_key: str) -> list[tuple[str, int]]:
    terms = MANUALS[manual_key]["critical_terms"]
    rows = []
    for term in terms:
        count = 0
        for item in items:
            text = "\n".join(
                [
                    item.get("raw_text", ""),
                    item.get("normalized_text", ""),
                    item.get("stay_status_code", ""),
                    item.get("visa_code", ""),
                    item.get("subtype_or_program", ""),
                ]
            )
            if term in text:
                count += 1
        rows.append((term, count))
    return rows


def quality_summary(items: list[dict[str, str]], errors: list[dict[str, str]], sample: bool = False) -> str:
    manual_counts = Counter(item.get("manual_type", "") for item in items)
    item_type_counts = Counter(item.get("item_type", "") for item in items)
    subsection_counts = Counter(item.get("subsection_type", "") for item in items)
    review_count = sum(1 for item in items if item.get("needs_human_review") == "true")
    evidence_failures = sum(1 for error in errors if "evidence quote" in error["message"])
    empty_raw = sum(1 for error in errors if "empty raw_text" in error["message"])
    suspicious = Counter()
    for item in items:
        scan_text = _text_for_suspicious_scan(item)
        for term in SUSPICIOUS_TERMS:
            if term in scan_text:
                suspicious[term] += 1

    lines = [
        "# Manual Review Dataset Quality Report",
        "",
        f"- Mode: {'sample' if sample else 'full'}",
        f"- Total rows: {len(items)}",
        f"- Rows needing human review: {review_count}",
        f"- Validation findings: {len(errors)}",
        f"- Empty raw_text findings: {empty_raw}",
        f"- Evidence containment findings: {evidence_failures}",
        "",
    ]
    lines.extend(_counter_table("Rows by manual_type", manual_counts))
    lines.extend(_counter_table("Rows by item_type", item_type_counts))
    lines.extend(_counter_table("Rows by subsection_type", subsection_counts))

    lines.extend(["## Suspicious Korean Terms", "", "| Term | Count |", "| --- | ---: |"])
    for term in sorted(SUSPICIOUS_TERMS):
        lines.append(f"| {term} | {suspicious[term]} |")
    lines.append("")

    lines.extend(["## Critical Coverage", "", "| Manual | Term | Matching Rows |", "| --- | --- | ---: |"])
    for manual_key in MANUALS:
        manual_name = MANUALS[manual_key]["manual_type"]
        for term, count in _coverage(items, manual_key):
            lines.append(f"| {manual_name} | {term} | {count} |")
    lines.append("")

    lines.extend(["## Validation Findings Preview", "", "| Severity | Item | Message |", "| --- | --- | --- |"])
    for error in errors[:100]:
        lines.append(f"| {error['severity']} | {error.get('item_id', '')} | {error['message']} |")
    if not errors:
        lines.append("| info |  | No validation findings |")
    lines.append("")
    return "\n".join(lines)
