# Scripts

반복 실행이 필요한 정제 및 CSV 생성 코드를 이 폴더에 둡니다.

원칙은 단순합니다. 노트북은 사람이 확인하기 위한 도구이고, 실제 반복 실행 기준은 이 폴더의 Python 스크립트입니다.

## 최종 CSV 생성

`data/parsed/`의 LlamaParse Markdown을 읽어 PDF당 최종 semantic CSV 하나씩 생성합니다.

```bash
.venv/bin/python scripts/build_semantic_manual_csvs.py
```

산출물:

- `data/processed/stay_manual_semantic_clean.csv`
- `data/processed/visa_manual_semantic_clean.csv`

최종 CSV에는 PDF 페이지 번호, 원문 근거, raw text, review/debug 컬럼을 포함하지 않습니다.

이 스크립트가 하는 일:

- Markdown heading/table/list를 의미 블록으로 나눕니다.
- 체류자격/사증코드를 찾아 현재 블록에 연결합니다.
- 민원유형과 하위 항목을 분류합니다.
- 제출서류를 공통/필수/기타서류로 나눕니다.
- 표지, 목차, 빈 양식 제목, 깨진 표 헤더 조각을 제거합니다.

## 챗봇용 CSV 생성

semantic clean CSV를 읽어 사용자의 실제 질문 상황과 연결하기 쉬운 CSV를 만듭니다.

```bash
.venv/bin/python scripts/build_chatbot_ready_manual_csvs.py
```

산출물:

- `data/processed/stay_manual_chatbot_ready.csv`
- `data/processed/visa_manual_chatbot_ready.csv`
- `data/processed/chatbot_intent_routes.csv`

이 스크립트가 추가하는 것:

- `user_situation_tags`: 결혼/배우자, 유학/연수, 취업/고용, 창업/투자 같은 사용자 상황 태그
- `intent_keywords`: 사용자가 실제로 입력할 만한 자연어 검색어
- `plain_language_summary`: 일반 사용자가 읽기 쉬운 한 줄 요약
- `required_user_info`: 챗봇이 추가로 물어봐야 할 정보
- `routing_hint`: 사증민원/체류민원/민원유형으로 보내는 힌트
- `search_text`: 벡터 검색 또는 키워드 검색에 넣기 좋은 통합 텍스트

`chatbot_intent_routes.csv`는 행 단위 검색 전에 사용할 상위 라우팅 색인입니다. 예를 들어 "유학생인데 알바 가능한가요?"는 `D-2/D-4`와 `체류자격외 활동허가` 쪽으로 먼저 좁힙니다.

## 품질검사 및 검수용 산출물 생성

최종 semantic CSV를 읽어 자동 품질검사 리포트와 사람이 검수하기 쉬운 Excel 파일을 생성합니다.

```bash
.venv/bin/python scripts/quality_report_semantic_manual_csvs.py
```

산출물:

- `output/quality/semantic_manual_quality_report.md`
- `output/quality/*_manual_quality_summary.csv`
- `output/quality/*_manual_field_fill_rates.csv`
- `output/quality/*_manual_review_candidates.csv`
- `output/review/stay_manual_review.xlsx`
- `output/review/visa_manual_review.xlsx`

`data/processed/`의 최종 CSV에는 review/debug 컬럼을 넣지 않고, 검수용 플래그는 `output/review/`의 Excel에만 둡니다.

검수 후보가 남아 있으면 먼저 Excel에서 실제 행을 확인합니다. 실제 노이즈라면 `build_semantic_manual_csvs.py`의 제거 규칙을 고치고, 검수 규칙이 과민한 것이라면 `quality_report_semantic_manual_csvs.py`의 검사 기준을 고칩니다.
