---
name: vizabridge-normalize
description: Use when normalizing Vizabridge kordoc Markdown into the canonical intermediate MD format consumed by the CSV builder. Invoke as `/vizabridge-normalize stay` or `/vizabridge-normalize visa`. The skill processes one chunk at a time from data/parsed/chunks/{manual}_chunks_index.jsonl, reads the corresponding line range from data/parsed/raw/{manual}_manual.md, and appends row blocks to data/parsed/normalized/{manual}_manual.md. Resumable across sessions.
---

# vizabridge-normalize

You are the LLM stage of the Vizabridge pipeline. You convert raw kordoc Markdown chunks into a strict canonical Markdown that later, deterministic Python parses into CSV rows.

## Inputs

- `data/parsed/chunks/{manual_key}_chunks_index.jsonl` — chunk metadata (chunk_id, line range, visa_codes, content_hash)
- `data/parsed/raw/{manual_key}_manual.md` — kordoc raw Markdown (do not load entirely; use offset/limit)
- `data/parsed/normalized/{manual_key}_manual.md` — your output, append-only

`{manual_key}` is `stay` or `visa`, chosen by the user when invoking.

## Output format (strict)

Append blocks like this to `data/parsed/normalized/{manual_key}_manual.md`:

```
<!-- vizabridge-normalize v1 chunk: <chunk_id> hash: <content_hash> lines: <start>-<end> -->

### row {visa_code} / {petition_type} / {subsection_type}
- visa_code: A-1
- visa_name_ko: 외교
- item_type: 사증
- petition_type: 사증발급
- subsection_type: 발급대상
- applicant_context: |
    외국정부의 외교사절단 구성원
- eligibility: |
    외교관 여권 소지
- mandatory_documents: |
    - 사증발급신청서
    - 여권
    - 표준규격사진
- duration_or_validity: 재임 기간
- expected_questions: |
    외교관 여권으로 한국 들어오려면 어떤 서류 내요?
    외교사절 비자는 얼마나 머물 수 있어요?
    외교관 가족도 같이 받을 수 있나요?

### row {visa_code} / {petition_type} / {subsection_type}
- visa_code: A-1
- ...

<!-- end chunk: <chunk_id> -->
```

Every chunk starts with `<!-- vizabridge-normalize v1 chunk: ... -->` and ends with `<!-- end chunk: ... -->`. Rows live between. The CSV builder treats anything outside these markers as ignored prose.

## Procedure

Follow these steps strictly. Do not improvise around them.

1. **Identify scope**. The user invokes `/vizabridge-normalize stay` or `/vizabridge-normalize visa`. If neither argument was given, ask which manual.

2. **Load progress**. Run `python .claude/skills/vizabridge-normalize/scripts/show_progress.py {manual_key}`. It prints the next pending chunk_id, total pending, and total completed. If everything is done, stop and report.

3. **Read the chunk's lines from the raw Markdown**. Use the Read tool with the chunk's `start_line` and `end_line - start_line + 1` as offset/limit on `data/parsed/raw/{manual_key}_manual.md`. Do not read the entire file.

4. **For oversized chunks** (the chunk record has `oversized: true`): split mentally by inspecting the content. Re-Read the chunk in two or three passes if needed (e.g. first half, then second half). Emit all rows within a single chunk block — do not split the output block by offset.

5. **Extract rows**. For each (visa_code, petition_type, subsection_type) triple that the chunk content meaningfully describes, emit one `### row ...` block following the rules in `references/extraction_rules.md` and the schema in `references/column_schema.md`. Use the noise filters in `references/noise_rules.md` to drop forms, cover, TOC, broken table fragments.

6. **Self-check before appending**: for the chunk you just produced, verify each row's `visa_code` value appears in the chunk source text. If a value is invented, drop it. Verify required fields are present (`visa_code`, `visa_name_ko`, `item_type`, `petition_type`, `subsection_type`).

7. **Append**. Run `python .claude/skills/vizabridge-normalize/scripts/append_normalized.py {manual_key} {chunk_id}` with your block on stdin. The script verifies the chunk_id and hash match the index, that the chunk is not already in the output, and writes atomically.

8. **Repeat** from step 2 until either (a) no chunks remain, or (b) you sense session-context fatigue, in which case stop and report progress. The next invocation will resume seamlessly.

## Hard rules

- **No invention.** If the source chunk does not state a fact (a document, an amount, a date), do not emit it. Empty string is better than a guess.
- **One block per chunk, always**. Even if a chunk yields zero rows (pure noise/cover/TOC), emit the markers with no rows in between — this records that the chunk was processed.
- **Preserve original numbers and names verbatim** (수수료 금액, 점수, 서류명). Korean wording matters for downstream search.
- **Do not edit existing blocks in the normalized file.** Append only. If a chunk's hash has changed, use the repair skill, not this one.
- **No CSV fields with PDF page numbers, raw text, review flags, or debug data.** Final CSV must stay clean.

## Stop conditions

Stop and tell the user when:

- All chunks for the requested manual are normalized.
- You have processed ≥ 6 chunks and feel the session is heavy — context pressure or fatigue.
- A chunk consistently fails self-check (hash mismatch, missing required fields after retry).

In all stop cases, run `show_progress.py` once more and print the summary.

## References

- `references/column_schema.md` — full STAY_COLUMNS / VISA_COLUMNS with one-line semantics
- `references/extraction_rules.md` — Korean admin-term → column mapping, petition-type rules, sub-section heuristics
- `references/noise_rules.md` — what to drop (cover, TOC, forms, broken table fragments)
- `references/output_format.md` — examples of the canonical Markdown block, including edge cases

Read references on demand. Do not load all four every time — pick the one you need for the current question.
