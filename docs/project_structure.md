# Project Structure Guide

이 문서는 비전공자가 저장소를 열었을 때 "어디에 무엇이 있고, 무엇을 실행해야 하며, 무엇을 건드리면 위험한지"를 빠르게 판단할 수 있게 만든 운영 가이드입니다.

## One-Line Summary

이 프로젝트는 출입국/비자 PDF 매뉴얼을 그대로 베끼는 작업이 아니라, PDF 속 행정 정보를 체류자격/사증코드, 민원유형, 대상, 요건, 제출서류, 제한, 예외, 수수료 같은 의미 단위로 정리하는 데이터 전처리 파이프라인입니다.

## Folder Map

```text
Vizabridge/
├── data/
│   ├── raw/
│   ├── parsed/
│   └── processed/
├── docs/
├── notebooks/
├── scripts/
├── tests/
├── output/
├── requirements.txt
└── README.md
```

## `data/`

데이터가 단계별로 지나가는 공간입니다.

| Folder | 역할 | 직접 수정 여부 |
| --- | --- | --- |
| `data/raw/` | 원본 PDF 보관소 | 원본 교체 외에는 수정하지 않음 |
| `data/parsed/` | LlamaParse가 PDF를 Markdown으로 바꾼 결과 | 보통 직접 수정하지 않음 |
| `data/processed/` | 최종 clean CSV 산출물 | 스크립트로만 재생성 |

`data/processed/`에는 최종 파일 두 개만 유지합니다.

- `stay_manual_semantic_clean.csv`
- `visa_manual_semantic_clean.csv`

이 두 CSV에는 검수용 컬럼, PDF 페이지 번호, 원문 근거, raw text를 넣지 않습니다. 최종 CSV는 downstream RAG 또는 서비스 데이터의 입력이므로 최대한 깨끗하게 유지합니다.

## `scripts/`

반복 실행하는 핵심 코드입니다.

| Script | 역할 |
| --- | --- |
| `build_semantic_manual_csvs.py` | parsed Markdown을 읽어 최종 CSV 2개를 만듭니다. |
| `quality_report_semantic_manual_csvs.py` | 최종 CSV를 점검하고 검수용 Excel/리포트를 만듭니다. |

실행 순서는 항상 다음과 같습니다.

```bash
.venv/bin/python scripts/build_semantic_manual_csvs.py
.venv/bin/python scripts/quality_report_semantic_manual_csvs.py
```

정제 규칙을 고칠 때는 테스트를 먼저 추가한 뒤 스크립트를 수정합니다.

## `output/`

검수와 분석을 위한 재생성 산출물이 생기는 곳입니다. Git에는 올리지 않습니다.

| Folder | 내용 |
| --- | --- |
| `output/quality/` | 품질 요약 CSV, 검수 후보 CSV, Markdown 리포트 |
| `output/review/` | 사람이 필터링하면서 볼 수 있는 Excel 파일 |

주요 파일:

- `output/quality/semantic_manual_quality_report.md`
- `output/review/stay_manual_review.xlsx`
- `output/review/visa_manual_review.xlsx`

검수 Excel의 `all_rows_with_flags` 시트는 전체 행을 보여주고, 앞쪽에 `needs_review`, `review_priority`, `review_reason`, `suggested_action`을 붙입니다.

## `notebooks/`

분석과 확인용입니다. 운영 파이프라인의 주 실행 경로는 `scripts/`이고, 노트북은 결과를 눈으로 확인하는 도구입니다.

| Notebook | 역할 |
| --- | --- |
| `01_setup_llamaparse_api_key.ipynb` | API 키 로딩 확인 |
| `02_parse_pdfs_with_llamaparse.ipynb` | PDF를 Markdown으로 파싱 |
| `03_review_semantic_manual_csvs.ipynb` | 최종 CSV 분포, 누락률, 검수 후보 확인 |

## `docs/`

프로젝트 판단 기준을 설명합니다.

| Document | 내용 |
| --- | --- |
| `data_columns.md` | 최종 CSV 컬럼 정의 |
| `data_preprocessing_runbook.md` | 재생성/검수 실행 절차 |
| `pipeline_strategy.md` | 왜 이런 파이프라인을 선택했는지 |
| `project_structure.md` | 폴더 구조와 운영 방식 |

## `tests/`

정제 규칙이 실수로 깨지지 않게 막는 안전장치입니다.

예를 들어 다음을 확인합니다.

- 최종 CSV에 페이지 번호/raw/evidence/review 컬럼이 들어가지 않는지
- 목차, 표지, 빈 양식, 깨진 표 조각이 제거되는지
- 검수 후보 탐지 규칙이 정상 동작하는지

실행:

```bash
.venv/bin/python -m pytest tests -q
```

## Maintenance Checklist

PDF 또는 정제 규칙을 바꾼 뒤에는 항상 아래 순서로 확인합니다.

1. 테스트 실행
2. 최종 CSV 재생성
3. 품질 리포트/검수 Excel 재생성
4. 노트북 전체 실행
5. `output/quality/semantic_manual_quality_report.md`에서 검수 후보 수 확인

명령:

```bash
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/build_semantic_manual_csvs.py
.venv/bin/python scripts/quality_report_semantic_manual_csvs.py
.venv/bin/jupyter nbconvert --to notebook --execute notebooks/03_review_semantic_manual_csvs.ipynb --output /tmp/semantic_review_executed.ipynb --ExecutePreprocessor.timeout=180
```

## Practical Rule

최종 CSV를 직접 손으로 수정하지 않습니다. 문제가 보이면 원인은 보통 세 곳 중 하나입니다.

- PDF 파싱 결과가 깨진 경우: `data/parsed/` 확인
- 의미 분류 규칙이 부족한 경우: `build_semantic_manual_csvs.py` 수정
- 검수 후보 기준이 과하거나 약한 경우: `quality_report_semantic_manual_csvs.py` 수정

이렇게 해야 같은 PDF를 다시 처리해도 같은 품질의 CSV를 재현할 수 있습니다.
