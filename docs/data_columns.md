# Final Semantic CSV Columns

최종 산출물은 PDF당 하나씩만 유지합니다.

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
