# Vizabridge Visa RAG

대한민국 비자 매뉴얼 PDF를 LlamaParse로 파싱하고, RAG 임베딩 전 단계의 CSV 데이터셋으로 정리하기 위한 작업 공간입니다.

## Folder Structure

```text
.
├── data/
│   ├── raw/          # 원본 PDF 보관
│   ├── parsed/       # LlamaParse 원문 파싱 결과
│   └── processed/    # RAG 임베딩 전 CSV/JSONL 산출물
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

API 키 확인은 [notebooks/01_setup_llamaparse_api_key.ipynb](notebooks/01_setup_llamaparse_api_key.ipynb)에서 실행합니다.
