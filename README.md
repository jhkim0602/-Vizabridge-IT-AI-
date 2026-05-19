<div align="center">

# Vizabridge

**한국 비자·체류 매뉴얼을 검수 가능한 데이터로 컴파일하는 파이프라인**

[![Pipeline](https://img.shields.io/badge/pipeline-6_stage-1971c2)]()
[![LLM](https://img.shields.io/badge/LLM-1_stage_only-9c36b5)]()
[![Schema](https://img.shields.io/badge/v3_CSV-26_columns-2f9e44)]()
[![Source](https://img.shields.io/badge/source-HWP-e8590c)]()
[![Page Match](https://img.shields.io/badge/page_match-100%25-2f9e44)]()
[![Rows](https://img.shields.io/badge/rows-체류_233_·_사증_130-1971c2)]()

[한국어](README.md) · [English](README_EN.md)

</div>

---

## 한 줄 정의

> 700 페이지짜리 정부 HWP 매뉴얼을, **검수자가 행 단위로 OK·NG 판단할 수 있는 26컬럼 CSV** 로 컴파일한다.

![Vizabridge architecture overview](docs/diagrams/architecture_overview.png)

---

## 왜 만들었나

비자 매뉴얼은 **문서가 아니라 행정 규칙 데이터베이스**다. 700 페이지짜리 PDF를 그대로 RAG에 넣으면:

- 검수자가 한 답변이 "정확한가" 판단할 기준이 없다.
- 자격 변경 요건과 기간 연장 서류가 한 답변에 섞여 나온다.
- 페이지 출처를 모르면 사용자가 원본을 확인할 수 없다.
- 매뉴얼이 개정될 때마다 임베딩을 다시 만들어야 한다.

그래서 **임베딩 전에 한 번 컴파일**한다. 비자코드·신청종류·자격요건·제출서류·제한·예외·출처 페이지를 각자 컬럼으로 분리한 CSV를 만들고, 사람이 검수한 뒤에야 챗봇/RAG로 넘긴다.

---

## 한국 비자 기초 — 이걸 모르면 컬럼 설계가 안 보인다

### 1. 사증 vs 체류 — 두 개의 매뉴얼이 따로 있는 이유

한국 출입국 행정에는 두 개의 큰 단계가 있다.

| 단계 | 누가 발급 | 어디서 | 무엇을 의미 |
| --- | --- | --- | --- |
| **사증 (Visa)** | 재외공관 (한국 대사관·총영사관) | 외국 현지 | "한국에 들어와도 된다" 는 입국 허가증 |
| **체류 (Sojourn)** | 출입국·외국인청 (사무소·출장소) | 한국 안 | "한국에서 X자격으로 N개월 살아도 된다" 는 거주 자격 |

같은 사람이 같은 비자코드(`F-6`) 로 들어와도, 매뉴얼은 두 권으로 나뉜다.

- `사증민원 자격별 안내 매뉴얼` — 베트남에서 결혼하고 처음 한국에 들어오려는 단계
- `체류민원 자격별 안내 매뉴얼` — 이미 한국에 다른 자격으로 있다가 결혼해서 자격을 바꾸려는 단계

→ 그래서 v3 CSV 의 `사증·체류` 컬럼이 두 매뉴얼을 구분하는 가장 큰 분기점이다.

### 2. 비자코드 — 알파벳 + 숫자의 의미

비자코드는 한국 출입국관리법 시행령 별표 1·2 에 고정된 분류다.

| 알파벳 | 의미 | 예시 |
| --- | --- | --- |
| **A** | 외교·공무·협정 | A-1 외교 / A-2 공무 / A-3 협정 (SOFA, Fulbright) |
| **B** | 사증면제·관광통과 | B-1 사증면제 / B-2 관광통과 |
| **C** | 단기 (90일 이내) | C-1 일시취재 / C-3 단기방문 / C-4 단기취업 |
| **D** | 학업·연수·투자·구직 | D-2 유학 / D-4 어학연수 / D-7 주재 / D-8 기업투자 / D-10 구직 |
| **E** | 취업 | E-1 교수 / E-2 회화지도 / E-7 특정활동 / E-9 비전문취업 |
| **F** | 거주·가족·동포·영주 | F-1 방문동거 / F-3 동반 / F-4 재외동포 / F-5 영주 / F-6 결혼이민 |
| **G** | 기타 (난민·인도적체류 등) | G-1 기타 |
| **H** | 관광취업·방문취업 | H-1 워킹홀리데이 / H-2 방문취업 (재외동포) |

부모 코드는 37개. 그런데 매뉴얼 한 곳에서 `E-7-4`, `F-6-1` 같은 sub-program 까지 합치면 **200+ 개의 세부 자격**이 등장한다.

### 3. sub-program — "E-7-4" 같은 게 왜 따로 있나

같은 부모 코드 안에서도 자격요건이 완전히 다른 경우가 많다. 그래서 정부가 sub-code 로 더 쪼갠다.

- `E-7` 특정활동은 부모 코드. 그 아래에:
  - `E-7-1` 전문인력 (학사 + 경력)
  - `E-7-2` 준전문인력
  - `E-7-3` 일반기능
  - `E-7-4` 숙련기능 (K-point E74, 점수제 200점)
  - `E-7-S` 네거티브 리스트 전문인력
  - `E-7-T` Top-Tier 고소득
- `F-6` 결혼이민은 부모 코드. 그 아래에:
  - `F-6-1` 국민의 배우자
  - `F-6-2` 자녀양육 (한부모)
  - `F-6-3` 혼인단절 (사별·이혼)

→ v3 CSV 의 `상위코드` 와 `비자코드` 가 다른 이유다. 비자코드 = `F-6 (F-6-1)`, 상위코드 = `F-6`.

### 4. 신청종류 — 같은 비자라도 13가지 다른 절차

한 자격을 가진 사람도 살면서 여러 번 출입국에 가야 한다.

| 신청종류 | 누가 | 무엇을 |
| --- | --- | --- |
| **사증발급** | 외국 현지인 | 처음 한국 들어오려고 비자 받기 |
| **사증발급인정서** | 한국에 있는 초청자 | 외국인을 부르려고 사전 인정서 받기 |
| **전자사증** | 외국 현지인 | 일부 인증대학·우대업종이 받는 e-Visa |
| **체류자격 변경** | 한국 체류자 | 다른 자격으로 갈아타기 (예: 유학 → 취업) |
| **체류자격 부여** | 한국 체류자 | 새로 자격이 필요해진 사람 (예: 한국 출생 외국 자녀) |
| **체류기간 연장** | 한국 체류자 | 더 머물기 |
| **외국인등록** | 입국 90일 이상 머무는 사람 | 외국인등록증 받기 |
| **재입국허가** | 한국 체류자 | 잠시 출국 후 돌아올 권리 |
| **근무처 변경/추가** | 취업 자격 체류자 | 직장 바꾸거나 추가 |
| **체류자격외 활동허가** | 한국 체류자 | 본업 외 활동 (예: 유학생 시간제 알바) |
| **거소신고** | F-4·H-2 재외동포 | 외국인등록 대신 받는 동포 전용 |
| **고용변동 신고** | E-9·E-10 고용주 | 외국인근로자 퇴사·이직 신고 |
| **공통사항** | 모든 자격 | 수수료·기간 기본 규칙 |

→ v3 CSV 가 `(비자코드 × 신청종류)` 로 행을 나누는 이유다. F-6 한 명도 사증발급 → 외국인등록 → 체류기간 연장 → ... 단계마다 요건·서류가 다 다르다.

### 5. 비자의 흐름 — 한국 거주 라이프사이클

사용자는 보통 한 자격에서 다음 자격으로 옮겨간다. v3 CSV 의 `선행자격` `다음단계` 컬럼이 이걸 잡는다.

```
유학       D-2  ─→  구직 D-10  ─→  취업 E-7  ─→  점수제 거주 F-2-7  ─→  영주 F-5
비전문    E-9  ─→  숙련기능 E-7-4  ─→  점수제 F-2-7  ─→  영주 F-5
결혼      F-6   ─→  영주 F-5  (혼인 2년+ 후)
기업투자  D-8  ─→  영주 F-5  (5년+ 후)
재외동포  F-4  ─→  영주 F-5  (2년+ 거소)
```

→ "결혼 후 영주는 언제 신청해요?" 같은 질문에 `F-6` 행의 `다음단계` 컬럼이 `F-5 영주 (혼인 2년+ 후)` 라고 답할 수 있다.

### 6. 동반가족 — 본인 자격에 종속된 가족 자격

한국은 가족 비자를 한 번에 안 준다. **본인은 X 자격, 가족은 따로 Y 자격** 형태다.

| 본인 자격 | 가족이 받는 자격 |
| --- | --- |
| E-1~E-7 / D-7~D-9 (취업·주재) | **F-3 동반** (배우자·미성년 자녀) |
| D-2 유학 (학사·석사·박사만) | F-3 동반 |
| F-6 결혼이민 | F-1-12 자녀, F-1-5 부모 |
| F-5 영주 (점수제 sub) | F-2-71 자녀 |
| A-1 외교 | A-1 (가족도 같은 자격) |

→ v3 CSV 의 `동반가족` 컬럼이 이 관계를 한 줄로 보여준다.

---

## 한국 비자 매뉴얼의 구조

이런 행정 체계가 700 페이지 매뉴얼로 들어가면 평평한 텍스트가 아니라 **5층 트리** 가 된다.

![Korean visa manual model](docs/diagrams/korean_visa_manual_model.png)

> **F-6 결혼이민 하나만 봐도** 3개 sub-code × 5개 신청종류 × 8개 항목 = 100+ 데이터 포인트가 흩어져 있다.

---

## 행 설계 — Bad vs Good

가장 큰 설계 결정은 "한 행이 무엇인가" 였다.

![Column design rationale](docs/diagrams/column_design_rationale.png)

| 모델 | 행 단위 | 한 행의 셀 길이 | 검수 가능성 |
| --- | --- | --- | --- |
| ❌ Bad | 비자코드 1개 | 5,000자 이상 | 불가능 — 사증발급/자격변경/기간연장이 한 셀에 섞임 |
| ✅ Good (v3) | (비자코드 × 신청종류) | 항목별 컬럼으로 분리 | 행 단위 OK·NG 즉시 판정 |

---

## 30초 요약

| 항목 | 내용 |
| --- | --- |
| 원본 | `data/raw/*.hwp` |
| 중간 표현 | `data/parsed/normalized/{stay,visa}_manual.md` |
| 최종 산출물 | `data/processed/{체류,사증}매뉴얼_검수용_v3.csv` |
| 행 단위 | `(비자코드 × 신청종류)` |
| 스키마 | 26컬럼 |
| LLM 호출 | Stage 3 정규화 1회 |
| 결정적 처리 | HWP 변환, 청크 분할, 검증, CSV 빌드, 페이지 매핑 |
| 현재 행 수 | 체류 233행, 사증 130행 |
| 페이지 매핑 | 100% (모든 행의 `출처`에 `p. NNN`) |

---

## 파이프라인

> **핵심 원칙: LLM은 의미 정규화만 담당하고, 나머지 5단계는 결정적 Python으로 재현 가능하게 한다.**

![Six stage pipeline](docs/diagrams/pipeline_flow.png)

### 단계별 책임

| Stage | 처리 | 도구 | 입력 | 출력 |
| --- | --- | --- | --- | --- |
| 1 | HWP → Markdown | `scripts/parse_hwp_to_markdown.py`, kordoc | `data/raw/*.hwp` | `data/parsed/raw/*.md` |
| 2 | 표 경계 기준 청크 분할 | `scripts/index_markdown_chunks.py` | raw Markdown | `data/parsed/chunks/*.jsonl` |
| 3 | 행정 의미 단위 정규화 | `/vizabridge-normalize` Claude Code 스킬 | chunks | `data/parsed/normalized/*.md` |
| 4 | 원본 대조 검증 | `scripts/validate_normalization.py` | normalized + raw | `data/parsed/validation/*.json` |
| 5 | v3 CSV 빌드 | `scripts/build_v3.py` | normalized MD | `data/processed/*_검수용_v3.csv` |
| 6 | PDF 페이지 fuzzy 매칭 | `scripts/fill_page_numbers.py` | v3 CSV + PDF | 출처 페이지 보강 CSV |

### 시퀀스 (개발자 시점)

```mermaid
sequenceDiagram
    autonumber
    actor Dev as 개발자
    participant HWP as data/raw/*.hwp
    participant RawMD as parsed/raw MD
    participant Chunks as chunks_index.jsonl
    participant LLM as /vizabridge-normalize
    participant Norm as normalized MD
    participant Validator as validate_normalization.py
    participant Builder as build_v3.py
    participant Pager as fill_page_numbers.py
    participant CSV as v3 CSV
    participant Reviewer as Notion 검수

    Dev->>HWP: 정부 HWP 원본 배치
    Dev->>RawMD: Stage 1 — parse_hwp_to_markdown
    RawMD->>Chunks: Stage 2 — index_markdown_chunks
    Dev->>LLM: Stage 3 — /vizabridge-normalize stay·visa
    LLM->>Norm: 청크별 행정 의미 row 블록 생성
    Norm->>Validator: Stage 4 — 원본 교차 검증
    Validator-->>Dev: 비자코드·금액·서류명 누락/발명 리포트
    Norm->>Builder: Stage 5 — v3 26컬럼 CSV 빌드
    HWP->>Pager: HWP → PDF 변환본
    Builder->>Pager: CSV 행의 핵심 텍스트
    Pager->>CSV: 출처 컬럼에 p. NNN 부착
    CSV->>Reviewer: 행 단위 OK·NG 검수
```

---

## v3 스키마 (26컬럼)

![v3 schema](docs/diagrams/v3_schema.png)

스키마 원본은 [`docs/diagrams/v3_schema.dbml`](docs/diagrams/v3_schema.dbml). dbdiagram.io 에 그대로 붙여넣으면 인터랙티브 ERD 를 볼 수 있다.

| 그룹 | 개수 | 컬럼 |
| --- | ---: | --- |
| 식별·분류 | 4 | `비자코드`, `상위코드`, `사증·체류`, `신청종류` |
| 행정 내용 | 13 | `신청상황`, `대상자`, `자격요건`, `절차`, `수수료`, `기간`, `제한`, `예외`, `의무사항`, `점수표`, `쿼터`, `초청자`, `추천·승인기관` |
| 자료 | 2 | `제출서류`, `예상질문` |
| 출처 | 1 | `출처` (섹션 + 페이지) |
| 흐름·검색 | 4 | `선행자격`, `다음단계`, `동반가족`, `키워드` |
| 검수 | 2 | `검수상태`, `검수메모` |

### 컬럼을 이렇게 나눈 이유 — 27개 각각의 존재 이유

#### 식별·분류 (4) — "이 행이 누구의 무엇인가"

| 컬럼 | 왜 필요한가 | 예시 |
| --- | --- | --- |
| **비자코드** | 행의 primary key. sub-code 까지 포함해 유일하게 식별. | `F-6 (F-6-1)`, `E-7 (E-7-4)` |
| **상위코드** | 같은 부모 비자 그룹핑·필터링용. Notion Select 컬럼에서 카테고리 역할. | `F-6`, `E-7` |
| **사증·체류** | 두 매뉴얼 분기. 사용자가 "현지 영사관 갈지 / 출입국청 갈지" 결정의 출발점. | `사증`, `체류` |
| **신청종류** | 행의 두 번째 primary key. 같은 비자라도 절차마다 요건이 다름. | `사증발급`, `체류자격 변경`, `체류기간 연장` |

→ `(비자코드, 신청종류)` 가 행의 유일성 보장. 같은 비자코드가 여러 행에 등장하면 신청종류가 다르다.

#### 행정 내용 (14) — 매뉴얼이 실제로 다루는 항목

| 컬럼 | 왜 별도 컬럼인가 | 검수 포커스 |
| --- | --- | --- |
| **신청상황** | "어떤 사용자에게 적용되는가" 의 문맥. 다른 항목은 모두 이 상황을 가정한다. | 누가 신청하는지 명확? |
| **대상자** | 자격 부여 대상 정의. 자격요건과 별개 — 대상은 분류, 요건은 조건. | 누락된 카테고리 없는지? |
| **자격요건** | 사용자가 충족해야 할 조건. 챗봇 답변의 가장 큰 부분. | 숫자(소득·체류기간·점수) 자릿수 정확한지? |
| **절차** | 신청 순서·방법. 추천서 ↔ 신청 ↔ 심사 단계 명시. | 빠진 단계 없는지? |
| **수수료** | 금액 — 출입국관리법 시행규칙 표 기준. F-6/F-5 예외 주의. | 변경허가 10만원 / F-6 변경 4만원 등 정확? |
| **기간** | 체류기간·유효기간. 1년·3년·재임기간 등. | 표기 단위 통일? (년/월/일) |
| **제한** | "할 수 없는" 케이스. 단기사증 제외, 직종 제한 등. | "할 수 있음" 항목과 안 섞였는지? |
| **예외** | 제한의 면제 케이스. 임신·출산·자녀 양육 등 인도적 사유. | 어느 제한에 대한 예외인지 명확? |
| **의무사항** | 자격자가 지켜야 할 신고·등록 의무. | 위반 시 페널티 명시 있는지? |
| **공통사항** | 특정 비자 한정이 아닌 공통 규칙. | 본 비자에 적용되는지? |
| **점수표** | 점수제 비자만 등장 (E-7-4, F-2-7, F-5-S1 등). 항목별 배점 표. | 점수표 합계가 실제 만점과 일치? |
| **쿼터** | 연간/직종별 인원 제한. E-9 송출국·E-7-4 35,000명 등. | 배정인원·총 쿼터 정확? |
| **초청자** | 사증 매뉴얼 전용. 누가 외국인을 부르는지. | 초청 자격 누락 없는지? |
| **추천·승인기관** | 외교부·노동부·산업부 사전 추천 필요한 경우. | 어느 부처의 어느 양식인지? |

> **왜 자격요건과 요건을 합쳤나** — 매뉴얼이 [자격요건] 과 [요건] 두 라벨을 혼용하기 때문. 정규화 단계에서 합쳐서 한 컬럼으로.

> **왜 점수표·쿼터가 별도 컬럼인가** — 점수제와 쿼터는 자격요건의 사실관계가 아니라 정량 표. 자격요건에 섞이면 챗봇이 "200점 이상" 같은 수치를 인용할 때 출처가 흐려진다.

#### 자료 (2) — 사용자가 실제로 챙기는 것

| 컬럼 | 왜 필요한가 | 검수 포커스 |
| --- | --- | --- |
| **제출서류** | `[공통서류]`, `[필수서류]`, `[기타서류]` 라벨로 내부 구조. 사용자에게 가장 실용적인 정보. | 누락 서류 없는지? 양식 번호 (별지 N호) 일치? |
| **예상질문** | 사용자가 비자코드를 모르고 자연어로 묻는 질문 2~4개. RAG 시맨틱 검색 매칭용. | 비자코드 직접 노출 X? 사용자 톤? |

#### 출처 (1) — 검수자의 생명선

| 컬럼 | 왜 필요한가 |
| --- | --- |
| **출처** | `섹션명 (p. NNN)` 형식. 검수자가 PDF 페이지로 즉시 점프해 원본 대조. **이게 없으면 검수 자체가 불가능.** |

→ HWP → PDF → pdfplumber → fuzzy 매칭 6단계 인프라가 오직 이 한 컬럼을 100% 채우기 위해 존재한다.

#### 흐름·검색 (4) — 챗봇·검색이 사용자 의도를 잡기 위한 보강

| 컬럼 | 왜 필요한가 | 활용 시나리오 |
| --- | --- | --- |
| **선행자격** | 이 자격을 받기 위한 사전 조건. | "F-5 영주 받으려면?" → "D-7~E-7 5년 + GNI 2배" |
| **다음단계** | 이 자격에서 자연스럽게 변경되는 다음 자격. | "결혼 후 영주는 언제?" → F-6 의 다음단계 = F-5 |
| **동반가족** | 가족이 함께 받는 별도 자격. | "취업하면 아내도 같이 올 수 있나?" → E-7 의 동반 = F-3 |
| **키워드** | 검색·라우팅용 명사 4~8개. 사용자 발화에서 매칭. | "결혼이민, 한국인 배우자, 가족결합" → F-6-1 행 라우팅 |

> **왜 동반가족이 별도 컬럼인가** — 한국 가족 비자는 본인 자격에 종속된다. 본인이 E-7이면 가족은 F-3 으로 따로 발급받는다. 이걸 자격요건이나 제한 안에 묻으면 "취업 비자에 가족이 따라올 수 있나?" 질문에 챗봇이 헤매게 된다.

#### 검수 (2) — Notion 검수 워크플로 진입점

| 컬럼 | 왜 필요한가 |
| --- | --- |
| **검수상태** | Status enum: `미검수` / `검수중` / `검수완료` / `이슈있음`. Notion 에서 칸반·뷰 필터링. |
| **검수메모** | 검수자가 발견한 이슈·코멘트. 자동 플래그 (`[자동 플래그] ...`) 도 여기. |

→ CSV 를 Notion 에 import 하면 별도 DB 설계 없이 검수 워크플로가 즉시 시작된다.

---

### 핵심 설계 결정 — 한눈에

| 결정 | 이유 |
| --- | --- |
| 행 = `(비자코드 × 신청종류)` | 사증발급·자격변경·기간연장은 요건과 서류가 완전히 다르다. 한 행으로 합치면 검수 불가능. |
| `자격요건` ↔ `제한` ↔ `예외` 분리 | RAG 답변에서 "할 수 있음/없음", "필수/예외"가 섞이는 사고를 막는다. |
| `점수표`·`쿼터` 별도 컬럼 | 수치 표를 자격요건에 섞으면 출처 흐려짐. 분리하면 챗봇이 "200점 이상" 같은 정량 사실을 정확히 인용. |
| `출처` 한 컬럼에 `(p. NNN)` 통합 | 검수자가 한 컬럼만 보고 원본 PDF 페이지로 즉시 점프. |
| `선행자격`·`다음단계`·`동반가족` 별도 보강 | 사용자는 비자코드를 모르고 "결혼 후 영주는?" 처럼 묻는다. 흐름이 컬럼으로 잡혀 있어야 답할 수 있다. |
| `키워드` 별도 컬럼 | RAG 시맨틱 검색에서 사용자 발화 매칭. 자격요건 본문보다 노이즈 적음. |
| `검수상태`·`검수메모` CSV 에 포함 | Notion import 직후 검수 시작. 별도 DB 마이그레이션 없음. |
| 정규화 MD 를 git 에 커밋 | LLM 비결정성을 동결. CSV 컬럼 매핑·페이지 매칭만 바뀌어도 LLM 재실행 불필요. |

---

## 빠른 시작

### 환경

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
node --version    # kordoc 용 Node.js 18+
```

### 새 매뉴얼 처음부터 처리

```bash
# Stage 1·2 — HWP → Markdown → chunks
python scripts/parse_hwp_to_markdown.py
python scripts/index_markdown_chunks.py

# Stage 3 — Claude Code 세션에서
#   /vizabridge-normalize stay
#   /vizabridge-normalize visa

# Stage 4·5 — 검증 + v3 CSV
python scripts/validate_normalization.py
python scripts/build_v3.py

# Stage 6 — HWP → PDF → 페이지 매핑
brew install --cask libreoffice
curl -L -o /tmp/H2Orestart.oxt \
  https://github.com/ebandal/H2Orestart/releases/latest/download/H2Orestart.oxt
unopkg add /tmp/H2Orestart.oxt
soffice --headless --convert-to pdf --outdir data/raw/pdf/ data/raw/*.hwp
python scripts/fill_page_numbers.py
```

### 페이지 매칭만 다시

```bash
python scripts/fill_page_numbers.py both --force
```

### 재실행 매트릭스

| 무엇이 바뀌었나 | 다시 실행 |
| --- | --- |
| HWP 원본 | 1 → 6 (전체) |
| 정규화 규칙 | 3 → 6 |
| v3 컬럼 매핑 | 5 → 6 |
| 페이지 번호만 어긋남 | 6 |
| 검수자가 오타 발견 | normalized MD 또는 빌더 규칙 수정 후 4 → 6 |

정규화 MD 를 git 에 커밋하는 이유가 여기다 — **CSV 컬럼이나 페이지 매핑을 바꿀 때 LLM 을 다시 부르지 않아도 된다.**

---

## 페이지 매핑 기술 상세

HWP 본문은 source of truth, 페이지 번호는 검수 편의를 위해 PDF 변환본에서 가져온다.

```
HWP  →  PDF  →  pdfplumber  →  페이지 텍스트 인덱스  →  fuzzy 매칭  →  출처 컬럼
       (LibreOffice               (캐시)                 (sliding
        + H2Orestart)                                     window)
```

### 매칭 알고리즘

1. **PDF 페이지별 텍스트 추출** — `pdfplumber`, JSON 캐시 (`data/raw/pdf/.cache/`)
2. **정규화 3단계**
   - `unicodedata.normalize("NFC", s)` — 자모 합성
   - 구두점·공백·괄호 제거
   - **`([가-힣])\1+ → \1` 한글 중복 글자 압축** ← LibreOffice + H2Orestart 변환 시 한글이 중복 출력되는 버그 보정. 이게 매칭률을 5%→100% 로 끌어올림.
3. **Sliding window** — 50자 → 30자 → 18자 차차 시도, step 8자
4. **점수 투표** — 같은 페이지에 여러 윈도우 매칭되면 점수 누적
5. **Hint 가중치** — 직전 행 페이지 ±8쪽 이내 2.5배 가산, 60쪽+ 떨어지면 0.15배 페널티 (boilerplate 오매칭 회피)
6. **Fallback** — 출처 라벨 → hint 페이지 → 빈값
7. **인접 페이지 그룹** — 한 (비자, 신청) 묶음이 여러 페이지에 걸치면 `p. 442~444`

### 매칭 결과

| 매뉴얼 | 행 수 | 페이지 매칭 |
| --- | ---: | ---: |
| 체류 | 233 | **100%** |
| 사증 | 130 | **100%** |

---

## 검수 워크플로 (Notion)

1. `data/processed/체류매뉴얼_노션검수용_v3.csv` 또는 `사증매뉴얼_노션검수용_v3.csv` 다운로드
2. Notion 에서 `+` → **Import** → CSV 선택
3. 컬럼 type 전환
   - `검수상태` → Status
   - `사증·체류`, `신청종류`, `상위코드` → Select
4. 뷰 추가 — 필터 `검수상태 = 미검수`, 정렬 `상위코드`
5. 각 행의 `출처` 컬럼 (`F-6-1 변경허가 (p. 442)`) → 원본 PDF·HWP 점프
6. 검수 완료 시 `검수상태` `검수메모` 갱신

---

## 데이터 품질 보증

```bash
python -m pytest tests -q
```

다음을 회귀로 잠근다:

- 정규화 row 의 비자코드·금액·서류명이 원본 청크에 실제 등장
- 모든 v3 행에 출처 페이지 채움
- 핵심 사실 8건 — F-6 2026 소득요건, E-7-4 200점/2,600만원, D-2-5 2년 초과 불가, F-5-1 5년 체류, F-2-7 80점, E-9 16개 송출국, H-1 만 18~30세, F-4 단순노무 제한
- Notion 호환 컬럼 type 구조 유지

---

## 디렉토리 구조

```text
.
├── data/
│   ├── raw/                       # HWP 원본, PDF 변환물 (gitignored)
│   ├── parsed/
│   │   ├── raw/                   # kordoc Markdown
│   │   ├── chunks/                # 청크 인덱스
│   │   ├── normalized/            # LLM 정규화 결과 (커밋)
│   │   └── validation/            # 검증 결과
│   └── processed/                 # 검수용 v3 CSV
├── docs/
│   ├── diagrams/                  # 아키텍처·스키마 이미지
│   ├── pipeline_strategy.md       # 파이프라인 설계 배경
│   └── project_structure.md       # 폴더 운영 정책
├── scripts/                       # 결정적 Python 파이프라인 (6 stage)
├── tests/                         # CSV 품질 회귀 테스트
├── interview/                     # 별도 Next.js 인터뷰 앱 (관련 X)
└── requirements.txt
```

더 자세한 문서:

- 스크립트별 사용법 → [`scripts/README.md`](scripts/README.md)
- 파이프라인 설계 배경 → [`docs/pipeline_strategy.md`](docs/pipeline_strategy.md)
- 폴더 운영 원칙 → [`docs/project_structure.md`](docs/project_structure.md)
- DBML 스키마 → [`docs/diagrams/v3_schema.dbml`](docs/diagrams/v3_schema.dbml)

---

## 개발자 노트 — "작은 컴파일러"

이 저장소는 사실 작은 컴파일러다.

```
Source       data/raw/*.hwp
   │
   ▼ Stage 1·2  (frontend — HWP를 표준 IR로)
IR           data/parsed/normalized/*.md
   │
   ▼ Stage 3   (semantic analysis — LLM)
   ▼ Stage 4   (validator — type/fact check)
   ▼ Stage 5   (codegen — CSV)
   ▼ Stage 6   (linker — 페이지 출처)
   │
   ▼
Output       data/processed/*_v3.csv
   │
   ▼
Quality gate validator + pytest + Notion 검수
```

새 컬럼을 추가하고 싶다면 `scripts/build_v3.py` 의 `V3_COLUMNS`, `DIRECT_MAP`, `PARENT_FLOW`, `SUB_OVERRIDE` 만 손대면 된다. 정규화 단계가 이미 의미 필드를 충분히 만들었다면 **LLM 을 다시 부르지 않고 Stage 5 부터 재생성**된다.

---

## 라이선스

내부 프로젝트 (헬로프렌즈 Vizabridge 데이터 전처리팀). 매뉴얼 원본은 법무부 공개자료.
