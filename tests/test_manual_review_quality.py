from scripts.manual_review.schema import empty_item
from scripts.manual_review.quality import quality_summary, validate_items


def test_validate_items_flags_missing_raw_text_and_bad_evidence():
    item = empty_item()
    item.update(
        {
            "item_id": "stay-000001",
            "manual_type": "체류민원",
            "raw_text": "",
            "evidence_quote": "없는 근거",
            "section_title": "제목자격 변경",
            "normalized_text": "",
            "needs_human_review": "false",
            "review_notes": "",
        }
    )
    errors = validate_items([item])
    messages = " ".join(error["message"] for error in errors)
    assert "empty raw_text" in messages
    assert "suspicious term" in messages


def test_quality_summary_reports_counts_and_coverage():
    item = empty_item()
    item.update(
        {
            "manual_type": "사증민원",
            "item_type": "visa_rule",
            "subsection_type": "대상",
            "visa_code": "C-3",
            "raw_text": "단기방문(C-3)",
            "evidence_quote": "단기방문(C-3)",
            "needs_human_review": "false",
        }
    )
    report = quality_summary([item], [])
    assert "Rows by manual_type" in report
    assert "C-3" in report


def test_validate_items_accepts_evidence_with_normalized_whitespace():
    item = empty_item()
    item.update(
        {
            "item_id": "stay-000002",
            "manual_type": "체류민원",
            "raw_text": "체류자격별 대상 및      제출서류 등 안내메뉴얼",
            "evidence_quote": "체류자격별 대상 및 제출서류 등 안내메뉴얼",
        }
    )
    errors = validate_items([item])
    assert not [error for error in errors if "evidence quote" in error["message"]]
