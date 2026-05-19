"""정규화 row 들을 (visa_code, petition_type) 묶음으로 집계해 v2 행 dict 생성."""

from __future__ import annotations

from collections import OrderedDict

from scripts.schema import BLANK, COLUMNS

from scripts.build_helpers.pivot import (
    ADMIN_COLUMNS,
    documents_blob,
    subsection_to_column,
    table_blob,
)


# (visa_code, petition_type) 키. dict 의 insertion order 가 묶음 순서를 결정한다.
GroupKey = tuple[str, str]


SOURCE_PDF: dict[str, str] = {
    "stay": "260504 체류민원 자격별 안내 매뉴얼.hwp",
    "visa": "260504 사증민원 자격별 안내 매뉴얼.hwp",
}


def manual_label(manual_type: str, manual_key: str) -> str:
    """'체류민원' / '사증민원' → '체류' / '사증'."""
    if "체류" in manual_type:
        return "체류"
    if "사증" in manual_type:
        return "사증"
    return "체류" if manual_key == "stay" else "사증"


def code_display(code: str, subtype: str) -> str:
    """visa_code + subtype → 'F-6 (F-6-1)' / 'F-6'."""
    code = (code or "").strip()
    subtype = (subtype or "").strip()
    if subtype and subtype != code:
        return f"{code} ({subtype})" if code else subtype
    return code


def _csv_to_list(value: str) -> list[str]:
    """콤마 분리 문자열 → trimmed list (빈 항목 제외)."""
    if not value:
        return []
    return [tok.strip() for tok in value.split(",") if tok.strip()]


def _multi_to_lines(value: str) -> list[str]:
    """줄바꿈 분리 문자열 → trimmed list."""
    if not value:
        return []
    return [ln.strip() for ln in value.splitlines() if ln.strip()]


def _ordered_unique(items: list[str]) -> list[str]:
    """입력 순서를 보존한 중복 제거."""
    seen: dict[str, None] = OrderedDict()
    for it in items:
        if it not in seen:
            seen[it] = None
    return list(seen.keys())


def _append_admin(target: dict[str, list[str]], column: str, value: str) -> None:
    """value(여러 줄 가능)를 행정구획 컬럼 버킷에 추가."""
    if not value or not value.strip():
        return
    target.setdefault(column, []).append(value.strip())


