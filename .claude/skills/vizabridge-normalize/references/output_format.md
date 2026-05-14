# Output Format

The CSV builder uses a single deterministic parser. It only recognizes:

1. Chunk open marker: `<!-- vizabridge-normalize v1 chunk: <chunk_id> hash: <hash> lines: <s>-<e> -->`
2. Chunk close marker: `<!-- end chunk: <chunk_id> -->`
3. Row blocks: `### row <code> / <petition_type> / <subsection_type>` followed by `- <field>: <value>` lines.

Everything else between markers (your commentary, blank lines) is ignored. So do not put commentary; just be silent.

## Field-value encoding

Each field is a single line `- field: value` or a multi-line block:

```
- mandatory_documents: |
    - 사증발급신청서
    - 여권
    - 표준규격사진
```

The `|` pipe indicates a multi-line literal block. Continuation lines must be indented exactly 4 spaces. Do not use other YAML modifiers.

## Edge cases by example

### Empty chunk (pure cover / TOC / decorations)

```
<!-- vizabridge-normalize v1 chunk: visa_001 hash: 8a2c91 lines: 1-87 -->
<!-- end chunk: visa_001 -->
```

No rows. This still counts as "processed" so the chunk is not re-attempted.

### Single-row chunk (simple visa code with one petition type)

```
<!-- vizabridge-normalize v1 chunk: visa_003 hash: 7f12bc lines: 113-122 -->

### row A-3 / 사증발급 / 대상
- manual_type: 사증민원
- visa_code: A-3
- visa_name_ko: 협정
- item_type: visa_rule
- section_title: A-3 협정
- subtype_or_program:
- petition_type: 사증발급
- subsection_type: 대상
- applicant_context:
- eligibility: |
    협정에 의해 외국인등록이 면제되거나 면제할 필요가 있다고 인정되는 자
    상기자의 가족
- target_persons: 협정에 의한 활동자
- common_documents:
- mandatory_documents:
- other_documents:
- requirements:
- procedure:
- restrictions:
- exceptions:
- fees:
- duration_or_validity: 신분존속기간 또는 협정상의 체류기간
- quota_or_limit:
- score_criteria:
- table_summary:
- table_rows:
- inviter_context:
- recommendation_or_approval:

<!-- end chunk: visa_003 -->
```

### Multi-row chunk (one visa code, multiple petition × subsection combos)

The same visa code emits one row per `(petition_type, subsection_type)` combination present in the source. Use the same `visa_code` value across them; vary `petition_type` and `subsection_type`.

```
<!-- vizabridge-normalize v1 chunk: visa_018 hash: 22ee44 lines: 466-475 -->

### row D-8 / 사증발급 / 요건
- manual_type: 사증민원
- visa_code: D-8
- visa_name_ko: 기업투자
- item_type: visa_rule
- section_title: D-8 기업투자
- subtype_or_program:
- petition_type: 사증발급
- subsection_type: 요건
- requirements: |
    외국인투자촉진법상 외국인투자기업으로 등록
    1인당 투자금 1억원 이상
- ...

### row D-8 / 사증발급 / 제출서류
- manual_type: 사증민원
- visa_code: D-8
- visa_name_ko: 기업투자
- item_type: required_documents
- section_title: D-8 기업투자
- subtype_or_program:
- petition_type: 사증발급
- subsection_type: 제출서류
- mandatory_documents: |
    - 외국인투자기업등록증
    - 투자금 입금증명
- ...

### row D-8 / 사증발급인정서 / 대상
- ...

<!-- end chunk: visa_018 -->
```

### Sub-program row (E-7-4 inside E-7 chunk)

```
### row E-7 / 체류자격 변경 / 요건
- manual_type: 체류민원
- stay_status_code: E-7
- stay_status_name_ko: 특정활동
- item_type: stay_status_rule
- section_title: E-7-4 숙련기능인력 / 자격변경
- subtype_or_program: E-7-4
- petition_type: 체류자격 변경
- subsection_type: 요건
- requirements: |
    최근 10년간 E-9, E-10, H-2 자격으로 4년 이상 체류
    현재 근무처에서 정상 근로 중
    점수제 총점 300점 중 200점 이상 (한국어 50점 이상)
    연봉 2,600만원 이상
- ...
```

`stay_status_code = E-7` (parent), `subtype_or_program = E-7-4` (sub-program). Same row pattern is used for D-2-1, F-2-R, F-2-T, etc.

## Order of fields in a row

Use the order in `column_schema.md`. The CSV builder does not require any particular order, but consistent ordering keeps the normalized file human-readable.

## Mandatory fields per row

Every row MUST have at least:

- `manual_type`
- One of `visa_code` / `stay_status_code`
- One of `visa_name_ko` / `stay_status_name_ko`
- `item_type`
- `section_title`
- `petition_type`
- `subsection_type`

Other fields can be empty (`- field:` with nothing after the colon). Do not omit field lines — keep them all for schema stability.

## Blank values

Both styles below mean empty:

```
- restrictions:
```

```
- restrictions: ""
```

Prefer the bare form (no quotes) for cleanliness. Reserve quotes for values that contain colons or start with special characters.
