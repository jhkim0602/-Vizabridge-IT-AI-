# Column Schema

The normalized rows you emit must populate the fields below. Field names are exact — they become CSV columns. Empty string is a valid value; missing field is not.

## Required for every row (both manuals)

| Field | Semantics |
| --- | --- |
| `item_type` | One of: `common_rule`, `stay_status_rule`, `visa_rule`, `required_documents`, `fee`, `score_table`, `quota`, `restriction`, `exception` |
| `section_title` | Clean section title (e.g. `D-8 기업투자`) |
| `subtype_or_program` | Sub-program like `E-7-4`, `지역특화형`, `복수사증`, `사증발급인정서` — empty if not applicable |
| `petition_type` | Petition type, see `extraction_rules.md` for the canonical list |
| `subsection_type` | One of: `대상`, `요건`, `제출서류`, `절차`, `제한`, `예외`, `수수료`, `점수표`, `쿼터`, `기간` |
| `applicant_context` | Who is applying / situational context |
| `eligibility` | Eligibility conditions |
| `target_persons` | 해당자 / 발급 대상 |
| `common_documents` | Common documents required across many applicants |
| `mandatory_documents` | Mandatory documents specific to this row |
| `other_documents` | Conditional / per-case documents |
| `requirements` | Qualifying requirements (요건, 심사기준) |
| `procedure` | Application procedure |
| `restrictions` | Restrictions / exclusions / disqualifications |
| `exceptions` | Exceptions / 면제 / 특례 |
| `fees` | Fees (수수료) — preserve numbers verbatim |
| `duration_or_validity` | Stay/visa duration, validity, single vs multiple entry |
| `quota_or_limit` | Quotas / 선발인원 / 허용인원 |
| `score_criteria` | Score table / 배점 reference |
| `table_summary` | One-line summary of any table this row represents |
| `table_rows` | Rendered key rows of that table (kept short) |
| `expected_questions` | 한국어로 3개. 이 행에 대해 일반 사용자가 비자코드를 모른 채 자기 상황으로 물을 법한 질문을 줄바꿈으로 구분해 적는다. 예: "한국인이랑 결혼했는데 비자 어떻게 받아요?\n결혼이민 갱신 서류 뭐 필요해요?\n이혼해도 체류 가능해요?" 행이 다루는 토픽 범위 안에서만, 본문에 근거를 둘 것. 코드명(F-6 등)을 질문에 쓰지 말 것 |

## Stay manual only (`체류민원`)

Use these in addition to the common fields. Set `manual_type = 체류민원`.

| Field | Semantics |
| --- | --- |
| `stay_status_code` | Code such as `D-2`, `E-7`, `F-2-R` |
| `stay_status_name_ko` | 한국어 이름 such as `유학`, `특정활동`, `거주` |
| `obligations` | Reporting / education / residency obligations |

## Visa manual only (`사증민원`)

Use these in addition to the common fields. Set `manual_type = 사증민원`.

| Field | Semantics |
| --- | --- |
| `visa_code` | Code such as `C-3`, `D-8`, `E-7`, `F-6` |
| `visa_name_ko` | 한국어 이름 such as `단기방문`, `기업투자` |
| `inviter_context` | 초청인 / 고용주 / 유치기관 맥락 |
| `recommendation_or_approval` | 고용추천서 / 관계기관 승인 / 추천기관 |

## Canonical visa-code names

Use these exact Korean names. If a code appears with a different name in the source (e.g. spaced or abbreviated), still use the canonical form below.

| Code | Name |
| --- | --- |
| A-1 | 외교 |
| A-2 | 공무 |
| A-3 | 협정 |
| B-1 | 사증면제 |
| B-2 | 관광통과 |
| C-1 | 일시취재 |
| C-3 | 단기방문 |
| C-4 | 단기취업 |
| D-1 | 문화예술 |
| D-2 | 유학 |
| D-3 | 기술연수 |
| D-4 | 일반연수 |
| D-5 | 취재 |
| D-6 | 종교 |
| D-7 | 주재 |
| D-8 | 기업투자 |
| D-9 | 무역경영 |
| D-10 | 구직 |
| E-1 | 교수 |
| E-2 | 회화지도 |
| E-3 | 연구 |
| E-4 | 기술지도 |
| E-5 | 전문직업 |
| E-6 | 예술흥행 |
| E-7 | 특정활동 |
| E-8 | 계절근로 |
| E-9 | 비전문취업 |
| E-10 | 선원취업 |
| F-1 | 방문동거 |
| F-2 | 거주 |
| F-3 | 동반 |
| F-4 | 재외동포 |
| F-5 | 영주 |
| F-6 | 결혼이민 |
| G-1 | 기타 |
| H-1 | 관광취업 |
| H-2 | 방문취업 |

For sub-codes (D-2-1, F-2-R, E-7-4, etc.) preserve the full code in `subtype_or_program` and the parent code in `visa_code`/`stay_status_code`.

## Forbidden fields

Never emit any of: PDF page numbers, raw original text, evidence quotes, review flags, debug fields, or comments about your reasoning. The CSV is for downstream consumers and must stay clean.
