# Vizabridge Visa RAG

대한민국 비자/체류 매뉴얼 PDF를 LlamaParse로 파싱하고, 최종 semantic CSV 데이터셋으로 정리하기 위한 작업 공간입니다.

이 저장소의 핵심 목표는 PDF를 단순히 표 형태로 옮기는 것이 아니라, 행정 매뉴얼의 의미 구조를 이해하기 쉬운 데이터로 바꾸는 것입니다. 최종 CSV는 체류자격/사증코드, 민원유형, 대상, 요건, 제출서류, 제한, 예외, 수수료, 점수표, 쿼터 같은 행정 단위로 정리합니다.

## Folder Structure

```text
.
├── data/
│   ├── raw/          # 사람이 받은 원본 PDF. 직접 수정하지 않음
│   ├── parsed/       # LlamaParse가 PDF를 Markdown으로 풀어낸 결과
│   └── processed/    # 최종 clean CSV 2개만 유지
├── docs/             # 왜 이런 구조로 만들었는지 설명하는 문서
├── notebooks/        # CSV를 눈으로 확인하고 시각화하는 분석 노트북
├── scripts/          # 반복 실행 가능한 파이프라인 코드
├── tests/            # 정제 규칙이 깨지지 않도록 확인하는 테스트
├── output/           # 품질 리포트/검수 Excel 같은 재생성 산출물, git 제외
├── .env              # 로컬 API 키, git 제외
└── requirements.txt  # 실행에 필요한 Python 패키지
```

더 자세한 폴더별 관리 기준은 [docs/project_structure.md](docs/project_structure.md)에 정리되어 있습니다.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`.env` 파일에는 실제 LlamaCloud API 키를 저장합니다.

```bash
LLAMA_CLOUD_API_KEY=llx-...
```

## Workflow

1. 원본 PDF는 `data/raw/`에 보관합니다.
2. [notebooks/01_setup_llamaparse_api_key.ipynb](notebooks/01_setup_llamaparse_api_key.ipynb)에서 API 키 로딩을 확인합니다.
3. [notebooks/02_parse_pdfs_with_llamaparse.ipynb](notebooks/02_parse_pdfs_with_llamaparse.ipynb)로 PDF를 Markdown으로 파싱합니다.
4. `scripts/build_semantic_manual_csvs.py`로 최종 semantic CSV 2개를 생성합니다.
5. `scripts/quality_report_semantic_manual_csvs.py`로 자동 품질검사와 검수용 Excel을 생성합니다.
6. [notebooks/03_review_semantic_manual_csvs.ipynb](notebooks/03_review_semantic_manual_csvs.ipynb)에서 분포, 누락률, 검수 후보를 확인합니다.

```bash
.venv/bin/python scripts/build_semantic_manual_csvs.py
.venv/bin/python scripts/quality_report_semantic_manual_csvs.py
```

완성 CSV는 아래 두 개만 유지합니다.

- `data/processed/stay_manual_semantic_clean.csv`
- `data/processed/visa_manual_semantic_clean.csv`

최종 CSV에는 PDF 페이지 번호, 원문 근거, raw text, review/debug 컬럼을 포함하지 않습니다.

검수용 산출물은 `output/quality/`와 `output/review/` 아래에 생성합니다. 최종 CSV는 깨끗하게 유지하고, 검수 플래그와 수정 우선순위는 별도 Excel에서 확인합니다.

## What To Edit

- PDF가 바뀌면 `data/raw/`와 `data/parsed/`를 갱신한 뒤 빌드 명령을 다시 실행합니다.
- 컬럼 정의를 바꾸려면 [docs/data_columns.md](docs/data_columns.md)와 `scripts/build_semantic_manual_csvs.py`의 `STAY_COLUMNS`, `VISA_COLUMNS`를 함께 수정합니다.
- 목차, 표지, 빈 양식, 깨진 표 조각이 남으면 `is_noise_row()` 또는 `is_low_value_semantic_row()`에 규칙을 추가합니다.
- 검수 후보 기준을 바꾸려면 `scripts/quality_report_semantic_manual_csvs.py`의 `row_issues()`를 수정합니다.

파이프라인 설계 판단은 [docs/pipeline_strategy.md](docs/pipeline_strategy.md)에 정리되어 있습니다.
