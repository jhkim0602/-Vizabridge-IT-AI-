<!-- vizabridge-chatbot v1 source_row: stay-00000-공통 source_hash: 653b9126ca78bfc5 -->

### chatbot stay-00000-공통
- record_id: stay-00000-공통
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: 공통
- primary_name_ko: 공통사항
- source_section_title: 공통사항: 각종 체류허가 등에 관한 심사수수료
- user_situation_tags: |
    - 공통사항
- intent_keywords: |
    - 체류 신청 수수료 얼마
    - F-6 결혼이민 비자 수수료
    - 영주권 신청 비용
    - 체류 자격 변경 비용
    - 외국인등록증 발급 비용
- applicant_profile: 외국인 본인 또는 대리인
- current_location_context: 국내 체류 중 민원
- current_status_context: 장기체류자격 외국인
- plain_language_summary: 체류자격 외 활동·근무처 변경·체류자격 부여/변경·기간연장·재입국허가·외국인등록증 발급 등 각종 체류 민원 수수료 안내
- required_user_info: |
    - 신청하려는 민원 유형
    - 결혼이민(F-6) 또는 영주(F-5) 여부
- routing_hint: 체류민원 / 공통사항
- answer_focus: 수수료
- search_text: 체류 수수료 12만원 10만원 6만원 8만원 3만5천원 외국인등록증 체류기간 연장 자격변경 결혼이민 영주

<!-- end chatbot: stay-00000-공통 -->


<!-- vizabridge-chatbot v1 source_row: stay-00001-공통 source_hash: 0941cc35f650d4ef -->

### chatbot stay-00001-공통
- record_id: stay-00001-공통
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: 공통
- primary_name_ko: 공통사항
- source_section_title: 공통사항: 여권 유효기간 범위 내 체류기간 부여
- user_situation_tags: |
    - 공통사항
- intent_keywords: |
    - 여권 유효기간 짧은데 체류 가능한가
    - 여권 곧 만료되는데 체류기간 연장
    - 체류기간 부여 기준
- applicant_profile: 장기체류자격 외국인
- current_location_context: 국내 체류 중 민원
- current_status_context: 여권 유효기간이 짧은 외국인
- plain_language_summary: 체류기간은 원칙적으로 여권 유효기간 범위 내 부여 (외교·공무·협정·영주·난민 제외)
- required_user_info: |
    - 여권 잔여 유효기간
    - 체류자격
    - 민원유형
- routing_hint: 체류민원 / 공통사항, 체류기간 연장, 체류자격 변경
- answer_focus: 기간, 요건
- search_text: 여권 유효기간 체류기간 6개월 1년 부여 기준 재발급 변경 연장

<!-- end chatbot: stay-00001-공통 -->


<!-- vizabridge-chatbot v1 source_row: stay-00002-공통 source_hash: bf8e46527e006592 -->

### chatbot stay-00002-공통
- record_id: stay-00002-공통
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: 공통
- primary_name_ko: 공통사항
- source_section_title: 공통사항: 직업 및 연간소득금액 신고 의무
- user_situation_tags: |
    - 취업/고용
    - 공통사항
- intent_keywords: |
    - 외국인 직업 신고
    - 연간 소득금액 신고
    - 직업 변경 신고
    - 소득금액증명
- applicant_profile: 취업 가능 체류자격 외국인
- current_location_context: 국내 체류 중 민원
- current_status_context: 주재 D-7, 기업투자 D-8, 무역경영 D-9, 교수 E-1~E-10, 거주 F-2, 재외동포 F-4, 결혼이민 F-6, 방문취업 H-2
- plain_language_summary: 취업 가능 체류자격자는 직업과 연간 소득금액을 출입국·외국인관서에 신고해야 합니다
- required_user_info: |
    - 현재 체류자격
    - 직업 변경 여부
    - 신고 시점
- routing_hint: 체류민원 / 공통사항, 외국인등록
- answer_focus: 신고의무, 제출서류
- search_text: 외국인 직업 신고서 연간 소득 외국인등록 자격변경 자격외 활동 근무처 변경 직업 변경

<!-- end chatbot: stay-00002-공통 -->


<!-- vizabridge-chatbot v1 source_row: stay-00003-공통 source_hash: 7e4418105f8cf0f9 -->

