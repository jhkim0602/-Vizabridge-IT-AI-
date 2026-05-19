# Extraction Rules

These rules port the regex-era logic into LLM-readable guidance. Apply them when deciding which (`petition_type`, `subsection_type`) triple a piece of source text belongs to.

## How to slice a visa-code section into rows

A single visa-code section in the source typically contains:

1. A header table with rows like `활동범위`, `해당자`, `1회 부여 체류기간의 상한`, `공관장 재량으로 발급할 수 있는 사증`, `사증발급인정서 발급대상`, `참고사항`.
2. Sometimes follow-up tables and headings describing variant programs (E-7-4, F-2-R, etc.), 점수표, 쿼터, FAQ, 첨부서식.

You emit **one row per (petition_type, subsection_type) you find usable content for**. Some visa codes will yield 3 rows, some 30. **No upper cap on rows per chunk — emit as many as the source meaningfully supports.** Use judgment, but follow the canonical lists below.

## Canonical petition types — 13종

Choose `petition_type` from this enum (13 values). Map source phrases to the canonical value on the left.

| Canonical value | Source phrases that map to it |
| --- | --- |
| `사증발급` | 공관장 재량, 단수사증, 복수사증, 사증발급 |
| `사증발급인정서` | 사증발급인정서, 비자발급인정서 |
| `전자사증` | 전자사증, 전자비자 |
| `체류자격 변경` | 체류자격 변경허가, 자격변경, 체류자격 변경 |
| `체류자격 부여` | 체류자격 부여 |
| `체류기간 연장` | 체류기간 연장허가, 기간연장, 체류기간연장 |
| `외국인등록` | 외국인등록, 등록사항 변경신고, 체류지변경신고 |
| `거소신고` | 거소신고, 국내거소신고, F-4 거소신고, H-2 거소신고 (재외동포·방문취업자 전용 신고) |
| `재입국허가` | 재입국허가, 복수재입국허가 |
| `근무처 변경/추가` | 근무처의 변경·추가, 근무처 변경, 근무처 추가 |
| `체류자격외 활동허가` | 체류자격외 활동, 자격외 활동 |
| `고용변동 신고` | 고용변동 신고, 고용 변동 등 신고, 고용주 신고, 이탈자 신고 (E-9·E-10 고용주 신고) |
| `공통사항` | 공통 적용 규정, 매뉴얼 양쪽 공통 사항 |

Stay manual rows typically use the bottom block (체류자격*, 외국인등록, 거소신고, 고용변동 신고 등). Visa manual rows typically use the top block (사증발급*). Some rows belong to both — pick whichever the surrounding text emphasizes.

`거소신고` 는 F-4·H-2 (재외동포·방문취업자) 전용 신고 행정행위로, 외국인등록과 구분된다.
`고용변동 신고` 는 E-9·E-10 (비전문취업·선원취업) 고용주가 의무적으로 행하는 신고 (이탈, 사망, 계약해지 등).

If the source clearly describes a common-rule across many visa codes (e.g. 결핵진단서 제출), use `petition_type` = `공통사항` and set `item_type` = `common_rule`.

## Canonical sub-section types

`subsection_type` is one of:

`대상`, `요건`, `제출서류`, `절차`, `제한`, `예외`, `수수료`, `점수표`, `쿼터`, `기간`

Mapping from source headings to canonical value (first matching rule wins, so prefer the more specific):

