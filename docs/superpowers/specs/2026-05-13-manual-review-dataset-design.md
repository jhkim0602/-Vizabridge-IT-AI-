# Manual Review Dataset Design

## Objective

Build a human-reviewable structured dataset from the two Korean immigration manuals:

- `data/raw/260504 체류민원 자격별 안내 매뉴얼.pdf`
- `data/raw/260504 사증민원 자격별 안내 매뉴얼.pdf`

The first priority is not RAG chunk optimization. The first priority is a dataset that a human reviewer can inspect, correct, and trust as a structured representation of the administrative manuals.

## Current Problem

The existing CSVs expose two separate issues:

1. Korean text quality defects such as `제목자격`, `제목관리과`, and `제목족적` indicate parsing or OCR contamination.
2. The semantic CSV shape is too narrow. The manuals are not simple required-document lists; they include common rules, fees, obligations, status-specific rules, petition-specific rules, score tables, quota tables, exceptions, and attachments.

The pipeline must preserve manual structure before producing any RAG-oriented output.

## Design Principle

Create a source-faithful intermediate representation first, then derive downstream datasets from it.

The review dataset must:

- preserve source evidence and page references,
- keep broad manual-specific fields,
- separate stay manual concepts from visa manual concepts,
- retain tables in a reviewable form,
- mark uncertain extraction instead of silently forcing a value,
- support automated quality checks before human review.

## Outputs

Primary outputs:

- `data/processed/manual_review_items.jsonl`
- `data/processed/manual_review_items.csv`
- `data/processed/manual_review_quality_report.md`

Optional debug outputs:

- `data/processed/manual_review_samples.csv`
- `data/processed/manual_review_validation_errors.jsonl`

Existing files such as `stay_manual_clean.csv`, `visa_manual_clean.csv`, `stay_manual_semantic_clean.csv`, and `visa_manual_semantic_clean.csv` remain as comparison artifacts unless explicitly replaced later.

## Common Fields

Every review item contains these fields:

| Field | Purpose |
| --- | --- |
| `item_id` | Stable generated id for review tracking |
| `manual_type` | `체류민원` or `사증민원` |
| `source_pdf` | Source PDF filename |
| `pdf_page_start` | First PDF page used as evidence |
| `pdf_page_end` | Last PDF page used as evidence |
| `printed_page_start` | Printed page label when available |
| `printed_page_end` | Printed page label when available |
| `section_path` | Hierarchical source path |
| `item_type` | Broad item class such as `common_rule`, `stay_status_rule`, `visa_rule`, `required_documents`, `fee`, `score_table`, `quota`, `restriction`, `exception`, `table` |
| `section_title` | Original or corrected section title |
| `subsection_type` | `대상`, `요건`, `제출서류`, `절차`, `제한`, `예외`, `수수료`, `점수표`, `쿼터`, `신고의무`, `기타` |
| `raw_text` | Source-faithful extracted text |
| `normalized_text` | Lightly normalized text for review and later retrieval |
| `table_summary` | Human-readable table summary when the item is table-derived |
| `table_rows` | JSON string of important table rows |
| `evidence_quote` | Short quote that must appear in `raw_text` or source text |
| `extraction_source` | `pdf_text`, `llamaparse_markdown`, `merged`, or `llm_assisted` |
| `confidence` | Numeric score from 0.0 to 1.0 |
| `needs_human_review` | Boolean review flag |
| `review_notes` | Reason for review flag or validation warning |

## Stay Manual Fields

Stay manual items may additionally contain:

| Field | Purpose |
| --- | --- |
| `stay_status_code` | Stay status code such as `D-2`, `E-7`, `F-2-R` |
| `stay_status_name_ko` | Korean status name such as `유학`, `특정활동`, `거주` |
| `subtype_or_program` | Detailed program such as `E-7-4`, `지역우수인재`, `K-point E74` |
| `petition_type` | `체류자격외 활동허가`, `근무처 변경/추가`, `체류자격 변경`, `체류기간 연장`, `재입국허가`, `외국인등록`, etc. |
| `eligibility` | Target applicant conditions |
| `requirements` | Review or approval requirements |
| `required_documents` | Required documents |
| `procedure` | Application procedure |
| `restrictions` | Restrictions and disallowed cases |
| `exceptions` | Exceptions and special cases |
| `obligations` | Reporting, education, residence, or other obligations |
| `fees` | Fees |
| `quota_or_limit` | Quotas, selection limits, permitted headcount, or caps |
| `score_criteria` | Score table or point allocation criteria |