### chatbot stay-00003-공통
- record_id: stay-00003-공통
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: 공통
- primary_name_ko: 공통사항
- source_section_title: 공통사항: 만 6세 이상 만 18세 이하 재학증명서 제출 의무
- user_situation_tags: |
    - 공통사항
- intent_keywords: |
    - 외국인 자녀 학교 신고
    - 미성년 외국인 재학증명서
    - 초중고 외국인 학생 등록
- applicant_profile: 만 6-18세 외국인 본인 또는 부모
- current_location_context: 국내 체류 중 민원
- current_status_context: 체류자격 외국인 중 미성년자
- plain_language_summary: 만 6-18세 외국인은 초·중·고 재학 여부를 신고해야 합니다 (재학증명서 제출)
- required_user_info: |
    - 자녀 나이
    - 재학 학교
    - 입학 또는 변경 시점
- routing_hint: 체류민원 / 공통사항, 외국인등록
- answer_focus: 신고의무, 제출서류
- search_text: 재학증명서 만 6세 만 18세 초등학교 중학교 고등학교 학교 변경 외국인등록 미취학

<!-- end chatbot: stay-00003-공통 -->


<!-- vizabridge-chatbot v1 source_row: stay-00004-공통 source_hash: a7e865c425deb4b4 -->

### chatbot stay-00004-공통
- record_id: stay-00004-공통
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: 공통
- primary_name_ko: 공통사항
- source_section_title: 공통사항: 외국인 결핵진단서 제출 의무
- user_situation_tags: |
    - 공통사항
    - 결핵검진
- intent_keywords: |
    - 결핵진단서 어디서 받나
    - 베트남에서 한국 장기비자
    - 결핵 고위험국가 비자
    - 사증 신청 결핵검사 면제
- applicant_profile: 결핵 고위험국가 35개국 국민
- current_location_context: 입국 전 사증 신청 또는 국내 체류 중 민원
- current_status_context: 장기체류 사증 신청자 또는 단기체류 자격 변경 신청자
- plain_language_summary: 결핵 고위험국가 35개국 국민은 90일 초과 사증 신청·외국인등록·체류허가 시 결핵진단서 제출
- required_user_info: |
    - 국적
    - 체류 목적 (90일 초과 여부)
    - 이전 결핵진단서 제출 이력
- routing_hint: 체류민원 / 공통사항, 외국인등록, 체류자격 변경, 체류기간 연장
- answer_focus: 제출서류, 제한사항, 예외
- search_text: 결핵진단서 결핵 고위험국가 35개국 베트남 중국 인도네시아 외국인등록 사증발급 적용제외 외교 공무 협정 임신부

<!-- end chatbot: stay-00004-공통 -->


<!-- vizabridge-chatbot v1 source_row: stay-00005-A-1 source_hash: 4366a56ff1fa21b1 -->

### chatbot stay-00005-A-1
- record_id: stay-00005-A-1
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: A-1
- primary_name_ko: 외교
- source_section_title: A-1 외교 / 자격 해당자 및 활동범위
- user_situation_tags: |
    - 공무/외교
- intent_keywords: |
    - 외교관 가족 한국 체류
    - 외교 비자 A-1 대상자
    - 국제기구 직원 한국
- applicant_profile: 외교관 또는 외교사절단 가족
- current_location_context: 입국 전 사증 신청 또는 국내 주재 중
- current_status_context: 외교사절단·영사기관 구성원, UN 사무총장 등 국제기구 고위 직원
- plain_language_summary: 외교사절단·영사기관 구성원과 그 가족, 그리고 외교사절과 동등한 특권 면제를 받는 자에게 부여되는 체류자격
- required_user_info: |
    - 본인 또는 가족 지위
    - 체류 기간
    - 소속 국가/국제기구
- routing_hint: 체류민원 / 공통사항
- answer_focus: 대상, 기간
- search_text: 외교 A-1 외교사절단 영사기관 UN 국제기구 재임기간 외교관 가족 배우자 자녀

<!-- end chatbot: stay-00005-A-1 -->


<!-- vizabridge-chatbot v1 source_row: stay-00006-A-1 source_hash: aa70f9b6d43e7e78 -->