| Canonical | Map from source phrases |
| --- | --- |
| `제출서류` (→ `mandatory_documents`/`common_documents`) | 제출서류, 제출 서류, 필수서류, 첨부서류, 구비서류, 신청서류, 사증발급신청서, 사증발급인정신청서, 여권사본, 표준규격사진, 공통서류, 공통 제출서류 |
| `대상` (→ `eligibility`, `target_persons`) | 해당자, 신청대상, 적용대상, 대상자, 발급대상, 발급 대상, 대상 |
| `요건` (→ `requirements`, `eligibility`) | 기본요건, 허가요건, 자격요건, 요건, 심사기준, 기준 |
| `절차` (→ `procedure`) | 신청기관, 신청 장소, 발급절차, 신청절차, 절차, 접수, 하이코리아 |
| `기간` (→ `duration_or_validity`) | 체류기간, 유효기간, 허가기간, 기간의 상한, 체류허가기간, 단수사증, 복수사증 |
| `제한` (→ `restrictions`) | 제한, 불허, 금지, 결격, 제외, 억제 |
| `예외` (→ `exceptions`) | 예외, 면제, 특례, 완화 |
| `수수료` (→ `fees`) | 수수료, 수입인지, 납부금 |
| `점수표` (→ `score_criteria`) | 점수표, 배점표, 점수제, 배점 |
| `쿼터` (→ `quota_or_limit`) | 쿼터, 선발인원, 허용인원, 상한 |

Stay manual specifically:

| Canonical | Map from source phrases |
| --- | --- |
| `신고의무` (→ `obligations`) | 신고의무, 신고하여야, 제출 의무, 교육의무, 거주의무 |

Visa manual specifically:

| Canonical | Map from source phrases |
| --- | --- |
| `추천/승인` (→ `recommendation_or_approval`) | 고용추천서, 추천서, 추천기관, 관계기관, 승인 |

## Vocabulary signals you can rely on

When you are uncertain which column some text belongs to, these word lists usually settle the question.

**Document phrases** (route to `mandatory_documents` / `other_documents`): 신청서, 여권, 사진, 수수료, 증명서, 등본, 계약서, 등록증, 허가증, 면허증, 추천서, 공한, 입증서류, 확인서, 사본, 초청장, 신원보증서, 진술서, 건강진단서, 범죄경력, 가족관계, 사업자등록증, 준비서류, 첨부서류, 구비서류, 제출서류.

**Score/point phrases** (route to `score_criteria`): 점수, 배점, 평가항목, 총점, 득점, 가점, 감점, 만점, 점 이상.

**Quota phrases** (route to `quota_or_limit`): 쿼터, 선발인원, 허용인원, 허용 인원, 배정인원, 명 이내, 명 이하, 인원.

**Exception phrases** (route to `exceptions`): 예외, 면제, 특례, 완화, 제출할 필요가 없, 제출 불요.

**Restriction phrases** (route to `restrictions`): 제외, 제한, 불허, 금지, 불가, 억제, 결격.

## Sub-code handling

The source mentions hundreds of sub-codes (`D-2-1`, `F-2-R`, `E-7-S`, etc.). Treat them like this:

- A sub-code described as its own program with its own eligibility/documents → its own row(s). Put the sub-code in `subtype_or_program`. Put the parent code (`D-2`, `F-2`, `E-7`) in `visa_code`/`stay_status_code`.
- A sub-code mentioned only in passing inside a parent program's body → do not split it out. Keep it referenced in the relevant field (e.g. `eligibility`) but don't fabricate a row.

## Section titles

`section_title` should be a clean human-readable title. Examples:

- `D-8 기업투자`
- `E-7-4 숙련기능인력 / 자격변경`
- `F-2 거주 / 점수표`
- `공통사항: 결핵진단서`

Keep it short. Lower-case English mixed in is fine where standard (e.g. `K-STAR`, `TOPIK`).

## 예상질문 작성 규칙 (expected_questions)

행마다 한국어 질문 **2~4개 가변** (중복 제거 후, 자연스러운 표현 우선)을 줄바꿈으로 구분해 적는다. 사람 검수자가 "이 행이 어떤 사용자 상황에 답이 되는가"를 한눈에 보기 위한 용도다.

