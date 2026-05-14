# HWP/kordoc + Skill-Based LLM Pipeline Redesign

- **Date**: 2026-05-14
- **Author**: ghibli2026team@gmail.com + Claude (collaborative)
- **Status**: Implemented
- **Scope**: Replace PDF/LlamaParse ingestion with HWP/kordoc. Replace regex-based CSV builders with Claude Code skill-driven normalization through a canonical intermediate Markdown.

## 1. Background

Vizabridge converts Korean immigration administrative manuals (사증민원/체류민원) into RAG-ready CSVs. The legacy pipeline had three weaknesses that drove this redesign:

1. **PDF/LlamaParse OCR** at stage 1 degraded Korean text and broke table structure.
2. **Regex semantic classifier** (`scripts/legacy/build_semantic_manual_csvs.py`, 999 lines) was tuned to LlamaParse output and would break again under any new parser.
3. **Hardcoded chatbot keyword rules** could not bridge "한국인 배우자와 결혼했어요" ↔ `F-6` reliably.

## 2. Goals

1. Use HWP files as the source of truth; rely on kordoc to convert them losslessly to Markdown.
2. Insert a canonical intermediate Markdown layer between LLM extraction and CSV generation. LLM does semantic classification only; CSV generation is deterministic Python.
3. Run all LLM stages inside Claude Code skills (Claude Max subscription) — no separate Anthropic API billing.
4. Make every stage idempotent and resumable. The normalize and enrich skills must survive session limits and pick up where they left off.
5. Catch hallucinations and information loss in a dedicated, deterministic validator — not in the LLM step itself.
6. Keep the final CSV schema unchanged so downstream consumers do not need to change.

## 3. Non-Goals

- Embedding generation, RAG retrieval evaluation, vector storage — out of scope.
- CI execution of LLM stages — Claude Code is interactive; skills run in user sessions.
- Migrating downstream consumers — final CSV columns are intentionally identical to the legacy pipeline.
- Live/streaming pipeline — manuals update infrequently; batch is fine.

## 4. Architecture (as implemented)

```
data/raw/*.hwp                                              source of truth
   │  Stage 1  scripts/parse_hwp_to_markdown.py             Python, kordoc subprocess
   ▼
data/parsed/raw/{stay,visa}_manual.md
   │  Stage 2  scripts/index_markdown_chunks.py             Python, deterministic
   ▼
data/parsed/chunks/{stay,visa}_chunks_index.jsonl
   │  Stage 3  /vizabridge-normalize                        Claude Code skill
   ▼
data/parsed/normalized/{stay,visa}_manual.md
   │  Stage 4  scripts/validate_normalization.py            Python, deterministic
   │  Stage 5  /vizabridge-repair (conditional)             Claude Code skill
   │  Stage 6  scripts/build_semantic_csv.py                Python, deterministic
   ▼
data/processed/{stay,visa}_manual_semantic_clean.csv
   │  Stage 7  /vizabridge-enrich-chatbot                   Claude Code skill
   ▼
data/parsed/normalized_chatbot/{stay,visa}_manual.md
   │  Stage 8  scripts/build_chatbot_csv.py                 Python, deterministic
   ▼
data/processed/{stay,visa}_manual_chatbot_ready.csv
   │  Stage 9  scripts/quality_report_semantic_manual_csvs.py
   ▼
output/quality/*, output/review/*
```

LLM (skills) operate in stages 3, 5, 7 only. Everything else is deterministic Python.

## 5. Empirical Findings That Shaped the Implementation

These were not in the original spec — they emerged from running kordoc on the actual HWPs and dictated several design choices.

### 5.1 kordoc output is HTML-table-centric, not heading-centric

kordoc preserves HWP tables as HTML `<table>` blocks with nested `<tr>`/`<td>`/`<th>`/`<br>`. Markdown headings (`#`, `##`, `###`) exist only sporadically between tables — for supplementary sections like `## □ 쿼터 유형별 설명` in E-7-4.

The first prototype chunker assumed "one visa code = one `<table>` whose first `<th>` is `<name>(<code>)`". This worked for ~95% of codes but failed on:

