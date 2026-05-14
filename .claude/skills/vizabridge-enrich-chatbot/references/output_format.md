# Chatbot Output Format

The chatbot CSV builder parses canonical Markdown deterministically. It only recognizes:

1. Open marker: `<!-- vizabridge-chatbot v1 source_row: <record_id> source_hash: <hash> -->`
2. Close marker: `<!-- end chatbot: <record_id> -->`
3. The single `### chatbot <record_id>` heading inside.
4. Field lines (`- field: value` or `- field: |` blocks).

Anything else between markers is ignored. Be silent — no commentary.

## record_id

`{manual_key}-{row_index:05d}-{primary_code}`

Examples:
- `visa-00042-D-8`
- `stay-00128-E-7`

`row_index` is the zero-based index in the semantic CSV (the same row order as the CSV writer used). The progress helper reports the next row_index; use it.

## source_hash

Hash the semantic row's content so re-runs after the semantic CSV changes get caught. Compute as SHA-256 of the row's serialized fields (column=value pairs concatenated with `|`), then take the first 16 hex chars. The progress helper computes and reports this for the next row.

## Standard block

```
<!-- vizabridge-chatbot v1 source_row: visa-00042-D-8 source_hash: 9c2a1b8e7f4d3520 -->

### chatbot visa-00042-D-8
- record_id: visa-00042-D-8
- source_dataset: visa_manual_semantic_clean.csv
- code_type: visa
- primary_code: D-8
- primary_name_ko: 기업투자
- source_section_title: D-8 기업투자 / 사증발급 / 요건
- user_situation_tags: |
    - 창업/투자
- intent_keywords: |
    - 한국에서 법인을 설립하고 싶다
    - 외국인 투자비자 받으려면
    - 1억원 이상 투자
    - 기업투자 비자 자격요건
- applicant_profile: 외국인 본인 (투자자)
- current_location_context: 입국 전 사증 신청
- current_status_context: 단기방문(C-3) 또는 무사증 입국 후
- plain_language_summary: 한국에 1억원 이상 투자하여 법인을 운영하려는 외국인 투자자를 위한 사증
- required_user_info: |
    - 투자 금액
    - 투자 형태 (신규 설립 / 기존 기업)
    - 외국인투자기업 등록 여부
- routing_hint: 사증민원 / 사증발급, 사증발급인정서
- answer_focus: 자격요건, 제출서류
- search_text: D-8 기업투자 외국인 투자 법인 설립 1억원 외국인투자기업 등록 사증발급 사증발급인정서

<!-- end chatbot: visa-00042-D-8 -->
```

## Empty fields

Leave the line present with no value. The CSV builder accepts that.

```
- current_status_context:
```

## Multi-tag situations

```
- user_situation_tags: |
    - 숙련기능
    - 취업/고용
    - 자격변경
```

## Multi-petition routing

```
- routing_hint: 체류민원 / 체류자격 변경, 체류기간 연장
```

## answer_focus picking

Pick 1-3 of: `자격요건`, `요건`, `제출서류`, `절차`, `제한사항`, `예외/면제`, `수수료`, `점수표`, `쿼터`, `기간`, `대상`. Match to whatever the source semantic row emphasizes. A `subsection_type = 점수표` row should have `answer_focus: 점수표` at minimum.

## one chatbot block per semantic row

Always exactly one. Even if a row looks "weak" (mostly empty semantic fields), emit the block — it keeps the chatbot CSV row-aligned with the semantic CSV. Skip only if `show_progress.py` reports the row is already done.

## search_text composition tips

Aim for ~20 short tokens, separated by spaces, no commas or pipes. Include:

- `primary_code` and `primary_name_ko`
- Korean nouns the semantic row uses (서류명, 점수 단위 등)
- 1-2 phrases mirroring `intent_keywords` for embedding overlap

The `search_text` is what RAG embedding sees most directly when matching user queries to this row. Make it rich but disciplined.
