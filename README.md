# Vizabridge Visa RAG

대한민국 비자/체류 매뉴얼 **HWP** 원본을 [kordoc](https://github.com/chrisryugj/kordoc)으로 Markdown으로 변환한 뒤, **Claude Code 스킬**로 의미 단위 정규화 → **결정적 Python**으로 RAG/챗봇용 CSV를 생성하는 데이터 전처리 파이프라인입니다.

이 저장소의 핵심 목표는 PDF를 단순히 표 형태로 옮기는 것이 아니라, 행정 매뉴얼의 의미 구조를 이해하기 쉬운 데이터로 바꾸는 것입니다. 최종 CSV는 체류자격/사증코드, 민원유형, 대상, 요건, 제출서류, 제한, 예외, 수수료, 점수표, 쿼터 같은 행정 단위로 정리합니다.

사용자는 보통 `E-7`, `F-6`, `D-2` 같은 코드를 모른 채 "한국인 배우자와 결혼했다", "유학생인데 아르바이트를 하고 싶다", "외국인 직원을 채용하고 싶다"처럼 자기 상황을 말합니다. 그래서 챗봇용 CSV에는 상황 태그, 자연어 검색 키워드, 되물어야 할 정보, 라우팅 힌트를 추가합니다.

## Pipeline

```
data/raw/*.hwp                                            (source of truth)
   │  Stage 1  scripts/parse_hwp_to_markdown.py           (Python, kordoc)
   ▼
data/parsed/raw/{stay,visa}_manual.md
   │  Stage 2  scripts/index_markdown_chunks.py           (Python, deterministic)
   ▼
data/parsed/chunks/{stay,visa}_chunks_index.jsonl
   │  Stage 3  /vizabridge-normalize                      (Claude Code skill)
   ▼
data/parsed/normalized/{stay,visa}_manual.md              ← canonical intermediate
   │  Stage 4  scripts/validate_normalization.py          (Python, deterministic)
   │  Stage 5  /vizabridge-repair                         (Claude Code skill, optional)
   │  Stage 6  scripts/build_semantic_csv.py              (Python, deterministic)
   ▼
data/processed/{stay,visa}_manual_semantic_clean.csv
   │  Stage 7  /vizabridge-enrich-chatbot                 (Claude Code skill)
   ▼
data/parsed/normalized_chatbot/{stay,visa}_manual.md
   │  Stage 8  scripts/build_chatbot_csv.py               (Python, deterministic)
   ▼
data/processed/{stay,visa}_manual_chatbot_ready.csv
   │  Stage 9  scripts/quality_report_semantic_manual_csvs.py
   ▼
output/quality/*, output/review/*
```

LLM은 stages 3, 5, 7 에서만 사용합니다. 나머지 6단계는 결정적 Python으로, 다시 실행해도 같은 결과가 나옵니다. **정규화 MD**(stages 3 / 7 산출물)는 의도적으로 git에 커밋합니다 — 같은 입력에서 같은 CSV가 재생성되도록.

## Folder Structure

```text
.
├── data/
│   ├── raw/                  # 원본 HWP (원본 교체 외 수정하지 않음)
│   │   └── legacy_pdf/       # 과거 PDF 백업
│   ├── parsed/
│   │   ├── raw/              # kordoc 출력 (.gitignored, 재생성 가능)
│   │   ├── chunks/           # 청크 인덱스 .jsonl (커밋)
│   │   ├── normalized/       # 정규화 MD — LLM 결과 (커밋)
│   │   ├── normalized_chatbot/  # 챗봇 정규화 MD (커밋)
│   │   └── validation/       # validator 산출 .json (커밋)
│   └── processed/            # 최종 CSV (.gitignored, 재생성 가능)
├── scripts/                  # 결정적 단계 Python
│   └── legacy/               # 과거 정규식 빌더 (quality_report에서 상수 재사용)
├── .claude/skills/
│   ├── vizabridge-normalize/
│   ├── vizabridge-enrich-chatbot/
│   └── vizabridge-repair/
├── notebooks/                # 분석 노트북
├── docs/                     # 설계/운영 문서
├── tests/                    # 정제 규칙 보호 테스트
├── output/                   # 검수 리포트/Excel (.gitignored)
└── requirements.txt
```

자세한 폴더별 관리 기준은 [docs/project_structure.md](docs/project_structure.md), 단계별 명령은 [scripts/README.md](scripts/README.md)에 있습니다.

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

# 3) Claude Code 세션에서 정규화
#    /vizabridge-normalize stay
#    /vizabridge-normalize visa
#    (세션 한도 닿으면 다음 세션에서 재개)

# 4) 결정적 검증
python scripts/validate_normalization.py

# 5) 필요 시 Claude Code 세션에서 수리
#    /vizabridge-repair stay
#    /vizabridge-repair visa
python scripts/validate_normalization.py   # 재검증

# 6) semantic CSV 빌드
python scripts/build_semantic_csv.py

# 7) Claude Code 세션에서 챗봇 풍부화
#    /vizabridge-enrich-chatbot stay
#    /vizabridge-enrich-chatbot visa

# 8) chatbot CSV 빌드
python scripts/build_chatbot_csv.py

# 9) 품질 리포트 + 검수용 Excel
python scripts/quality_report_semantic_manual_csvs.py
```

## 파이프라인 단계별 시각화

전체 9 단계의 산출물(청크, 정규화 MD, semantic/chatbot CSV, 품질 리포트)을 pandas + plotly로 한눈에 검토할 수 있는 노트북이 있습니다.

```bash
.venv/bin/jupyter notebook notebooks/04_pipeline_stages_visualization.ipynb
```

각 단계마다:
- 청크 크기 분포, 비자코드 종류 분포
- 정규화 행 수, validator 이슈 빈도
- semantic CSV의 비자코드별/민원유형별 분포, 컬럼 누락률 히트맵
- chatbot CSV의 상황 태그·키워드·라우팅 힌트 빈도
- 품질 리포트의 검수 후보 목록

노트북은 실행본을 커밋해 두어 GitHub에서도 시각화를 그대로 볼 수 있습니다.

## What To Edit

- 매뉴얼이 새로 나오면: `data/raw/`의 HWP를 교체하고 Stage 1부터 다시.
- 컬럼 스키마를 바꾸려면: [docs/data_columns.md](docs/data_columns.md), [.claude/skills/vizabridge-normalize/references/column_schema.md](.claude/skills/vizabridge-normalize/references/column_schema.md), `scripts/build_semantic_csv.py`의 `STAY_COLUMNS`/`VISA_COLUMNS`를 함께 수정.
- 정규화 규칙을 손보려면: `.claude/skills/vizabridge-normalize/references/*.md` 수정.
- 챗봇 상황 태그/키워드 규칙을 손보려면: `.claude/skills/vizabridge-enrich-chatbot/references/*.md` 수정.
- 검수 임계값을 바꾸려면: `scripts/quality_report_semantic_manual_csvs.py`의 `row_issues()` 수정.

## Design Rationale

설계 결정 배경은 [docs/pipeline_strategy.md](docs/pipeline_strategy.md), 전체 사양서는 [docs/superpowers/specs/2026-05-14-hwp-kordoc-llm-pipeline-design.md](docs/superpowers/specs/2026-05-14-hwp-kordoc-llm-pipeline-design.md)에 있습니다.

핵심 요약:
- **HWP/kordoc**: PDF/LlamaParse OCR가 한글·표 구조를 망쳤음. HWP는 원본 디지털 포맷이라 손실이 없음.
- **정규화 MD 중간 표현**: LLM은 의미 분류만 담당. 그 결과를 결정적 Python이 CSV로 변환. 할루시네이션을 별도 layer에서 잡고 (Stage 4 validator), 수정도 일관된 흐름으로 (Stage 5 repair).
- **Claude Code 스킬**: 별도 API 결제 없이 동일한 Claude 모델로 처리. 재현성은 정규화 MD 커밋으로 확보.
