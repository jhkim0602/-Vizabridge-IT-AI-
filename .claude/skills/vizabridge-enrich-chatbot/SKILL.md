---
name: vizabridge-enrich-chatbot
description: Use when enriching Vizabridge semantic CSV rows with chatbot-facing fields (situation tags, natural-language keywords, follow-up questions, routing hints, plain-language summary). Invoke as `/vizabridge-enrich-chatbot stay` or `/vizabridge-enrich-chatbot visa`. Reads data/processed/{manual}_manual_semantic_clean.csv, writes canonical row blocks to data/parsed/normalized_chatbot/{manual}_manual.md. Resumable across sessions.
---

# vizabridge-enrich-chatbot

You add the natural-language layer on top of the semantic CSV. The semantic CSV preserves administrative truth; the chatbot CSV preserves user-language access. Users will say "한국인 배우자와 결혼했어요" rather than "F-6". Your job is to bridge that gap.

## Inputs

- `data/processed/{manual_key}_manual_semantic_clean.csv` — semantic CSV produced by the normalize → CSV pipeline; one row per (visa_code, petition_type, subsection_type) triple
- `data/parsed/normalized_chatbot/{manual_key}_manual.md` — your output, append-only

`{manual_key}` is `stay` or `visa`.

## Output format (strict)

Append blocks like this to `data/parsed/normalized_chatbot/{manual_key}_manual.md`:

```
<!-- vizabridge-chatbot v1 source_row: <record_id> source_hash: <semantic_row_hash> -->

### chatbot {record_id}
- record_id: <record_id>
- source_dataset: {manual_key}_manual_semantic_clean.csv
- code_type: stay_status | visa
- primary_code: D-8
- primary_name_ko: 기업투자
- source_section_title: ...
- user_situation_tags: |
    - 창업/투자
    - 외국인 사업
- intent_keywords: |
    - 한국에서 법인을 설립하고 싶다
    - 외국인 투자비자
    - 한국 사업 시작
- applicant_profile: 외국인 본인 (투자자)
- current_location_context: 입국 전 사증 신청 또는 국내 체류 중 자격 변경
- current_status_context: 현재 단기방문(C-3) 또는 무사증 입국 후
- plain_language_summary: 한국에 1억원 이상 투자해 법인을 운영하려는 외국인 투자자를 위한 비자
- required_user_info: |
    - 투자 금액
    - 투자 형태 (신규/기존)
    - 외국인투자기업 등록 여부
- routing_hint: visa / 사증발급, 사증발급인정서
- answer_focus: 자격요건, 제출서류, 절차
- search_text: D-8 기업투자 외국인 투자 법인 설립 1억원 외국인투자기업 사증발급

<!-- end chatbot: <record_id> -->
```

`record_id` is unique per semantic row. Construct it as
`{manual_key}-{row_index:05d}-{primary_code}` where `row_index` is the
zero-based row index in the semantic CSV.

## Procedure

1. **Identify scope**. Take `stay` or `visa` from the invocation argument. If missing, ask.

2. **Load progress**. Run
   `python .claude/skills/vizabridge-enrich-chatbot/scripts/show_progress.py {manual_key}`.
   It prints the next pending row's index, primary_code, and a brief
   summary of the semantic data. If everything is done, stop.

3. **Build the enrichment**. Use the semantic row's content to fill in
   the user-facing fields. Follow the rules in `references/situation_taxonomy.md`
   for situation tags, `references/keyword_rules.md` for natural-language
   keywords, and `references/output_format.md` for the canonical block.

4. **Self-check**: primary_code must equal the semantic row's
   `visa_code`/`stay_status_code`. routing_hint must reference the
   semantic row's `petition_type`. Do not invent codes or facts that
   the semantic row does not contain.

5. **Append**. Write the candidate block to `/tmp/vizabridge_chatbot_block.md`
   and run
   `python .claude/skills/vizabridge-enrich-chatbot/scripts/append_block.py {manual_key} {record_id} /tmp/vizabridge_chatbot_block.md`.
   The script validates the block against the schema and refuses
   duplicates.

6. **Repeat** until done or session-context fatigue (~10 rows per
   session is comfortable; this work is denser than normalize per row
   because each row is small but creative). Stop and run show_progress.py
   once more to report.

## Hard rules

- **No invention of administrative facts.** You can phrase user
  situations creatively (intent_keywords, plain_language_summary), but
  you cannot add eligibility, document, or fee information that the
  semantic row doesn't carry. Keep your chatbot fields downstream of
  the semantic fields.
- **Use Korean for user-facing fields.** intent_keywords,
  plain_language_summary, situation_tags, required_user_info all speak
  to a Korean-reading user.
- **search_text is a flat keyword soup.** It is what RAG embedding
  treats as the corpus for this row — include primary_code,
  primary_name_ko, key Korean words from the semantic row, key
  user-language phrases. Aim for 15-40 short tokens, no punctuation
  ornamentation.
- **routing_hint format**: `<manual_type> / <petition_type>[, <petition_type>...]`.
  Routes the user's question toward the right CSV partition.

## References

- `references/chatbot_schema.md` — every output field and its semantics
- `references/situation_taxonomy.md` — canonical user-situation tags
  (결혼/배우자, 유학/연수, 취업/고용, 창업/투자, 가족초청, 영주신청, etc.)
- `references/keyword_rules.md` — how to derive intent_keywords from
  semantic content
- `references/output_format.md` — canonical Markdown block with edge
  cases (multi-tag rows, ambiguous primary_code, etc.)

Read references on demand; do not load all four every time.
