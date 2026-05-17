> 🌐 **Language:** [한국어](README.md) | **English**

# Vizabridge Visa RAG

A data preprocessing pipeline that converts the original **HWP** files of Korea's visa / residence-permit manuals into Markdown using [kordoc](https://github.com/chrisryugj/kordoc), normalizes them into semantic units via **Claude Code skills**, and finally produces RAG / chatbot-ready CSVs through **deterministic Python**.

The core goal of this repository is **not** to dump the PDF into tables, but to turn the semantic structure of administrative manuals into data that is easy to consume. The final CSVs are organized by administrative units such as residence/visa code, petition type, target, requirements, required documents, restrictions, exceptions, fees, scoring tables, and quotas.

Real users rarely know codes like `E-7`, `F-6`, or `D-2`. They describe their situation — "I married a Korean spouse", "I'm an international student and want a part-time job", "I want to hire a foreign employee". For this reason, the chatbot CSV adds situation tags, natural-language search keywords, follow-up questions to ask the user, and routing hints.

## Pipeline

```
data/raw/*.hwp                                            (source of truth)
   │  Stage 1  scripts/parse_hwp_to_markdown.py           (Python, kordoc)
   ▼
data/parsed/raw/{stay,visa}_manual.md
   │  Stage 2  scripts/index_markdown_chunks.py           (Python, deterministic)
   ▼
data/parsed/chunks/{stay,visa}_chunks_index.jsonl
   │  Stage 3  /vizabridge-normalize                      (Claude Code skill)
   ▼
data/parsed/normalized/{stay,visa}_manual.md              ← canonical intermediate
   │  Stage 4  scripts/validate_normalization.py          (Python, deterministic)
   │  Stage 5  /vizabridge-repair                         (Claude Code skill, optional)
   │  Stage 6  scripts/build_semantic_csv.py              (Python, deterministic)
   ▼
data/processed/{stay,visa}_manual_semantic_clean.csv
   │  Stage 7  /vizabridge-enrich-chatbot                 (Claude Code skill)
   ▼
data/parsed/normalized_chatbot/{stay,visa}_manual.md
   │  Stage 8  scripts/build_chatbot_csv.py               (Python, deterministic)
   ▼
data/processed/{stay,visa}_manual_chatbot_ready.csv
   │  Stage 9  scripts/quality_report_semantic_manual_csvs.py
   ▼
output/quality/*, output/review/*
```

LLMs are only used in stages **3, 5, and 7**. The other six stages are deterministic Python — re-running them on the same inputs always produces the same outputs. The **normalized MDs** (outputs of stages 3 / 7) are intentionally committed to git, so that the same CSVs can be regenerated from the same inputs.

## Folder Structure

```text
.
├── data/
│   ├── raw/                  # source HWP files (never modified except for replacement)
│   │   └── legacy_pdf/       # archived PDFs from the previous pipeline
│   ├── parsed/
│   │   ├── raw/              # kordoc output (.gitignored, regenerable)
│   │   ├── chunks/           # chunk index .jsonl (committed)
│   │   ├── normalized/       # normalized MDs — LLM output (committed)
│   │   ├── normalized_chatbot/  # chatbot-normalized MDs (committed)
│   │   └── validation/       # validator output .json (committed)
│   └── processed/            # final CSVs (.gitignored, regenerable)
├── scripts/                  # deterministic stage scripts (Python)
│   └── legacy/               # archived regex builders (constants reused by quality_report)
├── .claude/skills/
│   ├── vizabridge-normalize/
│   ├── vizabridge-enrich-chatbot/
│   └── vizabridge-repair/
├── notebooks/                # analysis notebooks
├── docs/                     # design / operations docs
├── tests/                    # tests protecting cleaning rules
├── interview/                # Next.js intern-interview app (frontend only)
├── output/                   # review reports / Excel (.gitignored)
└── requirements.txt
```

Folder-level conventions are documented in [docs/project_structure.md](docs/project_structure.md); per-stage commands live in [scripts/README.md](scripts/README.md).

## Setup

```bash
# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Node.js 18+ is required (to run kordoc)
node --version    # must be v18+
```

No API keys are required. The LLM stages run as skills inside a Claude Code session, and kordoc is fetched automatically by `npx` on first use.

## Workflow

```bash
# 1) HWP → Markdown (kordoc, 1–2 minutes)
python scripts/parse_hwp_to_markdown.py

# 2) Chunk indexing (instant)
python scripts/index_markdown_chunks.py

# 3) Normalize inside a Claude Code session
#    /vizabridge-normalize stay
#    /vizabridge-normalize visa
#    (resume in the next session if you hit the limit)

# 4) Deterministic validation
python scripts/validate_normalization.py

# 5) Repair inside a Claude Code session if needed
#    /vizabridge-repair stay
#    /vizabridge-repair visa
python scripts/validate_normalization.py   # re-validate

# 6) Build the semantic CSV
python scripts/build_semantic_csv.py

# 7) Enrich for chatbot use inside a Claude Code session
#    /vizabridge-enrich-chatbot stay
#    /vizabridge-enrich-chatbot visa

# 8) Build the chatbot CSV
python scripts/build_chatbot_csv.py

# 9) Quality report + reviewable Excel
python scripts/quality_report_semantic_manual_csvs.py
```

