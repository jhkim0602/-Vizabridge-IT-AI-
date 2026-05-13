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