- **체류 manual F-2** — the table header is mangled to `<th>.</th>`
- **H-2 in both manuals** — appears only in supplementary tables, never as a primary anchor
- **F-4 in 사증 manual** — appears twice (main section + 외국국적동포 부록)
- **F-1 in 체류 manual** — anchor table has a malformed colspan structure

### 5.2 The chunker re-design

Rather than patching the anchor heuristic, we replaced the "one chunk = one visa code" assumption entirely:

- Walk the file. Cut at top-level `<table>` close boundaries when accumulated size hits ~15K chars.
- For each chunk, regex-scan the entire chunk text and record all visa codes found (e.g. `["D-2", "D-2-1", "F-1-3"]`).
- The normalize skill receives a chunk plus its discovered codes; it emits one row per (code, petition_type, subsection_type) combination it judges meaningful. Many-to-many.

Result on real data:
- **stay**: 34 chunks, 181 unique codes discovered (including sub-codes D-2-1, F-2-R, E-7-S, …) — including F-2 and H-2 that the original anchor approach lost.
- **visa**: 23 chunks, 159 unique codes.
- Five oversized chunks (E-7, F-2/F-5, F-3 cluster, D-3, F-4 부록) trigger the normalize skill's internal sub-chunking.

### 5.3 Canonical intermediate Markdown is the right hinge

The normalized Markdown has block markers and YAML-ish fields:

```
<!-- vizabridge-normalize v1 chunk: stay_018 hash: 22ee44 lines: 466-475 -->

### row D-8 / 사증발급 / 요건
- manual_type: 사증민원
- visa_code: D-8
- visa_name_ko: 기업투자
- item_type: visa_rule
- ...

<!-- end chunk: stay_018 -->
```

Three properties make this hinge work:

- **Human-readable**: a reviewer can open the file and check rows.
- **Machine-parsable**: `scripts/build_semantic_csv.py` is ~140 lines and entirely regex.
- **Diffable**: schema changes don't require LLM re-run; just re-run the CSV builder.

### 5.4 The validator catches real hallucinations

Smoke test produced a row with `fees: 120,000원`. The source said `수수료(자격외 활동 12만원)`. Validator's amount-preservation check flagged this as `amount not in source: 120000원`. This is exactly the kind of unit-normalization slip an LLM makes and a regex never would. Validator works.

The validator currently checks:
- Visa codes claimed by row appear in source chunk
- Monetary amounts cited in `fees` appear in source
- Document names in `mandatory_documents` / `common_documents` appear in source (lenient: only flags if none match)
- Required fields are non-empty

## 6. Files Produced

### New Python scripts

| Path | Purpose |
| --- | --- |
| `scripts/parse_hwp_to_markdown.py` | Stage 1 — kordoc subprocess |
| `scripts/index_markdown_chunks.py` | Stage 2 — chunker |
| `scripts/validate_normalization.py` | Stage 4 — cross-validator |
| `scripts/build_semantic_csv.py` | Stage 6 — normalized → semantic CSV |
| `scripts/build_chatbot_csv.py` | Stage 8 — normalized chatbot → chatbot CSV |

### Claude Code skills

| Path | Purpose |
| --- | --- |
| `.claude/skills/vizabridge-normalize/` | Stage 3 — main LLM stage |
| `.claude/skills/vizabridge-enrich-chatbot/` | Stage 7 — chatbot enrichment |
| `.claude/skills/vizabridge-repair/` | Stage 5 — repair flagged chunks |

Each skill: `SKILL.md` (short procedure), `references/*.md` (loaded on demand), `scripts/*.py` (deterministic helpers like `show_progress.py`, `append_block.py`).

### Moved

- `data/raw/*.pdf` → `data/raw/legacy_pdf/`
- `scripts/build_semantic_manual_csvs.py`, `scripts/build_chatbot_ready_manual_csvs.py` → `scripts/legacy/` (quality_report still imports its constants and classifier helpers)

### Deleted

- `notebooks/01_setup_llamaparse_api_key.ipynb`
- `notebooks/02_parse_pdfs_with_llamaparse.ipynb`

### Modified

