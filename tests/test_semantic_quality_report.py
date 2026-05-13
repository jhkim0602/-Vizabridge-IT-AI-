import pandas as pd

from scripts import quality_report_semantic_manual_csvs as quality


def base_stay_row(**overrides):
    row = {
        "stay_status_code": "D-2",
        "stay_status_name_ko": "유학",
        "manual_type": "체류민원",
        "source_pdf": "stay.pdf",
        "item_type": "required_documents",
        "section_title": "제출서류",
        "subtype_or_program": "",
        "petition_type": "체류기간 연장",
        "subsection_type": "제출서류",
        "applicant_context": "",
        "eligibility": "",
        "target_persons": "",
        "common_documents": "",
        "mandatory_documents": "여권",
        "other_documents": "",
        "requirements": "",
        "procedure": "",
        "restrictions": "",
        "exceptions": "",
        "fees": "",
        "duration_or_validity": "",
        "quota_or_limit": "",
        "score_criteria": "",
        "table_summary": "",
        "table_rows": "",
        "normalized_text": "체류기간 연장을 위한 제출서류는 여권과 신청서이다.",
        "obligations": "",
    }
    row.update(overrides)
    return row


def test_collect_review_reasons_flags_required_documents_without_document_bucket():
    df = pd.DataFrame(
        [
            base_stay_row(
                item_type="required_documents",
                common_documents="",
                mandatory_documents="",
                other_documents="",
            )
        ]
    )

    candidates = quality.collect_review_candidates(df, "stay")

    assert len(candidates) == 1
    assert candidates.loc[0, "review_priority"] == "high"
    assert "required_documents_without_document_bucket" in candidates.loc[0, "review_reason"]
    assert candidates.loc[0, "suggested_action"]


def test_collect_review_reasons_flags_typed_field_mismatches_and_noise():
    df = pd.DataFrame(
        [
            base_stay_row(item_type="restriction", subsection_type="제한", restrictions=""),
            base_stay_row(section_title="목차", normalized_text="D-2 E-7 F-2 목차"),
        ]
    )

    candidates = quality.collect_review_candidates(df, "stay")

    reasons = " ".join(candidates["review_reason"].tolist())
    assert "restriction_without_restrictions" in reasons
    assert "noise_like_title" in reasons


def test_collect_review_reasons_flags_document_score_and_form_noise():
    df = pd.DataFrame(
        [
            base_stay_row(
                item_type="stay_status_rule",
                subsection_type="대상",
                section_title="3. (외국인 본인) 국내 운전면허증사본(가점 해당자만 제출)",
                normalized_text="3. (외국인 본인) 국내 운전면허증사본(가점 해당자만 제출)",
            ),
            base_stay_row(
                item_type="quota",
                subsection_type="쿼터",
                section_title="우수 재능 보유 (25)",
                normalized_text="우수 재능 보유 (25); 과학·경영·교육·문화예술·체육 등의 분야에 우수한 재능 보유",
                quota_or_limit="우수 재능 보유 (25)",
            ),
            base_stay_row(
                item_type="stay_status_rule",
                subsection_type="기타",
                section_title="ROWSPANCONTINUE",
                normalized_text="ROWSPANCONTINUE; 입국한 날로부터 1년 범위 내에서 연장",
            ),
        ]
    )

    candidates = quality.collect_review_candidates(df, "stay")
    reasons = " ".join(candidates["review_reason"].tolist())

    assert "document_like_row_outside_required_documents" in reasons
    assert "score_like_row_outside_score_table" in reasons
    assert "form_attachment_noise" in reasons


def test_stay_general_status_rows_may_have_blank_petition_type():
    df = pd.DataFrame(
        [
            base_stay_row(
                item_type="stay_status_rule",
                petition_type="",
                section_title="유학(D-2) 해당자",
                subsection_type="대상",
                eligibility="유학(D-2) 자격 해당자",
                normalized_text="유학(D-2) 체류자격에 해당하는 외국인 유학생 대상 설명",
            )
        ]
    )

    candidates = quality.collect_review_candidates(df, "stay")

    assert candidates.empty


def test_build_summary_reports_counts_candidates_and_fill_rates():
    df = pd.DataFrame(
        [
            base_stay_row(),
            base_stay_row(
                item_type="required_documents",
                section_title="추가 제출서류",
                mandatory_documents="",
                normalized_text="체류기간 연장 신청 시 추가 제출서류를 확인해야 한다.",
            ),
        ]
    )
    candidates = quality.collect_review_candidates(df, "stay")

    summary = quality.build_quality_summary(df, candidates, "stay")
    metrics = dict(zip(summary["metric"], summary["value"]))

    assert metrics["manual_key"] == "stay"
    assert metrics["row_count"] == "2"
    assert metrics["review_candidate_count"] == "1"
    assert "mandatory_documents" in metrics["lowest_fill_rate_fields"]


def test_review_candidates_keep_source_columns_for_human_review():
    df = pd.DataFrame(
        [
            base_stay_row(item_type="fee", subsection_type="수수료", fees=""),
        ]
    )

    candidates = quality.collect_review_candidates(df, "stay")

    for column in [
        "review_priority",
        "review_reason",
        "suggested_action",
        "stay_status_code",
        "petition_type",
        "section_title",
        "normalized_text",
    ]:
        assert column in candidates.columns
