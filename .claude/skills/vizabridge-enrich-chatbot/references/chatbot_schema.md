# Chatbot Schema

Required fields per chatbot block. Order is consistent for human readability; the CSV builder is order-independent.

| Field | Semantics |
| --- | --- |
| `record_id` | Unique per row. Format: `{manual_key}-{row_index:05d}-{primary_code}`, e.g. `visa-00042-D-8` |
| `source_dataset` | Always `{manual_key}_manual_semantic_clean.csv` |
| `code_type` | `stay_status` for stay manual rows, `visa` for visa manual rows |
| `primary_code` | The visa/stay code from the semantic row's `visa_code` or `stay_status_code` |
| `primary_name_ko` | Korean name from the semantic row's `visa_name_ko` or `stay_status_name_ko` |
| `source_section_title` | Copied verbatim from the semantic row's `section_title` |
| `user_situation_tags` | One or more canonical situation tags from `situation_taxonomy.md`. Bullet list under `\|` |
| `intent_keywords` | Natural-language user phrases that should match this row. 3-7 short phrases as a bullet list |
| `applicant_profile` | Who is asking (외국인 본인, 유학생/연수생, 초청인/고용주, 배우자/가족, 사업주, 대학/연구기관 담당자, etc.) |
| `current_location_context` | One of: `입국 전 사증 신청`, `국내 체류 중 민원`, `둘 다 가능`. Or a short phrase explaining the staging |
| `current_status_context` | Hints about the user's likely current visa/stay status before this petition. E.g. `현재 D-2 유학` |
| `plain_language_summary` | One sentence in plain Korean explaining what this row is about |
| `required_user_info` | Bullet list of things the chatbot should ask the user before answering with this row's content. E.g. 투자 금액, 결혼 일자 |
| `routing_hint` | `<manual_type> / <petition_type>[, <petition_type>...]`. The manual_type is `체류민원` or `사증민원`. petition_type comes from the semantic row |
| `answer_focus` | What the answer should emphasize: `자격요건`, `제출서류`, `절차`, `제한사항`, `점수표`, `쿼터`, etc. — choose 1-3 from the semantic row's non-empty fields |
| `search_text` | Flat keyword string: code, name, key Korean nouns from the semantic row, common user phrases. 15-40 tokens, no commas |

## Forbidden

- Do not include PDF page numbers, raw original text, evidence quotes, review flags, or debug fields.
- Do not duplicate the full semantic row content into the chatbot row — chatbot rows are the access layer, not a copy.