- `requirements.txt`: removed `llama-cloud`, `pypdf`, `pdfplumber`
- `.env.example`: removed `LLAMA_CLOUD_API_KEY`
- `.gitignore`: tracks `data/parsed/{chunks,normalized,normalized_chatbot,validation}/`; ignores `data/parsed/raw/` and `data/processed/`
- `scripts/quality_report_semantic_manual_csvs.py`: import path updated to `scripts.legacy`
- `README.md`, `docs/*.md`: rewritten for the new pipeline

## 7. Skill Design Details

Each LLM-stage skill follows the same pattern:

1. **SKILL.md** — short procedure: load progress → identify next unit of work → read source → emit canonical block → append via helper → repeat or stop on fatigue.
2. **references/*.md** — long-form domain knowledge (column schema, extraction rules, noise filters, situation taxonomy, output format examples). The skill reads only the relevant reference for each turn.
3. **scripts/show_progress.py** — prints next pending work item, completed count, and useful metadata. Exits 1 when nothing left.
4. **scripts/append_block.py** (or `replace_block.py` for repair) — validates the proposed block (schema, hash, no duplicates) and atomically writes.

### Resumability mechanism

Both normalize and enrich skills mark their work with open/close markers in the output Markdown:

```
<!-- vizabridge-normalize v1 chunk: stay_004 hash: ... lines: 432-617 -->
...
<!-- end chunk: stay_004 -->
```

`show_progress.py` cross-references the chunk index (or semantic CSV row list) against the markers already present in the output, identifying the next pending chunk/row. There is no separate state file; the output Markdown is the state.

### Hash-based drift detection

Each open marker carries the source `content_hash` at the time of writing. If kordoc is rerun and a chunk's source content changes, the hash in the index drifts away from the marker's hash. The validator flags this; the repair skill refuses to "repair" a drifted chunk (that's a re-normalize, not a repair).

## 8. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Sessions hit Max usage limits during normalization | Skill stops cleanly on context fatigue; next session resumes via show_progress |
| LLM hallucinates a fact (amount, document) | Validator catches; repair skill fixes |
| Source HWP gets updated and chunks drift | Hash mismatch detected; targeted re-normalize only on changed chunks |
| Chunker fails on a future manual format | Empirical chunker is simple (table boundaries + size budget); easy to inspect and tweak |
| Skill output format diverges from CSV builder expectations | Append helper validates schema before write; CSV builder defines the contract |
| Normalize/enrich users on different machines diverge | Normalized MD is committed; CSV is regenerated deterministically |
| Tests broken by refactor | Test status is documented in project_structure.md; tests are additive, not gating |

## 9. Acceptance Status

- ✅ HWP files parsed by kordoc into `data/parsed/raw/`
- ✅ Chunker discovers all 37 main visa codes + 100+ sub-codes
- ✅ vizabridge-normalize skill complete (SKILL.md + 4 references + 2 helpers)
- ✅ Validator runs and catches real entity mismatches (smoke-tested)
- ✅ Semantic CSV builder produces correct schema (smoke-tested with 2 hand-crafted rows)
- ✅ Enrich-chatbot skill complete (SKILL.md + 4 references + 2 helpers)
- ✅ Repair skill complete
- ✅ Chatbot CSV builder complete
- ✅ Docs (README, structure, strategy, runbook) updated
- ⏳ Real end-to-end run (normalize → enrich → CSVs) — deferred to user-driven Claude Code session, since this is the LLM work

The pipeline foundation is complete. Producing the actual CSVs is a future Claude Code session — the user invokes the skills and they pick up from `show_progress.py` reporting 0 / 34 (or 0 / 23) for the relevant manual.

## 10. Future Improvements (not in this work)

- **Intent route derivation**: a small `chatbot_intent_routes.csv` aggregated across the enriched chatbot CSV. Either as a fourth skill (`vizabridge-derive-routes`) or as a post-processing step in `enrich-chatbot`. Mentioned in `docs/data_columns.md` but deferred.
- **Streamlit dashboard**: read the produced CSVs, render Plotly visualizations (visa code distribution, missingness heatmap, intent graph). Loosely coupled — runs alongside the skill-driven backend, no UI-triggered LLM work.
- **Test coverage**: pytest tests for the chunker (chunk count stability, hash determinism), validator (entity detection rules), and CSV builders (schema enforcement).
- **Quality report threshold tuning**: thresholds were calibrated for legacy regex output; will need adjustment after first real end-to-end run.
