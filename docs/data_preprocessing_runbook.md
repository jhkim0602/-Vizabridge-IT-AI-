# Data Preprocessing Runbook

## Objective

Create final cleaned semantic CSVs and chatbot-ready CSVs from the parsed Korean
immigration manuals. The output is no longer a review dataset. It is the cleaned
dataset used as the next source for downstream RAG/chatbot preprocessing.

In plain terms: this pipeline does not preserve the PDF's page shape. It keeps
the administrative meaning. A paragraph, table row, or heading is kept only when
it helps answer questions about who is eligible, what documents are required,
what restrictions apply, what fees exist, or how a visa/stay petition works.

## Output Files

Semantic clean CSVs:

- `data/processed/stay_manual_semantic_clean.csv`
- `data/processed/visa_manual_semantic_clean.csv`

Chatbot-ready CSVs:

- `data/processed/stay_manual_chatbot_ready.csv`
- `data/processed/visa_manual_chatbot_ready.csv`
- `data/processed/chatbot_intent_routes.csv`

## Method

1. Keep raw PDFs under `data/raw/`.
2. Keep LlamaParse Markdown artifacts under `data/parsed/`.
3. Run `scripts/build_semantic_manual_csvs.py`.
4. The script reads the latest parsed Markdown for each manual.
5. It removes cover/table-of-contents/navigation noise.
6. It removes blank forms and broken table fragments that do not carry useful standalone meaning.
7. It classifies rows into clean administrative fields such as 대상, 요건, 제출서류, 절차, 제한, 예외, 수수료, 점수표, 쿼터.
8. It writes one final semantic CSV per PDF.
9. Run `scripts/build_chatbot_ready_manual_csvs.py`.
10. It adds user-situation tags, natural-language intent keywords, follow-up question hints, routing hints, and search text.

## Rebuild Command

```bash
.venv/bin/python scripts/build_semantic_manual_csvs.py
.venv/bin/python scripts/build_chatbot_ready_manual_csvs.py
```

## Quality Review Command

최종 CSV를 만든 뒤 다음 명령으로 자동 품질검사와 검수용 Excel을 생성합니다.

```bash
.venv/bin/python scripts/quality_report_semantic_manual_csvs.py
```

산출물은 `output/quality/`와 `output/review/`에 생성합니다.

- `output/quality/semantic_manual_quality_report.md`: 전체 품질 요약
- `output/quality/*_manual_review_candidates.csv`: 우선 검수 후보 행
- `output/review/stay_manual_review.xlsx`: 체류민원 전체 행 + 검수 플래그
- `output/review/visa_manual_review.xlsx`: 사증민원 전체 행 + 검수 플래그

검수용 Excel의 `all_rows_with_flags` 시트는 원본 semantic CSV 전체 행에 `needs_review`, `review_priority`, `review_reason`, `suggested_action`을 붙입니다. 최종 CSV 자체에는 이 검수 컬럼을 넣지 않습니다.

## Cleanup Rule

Do not keep old review/debug CSVs in `data/processed/`. The processed directory
should contain only `.gitkeep`, semantic clean CSVs, and chatbot-ready CSVs.
