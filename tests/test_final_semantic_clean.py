from scripts import build_semantic_manual_csvs as builder


def test_final_columns_exclude_page_evidence_raw_and_review_fields():
    forbidden = {
        "pdf_page_start",
        "pdf_page_end",
        "printed_page_start",
        "printed_page_end",
        "source_section_path",
        "evidence_quote",
        "source_raw_text",
        "raw_text",
        "needs_human_review",
        "review_notes",
    }
    assert forbidden.isdisjoint(builder.STAY_COLUMNS)
    assert forbidden.isdisjoint(builder.VISA_COLUMNS)


def test_final_columns_include_clean_document_buckets():
    for columns in [builder.STAY_COLUMNS, builder.VISA_COLUMNS]:
        assert "common_documents" in columns
        assert "mandatory_documents" in columns
        assert "other_documents" in columns
        assert "eligibility" in columns
        assert "requirements" in columns
        assert "normalized_text" in columns


def test_noise_detection_filters_table_of_contents_rows():
    assert builder.is_noise_row("目 次", "1. 외교(A-1) 2. 공무(A-2) 3. 협정(A-3)")
    assert builder.is_noise_row("목차", "단기방문(C-3)")
    assert builder.is_noise_row("외국인체류 안내매뉴얼", "# 외국인체류 안내매뉴얼\n24. 5.\n법무부")
    assert builder.is_noise_row("17. 무역경영(D-9)", "무역경영(D-9)\n외국국적동포 관련\n(C-3-8, F-1, H-2, F-4, F-5)")
    assert not builder.is_noise_row("제출서류", "사증발급신청서, 여권, 수수료")
    assert not builder.is_noise_row(
        "※ 허가요건 등 세부사항은 숙련기능인력(E-7-4) 안내매뉴얼 참조",
        "※ 허가요건 등 세부사항은 숙련기능인력(E-7-4) 안내매뉴얼 참조\n체류기간\n연장허가",
    )


def test_noise_detection_filters_blank_forms_and_table_fragments():
    assert builder.is_noise_row("외국인유학생 시간제취업 확인서", "외국인유학생 시간제취업 확인서")
    assert builder.is_noise_row("구분", "구분\n허용 인원\n명")
    assert builder.is_noise_row("① 사업장 면적(m2)", "① 사업장 면적(m2)\n중식당\n0\n,000")
    assert builder.is_noise_row("signature/seal", "signature/seal")
    assert builder.is_noise_row(
        "7. 임금 7. Payment",
        "Monthly Normal wages ( )won. Accommo-dations and Meals. Both employees and employers shall comply.",
    )


def test_clean_row_values_preserves_machine_enum_underscores():
    row = {
        "item_type": "stay_status_rule",
        "subsection_type": "제출서류",
        "section_title": "제목자격 변경",
    }
    cleaned = builder.clean_row_values(row)
    assert cleaned["item_type"] == "stay_status_rule"
    assert cleaned["section_title"] == "체류자격 변경"


def test_low_value_semantic_row_detection_filters_reviewed_fragments():
    assert builder.is_low_value_semantic_row(
        {
            "section_title": "외국인유학생 시간제취업 요건 준수 확인서",
            "normalized_text": "외국인유학생 시간제취업 요건 준수 확인서",
            "table_rows": "외국인유학생 시간제취업 요건 준수 확인서",
        }
    )
    assert builder.is_low_value_semantic_row(
        {
            "section_title": "연 수 계 획 서",
            "normalized_text": "연 수 계 획 서",
            "table_rows": "연 수 계 획 서",
        }
    )
    assert builder.is_low_value_semantic_row(
        {
            "section_title": "구분",
            "normalized_text": "구분; 허용 인원; 명",
            "table_rows": "구분; 허용 인원; 명",
        }
    )
    assert builder.is_low_value_semantic_row(
        {
            "section_title": "2,500만원",
            "normalized_text": ",500만원; ,000만원",
            "table_rows": ",500만원; ,000만원",
        }
    )
    assert not builder.is_low_value_semantic_row(
        {
            "section_title": "※ 허가요건 등 세부사항은 숙련기능인력(E-7-4) 안내매뉴얼 참조",
            "normalized_text": "※ 허가요건 등 세부사항은 숙련기능인력(E-7-4) 안내매뉴얼 참조; 체류기간; 연장허가",
            "table_rows": "",
        }
    )