### chatbot stay-00006-A-1
- record_id: stay-00006-A-1
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: A-1
- primary_name_ko: 외교
- source_section_title: A-1 외교 / 체류자격외 활동허가
- user_situation_tags: |
    - 공무/외교
    - 취업/고용
    - 자격외활동
- intent_keywords: |
    - 외교관 가족 한국 취업
    - 주한외국공관 가족 일자리
    - 외교부 고용추천서
    - 미국 대사관 가족 취업
- applicant_profile: 주한외국공관원 가족 또는 국제기구 직원 동반가족
- current_location_context: 국내 체류 중 민원
- current_status_context: 외교(A-1) 자격 소지자의 가족
- plain_language_summary: 주한외국공관원 가족과 국제기구 직원 동반가족이 한국에서 취업하려면 외교부 고용추천서를 받아 체류자격외 활동허가를 받습니다
- required_user_info: |
    - 공관원과의 관계
    - 취업 분야
    - 취업 국가별 협정 적용 여부
- routing_hint: 체류민원 / 체류자격외 활동허가
- answer_focus: 절차, 제출서류, 제한사항
- search_text: 외교 A-1 자격외 활동 외교부 고용추천서 주한외국공관 미국 캐나다 영국 일본 D-1 E-1 E-7 E-6-2 제외 12만원

<!-- end chatbot: stay-00006-A-1 -->


<!-- vizabridge-chatbot v1 source_row: stay-00007-A-1 source_hash: 11de1c3d45def6df -->

### chatbot stay-00007-A-1
- record_id: stay-00007-A-1
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: A-1
- primary_name_ko: 외교
- source_section_title: A-1 외교 / 체류자격 부여 (출생자)
- user_situation_tags: |
    - 공무/외교
    - 가족초청/동반
- intent_keywords: |
    - 외교관 자녀 출생 체류자격
    - 외교 자격 신규 부여
    - 출생일 90일 이내 신청
- applicant_profile: 외교관 부모가 한국 내 출생 자녀
- current_location_context: 국내 체류 중 민원
- current_status_context: 외교(A-1) 자격 소지자의 출생 자녀
- plain_language_summary: 외교관 가족 자녀가 한국에서 출생한 경우 출생일부터 90일 이내 체류자격 부여 신청
- required_user_info: |
    - 자녀 출생일
    - 부모 외교관 신분
    - 대사관 협조 가능 여부
- routing_hint: 체류민원 / 체류자격 부여
- answer_focus: 제출서류
- search_text: 외교 A-1 체류자격 부여 출생 90일 신청서 출생증명서 대사관 협조공한 외국공관원 신분증

<!-- end chatbot: stay-00007-A-1 -->


<!-- vizabridge-chatbot v1 source_row: stay-00008-A-1 source_hash: 3ebf079cde3c09c0 -->

### chatbot stay-00008-A-1
- record_id: stay-00008-A-1
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: A-1
- primary_name_ko: 외교
- source_section_title: A-1 외교 / 체류자격 변경허가
- user_situation_tags: |
    - 공무/외교
    - 자격변경
- intent_keywords: |
    - 외교 자격으로 변경
    - 외교사절 가족 자격변경
    - 동반가족 A-1 변경
- applicant_profile: 외교사절·영사기관 구성원 또는 그 동반가족
- current_location_context: 국내 체류 중 민원
- current_status_context: 외교(A-1) 자격 이외의 자격으로 입국한 외교 관계자
- plain_language_summary: 외교사절단·영사기관 구성원과 동반가족이 다른 자격으로 입국 후 외교(A-1) 자격으로 변경
- required_user_info: |
    - 현재 체류자격
    - 외교관과의 관계
    - 파견·재직 증빙 가능 여부
- routing_hint: 체류민원 / 체류자격 변경
- answer_focus: 제출서류, 기간
- search_text: 외교 A-1 자격변경 외교사절단 영사기관 동반가족 배우자 자녀 부모 신청서 자국 대사관 협조공문 파견 재직 증명

<!-- end chatbot: stay-00008-A-1 -->


<!-- vizabridge-chatbot v1 source_row: stay-00009-A-1 source_hash: 8b261b0b3caff123 -->

### chatbot stay-00009-A-1
- record_id: stay-00009-A-1
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: A-1
- primary_name_ko: 외교
- source_section_title: A-1 외교 / 체류기간 연장허가
- user_situation_tags: |
    - 공무/외교
    - 기간연장
