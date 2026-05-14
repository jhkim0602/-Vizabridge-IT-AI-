# HWP/kordoc + LLM Pipeline Redesign

- **Date**: 2026-05-14
- **Author**: ghibli2026team@gmail.com + Claude (collaborative)
- **Status**: Draft (awaiting user review)
- **Scope**: Replace PDF/LlamaParse ingestion with HWP/kordoc; replace regex-based CSV builders with Claude API extractors.

## 1. Background

Vizabridge converts Korean immigration administrative manuals (사증민원/체류민원) into RAG-ready CSVs. The current pipeline has three weaknesses:

1. **Stage 1 (PDF → Markdown via LlamaParse)** uses OCR-style parsing. Korean text rendering and table structure suffered noticeable quality loss. The original HWP files exist; using them removes OCR ambiguity entirely.
2. **Stage 2 (`scripts/build_semantic_manual_csvs.py`)** is a 999-line regex/keyword classifier tuned to LlamaParse's output. The most recent commit (`기존 semantic csv 품질 개선`) was patching this layer. Switching the upstream parser will break it again.
3. **Stage 3 (`scripts/build_chatbot_ready_manual_csvs.py`)** generates situation tags and natural-language keywords through hardcoded keyword rules. The project's stated goal is bridging "한국인 배우자와 결혼했다" → `F-6`-class natural-language understanding, which is the exact task an LLM does well and keyword rules do poorly.

This redesign tackles all three at once because (a) the parser swap forces re-tuning of stage 2 anyway, and (b) the project explicitly invites LLM-based improvements.

## 2. Goals

1. Restore Korean text and table fidelity at the source: parse the native HWP files instead of OCR'd PDFs.
2. Make extraction robust to format variation by replacing regex classifiers with LLM-based structured extraction.
3. Keep the final CSV contract unchanged: same filenames, same columns, no review/page/raw columns. Downstream consumers must not need changes.
4. Make full pipeline runs deterministic-enough to be CI-friendly: temperature 0 + on-disk cache keyed by content hash. Re-runs without input changes must hit the cache (zero cost, identical output).
5. Make first-run cost visible and capped: dry-run mode shows token estimates; full run requires explicit confirmation.

## 3. Non-Goals

- Embedding generation (pgvector, sentence-transformers) — out of scope. The CSV remains the downstream-RAG input boundary as stated in `docs/pipeline_strategy.md`.
- RAG retrieval quality evaluation — separate project.
- Migrating downstream consumers — Final CSV schema is intentionally unchanged.
- MCP/agent integration of kordoc — `subprocess` invocation is sufficient and simpler.
- Live/streaming pipeline — manuals update infrequently (the PDFs/HWPs are dated `260504`). Batch runs are fine.

## 4. Architecture

```
data/raw/*.hwp                                       (source of truth)
   │
   │ stage 1: scripts/parse_hwp_to_markdown.py
   │   - validates Node.js ≥ 18 and npx availability
   │   - shells out to `npx kordoc <hwp> -o <md>`
   │   - one md per hwp, deterministic filenames
   ▼
data/parsed/{stay,visa}_manual.md
   │
   │ stage 2: scripts/extract_semantic_csv_with_llm.py
   │   - chunker (deterministic, regex over headings)
   │   - extractor: Claude Sonnet 4.6 with tool-use schema
   │   - on-disk cache: data/parsed/llm_extracts/{stage}/{hash}.json
   ▼
data/processed/{stay,visa}_manual_semantic_clean.csv
   │
   │ stage 3: scripts/enrich_chatbot_csv_with_llm.py
   │   - per-row Claude call with tool-use schema
   │   - same disk cache pattern
   ▼
data/processed/{stay,visa}_manual_chatbot_ready.csv
data/processed/chatbot_intent_routes.csv
   │
   │ stage 4: scripts/quality_report_semantic_manual_csvs.py (kept, light edits)
   ▼
output/quality/*, output/review/*
```

### Component boundaries

Each stage reads files from the previous stage's output directory and writes to its own. No in-memory hand-off. This means any stage can be re-run independently as long as its inputs exist on disk — the same property the current pipeline has.

## 5. Stage Details

### Stage 1 — `scripts/parse_hwp_to_markdown.py`

- **Input**: `data/raw/*.hwp`
- **Output**: `data/parsed/{manual_key}_manual.md` where `manual_key` is `stay` or `visa`, derived from the filename keyword (`체류민원` → `stay`, `사증민원` → `visa`).
- **Behavior**:
  - On startup, runs `node --version` and `npx --version`; aborts with an actionable message if Node < 18 or npx missing.
  - For each HWP, runs `npx --yes kordoc <hwp_path> -o <output_path>` via `subprocess.run`. `--yes` ensures non-interactive package install on first run.
  - Skips files whose output already exists and is newer than the input, unless `--force` is passed.
  - Prints a summary table (file, size, output path, status).
- **Failure modes**: kordoc nonzero exit → stop, show stderr. We do not retry; we surface the failure.

