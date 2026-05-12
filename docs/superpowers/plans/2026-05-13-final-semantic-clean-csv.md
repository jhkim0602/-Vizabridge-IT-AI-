# Final Semantic Clean CSV Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace review/debug datasets with two final cleaned semantic CSVs: `stay_manual_semantic_clean.csv` and `visa_manual_semantic_clean.csv`.

**Architecture:** Keep one production builder, `scripts/build_semantic_manual_csvs.py`, that reads parsed Markdown and existing manual structure, filters noise/table-of-contents rows, classifies administrative sections into clean semantic fields, and writes exactly one CSV per PDF. Final CSVs exclude PDF page numbers, raw source text, evidence quotes, and review/debug columns.

**Tech Stack:** Python standard library CSV/regex, optional pandas only for inspection, pytest for contract tests.

---

### Task 1: Contract Tests

**Files:**
- Create: `tests/test_final_semantic_clean.py`
- Modify: `scripts/build_semantic_manual_csvs.py`

- [ ] Write tests asserting final CSV columns exclude page/evidence/raw/review fields.
- [ ] Write tests asserting obvious 목차/noise rows are filtered.
- [ ] Write tests asserting generated rows expose clean fields such as `common_documents`, `mandatory_documents`, `other_documents`, `eligibility`, `requirements`, `procedure`, `restrictions`, `exceptions`, `fees`, `score_criteria`, and `quota_or_limit`.
- [ ] Run the tests and confirm they fail before rewriting the builder.

### Task 2: Rewrite Semantic Builder

**Files:**
- Modify: `scripts/build_semantic_manual_csvs.py`

- [ ] Replace review-oriented output with two clean CSV schemas.
- [ ] Parse LlamaParse Markdown headings, tables, and text blocks.
- [ ] Normalize common Korean OCR spacing/code issues.
- [ ] Classify item type, petition type, subsection type, and document buckets.
- [ ] Drop table-of-contents and short navigation noise.
- [ ] Exclude page/evidence/raw/review columns.

### Task 3: Remove Old Artifacts

**Files:**
- Delete: `scripts/build_manual_csvs.py`
- Delete: `scripts/build_manual_review_dataset.py`
- Delete: `scripts/build_semantic_review_notebook.py`
- Delete: `scripts/manual_review/`
- Delete: `tests/test_manual_review_*.py`
- Delete: `docs/superpowers/plans/2026-05-13-manual-review-dataset.md`
- Delete: `docs/superpowers/specs/2026-05-13-manual-review-dataset-design.md`
- Delete processed outputs except the final two semantic CSVs and `.gitkeep`.

### Task 4: Generate and Verify

**Files:**
- Output: `data/processed/stay_manual_semantic_clean.csv`
- Output: `data/processed/visa_manual_semantic_clean.csv`

- [ ] Run `python3 scripts/build_semantic_manual_csvs.py`.
- [ ] Run `python3 -m pytest tests -q`.
- [ ] Verify `data/processed/` contains only `.gitkeep`, `stay_manual_semantic_clean.csv`, and `visa_manual_semantic_clean.csv`.
- [ ] Inspect row counts, column names, blank rates, and noise terms.