- intent_keywords: |
    - 외교 체류기간 연장
    - 재임기간 내 연장
- applicant_profile: 외교 자격 소지자
- current_location_context: 국내 체류 중 민원
- current_status_context: 현재 외교(A-1) 자격으로 체류 중
- plain_language_summary: 재임기간 범위 내에서 체류기간 연장 (수수료 면제)
- required_user_info: |
    - 재임기간
    - 현재 체류기간 만료일
- routing_hint: 체류민원 / 체류기간 연장
- answer_focus: 제출서류, 기간
- search_text: 외교 A-1 체류기간 연장 재임기간 수수료 면제

<!-- end chatbot: stay-00009-A-1 -->


<!-- vizabridge-chatbot v1 source_row: stay-00010-A-1 source_hash: 93946e2d3e941934 -->

### chatbot stay-00010-A-1
- record_id: stay-00010-A-1
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: A-1
- primary_name_ko: 외교
- source_section_title: A-1 외교 / 재입국허가
- user_situation_tags: |
    - 공무/외교
    - 재입국
- intent_keywords: |
    - 외교관 재입국허가
    - 단수사증 외교관 재입국
    - 복수재입국 외교
- applicant_profile: 외교 자격 소지자
- current_location_context: 국내 체류 중 민원
- current_status_context: 외교(A-1)~협정(A-3) 단수사증 소지자
- plain_language_summary: 출국일로부터 1년 이내 재입국 시 면제. 단수사증 외교(A-1)~협정(A-3) 소지자는 재임기간 내 재입국 시 허가
- required_user_info: |
    - 단·복수사증 여부
    - 출국 예정일
    - 재입국 시점
- routing_hint: 체류민원 / 재입국허가
- answer_focus: 제출서류, 예외
- search_text: 외교 A-1 재입국허가 1년 단수사증 복수사증 재임기간 외교관 신분증 대사관 협조공한

<!-- end chatbot: stay-00010-A-1 -->


<!-- vizabridge-chatbot v1 source_row: stay-00011-A-1 source_hash: ab47f8a36241ea59 -->

### chatbot stay-00011-A-1
- record_id: stay-00011-A-1
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: A-1
- primary_name_ko: 외교
- source_section_title: A-1 외교 / 외국인등록
- user_situation_tags: |
    - 공무/외교
    - 외국인등록
- intent_keywords: |
    - 외교관 외국인등록증
    - 등록 면제 외교관도 등록 가능
    - 외국인등록증 발급 외교
- applicant_profile: 외교 자격 소지자
- current_location_context: 국내 체류 중 민원
- current_status_context: 외교(A-1) 자격으로 국내 체류 중
- plain_language_summary: 외교 자격은 외국인등록 면제 대상이나 본인이 원할 경우 외국인등록증 발급 가능
- required_user_info: |
    - 등록 필요 여부 (사적 사유)
- routing_hint: 체류민원 / 외국인등록
- answer_focus: 제출서류, 예외
- search_text: 외교 A-1 외국인등록 면제 신청서 여권원본 사진 주한외국공관원 신분증

<!-- end chatbot: stay-00011-A-1 -->


<!-- vizabridge-chatbot v1 source_row: stay-00012-A-2 source_hash: afe9efc025d77481 -->

### chatbot stay-00012-A-2
- record_id: stay-00012-A-2
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: A-2
- primary_name_ko: 공무
- source_section_title: A-2 공무
- user_situation_tags: |
    - 공무/외교
- intent_keywords: |
    - 공무 비자 A-2 대상
    - 국제기구 직원 가족
    - 영사기관 사무직원
- applicant_profile: 외국정부 또는 국제기구 공무 수행자와 가족
- current_location_context: 입국 전 사증 신청 또는 국내 주재
- current_status_context: 공무 수행 외국인
- plain_language_summary: 외국정부·국제기구 공무 수행자와 그 가족에게 부여 (대한민국 본부 국제기구 직원 포함)
- required_user_info: |
    - 공무 종류
    - 소속 국가/기구
    - 가족 동반 여부
- routing_hint: 체류민원 / 공통사항
- answer_focus: 대상, 기간
- search_text: 공무 A-2 외교사절단 영사기관 사무직원 기술직원 노무직원 국제기구 공무수행기간