### Stage 2 — `scripts/extract_semantic_csv_with_llm.py`

#### 2a. Chunking (deterministic, no LLM)

Markdown headings define the chunk boundaries. Heuristics:

- A chunk is a `## <비자코드 or 자격 제목>` block (optionally `### <민원유형>` subblock).
- Front matter (cover, table of contents, common instructions) is one preamble chunk per manual.
- Each chunk carries: `manual_key`, `manual_type`, `chunk_index`, `chunk_title`, `chunk_text`, `content_hash` (sha256 of normalized text).

Chunker output is `data/parsed/chunks/{manual_key}_chunks.jsonl`. Reviewable by humans before LLM stage runs.

#### 2b. Extraction (LLM)

- Model: `claude-sonnet-4-6`. Temperature 0. Max tokens generous (e.g., 4096 for output).
- Strategy: **tool use with a strict JSON schema** that mirrors `STAY_COLUMNS` / `VISA_COLUMNS` in the current script. The model is forced (`tool_choice` on a named tool) to call `emit_semantic_rows`, whose input is a list of row objects. Always a list, even for one row — this handles the common case of one visa code containing multiple petition types (사증발급, 사증발급인정서, 체류자격 변경, 기간연장, 근무처 변경, ...) cleanly without per-chunk branching.
- System prompt:
  - Defines the data model (column-by-column with one-line semantics).
  - Defines noise rules ported from `is_noise_row` / `is_low_value_semantic_row` (cover, TOC, blank-form, broken-table fragments → "do not emit").
  - Asks the model to drop a row entirely instead of inventing data when the source is ambiguous (refusal is allowed and preferred over hallucination).
- **Prompt caching**: system prompt + schema are sent with `cache_control: ephemeral` so subsequent calls in the same 5-minute window hit cache (~50% input-token discount).
- **On-disk cache**: `data/parsed/llm_extracts/semantic/{content_hash}.json` holds the raw tool-call result. The CSV writer reads this cache, so re-runs without content changes are pure I/O.

#### Output

`data/processed/{stay,visa}_manual_semantic_clean.csv`, identical schema to current. The columns are not re-designed in this work.

### Stage 3 — `scripts/enrich_chatbot_csv_with_llm.py`

- **Input**: stage 2 semantic CSVs.
- For each row, Claude generates: `situation_tags`, `natural_language_keywords`, `followup_questions`, `routing_hints`, `intent_examples`.
- Same tool-use schema + caching pattern as stage 2.
- Routes file (`chatbot_intent_routes.csv`) is produced by aggregating across rows (a separate prompt that takes the full semantic CSV and emits route table — runs once per manual, not per row).
- Cache lives at `data/parsed/llm_extracts/chatbot/{content_hash}.json`.

### Stage 4 — `scripts/quality_report_semantic_manual_csvs.py`

Minor edits only:
- The `row_issues()` thresholds may need tuning because LLM extraction will likely have a different missingness profile than regex extraction.
- No structural change.

## 6. File and Directory Changes

### New files

| Path | Purpose |
|---|---|
| `scripts/parse_hwp_to_markdown.py` | Stage 1 entry point |
| `scripts/extract_semantic_csv_with_llm.py` | Stage 2 entry point |
| `scripts/enrich_chatbot_csv_with_llm.py` | Stage 3 entry point |
| `scripts/_llm.py` | Shared Anthropic client wrapper: prompt caching, retry on transient errors, dry-run mode, cost estimator |
| `scripts/_chunker.py` | Shared deterministic markdown chunker |
| `notebooks/02_parse_hwps_with_kordoc.ipynb` | Exploration of kordoc output |
| `data/raw/legacy_pdf/.gitkeep` | Preserve the legacy PDFs under a sibling folder |
| `scripts/legacy/.gitkeep` | Archive folder for old regex builders |

### Moved

| From | To |
|---|---|
| `data/raw/*.pdf` | `data/raw/legacy_pdf/*.pdf` |
| `scripts/build_semantic_manual_csvs.py` | `scripts/legacy/build_semantic_manual_csvs.py` |
| `scripts/build_chatbot_ready_manual_csvs.py` | `scripts/legacy/build_chatbot_ready_manual_csvs.py` |

### Deleted

- `notebooks/01_setup_llamaparse_api_key.ipynb` (kordoc has no API key)
- `notebooks/02_parse_pdfs_with_llamaparse.ipynb` (replaced by kordoc notebook)

### Modified

