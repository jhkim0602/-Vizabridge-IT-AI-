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

6. **Self-check before appending**: for the chunk you just produced, verify each row passes these checks:
   - `visa_code` / `stay_status_code` value appears in the chunk source text. If invented, drop it.
   - Required fields are present (`visa_code`/`stay_status_code`, `visa_name_ko`/`stay_status_name_ko`, `item_type`, `petition_type`, `subsection_type`).
   - `petition_type` is one of the 13 canonical enum values (see `references/extraction_rules.md`).
   - `source_excerpt`, if filled, is **verbatim** from the chunk source (no paraphrase). Re-grep the chunk text to confirm.
   - `related_visa_codes`, if filled, are codes that **actually appear** in the chunk source. No guessing.
   - `keywords` includes the row's primary visa code at minimum (when filled).

7. **Append**. Run `python .claude/skills/vizabridge-normalize/scripts/append_normalized.py {manual_key} {chunk_id}` with your block on stdin. The script verifies the chunk_id and hash match the index, that the chunk is not already in the output, and writes atomically.

8. **Repeat** from step 2 until either (a) no chunks remain, or (b) you sense session-context fatigue, in which case stop and report progress. The next invocation will resume seamlessly.

## Hard rules

- **No invention.** If the source chunk does not state a fact (a document, an amount, a date), do not emit it. Empty string is better than a guess.
- **One block per chunk, always**. Even if a chunk yields zero rows (pure noise/cover/TOC), emit the markers with no rows in between — this records that the chunk was processed.
- **No row cap per chunk.** Emit as many `(petition_type, subsection_type)` rows as the source meaningfully supports — 1 or 30. The previous 8-row guideline is removed; only the source's actual content limits row count.
- **Preserve original numbers and names verbatim** (수수료 금액, 점수, 서류명). Korean wording matters for downstream search.
- **`source_excerpt` must be verbatim.** If you fill it, copy the source text exactly — no rewording, no paraphrase. It is the human reviewer's hallucination check.
- **`petition_type` is a 13-value enum.** Use only canonical values from `references/extraction_rules.md` (사증발급 / 사증발급인정서 / 전자사증 / 체류자격 변경 / 체류자격 부여 / 체류기간 연장 / 외국인등록 / 거소신고 / 재입국허가 / 근무처 변경/추가 / 체류자격외 활동허가 / 고용변동 신고 / 공통사항).
- **The 4 enrichment fields (`keywords`, `source_page`, `source_excerpt`, `related_visa_codes`) are not mandatory but should be filled when the source supports them.** They drive search and review quality.
- **Do not edit existing blocks in the normalized file.** Append only. If a chunk's hash has changed, use the repair skill, not this one.
- **No CSV fields with raw debug data or reviewer reasoning.** `source_page` and `source_excerpt` ARE allowed in v2 — they support human review. But do not invent review flags or commentary.
- **통합행 분리 (보고서 4.3).** 같은 자격 안에서 매뉴얼이 별도 번호·섹션·국가·분야·협정·지역·sub-code 로 구분한 발급 기준은 **각각 별도 행**으로 분리한다. 예시:
  - C-3 복수사증 → 중국 / 한·몽골 / 동남아 / 자원외교 (국가별 4행)
  - C-4-5 단기취업 → 첨단기술 / 수입기계 / 영어캠프 / 일시흥행 / 단기 강의 / 기타 (분야별 6행)
  - D-7 주재 → 외국지사 / 해외진출 / 한·러 / 한·우즈벡 / 한·인도 (협정별 5행)
  - D-2 광역형 → 인천 / 광주 / 강원 / 충북 / 충남 / 전북 (지역별 6행)
  - D-10-1 변경 → 점수제 적용 + 면제 7개 카테고리 (sub-code별 8행)
  매뉴얼이 가독성을 위해 한 챕터에 묶어 서술하더라도, 첨부서류·체류기간·대상자가 카테고리마다 다르면 `subtype_or_program` 을 달리하여 별도 행으로 emit 한다. v4 산출물 (사증 158 / 체류 275) 의 행 수는 이 정책을 적용한 결과다.
- **사증·체류 단계 혼재 (보고서 4.4).** 사증 매뉴얼이라도 일부 자격은 사증발급이 불가하고 체류자격 변경만 허용된다 (예: E-7-4 K-point). 반대로 체류 매뉴얼에 사증발급인정서 기준이 포함된 챕터도 있다. `manual_type` 은 매뉴얼 출처를 나타내고, `petition_type` 은 실제 행정 단계를 나타내므로 두 값이 어긋날 수 있다 — 어긋나면 매뉴얼 본문이 실제로 다루는 행정 단계를 `petition_type` 에 적는다.

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