<!-- end chatbot: stay-00012-A-2 -->


<!-- vizabridge-chatbot v1 source_row: stay-00013-A-2 source_hash: 5a22005123c63d82 -->

### chatbot stay-00013-A-2
- record_id: stay-00013-A-2
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: A-2
- primary_name_ko: 공무
- source_section_title: A-2 공무 / 체류자격외 활동허가
- user_situation_tags: |
    - 공무/외교
    - 취업/고용
    - 자격외활동
- intent_keywords: |
    - 공무 자격 가족 취업
    - 공무 자격 외 활동 허가
- applicant_profile: 공무 자격자 가족 (배우자/미성년 자녀)
- current_location_context: 국내 체류 중 민원
- current_status_context: 공무(A-2) 자격으로 근무 중인 직원의 가족
- plain_language_summary: 공무(A-2) 주한외국공관원 가족과 국제기구 직원 동반가족의 한국 취업 활동 허가
- required_user_info: |
    - 공관원과의 관계
    - 취업 분야
    - 수수료 면제 대상 여부
- routing_hint: 체류민원 / 체류자격외 활동허가
- answer_focus: 절차, 제출서류
- search_text: 공무 A-2 자격외 활동 외교부 고용추천서 단순노무 D-3 E-9 E-10 H-2 제외 12만원

<!-- end chatbot: stay-00013-A-2 -->


<!-- vizabridge-chatbot v1 source_row: stay-00014-A-2 source_hash: a7e091857b853a5d -->

### chatbot stay-00014-A-2
- record_id: stay-00014-A-2
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: A-2
- primary_name_ko: 공무
- source_section_title: A-2 공무 / 체류자격 부여
- user_situation_tags: |
    - 공무/외교
    - 가족초청/동반
- intent_keywords: |
    - 공무 외국인 자녀 출생
    - 공무 자격 신규 부여
- applicant_profile: 공무(A-2) 자격자와 부양가족
- current_location_context: 국내 체류 중 민원
- current_status_context: 공무(A-2) 자격으로 입국 또는 한국 내 출생
- plain_language_summary: 공무 수행자 본인 및 부양가족에 대한 체류자격 부여 (출생일부터 90일 이내 신청)
- required_user_info: |
    - 본인 또는 부양가족 구분
    - 파견·재직 입증 서류 보유 여부
- routing_hint: 체류민원 / 체류자격 부여
- answer_focus: 제출서류
- search_text: 공무 A-2 체류자격 부여 출생 본인 부양가족 신청서 파견 재직 협조공문 출생증명서 부양자

<!-- end chatbot: stay-00014-A-2 -->


<!-- vizabridge-chatbot v1 source_row: stay-00023-C-3 source_hash: 4c1ceb9229ef5ecb -->

### chatbot stay-00023-C-3
- record_id: stay-00023-C-3
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: C-3
- primary_name_ko: 단기방문
- source_section_title: C-3 단기방문
- user_situation_tags: |
    - 방문/단기체류
- intent_keywords: |
    - 한국 단기 방문 비자
    - 관광 비자
    - 친지 방문 90일
    - 시장조사 단기상용
    - 단기방문 C-3 종류
- applicant_profile: 단기 방문자 (관광·상용·친지방문 등)
- current_location_context: 입국 전 사증 신청
- current_status_context: 사증 없이 또는 사증면제로 90일 이내 방문 예정
- plain_language_summary: 관광·통과·요양·친지방문·상용활동 등 90일 이내 단기 체류 목적 사증. 영리 목적은 발급 불가
- required_user_info: |
    - 방문 목적
    - 체류 기간
    - 동반자 여부
- routing_hint: 체류민원 / 공통사항, 체류기간 연장
- answer_focus: 대상, 기간
- search_text: 단기방문 C-3 90일 관광 통과 요양 친지방문 상용 시장조사 의료관광 도착관광 동포방문 순수환승

<!-- end chatbot: stay-00023-C-3 -->


<!-- vizabridge-chatbot v1 source_row: stay-00025-C-4 source_hash: ef770932c0c6c0c2 -->

