# Data

`data/`는 PDF가 최종 CSV가 되기까지 거치는 단계별 보관소입니다.

## `raw/`

원본 PDF를 보관합니다.

- 직접 수정하지 않습니다.
- 새 매뉴얼이 나오면 기존 파일을 덮어쓸지, 새 파일명으로 둘지 먼저 정합니다.
- 현재 기준 원본은 체류민원 PDF와 사증민원 PDF입니다.

## `parsed/`

LlamaParse가 PDF를 Markdown으로 변환한 결과입니다.

- 사람이 검토할 수 있는 중간 산출물입니다.
- 최종 CSV 생성 스크립트는 여기의 최신 `agentic_plus` Markdown을 읽습니다.
- 파싱 결과가 크게 깨진 경우에만 다시 생성합니다.

## `processed/`

반복 생성 가능한 최종 CSV를 보관합니다. 사람이 직접 한 줄씩 수정하지 않고, `scripts/`의 생성 스크립트로 다시 만듭니다.

Semantic clean CSV는 PDF 매뉴얼의 행정 의미를 정리한 기본 데이터입니다.

- `stay_manual_semantic_clean.csv`
- `visa_manual_semantic_clean.csv`

Chatbot-ready CSV는 사용자가 코드를 몰라도 자기 상황으로 검색할 수 있게 semantic clean CSV에서 파생한 데이터입니다.

- `stay_manual_chatbot_ready.csv`
- `visa_manual_chatbot_ready.csv`
- `chatbot_intent_routes.csv`

`chatbot_intent_routes.csv`는 "결혼비자", "유학생 알바", "외국인 직원 채용" 같은 질문을 어떤 코드군/민원유형으로 먼저 보낼지 정리한 작은 라우팅 색인입니다.

이 폴더에는 검수용 CSV, 임시 CSV, debug 파일을 두지 않습니다. 검수 산출물은 `output/quality/`와 `output/review/`에 생성합니다.