## How the Skills Work

The LLM stages (3 / 5 / 7) run as the three skills under `.claude/skills/`. They are auto-discovered when you open this repo as a Claude Code workspace — no installation is required.

Invoke them inside a session with slash commands:

```
/vizabridge-normalize stay
/vizabridge-normalize visa
/vizabridge-repair stay
/vizabridge-repair visa
/vizabridge-enrich-chatbot stay
/vizabridge-enrich-chatbot visa
```

Each command processes one chunk (or one row) at a time and records progress as markers in the output MD. If the session hits its limit or you stop manually, simply re-running the same slash command in the next session continues where it left off. `/vizabridge-repair` is only used when `scripts/validate_normalization.py` has flagged issues.

To inspect progress outside a session without invoking the skill:

```bash
python .claude/skills/vizabridge-normalize/scripts/show_progress.py stay
python .claude/skills/vizabridge-enrich-chatbot/scripts/show_progress.py stay
python .claude/skills/vizabridge-repair/scripts/show_flagged.py stay
```

<details>
<summary><b>Skill internals (expand)</b></summary>

### Components

Each skill directory contains three kinds of files:

| File | Role |
| --- | --- |
| `SKILL.md` | Frontmatter (`name`, `description`) plus a procedure. Claude Code matches the user's message against the `description` to decide whether to invoke the skill. The body is a short instruction loaded into the model's context when invoked. |
| `references/*.md` | Domain knowledge (column schema, extraction rules, noise filters, output format, …). Not loaded wholesale every call — the model pulls them in via the Read tool only when needed. |
| `scripts/*.py` | Deterministic tasks: validation, persistence, progress queries. Anything risky to leave to the LLM is delegated to Python. |

### Progress lives inside the output MD

There is no separate state file. The markers in the normalized output **are** the state:

```
<!-- vizabridge-normalize v1 chunk: stay_004 hash: ... lines: 449-1185 -->
### row D-3 / Common / Target
- ...
<!-- end chunk: stay_004 -->
```

`show_progress.py` cross-references the chunk index with these markers to find the next chunk to process. Even if a session is interrupted, or a human manually patches a few rows, the next invocation simply continues from where it left off.

### Hash-based drift detection

The `hash:` field in each marker is the first 16 chars of the source chunk's SHA-256 (after whitespace normalization). If kordoc is re-run and the source changes, the hash mismatches and the validator flags it as `hash drift`. `/vizabridge-repair` then re-normalizes only that chunk.

### Separation of concerns between LLM and validation

The LLM only performs semantic extraction (which cell is `mandatory_documents`, what is the `petition_type`). Integrity checks — does this visa code / amount / document name actually exist in the source? — are done by deterministic Python (`scripts/validate_normalization.py`). Having the LLM validate its own output would just reproduce the same errors, so the two are kept apart.

### Slash-command flow

```
User input: /vizabridge-normalize stay
   │
   ▼
Claude Code: matches SKILL.md description → invokes
   │
   ▼
Model: loads SKILL.md body → executes the procedure
   │
   ├─ calls scripts/show_progress.py (identify next chunk)
   ├─ uses Read to load the relevant line range of the raw MD
   ├─ reads references/*.md only as needed
   ├─ writes a row block → /tmp/*.md
   ├─ calls scripts/append_block.py (validate + atomic append)
   └─ loops, or stops when context runs low
   ▼
Output: data/parsed/normalized/{manual}_manual.md (append-only)
```

</details>

<details>
<summary><b>Architecture (expand)</b></summary>

### Directory tree

```
.claude/skills/
├── vizabridge-normalize/
│   ├── SKILL.md                    # procedure
│   ├── references/
│   │   ├── column_schema.md        # STAY_COLUMNS / VISA_COLUMNS
│   │   ├── extraction_rules.md     # Korean admin term → CSV column mapping
│   │   ├── noise_rules.md          # cover / TOC / form-noise filters
│   │   └── output_format.md        # normalized-MD format spec
│   └── scripts/
│       ├── show_progress.py        # next unprocessed chunk + drift report
│       └── append_block.py         # schema + hash check + atomic append
├── vizabridge-enrich-chatbot/
│   ├── SKILL.md
│   ├── references/
│   │   ├── chatbot_schema.md
│   │   ├── situation_taxonomy.md   # the 21 user-situation tags
│   │   ├── keyword_rules.md
│   │   └── output_format.md
│   └── scripts/
│       ├── show_progress.py
│       └── append_block.py
└── vizabridge-repair/
    ├── SKILL.md
    └── scripts/
        ├── show_flagged.py         # list of chunks with validator issues
        └── replace_block.py        # atomic in-place replacement of a block
```

### Data flow (from the skills' viewpoint)