### chatbot stay-00025-C-4
- record_id: stay-00025-C-4
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: C-4
- primary_name_ko: 단기취업
- source_section_title: C-4 단기취업
- user_situation_tags: |
    - 취업/고용
    - 방문/단기체류
    - 계절근로
- intent_keywords: |
    - 계절근로자 비자
    - 단기취업 비자
    - 일시흥행 비자
    - 광고 모델 한국
- applicant_profile: 단기 취업자 (계절근로자·강사·연구자·모델 등)
- current_location_context: 입국 전 사증 신청
- current_status_context: 단기간 한국에서 수익 활동 예정
- plain_language_summary: 농작물·수산물 원시가공 계절근로(C-4-1~4)와 일시흥행·광고·강의·연구·기술지도 등 수익 목적 단기간 취업(C-4-5)
- required_user_info: |
    - 취업 분야
    - 지자체 추천 여부 (계절근로)
    - 취업 기간
- routing_hint: 체류민원 / 공통사항, 근무처 변경/추가
- answer_focus: 대상, 기간
- search_text: 단기취업 C-4 계절근로 농작물 수산물 일시흥행 광고 패션모델 강의 연구 기술지도 90일

<!-- end chatbot: stay-00025-C-4 -->


<!-- vizabridge-chatbot v1 source_row: stay-00027-D-1 source_hash: 100e41b5ac24058e -->

### chatbot stay-00027-D-1
- record_id: stay-00027-D-1
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: D-1
- primary_name_ko: 문화예술
- source_section_title: D-1 문화예술
- user_situation_tags: |
    - 종교/문화
- intent_keywords: |
    - 예술 비자 한국
    - 학술 연구 비자
    - 한국 전통문화 연구 비자
    - D-1 문화예술
- applicant_profile: 학술·예술 활동자
- current_location_context: 입국 전 사증 신청 또는 국내 체류 중
- current_status_context: 비영리 학술·예술 활동 종사
- plain_language_summary: 수익 없는 학술·예술 활동자 (대한민국 고유문화·예술 전문연구·지도 포함). 영리단체 초청은 제외
- required_user_info: |
    - 활동 내용 (학술·예술)
    - 영리 여부
    - 초청 기관
- routing_hint: 체류민원 / 공통사항, 외국인등록
- answer_focus: 대상, 제한사항
- search_text: 문화예술 D-1 학술 예술 비영리 고유문화 태권도 무용 영리단체 제외 2년

<!-- end chatbot: stay-00027-D-1 -->


<!-- vizabridge-chatbot v1 source_row: stay-00029-D-2 source_hash: d78b09638019c809 -->

### chatbot stay-00029-D-2
- record_id: stay-00029-D-2
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: D-2
- primary_name_ko: 유학
- source_section_title: D-2 유학
- user_situation_tags: |
    - 유학/연수
- intent_keywords: |
    - 유학 비자 D-2
    - 한국 대학 유학
    - 전문대학 박사 비자
    - 어학연수 D-4 차이
- applicant_profile: 외국인 유학생 (전문학사·학사·석사·박사·연구·교환·방문학생)
- current_location_context: 입국 전 사증 신청
- current_status_context: 한국 전문대학 이상 교육기관에 정규 입학 예정
- plain_language_summary: 전문대학 이상 교육기관 정규과정 또는 특정 연구 외국인 (원격대학·평생교육기관·기능대학 직업훈련·야간대학원 등 제외)
- required_user_info: |
    - 진학 교육기관
    - 학위 과정
    - 어학연수 vs 학위 과정
- routing_hint: 체류민원 / 공통사항, 체류자격 변경, 외국인등록
- answer_focus: 대상, 기간
- search_text: 유학 D-2 전문대학 학사 석사 박사 연구과정 교환학생 방문학생 D-2-1 D-2-2 D-2-3 D-2-4 D-2-5 D-2-6 D-2-7 D-2-8 어학연수 D-4-1 D-4-7 2년

<!-- end chatbot: stay-00029-D-2 -->


<!-- vizabridge-chatbot v1 source_row: stay-00030-D-2 source_hash: fa10a25437578da9 -->

### chatbot stay-00030-D-2
- record_id: stay-00030-D-2
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: D-2
- primary_name_ko: 유학
- source_section_title: D-2 유학 / 시간제취업 활동 허가
- user_situation_tags: |
    - 유학/연수
    - 자격외활동
    - 취업/고용
