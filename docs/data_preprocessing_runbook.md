# Data Preprocessing Runbook

## Objective

Create reviewable CSV datasets from the two Korean immigration manuals in
`data/raw/`:

- `260504 체류민원 자격별 안내 매뉴얼.pdf`
- `260504 사증민원 자격별 안내 매뉴얼.pdf`

The data is intended for later RAG preprocessing. Because this is visa and
immigration administration data, the output must be treated as a review dataset,
not as a final legal knowledge base.

## Processing Decision

The current run parses both raw PDFs again with LlamaParse `agentic_plus`.
Completed older `agentic` jobs are not reused. The script saves markdown and
metadata artifacts for traceability, then builds a single clean CSV per PDF.

## Output Files

- `data/processed/stay_manual_clean.csv`
- `data/processed/visa_manual_clean.csv`

The default rebuild command removes old CSV files from `data/processed/` first,
so the completed CSV set contains only these two files.

## Method

1. Upload each raw PDF from `data/raw/` for LlamaParse.
2. Parse with `tier=agentic_plus`, `version=latest`, and `disable_cache=True`.
3. Save the parsed markdown and metadata locally.
4. Split each page conservatively by Markdown headings.
5. Create clean section rows with exact `source_raw_text`, normalized text, and
   short `evidence_quote`.
6. Derive metadata fields only from source text using deterministic keyword and
   code matching.
7. Mark rows needing review when they contain tables, multiple codes, parse
   warnings, or very long sections.

## Important Limitation

The script does not infer legal meaning. Derived fields such as
`petition_type`, `subsection_type`, `requirements`, and `required_documents`
are convenience fields for review and search preparation. The authoritative
content remains `source_raw_text` plus the PDF page reference.

Before using this data in production RAG, a human reviewer should verify:

- code-to-rule linkage
- 제출서류 vs 요건 separation
- restrictions vs exceptions
- table row/column meaning
- printed page labels
- evidence quotes
- rows marked `needs_human_review=true`

## Rebuild Command

```bash
/opt/anaconda3/bin/python scripts/build_manual_csvs.py
```

To run only one PDF:

```bash
/opt/anaconda3/bin/python scripts/build_manual_csvs.py --manual stay
```
