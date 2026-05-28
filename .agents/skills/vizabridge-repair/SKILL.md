---
name: vizabridge-repair
description: Use when scripts/validate_normalization.py has reported issues on normalized chunks and you need to fix them. Invoke as `/vizabridge-repair stay` or `/vizabridge-repair visa`. Reads data/parsed/validation/{manual}_validation.json, processes flagged chunks one at a time, re-reads source lines, emits a corrected block that REPLACES the old one in data/parsed/normalized/{manual}_manual.md.
---

# vizabridge-repair

You fix the mistakes that the normalize skill made. The deterministic validator (`scripts/validate_normalization.py`) flags specific issues per chunk — visa codes invented from thin air, document names not appearing in source, monetary amounts off, required fields empty, etc. Your job is to replace the offending chunk's block with a corrected one.

This skill is the only sanctioned way to modify an already-written chunk block. Do not edit the normalized file directly with the Edit tool.

## Inputs

- `data/parsed/validation/{manual_key}_validation.json` — issues per chunk
- `data/parsed/chunks/{manual_key}_chunks_index.jsonl` — chunk meta
- `data/parsed/raw/{manual_key}_manual.md` — original kordoc Markdown
- `data/parsed/normalized/{manual_key}_manual.md` — current normalized output (with the bad block)

## Procedure

1. **Run the validator first** if you haven't recently:
   `python scripts/validate_normalization.py {manual_key}`
   This refreshes the validation JSON.

2. **Pick the next flagged chunk**. Run
   `python .claude/skills/vizabridge-repair/scripts/show_flagged.py {manual_key}`.
   It lists chunks with issues, with a brief description of each issue
   type, ordered by severity. Pick the top one (or the chunk_id the user
   asked you to repair).

3. **Inspect both sides**:
   - Re-read the source line range from `data/parsed/raw/{manual_key}_manual.md`
   - Read the existing block from `data/parsed/normalized/{manual_key}_manual.md`
     (find it by searching for `<!-- vizabridge-normalize v1 chunk: <chunk_id>`)

4. **Diagnose**. For each issue the validator reported, find the
   source-of-truth in the raw chunk:
   - `visa code not in source` → check if the LLM that produced the
     block confused codes. Drop fabricated codes; keep only those present
     in source.
   - `amount not in source` → preserve the source's unit notation
     verbatim ("12만원", not "120,000원").
   - `documents: none of the cited documents found in source` → re-list
     the actual document names from the source text.
   - `missing required fields` → re-emit those fields with real source-derived
     content.

5. **Emit a corrected block** following the same canonical format as the
   normalize skill (see `.claude/skills/vizabridge-normalize/references/output_format.md`).
   Same open/close markers (`<!-- vizabridge-normalize v1 chunk: ... -->`
   and `<!-- end chunk: ... -->`), same chunk_id, same source_hash.

6. **Replace, don't append**. Write the new block to
   `/tmp/vizabridge_repair_block.md` and run
   `python .claude/skills/vizabridge-repair/scripts/replace_block.py {manual_key} {chunk_id} /tmp/vizabridge_repair_block.md`.
   The script:
   - Locates the old block by chunk_id
   - Validates the new block (schema + hash)
   - Atomically replaces the old text region with the new block

7. **Re-validate**:
   `python scripts/validate_normalization.py {manual_key}`
   Confirm the chunk's issue count dropped. If it didn't, re-inspect and try again.

8. **Repeat** for remaining flagged chunks, or stop if session is heavy.

## Hard rules

- **Same chunk_id, same source_hash**. The repair must claim ownership of
  the same chunk as before. If the chunk's source_hash drifted (source
  changed), this is not a repair — it's a re-normalize. Run the normalize
  skill on that chunk instead.
- **Preserve correct rows**. If only one row in a chunk had issues, do
  not regenerate every row from scratch — copy the good rows and only
  rewrite the bad ones. The replace script overwrites the entire chunk
  block, so you must include all rows in the replacement (correct +
  corrected).
- **No silent fabrication**. If the source genuinely lacks a fact the
  old block claimed, the corrected block must drop that fact (empty
  field) rather than invent a plausible substitute.
- **Verbatim unit notation**. 수수료 / 금액 / 점수 in the corrected
  block must use the same unit style the source uses ("12만원",
  "2,500만원", "200점").

## Stop conditions

- All flagged chunks repaired and the validator reports zero issues.
- A chunk fails repair twice in a row — escalate (tell the user; do not
  loop infinitely).
- Session-context fatigue after ~4 chunks. Repair is cognitively heavier
  than normalize because you're juggling diff-style reasoning.
