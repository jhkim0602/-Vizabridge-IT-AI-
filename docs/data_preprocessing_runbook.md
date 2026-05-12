# Data Preprocessing Runbook

## Objective

Create final cleaned semantic CSVs from the parsed Korean immigration manuals.
The output is no longer a review dataset. It is the cleaned dataset used as the
next source for downstream RAG preprocessing.

## Output Files

Only these processed files should remain:

- `data/processed/stay_manual_semantic_clean.csv`
- `data/processed/visa_manual_semantic_clean.csv`

## Method

1. Keep raw PDFs under `data/raw/`.
2. Keep LlamaParse Markdown artifacts under `data/parsed/`.
3. Run `scripts/build_semantic_manual_csvs.py`.
4. The script reads the latest parsed Markdown for each manual.
5. It removes cover/table-of-contents/navigation noise.
6. It classifies rows into clean administrative fields such as 대상, 요건, 제출서류, 절차, 제한, 예외, 수수료, 점수표, 쿼터.
7. It writes one final semantic CSV per PDF.

## Rebuild Command

```bash
.venv/bin/python scripts/build_semantic_manual_csvs.py
```

## Cleanup Rule

Do not keep old review/debug CSVs in `data/processed/`. The processed directory
should contain only `.gitkeep` and the two final semantic CSVs.
