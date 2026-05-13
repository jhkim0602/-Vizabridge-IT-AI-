# Final Semantic CSV Columns

기본 semantic 산출물은 PDF당 하나씩 유지합니다.

- `data/processed/stay_manual_semantic_clean.csv`
- `data/processed/visa_manual_semantic_clean.csv`

최종 CSV에는 PDF 페이지 번호, 원문 근거, raw text, review/debug 컬럼을 넣지 않습니다.

## 공통 컬럼

| Column | 설명 |
| --- | --- |
| `manual_type` | `체류민원` 또는 `사증민원` |
| `source_pdf` | 원본 PDF 파일명 |
| `item_type` | `common_rule`, `stay_status_rule`, `visa_rule`, `required_documents`, `fee`, `score_table`, `quota`, `restriction`, `exception` 등 |
| `section_title` | 정제된 섹션 제목 |
| `subtype_or_program` | `E-7-4`, `지역특화형`, `복수사증`, `사증발급인정서` 같은 세부 제도 |
| `petition_type` | 체류자격 변경, 체류기간 연장, 사증발급, 사증발급인정서 등 민원 유형 |
| `subsection_type` | 대상, 요건, 제출서류, 절차, 제한, 예외, 수수료, 점수표, 쿼터 등 |
| `applicant_context` | 신청자 상황 또는 적용 맥락 |
| `eligibility` | 대상/자격 조건 |
| `target_persons` | 해당자 또는 발급 대상 |
| `common_documents` | 공통 제출서류 |
| `mandatory_documents` | 필수 제출서류 |
| `other_documents` | 추가/해당자별/심사용 서류 |
| `requirements` | 심사요건, 자격요건 |
| `procedure` | 신청 절차 |
| `restrictions` | 제한사항, 불허 사유 |
| `exceptions` | 예외, 특례, 면제 |
| `fees` | 수수료 |
| `duration_or_validity` | 체류기간, 유효기간, 단수/복수 정보 |
| `quota_or_limit` | 쿼터, 선발인원, 허용인원, 상한 |
| `score_criteria` | 점수표, 배점 기준 |
| `table_summary` | 표의 주제 |
| `table_rows` | 정제된 주요 표 행 |
| `normalized_text` | 검색/검수에 쓰는 정제 텍스트 |

## 체류민원 전용 컬럼

| Column | 설명 |
| --- | --- |
| `stay_status_code` | D-2, E-7, F-2-R 등 체류자격 코드 |
| `stay_status_name_ko` | 유학, 특정활동, 거주 등 체류자격명 |
| `obligations` | 신고의무, 교육의무, 거주의무 등 |

## 사증민원 전용 컬럼

| Column | 설명 |
| --- | --- |
| `visa_code` | C-3, D-8, E-7, F-6 등 사증 코드 |
| `visa_name_ko` | 단기방문, 기업투자, 특정활동, 결혼이민 등 사증명 |
| `inviter_context` | 초청인, 고용주, 유치기관 등 초청자 맥락 |
| `recommendation_or_approval` | 고용추천서, 관계기관 승인, 추천기관 등 |

## Chatbot-Ready CSV Columns

챗봇용 CSV는 semantic clean CSV를 입력으로 다시 만든 파생 데이터입니다.

- `data/processed/stay_manual_chatbot_ready.csv`
- `data/processed/visa_manual_chatbot_ready.csv`

사용자가 코드를 모르는 상태에서 자기 상황을 말해도 관련 행을 찾기 쉽도록 아래 필드를 추가합니다.

| Column | 설명 |
| --- | --- |
| `record_id` | 챗봇용 행 식별자 |
| `source_dataset` | 입력으로 사용한 semantic clean CSV |
| `code_type` | `stay_status` 또는 `visa` |
| `primary_code` | 체류자격/사증 코드 |
| `primary_name_ko` | 코드의 한국어 이름 |
| `source_section_title` | semantic CSV의 원래 섹션 제목 |
| `user_situation_tags` | 결혼/배우자, 유학/연수, 취업/고용, 창업/투자 등 사용자 상황 태그 |
| `intent_keywords` | 사용자가 실제로 입력할 만한 자연어 검색어 |
| `applicant_profile` | 외국인 본인, 유학생/연수생, 초청인/고용주, 배우자/가족 등 |
| `current_location_context` | 입국 전 비자 신청인지, 국내 체류 중 민원인지 |
| `current_status_context` | 현재 체류자격 또는 현재 상태 확인 힌트 |
| `plain_language_summary` | 일반 사용자가 읽기 쉬운 한 줄 요약 |
| `required_user_info` | 챗봇이 답변 전 추가로 물어봐야 할 정보 |
| `routing_hint` | 사증민원/체류민원/민원유형으로 보내는 힌트 |
| `answer_focus` | 제출서류, 제한사항, 점수표, 쿼터 등 답변 초점 |
| `search_text` | 검색/RAG 색인에 넣기 좋은 통합 텍스트 |

## Intent Route CSV

`data/processed/chatbot_intent_routes.csv`는 행 단위 검색 전에 쓰는 작은 라우팅 색인입니다.

| Column | 설명 |
| --- | --- |
| `route_id` | 라우팅 규칙 식별자 |
| `user_intent` | 사용자의 실제 목적 |
| `example_questions` | 대표 질문 예시 |
| `situation_tags` | 관련 상황 태그 |
| `target_manuals` | 우선 조회할 매뉴얼 |
| `likely_codes` | 우선 후보 코드 |
| `likely_petition_types` | 우선 후보 민원유형 |
| `primary_filters` | chatbot-ready CSV에서 먼저 적용할 필터 |
| `required_user_info` | 챗봇이 되물을 정보 |
| `answer_strategy` | 답변 구성 순서 |
| `search_boost_terms` | 검색 가중치로 쓸 키워드 |