class GroupAggregator:
    """(visa_code, petition_type) 단위로 row 들을 누적."""

    def __init__(self, manual_key: str) -> None:
        self.manual_key = manual_key
        self.groups: "OrderedDict[GroupKey, dict]" = OrderedDict()

    def add(self, fields: dict[str, str], chunk_id: str) -> None:
        code_field = "stay_status_code" if self.manual_key == "stay" else "visa_code"
        name_field = "stay_status_name_ko" if self.manual_key == "stay" else "visa_name_ko"

        visa_code = (fields.get(code_field) or "").strip()
        petition = (fields.get("petition_type") or "").strip()
        if not visa_code or not petition:
            # 식별 키가 없으면 스킵 (data hygiene 위반은 위에서 raise 됨)
            return

        key: GroupKey = (visa_code, petition)
        bucket = self.groups.get(key)
        if bucket is None:
            bucket = {
                "visa_code": visa_code,
                "visa_name_ko": (fields.get(name_field) or "").strip(),
                "petition": petition,
                "manual_type": (fields.get("manual_type") or "").strip(),
                # 17 행정 컬럼: 각각 list[str] 로 누적, 마지막에 join.
                "admin": {col: [] for col in ADMIN_COLUMNS},
                # 메타 누적
                "subtypes": [],
                "section_titles": [],
                "chunk_ids": [],
                "keywords": [],
                "related": [],
                "expected_q": [],
                "excerpts": [],
                "source_pages": [],
            }
            self.groups[key] = bucket

        admin = bucket["admin"]

        # 1) subsection_type 기반 기본 매핑
        subsection = (fields.get("subsection_type") or "").strip()
        col = subsection_to_column(subsection)

        # subsection 의 "본문"이 될 자료를 결정한다. 사양상 매핑 표에 따라
        # 어떤 필드를 메인 본문으로 쓸지 다르므로, subsection 별로
        # 가장 관련 깊은 필드를 골라 admin[col] 에 넣는다.
        primary_field = {
            "대상": fields.get("target_persons") or fields.get("applicant_context") or "",
            "요건": fields.get("requirements") or fields.get("eligibility") or "",
            "제출서류": "",  # 제출서류는 아래 documents blob 로 처리
            "절차": fields.get("procedure") or "",
            "수수료": fields.get("fees") or "",
            "기간": fields.get("duration_or_validity") or "",
            "제한": fields.get("restrictions") or "",
            "예외": fields.get("exceptions") or "",
            "점수표": fields.get("score_criteria") or "",
            "쿼터": fields.get("quota_or_limit") or "",
        }.get(subsection, "")

        if primary_field:
            _append_admin(admin, col, primary_field)

        # 2) 필드 단위 cross-mapping (subsection 매핑과 별개로 모든 row 에 적용)
        _append_admin(admin, "신청상황", fields.get("applicant_context") or "")
        # target_persons / eligibility / requirements 는 위 1) 에서 이미
        # 적절한 subsection 에 들어갔을 수 있으나, "다른" subsection 인
        # row 에서도 정보 손실을 막기 위해 항상 해당 컬럼에 추가한다.
        if subsection != "대상":
            _append_admin(admin, "대상", fields.get("target_persons") or "")
        if subsection != "요건":
            _append_admin(admin, "자격요건", fields.get("eligibility") or "")
            _append_admin(admin, "자격요건", fields.get("requirements") or "")
        # 제출서류 blob 은 라벨 없이 한 덩어리로
        docs = documents_blob(
            fields.get("common_documents") or "",
            fields.get("mandatory_documents") or "",
            fields.get("other_documents") or "",
        )
        if docs:
            _append_admin(admin, "제출서류", docs)

        if subsection != "절차":
            _append_admin(admin, "절차", fields.get("procedure") or "")
        if subsection != "수수료":
            _append_admin(admin, "수수료", fields.get("fees") or "")
        if subsection != "기간":
            _append_admin(admin, "기간", fields.get("duration_or_validity") or "")
        if subsection != "제한":
            _append_admin(admin, "제한", fields.get("restrictions") or "")
        if subsection != "예외":
            _append_admin(admin, "예외", fields.get("exceptions") or "")
        if subsection != "점수표":
            _append_admin(admin, "점수표", fields.get("score_criteria") or "")
        if subsection != "쿼터":
            _append_admin(admin, "쿼터", fields.get("quota_or_limit") or "")

        _append_admin(admin, "의무사항", fields.get("obligations") or "")
        _append_admin(admin, "초청자", fields.get("inviter_context") or "")
        _append_admin(admin, "추천·승인기관", fields.get("recommendation_or_approval") or "")

        tbl = table_blob(fields.get("table_summary") or "", fields.get("table_rows") or "")
        if tbl:
            _append_admin(admin, "표 데이터", tbl)

        # subsection 이 위 매핑 표에 없으면 (예: 공통사항/의무사항 등) → 참고사항
        if subsection and subsection not in {
            "대상", "요건", "제출서류", "절차", "수수료", "기간",
            "제한", "예외", "점수표", "쿼터",
        }:
            # primary_field 가 빈 케이스에서 정보 손실을 막기 위해 section_title
            # + 가능한 본문 (eligibility/requirements/normalized_text 같은 자유 텍스트)
            # 일부도 참고사항으로 흘려보낸다.
            fallback = fields.get("normalized_text") or ""
            _append_admin(admin, "참고사항", fallback)

        # 3) 메타 누적
        subtype = (fields.get("subtype_or_program") or "").strip()
        if subtype:
            bucket["subtypes"].append(subtype)
        section_title = (fields.get("section_title") or "").strip()
        if section_title:
            bucket["section_titles"].append(section_title)
        if chunk_id:
            bucket["chunk_ids"].append(chunk_id)

        bucket["keywords"].extend(_csv_to_list(fields.get("keywords") or ""))
        bucket["related"].extend(_csv_to_list(fields.get("related_visa_codes") or ""))
        bucket["expected_q"].extend(_multi_to_lines(fields.get("expected_questions") or ""))
        excerpt = (fields.get("source_excerpt") or "").strip()
        if excerpt:
            bucket["excerpts"].append(excerpt)
        page = (fields.get("source_page") or "").strip()
        if page:
            bucket["source_pages"].append(page)

    # -----------------------------------------------------------------
    def finalize_rows(self, chunk_lines: dict[str, tuple[int, int]]) -> list[dict[str, str]]:
        """누적된 그룹을 v2 32컬럼 dict 리스트로 변환."""
        from scripts.build_helpers.sources import line_range_label

        out: list[dict[str, str]] = []
        for (visa_code, petition), bucket in self.groups.items():
            row: dict[str, str] = {col: BLANK for col in COLUMNS}

            subtype = _ordered_unique(bucket["subtypes"])
            primary_subtype = subtype[0] if subtype else ""

            row["비자코드"] = code_display(visa_code, primary_subtype)
            row["상위코드"] = visa_code
            row["사증·체류"] = manual_label(bucket["manual_type"], self.manual_key)
            row["신청종류"] = petition
            row["하위프로그램"] = primary_subtype

            # 17 행정 컬럼 — list 를 줄바꿈으로 join (입력 순서 보존, 중복 제거)
            for col in ADMIN_COLUMNS:
                lines = _ordered_unique(bucket["admin"].get(col, []))
                row[col] = "\n".join(lines) if lines else BLANK

            # 출처
            row["원본파일"] = SOURCE_PDF[self.manual_key]
            sections = _ordered_unique(bucket["section_titles"])
            row["섹션"] = "\n".join(sections) if sections else BLANK
            pages = _ordered_unique(bucket["source_pages"])
            row["페이지"] = ", ".join(pages) if pages else BLANK
            chunk_ids = _ordered_unique(bucket["chunk_ids"])
            ranges = [
                line_range_label(cid, chunk_lines, self.manual_key) for cid in chunk_ids
            ]
            ranges = [r for r in ranges if r]
            row["원본 라인범위"] = "\n".join(ranges) if ranges else BLANK

            # 관계·검색
            related = _ordered_unique(bucket["related"])
            row["연계비자"] = ", ".join(related) if related else BLANK
            keywords = _ordered_unique(bucket["keywords"])
            row["키워드"] = ", ".join(keywords) if keywords else BLANK
            excerpts = _ordered_unique(bucket["excerpts"])
            row["원문발췌"] = "\n\n".join(excerpts) if excerpts else BLANK

            # 검수
            expected = _ordered_unique(bucket["expected_q"])[:4]
            row["예상질문"] = "\n".join(expected) if expected else BLANK
            row["검수상태"] = "미검수"
            row["검수메모"] = BLANK

            out.append(row)
        return out
