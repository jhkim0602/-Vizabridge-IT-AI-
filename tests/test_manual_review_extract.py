from scripts.manual_review.extract import classify_text, item_from_block, split_page_blocks


def test_split_page_blocks_keeps_heading_with_following_text():
    text = (
        "1 각종 체류허가 등에 관한 심사수수료\n"
        "수수료 12만원\n\n"
        "2 여권 유효기간 범위 내 체류기간 부여 안내\n"
        "적용대상 모든 장기 체류자격 외국인"
    )
    blocks = split_page_blocks(text)
    assert len(blocks) == 2
    assert blocks[0].title == "1 각종 체류허가 등에 관한 심사수수료"
    assert "12만원" in blocks[0].text


def test_classify_stay_fee_and_petition_fields():
    result = classify_text("체류자격 변경허가 수수료 10만원", "stay")
    assert result["item_type"] == "fee"
    assert result["subsection_type"] == "수수료"
    assert result["petition_type"] == "체류자격 변경"


def test_item_from_block_preserves_raw_text_and_evidence():
    item = item_from_block(
        manual_key="visa",
        page_no=7,
        title="외 교(A-1)",
        text="외 교(A-1)\n첨부서류\n① 사증발급신청서, 여권, 수수료",
        sequence=1,
    )
    assert item["visa_code"] == "A-1"
    assert item["visa_name_ko"] == "외교"
    assert item["required_documents"]
    assert item["evidence_quote"] in item["raw_text"]
