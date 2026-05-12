# Visa RAG Data Columns

비자 챗봇은 사용자가 비자코드를 모르는 상태에서 질문하는 경우가 많습니다. 따라서 CSV는 단순히 비자코드별 문단을 저장하는 구조보다, 사용자 의도와 상황을 함께 검색할 수 있는 구조로 설계합니다.

## Initial Column Plan

| Column | Purpose |
| --- | --- |
| `source_pdf` | 원본 PDF 파일명 |
| `manual_type` | 사증민원 또는 체류민원 |
| `page_start` | 근거 시작 페이지 |
| `page_end` | 근거 종료 페이지 |
| `visa_code` | A-1, D-8, E-7 등 명시 코드. 없으면 빈 값 |
| `visa_name_ko` | 비자 또는 체류자격 한글명 |
| `section_title` | 원문 섹션 제목 |
| `user_intent` | 퇴사, 법인설립, 초청, 연장, 변경, 서류문의 등 고객 질문 의도 |
| `applicant_context` | 신청자 상황: 외국인 근로자, 투자자, 가족, 유학생 등 |
| `question_examples` | 고객이 실제로 물을 법한 질문 예시 |
| `requirements` | 필요 서류 또는 요건 |
| `procedure` | 신청 절차 |
| `restrictions` | 제한, 예외, 주의사항 |
| `raw_text` | LlamaParse로 추출한 원문 |
| `normalized_text` | 임베딩에 사용할 정제 텍스트 |
| `evidence_quote` | 답변 근거로 보여줄 짧은 원문 |

