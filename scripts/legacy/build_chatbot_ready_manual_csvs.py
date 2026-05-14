#!/usr/bin/env python3
"""Build chatbot-ready CSVs from the clean semantic manual CSVs.

The semantic CSVs are organized around the manual's administrative structure:
visa/stay code, petition type, subsection type, documents, requirements, and
restrictions. A real chatbot also needs user-situation clues because users
usually ask with plain language:

- "한국인 배우자랑 결혼했는데 비자 뭐 해야 해?"
- "유학생인데 알바 가능한가요?"
- "외국인 직원을 한국 회사에서 채용하려면?"

This script keeps the clean semantic facts and adds deterministic routing
fields such as situation tags, intent keywords, applicant profile, and follow-up
questions. It creates one chatbot-ready CSV per manual without PDF page numbers,
evidence quotes, raw source text, or review/debug columns.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

INPUTS = {
    "stay": {
        "input_csv": PROCESSED_DIR / "stay_manual_semantic_clean.csv",
        "output_csv": PROCESSED_DIR / "stay_manual_chatbot_ready.csv",
        "code_col": "stay_status_code",
        "name_col": "stay_status_name_ko",
        "code_type": "stay_status",
    },
    "visa": {
        "input_csv": PROCESSED_DIR / "visa_manual_semantic_clean.csv",
        "output_csv": PROCESSED_DIR / "visa_manual_chatbot_ready.csv",
        "code_col": "visa_code",
        "name_col": "visa_name_ko",
        "code_type": "visa",
    },
}

CHATBOT_COLUMNS = [
    "record_id",
    "manual_type",
    "source_pdf",
    "source_dataset",
    "code_type",
    "primary_code",
    "primary_name_ko",
    "item_type",
    "petition_type",
    "subsection_type",
    "subtype_or_program",
    "source_section_title",
    "user_situation_tags",
    "intent_keywords",
    "applicant_profile",
    "current_location_context",
    "current_status_context",
    "plain_language_summary",
    "required_user_info",
    "routing_hint",
    "answer_focus",
    "eligibility",
    "requirements",
    "common_documents",
    "mandatory_documents",
    "other_documents",
    "procedure",
    "restrictions",
    "exceptions",
    "fees",
    "duration_or_validity",
    "quota_or_limit",
    "score_criteria",
    "search_text",
]

ROUTE_OUTPUT_CSV = PROCESSED_DIR / "chatbot_intent_routes.csv"
ROUTE_COLUMNS = [
    "route_id",
    "user_intent",
    "example_questions",
    "situation_tags",
    "target_manuals",
    "likely_codes",
    "likely_petition_types",
    "primary_filters",
    "required_user_info",
    "answer_strategy",
    "search_boost_terms",
]

TEXT_FIELDS = [
    "section_title",
    "subtype_or_program",
    "petition_type",
    "subsection_type",
    "applicant_context",
    "eligibility",
    "target_persons",
    "common_documents",
    "mandatory_documents",
    "other_documents",
    "requirements",
    "procedure",
    "restrictions",
    "exceptions",
    "fees",
    "duration_or_validity",
    "quota_or_limit",
    "score_criteria",
    "table_summary",
    "table_rows",
    "normalized_text",
    "inviter_context",
    "recommendation_or_approval",
    "obligations",
]


SITUATION_RULES = [
    ("결혼/배우자", ["결혼", "혼인", "배우자", "F-6", "국민의 배우자", "결혼이민"]),
    ("가족/동반", ["가족", "자녀", "부모", "동반", "방문동거", "양육", "친척", "F-1", "F-3"]),
    ("유학/연수", ["유학", "유학생", "어학연수", "일반연수", "학교", "대학", "학위", "D-2", "D-4"]),
    ("아르바이트/시간제취업", ["시간제", "아르바이트", "수익적 연구", "인턴", "자격외 활동", "체류자격외 활동"]),
    ("취업/고용", ["취업", "고용", "근로", "근무", "근무처", "회사", "고용계약", "전문인력", "E-7", "E-9", "E-10"]),
    ("숙련기능/전환", ["숙련기능", "E-7-4", "K-point", "점수제", "전환", "뿌리기업"]),
    ("창업/투자", ["창업", "투자", "스타트업", "기업투자", "벤처", "지식재산", "D-8", "D-10-2"]),
    ("초청/사증발급", ["초청", "사증발급", "사증 발급", "사증발급인정서", "재외공관", "비자발급"]),
    ("체류연장/변경", ["체류기간 연장", "기간연장", "체류자격 변경", "자격변경", "체류자격 부여"]),
    ("외국인등록/신고", ["외국인등록", "등록사항", "체류지변경", "신고의무", "거소신고"]),
    ("재입국", ["재입국"]),
    ("지역특화", ["지역특화", "지역우수인재", "인구감소지역", "F-2-R", "E-7-4R", "F-3-R"]),
    ("재외동포", ["재외동포", "동포", "F-4", "H-2", "방문취업"]),
    ("단기방문/관광", ["단기방문", "관광", "방문", "C-3", "B-1", "B-2"]),
    ("난민/인도적", ["난민", "인도적", "G-1"]),
]

PROFILE_RULES = [
    ("초청인/고용주", ["초청인", "초청자", "고용주", "고용업체", "회사", "근무처", "사업장", "유치기관"]),
    ("외국인 근로자", ["근로자", "취업", "고용", "E-9", "E-10", "E-7", "숙련기능"]),
    ("유학생/연수생", ["유학생", "유학", "어학연수", "연수생", "D-2", "D-4"]),
    ("배우자/가족", ["배우자", "결혼", "혼인", "자녀", "부모", "가족", "동반"]),
    ("투자자/창업자", ["투자", "창업", "스타트업", "벤처", "기술창업"]),
]

ANSWER_FOCUS = {
    "required_documents": "제출서류 안내",
    "fee": "수수료 안내",
    "score_table": "점수표/배점 안내",
    "quota": "쿼터/허용인원 안내",
    "restriction": "제한사항/불허 사유 안내",
    "exception": "예외/특례/면제 안내",
}

FOLLOW_UP_INFO = {
    "결혼/배우자": ["혼인 여부", "배우자 국적", "국내/해외 신청 위치", "소득/주거/의사소통 요건"],
    "가족/동반": ["가족관계", "초청인 체류자격", "초청 목적", "체류 예정 기간"],
    "유학/연수": ["학교/교육기관", "과정 종류", "재학 여부", "한국어능력"],
    "아르바이트/시간제취업": ["현재 체류자격", "학교 과정", "근무시간", "근무처", "한국어능력"],
    "취업/고용": ["직무", "고용주", "학력/경력", "임금", "고용계약", "현재 체류자격"],
    "숙련기능/전환": ["현재 체류자격", "근무기간", "소득", "한국어능력", "점수", "추천서"],
    "창업/투자": ["투자금", "사업자등록/법인", "지식재산", "추천/승인 여부", "사업 분야"],
    "초청/사증발급": ["신청 위치", "초청인", "입국 목적", "체류 예정 기간", "재외공관/출입국기관 절차"],
    "체류연장/변경": ["현재 체류자격", "체류만료일", "변경 목적", "국내 체류 중인지 여부"],
    "외국인등록/신고": ["입국일", "체류지", "현재 체류자격", "신고 사유"],
    "재입국": ["출국 예정일", "재입국 예정일", "현재 체류자격", "입국규제 여부"],
    "지역특화": ["거주/근무 지역", "지자체 추천", "현재 체류자격", "소득", "가족 동반 여부"],
    "재외동포": ["동포 입증", "국적/출생 배경", "방문 목적", "취업 여부"],
    "단기방문/관광": ["방문 목적", "초청인 여부", "체류 예정 기간", "국적"],
    "난민/인도적": ["현재 신청 상태", "체류 기간", "취업 필요 사유", "보호/심사 진행 상황"],
}

INTENT_ROUTES = [
    {
        "route_id": "route_marriage_spouse",
        "user_intent": "한국인 배우자와 결혼 또는 결혼생활을 위한 비자/체류 상담",
        "example_questions": "한국인 배우자랑 결혼했는데 비자 뭐 해야 해?; 결혼비자 신청하려면 뭐가 필요해?; F-6 서류 알려줘",
        "situation_tags": "결혼/배우자; 가족/동반",
        "target_manuals": "visa; stay",
        "likely_codes": "F-6; F-6-1; F-6-2; F-6-3",
        "likely_petition_types": "사증발급; 체류자격 변경; 체류기간 연장; 외국인등록",
        "primary_filters": "user_situation_tags contains 결혼/배우자 OR primary_code starts F-6",
        "required_user_info": "혼인 여부; 배우자 국적; 국내/해외 신청 위치; 소득요건; 주거요건; 의사소통 요건; 자녀 유무",
        "answer_strategy": "먼저 입국 전 사증발급인지 국내 체류자격 변경/연장인지 구분한 뒤 대상, 제한, 제출서류 순서로 답변",
        "search_boost_terms": "한국인 배우자; 결혼비자; 결혼이민; 혼인; F-6; 배우자 비자",
    },
    {
        "route_id": "route_hire_foreign_worker",
        "user_intent": "한국 회사가 외국인 직원을 채용하거나 초청하려는 상황",
        "example_questions": "외국인 직원을 한국 회사에서 채용하려면?; 해외 개발자를 데려오려면 어떤 비자야?; E-7 채용 서류 알려줘",
        "situation_tags": "취업/고용; 초청/사증발급",
        "target_manuals": "visa; stay",
        "likely_codes": "E-1; E-2; E-3; E-4; E-5; E-6; E-7; E-9; E-10",
        "likely_petition_types": "사증발급; 사증발급인정서; 체류자격 변경; 근무처 변경/추가; 외국인등록",
        "primary_filters": "user_situation_tags contains 취업/고용 AND applicant_profile contains 초청인/고용주",
        "required_user_info": "직무; 고용주 업종; 학력/경력; 임금; 고용계약; 국내외 신청 위치; 추천서 필요 여부",
        "answer_strategy": "직무가 전문인력인지 비전문/선원/계절근로인지 먼저 나누고, 사증발급인정서와 제출서류를 확인",
        "search_boost_terms": "외국인 직원; 채용; 고용; 회사; E-7; 특정활동; 사증발급인정서; 고용추천서",
    },
    {
        "route_id": "route_student_part_time_work",
        "user_intent": "유학생 또는 연수생의 아르바이트/시간제 취업 가능 여부",
        "example_questions": "유학생인데 알바 가능한가요?; D-2 학생이 시간제 취업하려면?; 어학연수생 아르바이트 허가 필요해?",
        "situation_tags": "유학/연수; 아르바이트/시간제취업",
        "target_manuals": "stay",
        "likely_codes": "D-2; D-4",
        "likely_petition_types": "체류자격외 활동허가",
        "primary_filters": "user_situation_tags contains 아르바이트/시간제취업 OR petition_type = 체류자격외 활동허가",
        "required_user_info": "현재 체류자격; 학교/과정; 학기/방학 여부; 한국어능력; 근무시간; 근무처",
        "answer_strategy": "현재 체류자격과 과정별 허용시간을 확인하고 제한 업종, 제출서류, 허가 절차를 안내",
        "search_boost_terms": "유학생; 알바; 아르바이트; 시간제 취업; D-2; D-4; 체류자격외 활동허가",
    },
    {
        "route_id": "route_invite_parent_short_visit",
        "user_intent": "부모 또는 가족을 한국에 단기 초청하려는 상황",
        "example_questions": "부모님을 한국에 잠깐 모시고 오고 싶어요.; 외국인 배우자의 부모 초청 비자는?; 가족 단기방문 서류 알려줘",
        "situation_tags": "가족/동반; 초청/사증발급; 단기방문/관광",
        "target_manuals": "visa",
        "likely_codes": "C-3; F-1; F-1-5",
        "likely_petition_types": "사증발급; 초청",
        "primary_filters": "user_situation_tags contains 가족/동반 AND target_manuals contains visa",
        "required_user_info": "초청인 체류자격; 가족관계; 방문 목적; 체류 예정 기간; 초청 횟수; 소득/주거 입증",
        "answer_strategy": "단기방문(C-3)인지 결혼이민자 부모 등 가족(F-1-5)인지 먼저 구분하고 초청 제한과 제출서류를 안내",
        "search_boost_terms": "부모 초청; 가족 초청; 방문동거; F-1-5; C-3; 단기방문",
    },
    {
        "route_id": "route_e9_to_skilled_worker",
        "user_intent": "E-9 등 비전문 인력이 숙련기능인력으로 전환하려는 상황",
        "example_questions": "E-9로 일하다가 숙련기능인력으로 바꾸고 싶어요.; E-7-4 점수제 조건 알려줘; K-point E74 서류 뭐야?",
        "situation_tags": "취업/고용; 숙련기능/전환; 체류연장/변경",
        "target_manuals": "stay; visa",
        "likely_codes": "E-7-4; E-7-4R; E-9; E-10; H-2",
        "likely_petition_types": "체류자격 변경; 체류기간 연장; 외국인등록; 사증발급",
        "primary_filters": "user_situation_tags contains 숙련기능/전환 OR primary_code contains E-7-4",
        "required_user_info": "현재 체류자격; 근무기간; 현재 근무처; 소득; 한국어능력; 점수; 추천서; 지역특화 여부",
        "answer_strategy": "기본 대상 여부를 먼저 확인하고 점수표, 추천/쿼터, 제출서류, 제한사항 순서로 안내",
        "search_boost_terms": "E-9; E-7-4; E-7-4R; 숙련기능; K-point E74; 점수제; 체류자격 변경",
    },
    {
        "route_id": "route_startup_founder",
        "user_intent": "외국인이 한국에서 창업하거나 스타트업을 준비하는 상황",
        "example_questions": "스타트업 창업하려는 외국인은 어떤 비자가 맞나요?; 기술창업 비자 알려줘; D-8-4S 조건이 뭐야?",
        "situation_tags": "창업/투자; 초청/사증발급",
        "target_manuals": "visa; stay",
        "likely_codes": "D-8; D-8-4; D-8-4S; D-10-2",
        "likely_petition_types": "사증발급; 사증발급인정서; 체류자격 변경; 체류기간 연장",
        "primary_filters": "user_situation_tags contains 창업/투자 OR primary_code starts D-8 OR primary_code = D-10-2",
        "required_user_info": "창업 단계; 투자금; 법인/사업자등록 여부; 지식재산; 추천/평가 여부; 국내외 신청 위치",
        "answer_strategy": "창업 준비(D-10-2)인지 기업투자(D-8 계열)인지 나누고 추천/평가, 요건, 제출서류를 안내",
        "search_boost_terms": "스타트업; 창업; 기술창업; 기업투자; D-8-4; D-8-4S; D-10-2",
    },
]


def compact(value: object, max_chars: int = 1400) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def join_unique(values: Iterable[str], max_chars: int = 1400) -> str:
    out: list[str] = []
    for value in values:
        value = compact(value, 300)
        if value and value not in out:
            out.append(value)
    return compact("; ".join(out), max_chars)


def row_text(row: pd.Series, code_col: str, name_col: str) -> str:
    parts = [row.get(code_col, ""), row.get(name_col, "")]
    parts.extend(row.get(field, "") for field in TEXT_FIELDS if field in row.index)
    return compact(" ".join(str(part) for part in parts), 5000)


def situation_tags(text: str) -> list[str]:
    tags = [label for label, keywords in SITUATION_RULES if any(keyword in text for keyword in keywords)]
    return tags or ["일반 체류/비자 상담"]


def applicant_profile(text: str) -> str:
    profiles = [label for label, keywords in PROFILE_RULES if any(keyword in text for keyword in keywords)]
    return join_unique(profiles) or "외국인 본인"


def location_context(manual_key: str, petition_type: str, text: str) -> str:
    if manual_key == "visa":
        if "재외공관" in text:
            return "입국 전 해외 신청 또는 재외공관 절차"
        return "입국 전 비자/초청 절차"
    if petition_type in {"체류자격 변경", "체류기간 연장", "외국인등록", "근무처 변경/추가", "체류자격외 활동허가"}:
        return "국내 체류 중 출입국기관 민원"
    return "국내 체류 중 체류관리 절차"


def current_status_context(primary_code: str, primary_name: str, text: str) -> str:
    contexts = []
    if primary_code:
        contexts.append(f"관련 코드: {primary_code} {primary_name}".strip())
    for marker in ["현재 체류자격", "소지자", "등록외국인", "체류 중", "현재 근무처", "입국규제", "사증발급규제"]:
        if marker in text:
            contexts.append(marker)
    return join_unique(contexts, 900)


def required_user_info(tags: list[str], item_type: str, subsection_type: str) -> str:
    info: list[str] = []
    for tag in tags:
        info.extend(FOLLOW_UP_INFO.get(tag, []))
    if item_type == "required_documents" or subsection_type == "제출서류":
        info.extend(["공통서류 필요 여부", "해당자별 추가서류 여부"])
    if item_type == "score_table":
        info.extend(["점수 산정 항목", "가점/감점 해당 여부"])
    if item_type == "restriction":
        info.extend(["제한 사유 해당 여부", "위반/불허 이력"])
    return join_unique(info or ["국적", "현재 위치", "신청 목적", "현재 체류자격"], 1200)


def routing_hint(manual_key: str, petition_type: str, tags: list[str]) -> str:
    if manual_key == "visa":
        base = "사증민원: 입국 전 비자 발급/초청/사증발급인정서 확인"
    else:
        base = "체류민원: 국내 체류 중 변경/연장/등록/신고/허가 확인"
    if petition_type:
        base += f" -> {petition_type}"
    if tags:
        base += f" -> {tags[0]}"
    return base


def plain_summary(row: pd.Series, primary_code: str, primary_name: str) -> str:
    code_label = f"{primary_name}({primary_code})" if primary_code else primary_name or "공통사항"
    petition = compact(row.get("petition_type", ""))
    subsection = compact(row.get("subsection_type", ""))
    title = compact(row.get("section_title", ""), 160)
    body = compact(
        row.get("eligibility")
        or row.get("requirements")
        or row.get("mandatory_documents")
        or row.get("other_documents")
        or row.get("restrictions")
        or row.get("exceptions")
        or row.get("normalized_text"),
        260,
    )
    pieces = [piece for piece in [code_label, petition, subsection, title] if piece]
    summary = " / ".join(pieces)
    if body:
        summary += f": {body}"
    return compact(summary, 700)


def intent_keywords(tags: list[str], row: pd.Series, primary_code: str, primary_name: str) -> str:
    keywords = [*tags, primary_code, primary_name]
    keywords.extend(
        [
            row.get("petition_type", ""),
            row.get("subsection_type", ""),
            row.get("subtype_or_program", ""),
            row.get("section_title", ""),
        ]
    )
    if "결혼/배우자" in tags:
        keywords.extend(["한국인 배우자", "배우자 비자", "결혼 비자", "혼인 비자"])
    if "유학/연수" in tags:
        keywords.extend(["학생 비자", "유학생", "학교", "어학연수"])
    if "아르바이트/시간제취업" in tags:
        keywords.extend(["알바", "아르바이트", "시간제 취업", "유학생 근로"])
    if "취업/고용" in tags:
        keywords.extend(["외국인 직원", "채용", "고용", "취업비자", "회사"])
    if "창업/투자" in tags:
        keywords.extend(["스타트업", "창업비자", "투자비자", "기업투자"])
    if "가족/동반" in tags:
        keywords.extend(["부모 초청", "가족 초청", "동반가족", "자녀"])
    return join_unique(keywords, 1400)


def answer_focus(row: pd.Series) -> str:
    item_type = compact(row.get("item_type", ""))
    if item_type in ANSWER_FOCUS:
        return ANSWER_FOCUS[item_type]
    subsection = compact(row.get("subsection_type", ""))
    if subsection:
        return f"{subsection} 안내"
    return "일반 안내"


def build_chatbot_rows(manual_key: str, df: pd.DataFrame) -> list[dict[str, str]]:
    config = INPUTS[manual_key]
    rows: list[dict[str, str]] = []
    for idx, row in df.fillna("").iterrows():
        primary_code = compact(row.get(config["code_col"], ""))
        primary_name = compact(row.get(config["name_col"], ""))
        text = row_text(row, config["code_col"], config["name_col"])
        tags = situation_tags(text)
        summary = plain_summary(row, primary_code, primary_name)
        keyword_text = intent_keywords(tags, row, primary_code, primary_name)
        search_text = join_unique(
            [
                keyword_text,
                summary,
                row.get("eligibility", ""),
                row.get("requirements", ""),
                row.get("mandatory_documents", ""),
                row.get("other_documents", ""),
                row.get("restrictions", ""),
                row.get("exceptions", ""),
                row.get("normalized_text", ""),
            ],
            3200,
        )
        rows.append(
            {
                "record_id": f"{manual_key}_{idx + 1:06d}",
                "manual_type": compact(row.get("manual_type", "")),
                "source_pdf": compact(row.get("source_pdf", "")),
                "source_dataset": config["input_csv"].name,
                "code_type": config["code_type"],
                "primary_code": primary_code,
                "primary_name_ko": primary_name,
                "item_type": compact(row.get("item_type", "")),
                "petition_type": compact(row.get("petition_type", "")),
                "subsection_type": compact(row.get("subsection_type", "")),
                "subtype_or_program": compact(row.get("subtype_or_program", "")),
                "source_section_title": compact(row.get("section_title", "")),
                "user_situation_tags": join_unique(tags),
                "intent_keywords": keyword_text,
                "applicant_profile": applicant_profile(text),
                "current_location_context": location_context(manual_key, compact(row.get("petition_type", "")), text),
                "current_status_context": current_status_context(primary_code, primary_name, text),
                "plain_language_summary": summary,
                "required_user_info": required_user_info(tags, compact(row.get("item_type", "")), compact(row.get("subsection_type", ""))),
                "routing_hint": routing_hint(manual_key, compact(row.get("petition_type", "")), tags),
                "answer_focus": answer_focus(row),
                "eligibility": compact(row.get("eligibility", "")),
                "requirements": compact(row.get("requirements", "")),
                "common_documents": compact(row.get("common_documents", "")),
                "mandatory_documents": compact(row.get("mandatory_documents", "")),
                "other_documents": compact(row.get("other_documents", "")),
                "procedure": compact(row.get("procedure", "")),
                "restrictions": compact(row.get("restrictions", "")),
                "exceptions": compact(row.get("exceptions", "")),
                "fees": compact(row.get("fees", "")),
                "duration_or_validity": compact(row.get("duration_or_validity", "")),
                "quota_or_limit": compact(row.get("quota_or_limit", "")),
                "score_criteria": compact(row.get("score_criteria", "")),
                "search_text": search_text,
            }
        )
    return rows


def write_csv(path: Path, rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CHATBOT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in CHATBOT_COLUMNS})


def build_all() -> dict[str, int]:
    counts: dict[str, int] = {}
    for manual_key, config in INPUTS.items():
        df = pd.read_csv(config["input_csv"], dtype=str).fillna("")
        rows = build_chatbot_rows(manual_key, df)
        write_csv(config["output_csv"], rows)
        counts[manual_key] = len(rows)
    write_intent_routes()
    counts["routes"] = len(INTENT_ROUTES)
    return counts


def write_intent_routes() -> None:
    ROUTE_OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with ROUTE_OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ROUTE_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in INTENT_ROUTES:
            writer.writerow({column: compact(row.get(column, ""), 2400) for column in ROUTE_COLUMNS})


def main() -> None:
    counts = build_all()
    for manual_key, count in counts.items():
        if manual_key == "routes":
            print(f"routes: {count} chatbot intent routes")
        else:
            print(f"{manual_key}: {count} chatbot-ready rows")


if __name__ == "__main__":
    main()
