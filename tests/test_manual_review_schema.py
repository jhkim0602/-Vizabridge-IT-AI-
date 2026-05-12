from scripts.manual_review.schema import (
    ALL_FIELDS,
    COMMON_FIELDS,
    STAY_FIELDS,
    SUSPICIOUS_TERMS,
    VISA_FIELDS,
    empty_item,
)


def test_all_fields_include_manual_specific_review_fields():
    assert "stay_status_code" in ALL_FIELDS
    assert "visa_code" in ALL_FIELDS
    assert "table_rows" in COMMON_FIELDS
    assert "recommendation_or_approval" in VISA_FIELDS
    assert "score_criteria" in STAY_FIELDS


def test_empty_item_contains_every_field_with_defaults():
    item = empty_item()
    assert set(ALL_FIELDS) == set(item)
    assert item["needs_human_review"] == "false"
    assert item["confidence"] == "0.00"


def test_suspicious_terms_match_known_korean_parse_errors():
    assert {"제목자격", "제목관리과", "제목족적"}.issubset(SUSPICIOUS_TERMS)
