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

### row A-1 / 사증발급 / 대상
- manual_type: 사증민원
- visa_code: A-1
- visa_name_ko: 외교
- item_type: visa_rule
- section_title: A-1 외교
- subtype_or_program:
- petition_type: 사증발급
- subsection_type: 대상
- applicant_context:
- eligibility: |
    대한민국정부가 접수한 외국정부의 외교사절단이나 영사기관의 구성원
    조약 또는 국제관행에 의하여 외교사절과 동등한 특권과 면제를 받는 자
    그 가족
- target_persons: 외교사절 및 가족
- common_documents:
- mandatory_documents:
- other_documents:
- requirements:
- procedure:
- restrictions:
- exceptions:
- fees:
- duration_or_validity: 재임기간
- quota_or_limit:
- score_criteria:
- table_summary:
- table_rows:
- inviter_context:
- recommendation_or_approval:
- keywords: 외교, 외교사절, 영사기관, 외교관 여권, A-1
- source_page: p. 17
- source_excerpt: |
    대한민국정부가 접수한 외국정부의 외교사절단이나 영사기관의 구성원
    조약 또는 국제관행에 의하여 외교사절과 동등한 특권과 면제를 받는 자
    그 가족
- related_visa_codes: A-2, A-3
- expected_questions: |
    한국 외교사절단으로 와있는데 비자 어떻게 받아요?
    외교관 가족도 같이 받을 수 있나요?
    얼마나 머물 수 있어요?

<!-- end chunk: visa_003 -->
```

### Multi-row chunk (F-6-1 결혼이민, multiple petition × subsection combos)

The same visa code emits one row per `(petition_type, subsection_type)` combination present in the source. Use the same `visa_code` value across them; vary `petition_type` and `subsection_type`.

```
<!-- vizabridge-normalize v1 chunk: visa_142 hash: 9c14ab lines: 1820-1875 -->

### row F-6 / 사증발급 / 요건
- manual_type: 사증민원
- visa_code: F-6
- visa_name_ko: 결혼이민
- item_type: visa_rule
- section_title: F-6 결혼이민 / F-6-1 국민의 배우자
- subtype_or_program: F-6-1
- petition_type: 사증발급
- subsection_type: 요건
- requirements: |
    한국인과 혼인하여 국내에서 결혼생활을 영위하는 자
    신청인의 연간소득이 한국은행 고시 전년도 1인당 국민총소득(GNI) 이상
    초청인의 신원보증서 제출
- ...
- keywords: 결혼이민, 한국인 배우자, 소득요건, 신원보증, F-6, F-6-1
- source_page: p. 142~144
- source_excerpt: |
    한국인과 혼인하여 국내에서 결혼생활을 영위하는 자
    신청인의 연간소득이 한국은행 고시 전년도 1인당 국민총소득(GNI) 이상
- related_visa_codes: F-5, F-2-R, F-1
- expected_questions: |
    한국인이랑 결혼했는데 비자 어떻게 받아요?
    소득이 얼마나 있어야 받을 수 있어요?
    배우자 신원보증서가 꼭 필요한가요?
    국적 다른 부부도 한국에서 같이 살 수 있어요?

### row F-6 / 사증발급 / 제출서류
- manual_type: 사증민원
- visa_code: F-6
- visa_name_ko: 결혼이민
- item_type: required_documents
- section_title: F-6 결혼이민 / F-6-1 국민의 배우자
- subtype_or_program: F-6-1
- petition_type: 사증발급
- subsection_type: 제출서류
- mandatory_documents: |
    - 통합신청서(별지 제17호 서식)
    - 여권 및 사진 1매
    - 혼인관계증명서
    - 신원보증서
- ...
- keywords: 결혼이민, 통합신청서, 혼인관계증명서, 신원보증서, F-6
- source_page: p. 145
- source_excerpt: |
    - 통합신청서(별지 제17호 서식)
    - 여권 및 사진 1매
    - 혼인관계증명서
- related_visa_codes:
- expected_questions: |
    결혼이민 비자 받으려면 무슨 서류 내요?
    혼인관계증명서는 어디서 떼나요?

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
- keywords: 숙련기능인력, 점수제, 한국어능력, 자격변경, E-7-4
- source_page: p. 612~616
- source_excerpt: |
    최근 10년간 E-9, E-10, H-2 자격으로 4년 이상 체류
    점수제 총점 300점 중 200점 이상 (한국어 50점 이상)
- related_visa_codes: E-9, E-10, H-2
- expected_questions: |
    비전문취업으로 오래 일했는데 숙련기능인력으로 바꿀 수 있어요?
    점수표에서 몇 점이면 자격변경이 되나요?
    한국어 시험 점수 기준이 얼마예요?

<!-- end chunk: visa_142 -->
```

### Sub-program note

When the source describes a sub-program (E-7-4, F-2-R, D-2-1 등), set `stay_status_code` / `visa_code` to the **parent** (E-7, F-2, D-2) and put the full sub-code in `subtype_or_program` (E-7-4, F-2-R, D-2-1). See the second F-6-1 / third E-7-4 examples above.

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

The 4 newer enrichment fields — `keywords`, `source_page`, `source_excerpt`, `related_visa_codes` — are **not mandatory** (빈 값 허용) but should be filled whenever the source supports it. They drive search quality and human review confidence.

`expected_questions` is **2~4개 가변** (drop down to 1개 only if the source is exceptionally thin). 억지로 3개 고정하지 말 것.

## Blank values

Both styles below mean empty:

```
- restrictions:
```

```
- restrictions: ""
```

Prefer the bare form (no quotes) for cleanliness. Reserve quotes for values that contain colons or start with special characters.
