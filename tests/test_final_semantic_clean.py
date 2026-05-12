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
    assert not builder.is_noise_row("제출서류", "사증발급신청서, 여권, 수수료")


def test_clean_row_values_preserves_machine_enum_underscores():
    row = {
        "item_type": "stay_status_rule",
        "subsection_type": "제출서류",
        "section_title": "제목자격 변경",
    }
    cleaned = builder.clean_row_values(row)
    assert cleaned["item_type"] == "stay_status_rule"
    assert cleaned["section_title"] == "체류자격 변경"
