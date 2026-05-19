> 🌐 **언어:** **한국어** | [English](README_EN.md)

# Vizabridge Visa RAG

대한민국 비자/체류 매뉴얼 **HWP** 원본을 [kordoc](https://github.com/chrisryugj/kordoc)으로 Markdown으로 변환한 뒤, **Claude Code 스킬**로 의미 단위 정규화 → **결정적 Python**으로 **사람이 검수 가능한 1차 정리 CSV**를 생성하는 데이터 전처리 파이프라인입니다.

이번 회차의 1차 산출물은 **챗봇/RAG용 최종 데이터 구조가 아니라, 사람이 원본 자료를 검수하기 위한 CSV**입니다. 검수가 끝난 후에 챗봇용 변환을 진행합니다.

검수용 CSV는 **v2 스키마 (32컬럼)** 를 따릅니다. 클라이언트 피드백을 전면 반영해 행정 단위별로 컬럼을 분리하고, 빈 셀 보존·enum 잠금·누락 ZERO 원칙을 강제합니다. 한 행 = **(비자코드 × 신청종류)** 1조합으로 펼쳐지므로, 같은 비자가 사증발급/체류자격 변경/기간 연장 등 신청종류별로 5~10행에 분산됩니다.

상세 스키마: [docs/data_schema_v2.md](docs/data_schema_v2.md) — 32컬럼 정의, enum 사전, 빈 셀 정책의 단일 진실 원천 (Python: `scripts/schema.py`).

| 그룹 | 컬럼 수 | 예시 컬럼 |
| --- | --- | --- |
| 식별·분류 | 5 | `비자코드`, `상위코드`, `사증·체류`, `신청종류`, `하위프로그램` |
| 행정 내용 | 17 | `대상`, `자격요건`, `제출서류`, `절차`, `수수료`, `기간`, `점수표`, `쿼터`, `초청자`, `추천·승인기관`, … |
| 출처·추적 | 4 | `원본파일`, `섹션`, `페이지`, `원본 라인범위` |
| 관계·검색 | 3 | `연계비자`, `키워드`, `원문발췌` |
| 검수 | 3 | `예상질문`, `검수상태`, `검수메모` |

## Pipeline

```
data/raw/*.hwp                                            (source of truth)
   │  Stage 1  scripts/parse_hwp_to_markdown.py           (Python, kordoc)
   ▼
data/parsed/raw/{stay,visa}_manual.md
   │  Stage 2  scripts/index_markdown_chunks.py           (Python, deterministic)
   ▼
data/parsed/chunks/{stay,visa}_chunks_index.jsonl
   │  Stage 3  /vizabridge-normalize                      (Claude Code skill, v2)
   ▼
data/parsed/normalized/{stay,visa}_manual.md              ← canonical intermediate
   │  Stage 4  scripts/validate_normalization.py          (Python, deterministic)
   │  Stage 5  /vizabridge-repair                         (Claude Code skill, optional)
   │  Stage 6  scripts/build_semantic_csv.py              (Python v2 빌더, 32컬럼)
   ▼
data/processed/{체류,사증}매뉴얼_검수용_v2.csv             ← 사람 검수용 (32컬럼)
   │  Stage 7  scripts/notion_export_v2.py                (Notion import 친화 가공)
   ▼
data/processed/{체류,사증}매뉴얼_노션검수용_v2.csv
   │  Stage 8  scripts/qc_v2.py + scripts/cross_check_v2.py
   ▼
output/quality/v2/{v2_quality_report.md, v2_cross_check_report.md, *_fill_rates.csv}

(RAG/챗봇 변환 단계는 검수 완료 후 별도 회차에서 진행 예정)
```

LLM은 stages 3, 5 에서만 사용합니다. 나머지 단계는 결정적 Python으로, 다시 실행해도 같은 결과가 나옵니다. **정규화 MD**(stage 3 산출물)는 의도적으로 git에 커밋합니다 — 같은 입력에서 같은 CSV가 재생성되도록.

## Folder Structure

```text
.
├── data/
│   ├── raw/                  # 원본 HWP (원본 교체 외 수정하지 않음)
│   │   └── legacy_pdf/       # 과거 PDF 백업
│   ├── parsed/
│   │   ├── raw/              # kordoc 출력 (커밋)
│   │   ├── chunks/           # 청크 인덱스 .jsonl (커밋)
│   │   ├── normalized/       # 정규화 MD — LLM 결과 (커밋)
│   │   │   └── *.backup_v1.md  # v1 스냅샷 (안전 보존, 비커밋)
│   │   └── validation/       # validator 산출 .json (커밋)
│   └── processed/            # 검수용 v2 CSV (커밋, 다운로드 가능)
├── scripts/                  # 결정적 단계 Python
│   ├── schema.py             # ★ v2 스키마 SSoT (32컬럼 + enum)
│   ├── build_semantic_csv.py # v2 빌더
│   ├── notion_export_v2.py   # Notion import 가공
│   ├── qc_v2.py              # 품질 리포트 v2
│   ├── cross_check_v2.py     # 정규화 MD ↔ CSV 교차 검증
│   ├── build_helpers/        # 빌더 공통 유틸 (aggregate / pivot / sources)
│   └── legacy/               # 과거 정규식 빌더 보존본
├── .claude/skills/
│   ├── vizabridge-normalize/  # v2 정규화 (32컬럼 출력)
│   └── vizabridge-repair/
├── docs/
│   └── data_schema_v2.md     # ★ 32컬럼 스키마 사양
├── notebooks/                # 분석 노트북
├── tests/                    # 정제 규칙 보호 테스트
├── output/quality/v2/        # v2 품질 리포트 (커밋)
└── requirements.txt
```

자세한 폴더별 관리 기준은 [docs/project_structure.md](docs/project_structure.md)에 있습니다.

## Setup

```bash
# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Node.js 18+ 필요 (kordoc 실행용)
node --version    # v18 이상이어야 함
```

별도 API 키는 필요하지 않습니다. LLM 단계는 Claude Code 세션 안에서 동작하는 스킬이고, kordoc은 첫 실행 시 `npx`가 자동으로 받아옵니다.

## Workflow

```bash
# 1) HWP → Markdown (kordoc, 1~2분)
python scripts/parse_hwp_to_markdown.py

# 2) 청크 분할 (즉시)
python scripts/index_markdown_chunks.py

# 3) Claude Code 세션에서 정규화 (v2 32컬럼 출력)
#    /vizabridge-normalize stay
#    /vizabridge-normalize visa
#    (세션 한도 닿으면 다음 세션에서 재개)

# 4) 결정적 검증
python scripts/validate_normalization.py

# 5) 필요 시 Claude Code 세션에서 수리
#    /vizabridge-repair stay
#    /vizabridge-repair visa
python scripts/validate_normalization.py   # 재검증

# 6) 검수용 CSV v2 빌드 (32컬럼, 행 단위 비자×신청)
python scripts/build_semantic_csv.py
#    → data/processed/체류매뉴얼_검수용_v2.csv
#    → data/processed/사증매뉴얼_검수용_v2.csv

# 7) Notion import 가공
python scripts/notion_export_v2.py
#    → data/processed/체류매뉴얼_노션검수용_v2.csv
#    → data/processed/사증매뉴얼_노션검수용_v2.csv

# 8) 품질 리포트 + 교차 검증
python scripts/qc_v2.py
python scripts/cross_check_v2.py
#    → output/quality/v2/*
```

## 검수 워크플로 (Notion import)

`*_노션검수용_v2.csv` 는 Notion 데이터베이스 import 친화 가공판입니다. 워크스페이스에서 새 DB 생성 → CSV import 로 32컬럼을 그대로 가져온 뒤, `검수상태` 컬럼을 select 필터로 두고 `미검수 → 검수중 → 검수완료 / 이슈있음` 흐름으로 진행합니다. `섹션`·`페이지`·`원본 라인범위`·`원문발췌` 4개 컬럼이 출처 추적용이며, `원본 라인범위` 의 `{경로}:{시작}-{끝}` 포맷은 GitHub 에서 직접 점프 가능합니다.

## Skills 적용법

LLM 단계(3·5)는 `.claude/skills/` 안의 두 skill로 동작합니다. 저장소를 Claude Code 워크스페이스로 열면 자동 인식되므로 별도 설치 절차가 없습니다.

세션 안에서 슬래시 명령으로 호출합니다.

```
/vizabridge-normalize stay
/vizabridge-normalize visa
/vizabridge-repair stay
/vizabridge-repair visa
```

각 명령은 청크 또는 행 단위로 처리하며 진행률을 출력 MD의 마커로 기록합니다. 세션 한도에 닿거나 사용자가 중단해도 다음 세션에서 같은 명령만 다시 입력하면 자연스럽게 이어집니다. `/vizabridge-repair`는 `scripts/validate_normalization.py`가 이슈를 잡았을 때만 사용합니다.

세션 밖에서 진행률을 미리 보고 싶으면 (skill을 invoke하지 않고 상태만 확인):

```bash
python .claude/skills/vizabridge-normalize/scripts/show_progress.py stay
python .claude/skills/vizabridge-repair/scripts/show_flagged.py stay
```

<details>
<summary><b>Skill 원리 (펼쳐서 보기)</b></summary>

### 구성 요소

각 skill 디렉토리는 세 종류 파일로 이루어져 있습니다.

| 파일 | 역할 |
| --- | --- |
| `SKILL.md` | frontmatter(`name`, `description`)와 절차서. Claude Code는 사용자 입력을 description과 매칭해 invoke 여부를 결정합니다. 본문은 invoke 시 모델 컨텍스트로 로드되는 짧은 지침. |
| `references/*.md` | 도메인 지식(컬럼 스키마, 추출 규칙, 노이즈 필터, 출력 포맷 등). 매 호출마다 통째로 로드되지 않고, 모델이 필요할 때만 Read 도구로 가져옵니다. |
| `scripts/*.py` | 검증·저장·진행률 조회 같은 결정적 작업. LLM이 직접 하면 변동 위험이 있는 일은 Python에 맡깁니다. |

### 진행률은 출력 MD 자체

별도 상태 파일을 두지 않습니다. 정규화 산출물의 마커가 그대로 상태입니다.

```
<!-- vizabridge-normalize v2 chunk: stay_004 hash: ... lines: 449-1185 -->
### row D-3 / 체류자격 변경 / 자격요건
- ...
<!-- end chunk: stay_004 -->
```

`show_progress.py`는 chunk index와 위 마커를 대조해 다음 처리 대상을 찾습니다. 따라서 세션이 끊겨도, 사람이 수동으로 일부 행을 보강해도, 다음 invoke가 이어 받습니다.

### Hash 기반 drift 탐지

마커의 `hash:` 값은 원본 청크의 SHA-256 앞 16자(공백 정규화 후)입니다. kordoc 재실행으로 원본이 바뀌면 hash가 어긋나고 validator가 `hash drift` 이슈로 잡아냅니다. 그러면 `/vizabridge-repair`가 해당 청크만 재정규화합니다.

### 검증과 LLM의 역할 분리

LLM은 의미 추출(어느 셀이 `제출서류`인지, `신청종류`가 무엇인지)만 합니다. 그 결과의 정합성 검사 — 비자코드/금액/서류명이 원본에 실제 등장하는지 — 는 결정적 Python(`scripts/validate_normalization.py`, `scripts/cross_check_v2.py`)이 합니다. 같은 LLM이 자기 출력을 검증하면 같은 오류를 재생산할 수 있어서 분리합니다.

</details>

<details>
<summary><b>아키텍처 구성 (펼쳐서 보기)</b></summary>

### 디렉토리 트리

```
.claude/skills/
├── vizabridge-normalize/
│   ├── SKILL.md                    # 절차서 (v2)
│   ├── references/
│   │   ├── column_schema.md        # v2 32컬럼 정의
│   │   ├── extraction_rules.md     # Korean admin term → CSV 컬럼 매핑
│   │   ├── noise_rules.md          # 표지/목차/양식 노이즈 필터
│   │   └── output_format.md        # 정규화 MD 형식 명세
│   └── scripts/
│       ├── show_progress.py        # 다음 미처리 청크 + drift 보고
│       └── append_block.py         # 스키마 + hash 검증 + 원자적 append
└── vizabridge-repair/
    ├── SKILL.md
    └── scripts/
        ├── show_flagged.py         # validator 이슈 청크 목록
        └── replace_block.py        # 기존 블록을 원자적 교체
```

### 데이터 흐름 (skill 관점)

```
data/parsed/chunks/{m}_chunks_index.jsonl  (Python이 만든 입력)
        │
        ▼
   /vizabridge-normalize  ──┐
        │                   │ (모델이 references 읽고 청크 처리)
        ▼                   │
data/parsed/normalized/{m}_manual.md  (skill의 출력)
        │
        │   scripts/validate_normalization.py  (결정적 검증)
        ▼
data/parsed/validation/{m}_validation.json
        │
        │   issue 있을 시 → /vizabridge-repair  ──→ normalized MD 갱신
        ▼
   scripts/build_semantic_csv.py  (결정적 v2 빌드)
        │
        ▼
data/processed/{체류,사증}매뉴얼_검수용_v2.csv  (32컬럼)
        │
        ▼
   scripts/notion_export_v2.py / qc_v2.py / cross_check_v2.py
```

### 헬퍼 스크립트 책임 분담

| 스크립트 | 입력 | 출력 | 무엇을 보장하는가 |
| --- | --- | --- | --- |
| `schema.py` | (모듈) | `COLUMNS`, `PETITION_TYPES`, `validate_row()` | 32컬럼 + enum의 단일 진실 원천 |
| `show_progress.py` | chunk index + normalized MD | stdout (다음 chunk_id, 누적 통계) | 진행률 명시화 |
| `append_block.py` | manual_key + chunk_id + block 파일 | normalized MD (append) | 마커 형식·hash·필수 필드 검증, atomic write |
| `replace_block.py` | manual_key + chunk_id + 신규 block | normalized MD (in-place replace) | hash drift 거부, atomic write |
| `show_flagged.py` | validator JSON | stdout (수리 대상 청크 목록) | 우선순위 정렬 |
| `build_semantic_csv.py` | normalized MD | v2 CSV (32컬럼) | 신청종류별 행 펼침, 빈 셀 정규화, enum 강제 |
| `notion_export_v2.py` | v2 CSV | Notion import 친화 CSV | 컬럼은 동일, 셀 가공 |
| `qc_v2.py` / `cross_check_v2.py` | v2 CSV + normalized MD | 품질 리포트 | fill rate, 원문발췌 ↔ 라인범위 일치 |

### 왜 skill + Python 하이브리드인가

| 작업 | 누가 | 왜 |
| --- | --- | --- |
| 청크 분할 (`<table>` 경계) | Python | 결정적, regex로 충분 |
| 의미 추출 (한국 행정 자연어 → 32컬럼) | skill (LLM) | 정규식으로 다 표현하기 어려운 매핑 |
| 행 단위 정합성 검증 (visa code/금액/서류명) | Python | 결정적 ground truth 비교. LLM이 자기 출력을 검증하면 같은 오류 재생산 |
| CSV 빌드 (정규화 MD → CSV) | Python | 결정적, 단순 파싱. 스키마 강제 |
| 품질 리포트 | Python | 통계·임계값 비교 |

### 캐싱 (정규화 MD 커밋)

`data/parsed/normalized/` 는 `.gitignore` 예외로 커밋 대상입니다. 이 디렉토리가 곧 LLM 단계의 출력 캐시 역할을 하기 때문에, fresh clone에서 `scripts/build_semantic_csv.py`만 실행해도 결정적으로 동일한 v2 CSV가 재생성됩니다. skill을 다시 돌릴 필요는 입력(HWP, kordoc 출력, chunk index) 자체가 바뀐 경우뿐입니다.

</details>

## What To Edit

- 매뉴얼이 새로 나오면: `data/raw/`의 HWP를 교체하고 Stage 1부터 다시.
- 컬럼 스키마를 바꾸려면: **반드시 [scripts/schema.py](scripts/schema.py)에서만 수정** 후 [docs/data_schema_v2.md](docs/data_schema_v2.md)와 [.claude/skills/vizabridge-normalize/references/column_schema.md](.claude/skills/vizabridge-normalize/references/column_schema.md)를 동기화.
- 정규화 규칙을 손보려면: `.claude/skills/vizabridge-normalize/references/*.md` 수정.
- 검수 임계값을 바꾸려면: `scripts/qc_v2.py` 수정.

## Design Rationale

설계 결정 배경은 [docs/pipeline_strategy.md](docs/pipeline_strategy.md), 전체 사양서는 [docs/superpowers/specs/2026-05-14-hwp-kordoc-llm-pipeline-design.md](docs/superpowers/specs/2026-05-14-hwp-kordoc-llm-pipeline-design.md), 스키마 v2 사양은 [docs/data_schema_v2.md](docs/data_schema_v2.md)에 있습니다.

핵심 요약:
- **HWP/kordoc**: PDF/LlamaParse OCR가 한글·표 구조를 망쳤음. HWP는 원본 디지털 포맷이라 손실이 없음.
- **정규화 MD 중간 표현**: LLM은 의미 분류만 담당. 그 결과를 결정적 Python이 CSV로 변환. 할루시네이션을 별도 layer에서 잡고 (Stage 4 validator), 수정도 일관된 흐름으로 (Stage 5 repair).
- **v2 32컬럼 + 행 단위 (비자×신청)**: 한 비자코드가 사증발급/체류자격 변경/기간 연장별로 5~10행에 분산되어, 셀당 평균 길이가 작아지고 검수·임포트·후속 RAG 청킹이 모두 깔끔해짐.
- **Claude Code 스킬**: 별도 API 결제 없이 동일한 Claude 모델로 처리. 재현성은 정규화 MD 커밋으로 확보.