```
data/parsed/chunks/{m}_chunks_index.jsonl  (input produced by Python)
        │
        ▼
   /vizabridge-normalize  ──┐
        │                   │ (model reads references and processes chunk)
        ▼                   │
data/parsed/normalized/{m}_manual.md  (skill output)
        │
        │   scripts/validate_normalization.py  (deterministic validation)
        ▼
data/parsed/validation/{m}_validation.json
        │
        │   if issues → /vizabridge-repair  ──→ normalized MD updated
        ▼
   scripts/build_semantic_csv.py  (deterministic build)
        │
        ▼
data/processed/{m}_manual_semantic_clean.csv  (input to the next skill)
        │
        ▼
   /vizabridge-enrich-chatbot
        │
        ▼
data/parsed/normalized_chatbot/{m}_manual.md
        │
        ▼
   scripts/build_chatbot_csv.py
        │
        ▼
data/processed/{m}_manual_chatbot_ready.csv
```

### Helper-script responsibilities

| Script | Input | Output | Guarantees |
| --- | --- | --- | --- |
| `show_progress.py` | chunk index + normalized MD | stdout (next chunk_id, cumulative stats) | makes progress explicit |
| `append_block.py` | manual_key + chunk_id + block file | normalized MD (append) | validates marker format / hash / required fields; atomic write (temp + rename) |
| `replace_block.py` | manual_key + chunk_id + new block | normalized MD (in-place replace) | rejects hash drift (so repair is only meaningful at the same hash); atomic write |
| `show_flagged.py` | validator JSON | stdout (list of chunks to repair) | priority ordering |

### Why a skill + Python hybrid

| Task | Owner | Why |
| --- | --- | --- |
| Chunk splitting (on `<table>` boundaries) | Python | Deterministic, regex is enough |
| Semantic extraction (Korean admin text → CSV columns) | Skill (LLM) | Mapping hard to express in regex. Replaces the ~999-line classifier from the LlamaParse era |
| Per-row integrity checks (visa code / amount / document name) | Python | Deterministic ground-truth comparison; if the LLM validates its own output it just reproduces the same errors |
| CSV build (normalized MD → CSV) | Python | Deterministic, simple parsing; enforces the schema |
| Chatbot situation tags / natural-language keywords | Skill (LLM) | Natural-language generation, hard to fake with regex |
| Quality report | Python | Statistics, threshold comparisons |

### Caching (committing the normalized MD)

`data/parsed/normalized/` and `data/parsed/normalized_chatbot/` are gitignore exceptions and are committed. They effectively act as the output cache of the LLM stages, so a fresh clone can regenerate the same CSVs deterministically just by running `scripts/build_*.py`. The skills only need to be re-run when the input itself (HWP, kordoc output, chunk index) changes.

</details>

## Per-Stage Visualization

A notebook visualizes every artifact across the nine stages (chunks, normalized MDs, semantic/chatbot CSVs, quality reports) using pandas + plotly:

```bash
.venv/bin/jupyter notebook notebooks/04_pipeline_stages_visualization.ipynb
```

For each stage you can see:
- Chunk size distribution, visa-code type distribution
- Normalized-row counts, validator-issue frequencies
- Per-visa-code / per-petition-type distribution in the semantic CSV, plus a heatmap of column missingness
- Situation-tag / keyword / routing-hint frequencies in the chatbot CSV
- The list of review candidates from the quality report

The notebook is committed with its outputs, so the visualizations are visible directly on GitHub.

## What To Edit

- When a new manual is released: replace the HWP in `data/raw/` and re-run from Stage 1.
- To change the column schema: update [docs/data_columns.md](docs/data_columns.md), [.claude/skills/vizabridge-normalize/references/column_schema.md](.claude/skills/vizabridge-normalize/references/column_schema.md), and the `STAY_COLUMNS` / `VISA_COLUMNS` constants in `scripts/build_semantic_csv.py` together.
- To tweak the normalization rules: edit `.claude/skills/vizabridge-normalize/references/*.md`.
- To tweak the chatbot situation-tag / keyword rules: edit `.claude/skills/vizabridge-enrich-chatbot/references/*.md`.
- To change the review thresholds: edit `row_issues()` in `scripts/quality_report_semantic_manual_csvs.py`.

## Design Rationale

The reasoning behind the design lives in [docs/pipeline_strategy.md](docs/pipeline_strategy.md), with the full spec in [docs/superpowers/specs/2026-05-14-hwp-kordoc-llm-pipeline-design.md](docs/superpowers/specs/2026-05-14-hwp-kordoc-llm-pipeline-design.md).

Key points:
- **HWP / kordoc**: PDF / LlamaParse OCR mangled Korean and table structure. HWP is the original digital format and is lossless.
- **Normalized MD as the intermediate representation**: the LLM only does semantic classification; deterministic Python converts that into CSV. Hallucinations are caught in a separate layer (Stage 4 validator), and fixes flow through a consistent path (Stage 5 repair).
- **Claude Code skills**: same Claude model, no separate API billing. Reproducibility is ensured by committing the normalized MD.