- `requirements.txt`: remove `llama-cloud>=2.1`, add `anthropic>=0.40`.
- `.env.example`: remove `LLAMA_CLOUD_API_KEY`, add `ANTHROPIC_API_KEY`.
- `README.md`: rewrite workflow section. New commands listed below.
- `docs/pipeline_strategy.md`: drop the "Parse First or Split First?" OCR-driven rationale; replace with a short note on why HWP+kordoc + LLM extraction was chosen.
- `docs/project_structure.md`: update the scripts table.
- `docs/data_preprocessing_runbook.md`: update commands and add the cost/dry-run note.
- `scripts/README.md`: update to match new entry points.
- `tests/*`: tests will be updated alongside the scripts they cover. Tests for the legacy builders move with them to `scripts/legacy/` (preserved but not run by default).
- `.gitignore`: add an exception so the LLM cache directory is tracked. Concretely: keep the existing `data/parsed/*` exclusion, and add `!data/parsed/llm_extracts/` plus `!data/parsed/llm_extracts/**`. Rationale: manual content rarely changes; committing the cache means a fresh checkout produces identical CSVs with zero API spend. The kordoc-generated `.md` files stay gitignored as before.

### New commands

```bash
.venv/bin/python scripts/parse_hwp_to_markdown.py
.venv/bin/python scripts/extract_semantic_csv_with_llm.py --dry-run    # cost estimate
.venv/bin/python scripts/extract_semantic_csv_with_llm.py --yes        # real run
.venv/bin/python scripts/enrich_chatbot_csv_with_llm.py --dry-run
.venv/bin/python scripts/enrich_chatbot_csv_with_llm.py --yes
.venv/bin/python scripts/quality_report_semantic_manual_csvs.py
```

## 7. LLM Integration Details

### Anthropic SDK usage

- SDK: `anthropic` (Python).
- Model: `claude-sonnet-4-6`.
- Tool use: each extractor defines one tool with `input_schema` reflecting the target CSV row(s). `tool_choice = {"type": "tool", "name": "..."}` to force the call.
- Prompt caching: system block + tool definitions marked `cache_control = {"type": "ephemeral"}`. Each chunk goes in the user turn (uncached).
- Retries: built-in SDK retries for 5xx; we add no manual loop.
- Concurrency: limit to ~5 in-flight calls. The chunk counts are small enough that we don't need sophisticated rate limiting.

### Determinism & caching

- Cache key is `sha256(normalize(chunk_text) + schema_version + system_prompt_version + model_id)`. Bumping the prompt, schema, or model invalidates cache cleanly.
- Cache files store the full tool call result + the prompt/model versions used, so we can audit what produced each row.

### Cost guard

- `--dry-run` prints: chunk count, estimated input tokens (chunk + system), estimated output tokens (heuristic: 1/3 of input), estimated USD at current Sonnet 4.6 pricing. No API calls are made.
- Without `--dry-run` and without `--yes`: print the same estimate and prompt for interactive confirmation before making any API call.
- With `--yes`: skip confirmation. Intended for re-runs after the user has validated cost once.
- After the run, print actual usage and a delta from the estimate.

## 8. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| First-run cost overshoots estimate | `--dry-run` + confirmation gate; print running total after each batch |
| kordoc Markdown structure differs from expectations, breaking the chunker | Chunker is deliberately the simplest piece; if headings look different, the chunker rule is a small file to adjust |
| LLM extraction hallucinates data not in source | Prompt explicitly forbids; tool schema validates field presence; quality report compares semantic CSV rows against source chunk text via a "needs review" flag |
| Anthropic SDK API errors mid-run | Per-chunk caching means re-runs resume; no progress lost |
| Old regex script removed prematurely | Moved to `scripts/legacy/`, not deleted |
| `.env` setup confusion | `.env.example` updated; stage 2/3 scripts fail fast with a clear message if `ANTHROPIC_API_KEY` missing |
| Tests broken by refactor | New tests added per new script; legacy tests move with legacy scripts |

## 9. Rollout / Commit Plan

1. `chore: archive legacy regex builders and pdfs`
   - Move PDFs to `data/raw/legacy_pdf/`; move regex scripts to `scripts/legacy/`.
2. `feat: parse hwp via kordoc`
   - Add stage 1 script, kordoc notebook, run once to produce `data/parsed/{stay,visa}_manual.md`.
3. `feat: extract semantic csv via claude api`
   - Add chunker, stage 2 script, shared `_llm.py`. Run once with `--dry-run`, then with `--yes`. Commit cache.
4. `feat: enrich chatbot csv via claude api`
   - Add stage 3 script. Run.
5. `chore: tune quality report thresholds for llm output`
6. `docs: rewrite workflow for hwp/kordoc + llm pipeline`
   - Update README, docs, scripts/README, .env.example, requirements.txt.

Each step is independently reviewable. After step 3 the new pipeline is functionally complete; steps 4–6 add the chatbot layer and documentation.

## 10. Open Questions

None at this time. User authorized expanded scope and gave discretion. Decisions in `§4–§7` are recorded as final unless overturned during plan/implementation review.

## 11. Acceptance Criteria

- Running the three commands above end-to-end on fresh checkout produces the same CSV filenames in `data/processed/` as the current pipeline.
- Final CSVs contain no PDF page columns, evidence quotes, raw text, or review flags (unchanged contract).
- Re-running stages 2 and 3 with no input changes makes zero API calls (cache hits 100%).
- `quality_report` runs without code changes; threshold tuning may be required.
- `pytest tests -q` passes for the new scripts.