- intent_keywords: |
    - 유학생 아르바이트
    - D-2 시간제 취업
    - 한국 유학생 알바
    - TOPIK 3급 아르바이트
    - 어학연수생 알바
- applicant_profile: 유학생 또는 어학연수생
- current_location_context: 국내 체류 중 민원
- current_status_context: D-2 학위과정 또는 D-4-1/D-4-7 어학연수 (변경 6개월 경과)
- plain_language_summary: 한국어 능력을 갖춘 유학생의 시간제 취업 활동 허가 (학위과정·연구과정·일-학습연계는 즉시, 어학연수는 6개월 경과 후)
- required_user_info: |
    - 한국어 능력 수준 (TOPIK/사회통합/세종학당)
    - 체류기간
    - 취업 분야
    - 학과 성적
- routing_hint: 체류민원 / 체류자격외 활동허가
- answer_focus: 요건, 제출서류, 제한사항
- search_text: 유학 D-2 시간제 취업 알바 아르바이트 TOPIK 3급 4급 사회통합 세종학당 주중 25시간 30시간 35시간 제조업 건설업 제한 미성년 영어 학원

<!-- end chatbot: stay-00030-D-2 -->


<!-- vizabridge-chatbot v1 source_row: stay-00034-D-3 source_hash: b788728700842fb3 -->

### chatbot stay-00034-D-3
- record_id: stay-00034-D-3
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: D-3
- primary_name_ko: 기술연수
- source_section_title: D-3 기술연수
- user_situation_tags: |
    - 취업/고용
- intent_keywords: |
    - 기술연수 비자 D-3
    - 외국 투자 기업 연수
    - 해외투자기업 기술연수생
- applicant_profile: 해외투자기업 또는 기술 수출 산업체 연수생
- current_location_context: 입국 전 사증 신청 또는 국내 체류 중
- current_status_context: 외국환거래법상 외국 직접투자 산업체 또는 기술수출 산업체에서 연수
- plain_language_summary: 법무부장관이 정하는 연수조건을 갖춘 자로 국내 산업체에서 연수받는 자 (자격외활동·근무처 변경·자격 변경 모두 제한)
- required_user_info: |
    - 연수 산업체
    - 연수 기간
    - 국내 모기업 정보
- routing_hint: 체류민원 / 공통사항, 체류기간 연장
- answer_focus: 대상, 제한사항
- search_text: 기술연수 D-3 해외투자기업 외국환거래법 기술수출 대외무역법 산업설비 2년 자격외 활동 억제 변경 불가

<!-- end chatbot: stay-00034-D-3 -->


<!-- vizabridge-chatbot v1 source_row: stay-00036-D-4 source_hash: 3ea24f0fafd24e65 -->

### chatbot stay-00036-D-4
- record_id: stay-00036-D-4
- source_dataset: stay_manual_semantic_clean.csv
- code_type: stay_status
- primary_code: D-4
- primary_name_ko: 일반연수
- source_section_title: D-4 일반연수
- user_situation_tags: |
    - 유학/연수
- intent_keywords: |
    - 일반연수 비자 D-4
    - 어학연수 D-4-1
    - 한국어 연수 비자
    - 외국인학교 D-4-3
- applicant_profile: 교육기관·기업체 연수자
- current_location_context: 입국 전 사증 신청 또는 국내 체류 중
- current_status_context: D-2 외의 교육기관·기업체·단체에서 교육·연수·연구 종사
- plain_language_summary: 한국어 연수(D-4-1)·기업맞춤형 인턴십(D-4-2K)·외국인 유학생(D-4-3)·한식조리연수(D-4-5)·우수사설교육기관 연수(D-4-6)·외국어 연수(D-4-7) 등
- required_user_info: |
    - 연수 종류
    - 연수기관
    - 연수 기간
- routing_hint: 체류민원 / 공통사항, 체류자격 변경
- answer_focus: 대상, 기간
- search_text: 일반연수 D-4 어학연수 D-4-1 외국어연수 D-4-7 한국어 외국인유학생 D-4-3 한식조리 D-4-5 우수사설교육기관 D-4-6 기업맞춤형 인턴십 D-4-2K 2년

<!-- end chatbot: stay-00036-D-4 -->
