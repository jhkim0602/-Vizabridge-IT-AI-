# Vizabridge Visa RAG

대한민국 비자/체류 매뉴얼 PDF를 LlamaParse로 파싱하고, 최종 semantic CSV 데이터셋으로 정리하기 위한 작업 공간입니다.

## Folder Structure

```text
.
├── data/
│   ├── raw/          # 원본 PDF 보관
│   ├── parsed/       # LlamaParse 원문 파싱 결과
│   └── processed/    # 최종 semantic CSV 산출물
├── docs/             # 데이터 설계, 컬럼 정의, 운영 메모
├── notebooks/        # 실행용 Jupyter notebooks
├── scripts/          # 반복 실행용 Python scripts
├── .env              # 로컬 API 키, git 제외
├── .env.example      # 환경변수 예시
└── requirements.txt
```

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

1. [notebooks/01_setup_llamaparse_api_key.ipynb](notebooks/01_setup_llamaparse_api_key.ipynb)에서 API 키 로딩을 확인합니다.
2. `data/parsed/`의 LlamaParse Markdown 결과를 확인합니다.
3. `scripts/build_semantic_manual_csvs.py`로 최종 semantic CSV 2개를 생성합니다.

```bash
.venv/bin/python scripts/build_semantic_manual_csvs.py
```

완성 CSV는 아래 두 개만 유지합니다.

- `data/processed/stay_manual_semantic_clean.csv`
- `data/processed/visa_manual_semantic_clean.csv`

최종 CSV에는 PDF 페이지 번호, 원문 근거, raw text, review/debug 컬럼을 포함하지 않습니다.

파이프라인 설계 판단은 [docs/pipeline_strategy.md](docs/pipeline_strategy.md)에 정리되어 있습니다.
