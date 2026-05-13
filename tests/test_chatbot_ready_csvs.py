import pandas as pd

from scripts import build_chatbot_ready_manual_csvs as chatbot


def test_marriage_rows_get_plain_language_situation_tags():
    df = pd.DataFrame(
        [
            {
                "visa_code": "F-6",
                "visa_name_ko": "결혼이민",
                "manual_type": "사증민원",
                "source_pdf": "visa.pdf",
                "item_type": "visa_rule",
                "petition_type": "사증발급",
                "subsection_type": "대상",
                "section_title": "국민의 배우자(F-6-1)",
                "eligibility": "한국에 혼인이 유효하게 성립되어 있고 우리 국민과 결혼생활을 지속하려는 외국인",
                "normalized_text": "국민의 배우자 결혼이민 사증발급",
            }
        ]
    )

    row = chatbot.build_chatbot_rows("visa", df)[0]

    assert row["primary_code"] == "F-6"
    assert "결혼/배우자" in row["user_situation_tags"]
    assert "한국인 배우자" in row["intent_keywords"]
    assert "혼인 여부" in row["required_user_info"]
    assert row["routing_hint"].startswith("사증민원")


def test_student_part_time_work_rows_get_work_and_study_tags():
    df = pd.DataFrame(
        [
            {
                "stay_status_code": "D-2",
                "stay_status_name_ko": "유학",
                "manual_type": "체류민원",
                "source_pdf": "stay.pdf",
                "item_type": "stay_status_rule",
                "petition_type": "체류자격외 활동허가",
                "subsection_type": "요건",
                "section_title": "유학생(D-2)의 시간제 취업 허가",
                "requirements": "학위과정 유학생은 한국어능력 기준과 허용시간 범위를 충족해야 함",
                "normalized_text": "유학생 시간제 취업 아르바이트 체류자격외 활동허가",
            }
        ]
    )

    row = chatbot.build_chatbot_rows("stay", df)[0]

    assert "유학/연수" in row["user_situation_tags"]
    assert "아르바이트/시간제취업" in row["user_situation_tags"]
    assert "알바" in row["intent_keywords"]
    assert "근무시간" in row["required_user_info"]
    assert row["current_location_context"].startswith("국내 체류 중")


def test_chatbot_columns_exclude_debug_and_source_raw_fields():
    forbidden = {
        "pdf_page_start",
        "pdf_page_end",
        "evidence_quote",
        "source_raw_text",
        "raw_text",
        "needs_human_review",
        "review_notes",
    }

    assert forbidden.isdisjoint(chatbot.CHATBOT_COLUMNS)
    assert {"user_situation_tags", "intent_keywords", "plain_language_summary", "required_user_info", "search_text"}.issubset(
        chatbot.CHATBOT_COLUMNS
    )


def test_intent_routes_cover_user_plain_language_entry_points():
    routes = {route["route_id"]: route for route in chatbot.INTENT_ROUTES}

    assert "route_marriage_spouse" in routes
    assert "F-6" in routes["route_marriage_spouse"]["likely_codes"]
    assert "한국인 배우자" in routes["route_marriage_spouse"]["search_boost_terms"]
    assert "route_student_part_time_work" in routes
    assert "알바" in routes["route_student_part_time_work"]["search_boost_terms"]
    assert "route_startup_founder" in routes
    assert "D-8-4S" in routes["route_startup_founder"]["likely_codes"]