def test_section_heading_context_overrides_previous_reference_codes():
    markdown = """
# 회화지도(E-2)

③ 채용신체검사서 1부. 회화지도(E-2) 강사 등에 대한 규정 비적용

# 특정활동(E-7)

| 적용대상 및 도입기준 등 | 1. 적용대상 [출입국관리법 시행령 별표 1의2 20. 특정활동(E-7)] 대한민국 내의 공·사기관 등과의 계약에 따라 법무부장관이 특별히 지정하는 활동에 종사하려는 사람 |
| --- | --- |
"""
    rows = builder.build_semantic_rows("stay", markdown)
    target = next(row for row in rows if row["section_title"] == "적용대상 및 도입기준 등")

    assert target["stay_status_code"] == "E-7"
    assert target["stay_status_name_ko"] == "특정활동"


def test_section_heading_context_resets_stay_petition_inheritance():
    markdown = """
# 기타(G-1)

# 1. 재입국허가 면제 제도

등록을 필한 외국인이 출국한 날로부터 1년 이내에 재입국하려는 경우 재입국허가 면제

# 관광취업(H-1)

관광이 주된 목적이어야 하며, 취업 또는 학업활동에 전념하거나 취재, 정치활동 등 협정의 취지에 부합하지 않은 활동은 금지됨
"""
    rows = builder.build_semantic_rows("stay", markdown)
    target = next(row for row in rows if row["stay_status_code"] == "H-1")

    assert target["petition_type"] == ""
    assert target["subsection_type"] == "제한"


def test_exclusion_reference_code_does_not_become_primary_code():
    markdown = """
# 유학(D-2)

○ (대상) 아래 요건을 모두 충족한 광역형 비자 유학생(D-2)

※ 단, 논문준비 등으로 체류기간 연장허가 특례를 받은 사람, 연구유학(D-2-5)는 제외
"""
    rows = builder.build_semantic_rows("stay", markdown)
    target = next(row for row in rows if "D-2-5" in row["normalized_text"])

    assert target["stay_status_code"] == "D-2"
    assert target["subsection_type"] == "제한"


def test_document_line_with_fee_stays_required_documents_not_fee():
    markdown = """
# 주재(D-7)

### 첨부서류

① 사증발급신청서 (별지 제17호 서식), 여권사본, 표준규격사진 1매, 수수료
② 수주계약서 사본
③ 초청회사의 사업자등록증 사본 또는 법인등기사항전부증명서
"""
    rows = builder.build_semantic_rows("visa", markdown)
    target = next(row for row in rows if "사증발급신청서" in row["normalized_text"])

    assert target["visa_code"] == "D-7"
    assert target["item_type"] == "required_documents"
    assert target["subsection_type"] == "제출서류"


def test_document_keywords_override_target_or_restriction_words():
    assert builder.classify_subsection(
        "⑩ 근로자파견사업허가증(해당자)",
        "⑩ 근로자파견사업허가증(해당자)\n광고 모델의 경우 일반심사 기준",
    ) == ("mandatory_documents", "제출서류")
    assert builder.classify_subsection(
        "- 피초청(외국인)인 준비서류 : 여권사본, 고용계약서, 자격요건 입증서류",
        "신원보증서는 법무부장관이 고시한 근무처변경, 추가 신고가 제한되는 직종 종사자만 해당",
    ) == ("mandatory_documents", "제출서류")
    assert builder.classify_subsection(
        "3. (외국인 본인) 국내 운전면허증사본(가점 해당자만 제출)",
        "원청확인서 또는 기자재업체확인서(조선업만 해당)",
    ) == ("mandatory_documents", "제출서류")


def test_score_point_rows_do_not_become_quota():
    field, subsection = builder.classify_subsection(
        "우수 재능 보유 (25)",
        "과학·경영·교육·문화예술·체육 등의 분야에 우수한 재능 보유",
    )

    assert field == "score_criteria"
    assert subsection == "점수표"
    assert builder.classify_item_type("visa", subsection, "") == "score_table"


def test_strong_restriction_title_overrides_document_words():
    assert builder.classify_subsection(
        "【취업제한 업종】",
        "건설업(사업자등록증상 업종이 건설업만 기재되어 있으면 취업불가)",
    ) == ("restrictions", "제한")


def test_form_attachment_noise_filters_known_parser_fragments():
    assert builder.is_noise_row("ROWSPANCONTINUE", "ROWSPANCONTINUE\n입국한 날로부터 1년 범위 내에서 연장")
    assert builder.is_noise_row(
        "근로계약서 견본Labor Contract(Sample)",
        "근로계약서 견본Labor Contract(Sample) 사용자 Employer",
    )


def test_petition_classification_is_limited_by_manual_type():
    assert builder.classify_petition("사증발급", "사증발급 대상", "stay", "") == ""
    assert builder.classify_petition("체류기간 연장", "체류기간 연장 대상", "visa", "") == "사증발급"
    assert builder.classify_petition("사증발급", "사증발급 대상", "visa", "") == "사증발급"
    assert builder.classify_petition("체류기간 연장", "체류기간 연장 대상", "stay", "") == "체류기간 연장"