## Visa Manual Fields

Visa manual items may additionally contain:

| Field | Purpose |
| --- | --- |
| `visa_code` | Visa code such as `C-3`, `D-8`, `E-7`, `F-6` |
| `visa_name_ko` | Korean visa name such as `단기방문`, `기업투자`, `특정활동`, `결혼이민` |
| `subtype_or_program` | Detailed visa type, special program, or recommendation track |
| `petition_type` | `사증발급`, `사증발급인정서`, `초청`, `재외공관 신청`, `전자사증`, etc. |
| `applicant_context` | Applicant situation |
| `inviter_context` | Inviter, employer, or host situation |
| `eligibility` | Issuance target |
| `requirements` | Issuance requirements |
| `required_documents` | Required documents |
| `procedure` | Application or issuance procedure |
| `restrictions` | Issuance restrictions and refusal reasons |
| `exceptions` | Exceptions and special cases |
| `duration_or_validity` | Stay period, visa validity, single/multiple visa information |
| `recommendation_or_approval` | Employment recommendation, agency approval, or recommendation body |

## Pipeline

1. Extract PDF text layer page by page with layout preservation.
2. Read LlamaParse Markdown artifacts as structural hints, especially headings and tables.
3. Align extracted text and Markdown by PDF page and nearby section titles.
4. Split into reviewable administrative items, not RAG chunks.
5. Classify each item into the broad schema using deterministic rules first.
6. Use LLM/API assistance only for bounded section-level classification, summarization, and field assignment where rules are weak.
7. Validate every item against schema and quality rules.
8. Generate sample outputs for critical sections.
9. Run full manual extraction only after sample quality gates pass.
10. Emit final JSONL, CSV, and quality report.

## LLM Usage Boundary

LLM assistance is allowed, but it must not be the source of truth.

Allowed LLM tasks:

- classify `item_type` and `subsection_type`,
- map text into schema fields,
- summarize table purpose,
- propose review notes,
- repair malformed structured output.

Required safeguards:

- the prompt input must be a bounded section or table block,
- output must be validated JSON,
- evidence quote must be checked against source text,
- uncertain fields must remain blank or set `needs_human_review=true`,
- generated summaries must not replace `raw_text`.

## Automated Quality Checks

The quality report must include:

- row counts by `manual_type`, `item_type`, and `subsection_type`,
- missing required field counts,
- code recognition counts for major codes,
- suspicious Korean term hits such as `제목자격`, `제목관리과`, `제목족적`,
- evidence quote containment failures,
- rows with empty `raw_text`,
- rows with tables collapsed into unreadable single-cell text,
- stay manual rows with visa-only fields populated incorrectly,
- visa manual rows with stay-only fields populated incorrectly,
- high-value section coverage.

High-value stay coverage includes:

- common notes and fees,
- reporting obligations,
- `D-2`,
- `E-7`,
- `E-7-4`,
- region-specific visa sections,
- score tables,
- quota tables,
- accompanying family requirements.

High-value visa coverage includes:

- `C-3`,
- `D-8`,
- `E-7`,
- `F-6`,
- visa issuance certificate sections,
- inviter and invitee requirements,
- single and multiple visa rules,
- recommendation or approval requirements,
- issuance restrictions and exceptions.

## Failure Conditions

The pipeline must stop before final output if any of these occur:

- PDF text extraction fails for either manual.
- More than 2 percent of rows have empty `raw_text`.
- More than 5 percent of evidence quotes cannot be found in the source text.
- Any suspicious Korean term appears in final `section_title`, `normalized_text`, or key schema fields without a review note.
- Critical sections such as `D-2`, `E-7`, `E-7-4`, `C-3`, `D-8`, or `F-6` are missing.
- JSON validation fails for generated records.

## Acceptance Criteria

The work is acceptable when:

- final JSONL and CSV are generated,
- the quality report is generated,
- critical section coverage is present,
- validation failures are either zero or explicitly listed in the report,
- uncertain rows are marked with `needs_human_review=true`,
- the dataset remains source-faithful enough for a human reviewer to correct without reopening every PDF page.

## Non-Goals

This design does not produce the final RAG retrieval dataset directly. RAG-oriented rows, embeddings, question examples, and answer summaries should be derived later from the human-reviewed structured dataset.