- 질문은 일반인이 자기 상황을 그대로 말하는 톤. 예: "한국인과 결혼했는데 어떤 비자 받아요?"
- **비자코드(F-6, D-8 등)를 질문 본문에 쓰지 않는다.** 사용자는 코드를 모르고 묻는 것이 전제.
- 행이 다루는 본문 범위 안에서만 묻는다. 본문에 없는 사실로 질문을 만들지 말 것 (예: 행이 "제출서류"만 다루면 수수료를 묻지 말 것).
- 형식: `petition_type`이 "사증발급" → 질문은 "어떻게 받아요/신청해요" 톤. "체류기간 연장" → "얼마나 더 머물 수 있어요" 톤. "제한"/"예외" → "안 되는 경우는요/예외 있어요" 톤.
- **개수는 2~4개 가변.** 본문 정보가 얇으면 2개로 충분. 풍부하면 4개까지. 의미가 겹치는 질문은 합쳐서 자연스러운 표현 하나로. 억지로 3개에 맞추지 말 것.
- 본문이 너무 빈약해 2개도 어렵다면 1개도 허용. 단, 가능한 한 2~4개 범위를 채울 것.

## 4개 신규 필드 추출 가이드

다음 4개 필드는 빈 값 허용이지만 **가능한 한 채울 것**. 검색·검수 품질을 좌우한다.

### `keywords` — 검색·RAG 매칭용 키워드 (콤마 분리 4~8개)

행이 다루는 토픽을 압축한 명사 위주 키워드. 검색 입력으로 들어왔을 때 이 행이 후보로 떠야 한다고 생각하는 표현을 모은다.

구성 가이드:
- **비자코드 (필수)**: `F-6`, `E-7-4` 등. 부모코드 + 서브코드 모두 적어도 무방.
- **자격 한국어 이름**: `결혼이민`, `숙련기능인력`, `재외동포` 등.
- **핵심 명사 2~5개**: 본문에서 가장 두드러진 개념. 신청서, 소득요건, 점수표, 통합신청서, 한국어능력, 고용추천서 등.
- 동사·서술어는 제외. 명사·복합명사 위주.
- 콤마 + 공백 하나로 구분. 한 항목 내부에는 콤마 금지.

예: `결혼이민, 한국인 배우자, 소득요건, 통합신청서, F-6`
예: `숙련기능인력, 점수제, 한국어능력, 자격변경, E-7-4`

### `source_page` — 원문 페이지 추정 (빈 값 허용)

raw MD 청크에서 페이지 번호가 보이면 적고, 없으면 빈 값. 추정으로 메꾸지 말 것.

- 단일 페이지: `p. 142`
- 페이지 범위: `p. 142~144`
- 없으면 그냥 빈 값. 빈 값이 더 안전하다.

### `source_excerpt` — 원문 핵심 발췌 (변형 금지, 100~400자)

이 행을 만들 때 근거로 삼은 원문 문장 1~3개를 **그대로** 복사해 붙인다. LLM 환각 여부를 사람이 1초 안에 검증할 수 있게 하는 닻이다.

- **변형·요약·재서술 금지.** 원문 그대로의 표기·띄어쓰기·기호를 유지한다.
- 1~3개 문장. 100~400자 권장.
- 불릿(`-`)로 시작하는 원문이면 불릿 형태 유지. 표 셀이면 셀 내용 그대로.
- 청크 마커(`<!-- ... -->`)는 발췌에 포함하지 않는다.

예 (그대로 발췌):
```
- 한국인과 혼인하여 국내에서 결혼생활을 영위하는 자
- 신청인의 연간소득이 한국은행이 고시한 전년도 1인당 국민총소득(GNI) 이상
```

### `related_visa_codes` — 함께 보는 비자코드 (콤마 분리)

같은 청크 본문 안에서 명시적으로 함께 언급된 다른 비자/체류 코드. 후속 행정행위(예: F-6 → F-5 영주 전환)나 사촌 자격(예: F-4 ↔ H-2)을 잇는 데 쓴다.

- 청크 안에 실제로 적혀 있는 코드만. 추정 금지.
- 콤마 + 공백 구분. 예: `F-5, F-2-R, F-1-D`
- 본 행의 `visa_code` 자체는 제외 (중복).
- 없으면 빈 값.
