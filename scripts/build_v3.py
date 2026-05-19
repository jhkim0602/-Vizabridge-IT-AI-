#!/usr/bin/env python3
"""검수용 v3 CSV 빌더 — 정규화 MD → 28컬럼 CSV.

흐름:
1. `data/parsed/normalized/{stay,visa}_manual.md` 의 row 블록을 파싱
2. 같은 (비자코드, 신청종류) 묶음을 한 행으로 병합
3. 정규화 row의 필드(applicant_context, eligibility, ...)를 v3 컬럼으로 분배
   - `duration_or_validity` 는 사증유효기간 / 1회부여 체류기간 / 체류상한 3컬럼으로 분리
4. 상위코드/사증·체류 derive
5. 비자 흐름 매핑 (선행자격/다음단계/동반가족/키워드)
6. 검수 컬럼 추가 (검수상태=미검수, 검수메모="")

산출물:
- data/processed/체류매뉴얼_검수용_v3.csv
- data/processed/사증매뉴얼_검수용_v3.csv
- data/processed/체류매뉴얼_노션검수용_v3.csv (=검수용과 동일)
- data/processed/사증매뉴얼_노션검수용_v3.csv

이후 `scripts/fill_page_numbers.py` 로 출처에 페이지 번호 통합.

용법:
    .venv/bin/python scripts/build_v3.py
"""

from __future__ import annotations

import csv
import re
from collections import OrderedDict
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NORMALIZED_DIR = PROJECT_ROOT / "data" / "parsed" / "normalized"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# ---------------------------------------------------------------------------
# 컬럼 스키마 (v3)
# ---------------------------------------------------------------------------

V3_COLUMNS = [
    # 식별·분류 (4)
    "비자코드", "상위코드", "사증·체류", "신청종류",
    # 행정 내용 (15) — 표 데이터는 v3.1 에서 폐기 (점수표/쿼터/동반가족/수수료/자격요건 라우팅).
    # 기간은 v3.2 에서 3컬럼으로 분리 (사증유효기간 / 1회부여 체류기간 / 체류상한).
    "신청상황", "대상자", "자격요건", "절차", "수수료",
    "사증유효기간", "1회부여 체류기간", "체류상한",
    "제한", "예외", "의무사항", "점수표", "쿼터",
    "초청자", "추천·승인기관",
    # 자료 (2)
    "제출서류", "예상질문",
    # 출처 (1) — 페이지는 fill_page_numbers.py 가 추가
    "출처",
    # 흐름·검색 (4)
    "선행자격", "다음단계", "동반가족", "키워드",
    # 검수 (2)
    "검수상태", "검수메모",
]


# ---------------------------------------------------------------------------
# 정규화 MD 파서
# ---------------------------------------------------------------------------

OPEN_MARKER_RE = re.compile(
    r"<!--\s*vizabridge-normalize v1 chunk:\s*([^\s]+)\s+hash:\s*([^\s]+)\s+lines:\s*(\d+)-(\d+)\s*-->"
)
CLOSE_MARKER_RE = re.compile(r"<!--\s*end chunk:\s*([^\s]+)\s*-->")
ROW_HEADER_RE = re.compile(r"^###\s+row\s+.*$", re.MULTILINE)
FIELD_LINE_RE = re.compile(r"^-\s+([a-z_]+):\s*(.*)$", re.MULTILINE)
MULTILINE_VALUE_START_RE = re.compile(r"^-\s+([a-z_]+):\s*\|\s*$")


def parse_row_body(body: str) -> dict[str, str]:
    """`- field: value` 라인 및 `- field: |` 멀티라인 블록 파싱."""
    fields: dict[str, str] = {}
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        multi = MULTILINE_VALUE_START_RE.match(line)
        if multi:
            name = multi.group(1)
            collected: list[str] = []
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.startswith("    "):
                    collected.append(nxt[4:])
                    i += 1
                elif nxt.strip() == "" and i + 1 < len(lines) and lines[i + 1].startswith("    "):
                    collected.append("")
                    i += 1
                else:
                    break
            fields[name] = "\n".join(collected).rstrip()
            continue
        single = FIELD_LINE_RE.match(line)
        if single:
            fields[single.group(1)] = single.group(2).strip()
        i += 1
    return fields


def iter_row_blocks(text: str) -> Iterable[dict[str, str]]:
    """청크 마커 안의 `### row` 블록 파싱하여 row dict 리스트로 yield."""
    opens = list(OPEN_MARKER_RE.finditer(text))
    close_by_id = {m.group(1): m for m in CLOSE_MARKER_RE.finditer(text)}
    for open_m in opens:
        chunk_id = open_m.group(1)
        close_m = close_by_id.get(chunk_id)
        if not close_m or close_m.start() < open_m.end():
            continue
        chunk_body = text[open_m.end() : close_m.start()]
        positions = [m.start() for m in ROW_HEADER_RE.finditer(chunk_body)]
        if not positions:
            continue
        positions.append(len(chunk_body))
        for i in range(len(positions) - 1):
            row_text = chunk_body[positions[i] : positions[i + 1]]
            row_lines = row_text.splitlines()
            body = "\n".join(row_lines[1:])
            yield parse_row_body(body)


# ---------------------------------------------------------------------------
# 행 → v3 컬럼 매핑
# ---------------------------------------------------------------------------

# normalized 필드 → v3 컬럼 직접 매핑.
# duration_or_validity 는 직접 매핑하지 않고 _split_duration 으로 3컬럼에 분배.
DIRECT_MAP = {
    "applicant_context": "신청상황",
    "target_persons": "대상자",
    "eligibility": "자격요건",
    "requirements": "자격요건",  # eligibility 와 같은 컬럼으로
    "procedure": "절차",
    "fees": "수수료",
    "restrictions": "제한",
    "exceptions": "예외",
    "obligations": "의무사항",
    "score_criteria": "점수표",
    "quota_or_limit": "쿼터",
    "inviter_context": "초청자",
    "recommendation_or_approval": "추천·승인기관",
}


def derive_parent_code(visa_code: str) -> str:
    """비자코드 'F-6 (F-6-1)' → 상위코드 'F-6'."""
    return visa_code.split(" (", 1)[0].strip()


def merge_list(values: list[str], sep: str = "\n\n") -> str:
    """non-empty 값 dedup 후 sep 로 결합."""
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        v = v.strip()
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return sep.join(out)


# ---------------------------------------------------------------------------
# 기간 3분할 (사증유효기간 / 1회부여 체류기간 / 체류상한)
# ---------------------------------------------------------------------------
#
# 매뉴얼의 기간 정보는 통상 세 축이 한 셀에 줄바꿈으로 혼재한다:
#   - 사증유효기간: 사증 자체의 효력 기간 (단수/복수, 유효기간 N월/년)
#   - 1회부여 체류기간: 입국 시마다 부여되는 체류허가 기간 (체류기간 상한)
#   - 체류상한: 누적 또는 자격존속 상한 (재임기간·최장체류기간·범위 내)
#
# 라인 단위로 매칭하되, 한 라인이 두 축을 동시에 언급하면 양쪽에 모두 들어간다.

_VISA_VALIDITY_RE = re.compile(
    r"단수사증|복수사증|단·복수\s*사증|단·복수재입국허가|복수재입국허가"
    r"|사증유효기간"
    r"|유효기간\s*\d+\s*(?:개월|년|월|月)"
    r"|유효기간\s*\d+\s*년\s*이내"
    r"|재입국허가\s*(?:면제|복수)"
    r"|단·복수\s*비자|단수\s*비자|복수\s*비자"
    r"|단수\b|복수\b"  # "체류기간 1년 이내, 단수" 같은 trailing
)

_SINGLE_STAY_RE = re.compile(
    r"1회\s*부여|1회에\s*부여|체류기간\s*상한|체류기간의\s*상한"
    r"|체류기간\s*\d+\s*(?:일|개월|년)"
    r"|체류기간\s*[가-힣]*\s*\d+\s*(?:일|개월|년)\s*이내"
    r"|허용기간|허가기간|연장(?:허가)?\s*[:는]"
    r"|\d+차\s*연장"
    r"|체류기간\s*\d+일\s*\("
    r"|입국일로부터\s*\d+개월\s*미만"
)

_TOTAL_STAY_RE = re.compile(
    r"최장체류기간|총\s*체류기간|최대\s*\d+\s*(?:일|개월|년)"
    r"|최장\s*\d+\s*(?:일|개월|년)"
    r"|재임기간|공무수행기간|신분존속기간"
    r"|여권\s*유효기간\s*범위|범위\s*내"
    r"|협정상의?\s*체류기간"
    r"|법무부장관이\s*따로\s*정하는"
    r"|근로계약기간|재직기간|연구기간|교육기간|공연추천기간"
    r"|체류허가기간|체류허가\s*기간"
    r"|재고용\s*특례"
)

# 라인이 사실상 숫자+기간단위로만 끝나면 (예: "2년", "90일", "2년 이내") → 1회부여
_PLAIN_PERIOD_RE = re.compile(r"^\d+\s*(?:일|개월|년)(?:\s*이내|\s*이하)?$")


def _split_duration(text: str) -> tuple[str, str, str]:
    """기간 셀 본문을 (사증유효기간, 1회부여 체류기간, 체류상한) 3개로 분리."""
    if not text:
        return ("", "", "")

    visa_validity: list[str] = []
    single_stay: list[str] = []
    total_stay: list[str] = []

    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue

        is_visa = bool(_VISA_VALIDITY_RE.search(line))
        is_single = bool(_SINGLE_STAY_RE.search(line))
        is_total = bool(_TOTAL_STAY_RE.search(line))

        # 어느 정규식에도 잡히지 않으면 휴리스틱 fallback
        if not (is_visa or is_single or is_total):
            if _PLAIN_PERIOD_RE.match(line):
                is_single = True  # "2년" 같은 단독 표기는 통상 체류기간
            else:
                # 잘 모르겠는 라인 — 체류상한으로 폴백 (가장 일반적 의미)
                is_total = True

        if is_visa:
            visa_validity.append(line)
        if is_single:
            single_stay.append(line)
        if is_total:
            total_stay.append(line)

    def _dedup_join(items: list[str]) -> str:
        seen: set[str] = set()
        out: list[str] = []
        for s in items:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return "\n".join(out)

    return (
        _dedup_join(visa_validity),
        _dedup_join(single_stay),
        _dedup_join(total_stay),
    )


# 표 내용 라우팅용 키워드 → 컬럼 매핑. 우선순위 위에서 아래로.
_TABLE_ROUTING = [
    ("점수표", re.compile(r"점수|배점|만점|점 ?이상|합격선")),
    ("쿼터", re.compile(r"쿼터|허용인원|제재 ?기준|선발 ?인원|%|인원 ?\(|명 ?이내")),
    ("동반가족", re.compile(r"동반가족|동반 ?범위")),
    ("수수료", re.compile(r"수수료 ?일람|수수료 ?표")),
]


def _route_table_blob(text: str) -> str:
    """표 본문을 분석해 점수표 / 쿼터 / 동반가족 / 수수료 / 자격요건 중 적절한 컬럼명을 리턴.

    매뉴얼의 표는 종류가 다양해서 (점수표·쿼터표·국가 목록·약호 분류 등) v3 의 다른
    컬럼이 이미 자기 목적을 가진 경우 그쪽으로 흘려보내고, 그 외는 자격요건이 catchall.
    """
    for target, pat in _TABLE_ROUTING:
        if pat.search(text):
            return target
    return "자격요건"


def aggregate_rows(rows: list[dict[str, str]], manual_kind: str) -> list[dict[str, str]]:
    """같은 (비자코드, 신청종류) 그룹을 한 v3 행으로 병합."""
    groups: "OrderedDict[tuple[str, str], list[dict[str, str]]]" = OrderedDict()
    for r in rows:
        # 비자코드 정규화: subtype 이 있으면 "X (X-N)" 형식
        base = r.get("visa_code") or r.get("stay_status_code") or ""
        subtype = r.get("subtype_or_program", "").strip()
        if subtype and subtype != base:
            visa_code = f"{base} ({subtype})"
        else:
            visa_code = base
        petition = r.get("petition_type", "").strip()
        if not visa_code or not petition:
            continue
        groups.setdefault((visa_code, petition), []).append(r)

    out_rows: list[dict[str, str]] = []
    for (visa_code, petition), group in groups.items():
        new = {c: "" for c in V3_COLUMNS}
        new["비자코드"] = visa_code
        new["상위코드"] = derive_parent_code(visa_code)
        new["사증·체류"] = "사증" if manual_kind == "visa" else "체류"
        new["신청종류"] = petition
        new["검수상태"] = "미검수"

        # 내용 컬럼: 모든 row 의 같은 normalized 필드를 모아서 v3 컬럼에 결합
        for col in [c for c in V3_COLUMNS if c in DIRECT_MAP.values()]:
            keys = [k for k, v in DIRECT_MAP.items() if v == col]
            values = [r.get(k, "") for r in group for k in keys]
            new[col] = merge_list(values)

        # 기간: duration_or_validity 를 3컬럼으로 분리.
        # 그룹 안 여러 row 의 본문을 모은 뒤 라인 단위 분류.
        duration_blob = merge_list([r.get("duration_or_validity", "") for r in group])
        v_valid, s_stay, t_stay = _split_duration(duration_blob)
        new["사증유효기간"] = v_valid
        new["1회부여 체류기간"] = s_stay
        new["체류상한"] = t_stay

        # 제출서류 = common + mandatory + other documents (라벨 prefix)
        docs_parts: list[str] = []
        common = merge_list([r.get("common_documents", "") for r in group])
        mandatory = merge_list([r.get("mandatory_documents", "") for r in group])
        other = merge_list([r.get("other_documents", "") for r in group])
        if common:
            docs_parts.append(f"[공통서류]\n{common}")
        if mandatory:
            docs_parts.append(f"[필수서류]\n{mandatory}")
        if other:
            docs_parts.append(f"[기타서류]\n{other}")
        new["제출서류"] = "\n\n".join(docs_parts)

        # 표 내용은 별도 컬럼이 아니라 라우팅 로직으로 적절한 v3 컬럼에 흡수.
        # 표 요약(table_summary)과 표 항목(table_rows)을 합친 다음 키워드로
        # 점수표 / 쿼터 / 동반가족 / 수수료 / 자격요건 중 한 곳에 append.
        ts = merge_list([r.get("table_summary", "") for r in group])
        tr = merge_list([r.get("table_rows", "") for r in group])
        table_blob = "\n\n".join([x for x in (ts, tr) if x])
        if table_blob:
            target = _route_table_blob(table_blob)
            new[target] = merge_list([new[target], f"[표]\n{table_blob}"])

        # 예상질문 (LLM 출력에 있으면)
        new["예상질문"] = merge_list([r.get("expected_questions", "") for r in group], sep="\n")
        # 4개로 cap
        questions = [q for q in new["예상질문"].split("\n") if q.strip()][:4]
        new["예상질문"] = "\n".join(questions)

        # 출처: section_title 모음 (페이지는 fill_page_numbers.py 가 추가)
        new["출처"] = merge_list([r.get("section_title", "") for r in group])

        # 흐름 (선행자격/다음단계/동반가족/키워드)
        flow = visa_flow(visa_code, new["상위코드"])
        new["선행자격"] = flow["선행자격"]
        new["다음단계"] = flow["다음단계"]
        new["동반가족"] = flow["동반가족"]
        new["키워드"] = flow["키워드"]

        out_rows.append(new)
    return out_rows


# ---------------------------------------------------------------------------
# 비자 흐름 매핑
# ---------------------------------------------------------------------------

PARENT_FLOW = {
    "A-1": {"선행자격": "외국 정부에서 외교사절단·영사기관 구성원으로 파견",
            "다음단계": "A-2 공무, F-2 거주 (장기체류 변경)",
            "동반가족": "동반가족도 A-1 (배우자·자녀)",
            "키워드": "외교, 외교관, 공무·외교, 협정"},
    "A-2": {"선행자격": "외국 정부 파견 공무원",
            "다음단계": "A-1 외교, F-2 거주",
            "동반가족": "동반가족도 A-2",
            "키워드": "공무, 정부 파견, 공무·외교"},
    "A-3": {"선행자격": "SOFA·국제협정 적용 대상자",
            "다음단계": "F-2 거주",
            "동반가족": "동반가족도 A-3",
            "키워드": "SOFA, 협정, 미군, Fulbright"},
    "B-1": {"선행자격": "사증면제 협정국 국민",
            "다음단계": "자격변경 원칙 불가 (독일·캐나다 등 예외)",
            "동반가족": "-",
            "키워드": "사증면제, 단기방문, 무비자"},
    "B-2": {"선행자격": "관광통과 입국",
            "다음단계": "자격변경 원칙 불가",
            "동반가족": "-",
            "키워드": "관광통과, 단기방문"},
    "C-1": {"선행자격": "90일 이내 일시취재",
            "다음단계": "D-5 취재 (장기)",
            "동반가족": "-",
            "키워드": "단기취재, 언론"},
    "C-3": {"선행자격": "90일 이내 단기방문·관광",
            "다음단계": "자격변경 원칙 불가",
            "동반가족": "동반자 별도 신청",
            "키워드": "단기방문, 관광, 의료관광, 단체관광"},
    "C-4": {"선행자격": "90일 이내 단기취업·계절근로",
            "다음단계": "E-7, E-8 (장기)",
            "동반가족": "-",
            "키워드": "단기취업, 일시흥행, 계절근로"},
    "D-1": {"선행자격": "문화예술 활동 초청",
            "다음단계": "F-2 거주",
            "동반가족": "F-3 동반",
            "키워드": "문화예술, 비영리 연수"},
    "D-2": {"선행자격": "대학·대학원 입학허가",
            "다음단계": "D-10 구직, E-1~E-7 취업, F-2-7 점수제",
            "동반가족": "F-3 동반 (학사·석사·박사만)",
            "키워드": "유학, 학생, 학위과정, 어학연수"},
    "D-3": {"선행자격": "해외투자기업 산업연수 초청",
            "다음단계": "자격변경 제한적",
            "동반가족": "F-3 동반",
            "키워드": "기술연수, 산업연수"},
    "D-4": {"선행자격": "어학원·기관 입학 또는 대학생 단기연수",
            "다음단계": "D-2 유학 (정규과정 진학)",
            "동반가족": "-",
            "키워드": "일반연수, 어학연수, 한국어"},
    "D-5": {"선행자격": "외국 언론사·방송사 소속",
            "다음단계": "F-2 거주, F-5 영주",
            "동반가족": "F-3 동반",
            "키워드": "취재, 언론, 특파원"},
    "D-6": {"선행자격": "종교단체 파송",
            "다음단계": "F-2 거주, F-5 영주",
            "동반가족": "F-3 동반",
            "키워드": "종교, 선교, 종교활동"},
    "D-7": {"선행자격": "동일 계열 외국기업 파견명령",
            "다음단계": "F-2 거주, F-5 영주",
            "동반가족": "F-3 동반",
            "키워드": "주재, 파견, 외국기업 지사"},
    "D-8": {"선행자격": "외국인투자촉진법상 1억원 이상 투자",
            "다음단계": "F-5-5 (5억 이상) / F-5 영주",
            "동반가족": "F-3 동반",
            "키워드": "기업투자, 외국인투자, 창업"},
    "D-9": {"선행자격": "국내외 무역·수출 경영",
            "다음단계": "F-5 영주",
            "동반가족": "F-3 동반",
            "키워드": "무역경영, 산업기술, 수출"},
    "D-10": {"선행자격": "D-2 졸업 또는 점수제 60점 이상",
             "다음단계": "E-1~E-7 취업, F-2-7 점수제",
             "동반가족": "F-3 동반",
             "키워드": "구직, 졸업생, 취업준비"},
    "E-1": {"선행자격": "대학 교수·부교수·조교수 채용",
            "다음단계": "F-2-7 점수제, F-5-9 영주",
            "동반가족": "F-3 동반",
            "키워드": "교수, 강의, 학술"},
    "E-2": {"선행자격": "회화지도 자격 + 학사 학위 + TESL 등",
            "다음단계": "F-2-7, F-5 영주",
            "동반가족": "F-3 동반",
            "키워드": "회화지도, 영어강사, EPIK"},
    "E-3": {"선행자격": "석사 이상 학위 + 연구기관 채용",
            "다음단계": "F-2-7, F-5-9 영주",
            "동반가족": "F-3 동반",
            "키워드": "연구, 연구원, 학술연구"},
    "E-4": {"선행자격": "특수기술 보유 + 국내기업 초청",
            "다음단계": "F-2-7, F-5 영주",
            "동반가족": "F-3 동반",
            "키워드": "기술지도, 기술이전"},
    "E-5": {"선행자격": "의사·변호사·회계사 등 전문 자격증",
            "다음단계": "F-2-7, F-5 영주",
            "동반가족": "F-3 동반",
            "키워드": "전문직업, 변호사, 의사"},
    "E-6": {"선행자격": "예술·연예·체육 활동 초청",
            "다음단계": "F-2 거주, F-5 영주",
            "동반가족": "F-3 동반",
            "키워드": "예술흥행, 연예인, 운동선수"},
    "E-7": {"선행자격": "학력·경력 요건 + 국내기업 채용",
            "다음단계": "E-7-4 숙련 (변경), F-2-7 점수제, F-5 영주",
            "동반가족": "F-3 동반",
            "키워드": "특정활동, 전문인력, 외국인 채용"},
    "E-8": {"선행자격": "계절근로 양해각서 체결 지자체 초청",
            "다음단계": "단기 자격, 변경 제한적",
            "동반가족": "-",
            "키워드": "계절근로, 농어업"},
    "E-9": {"선행자격": "고용허가제 EPS-TOPIK + 사업장 매칭",
            "다음단계": "E-7-4 K-point E74 (4년+ 후)",
            "동반가족": "-",
            "키워드": "비전문취업, 고용허가제, 단순노무"},
    "E-10": {"선행자격": "선원 자격 + 해운회사 채용",
             "다음단계": "E-7-4 (4년+ 후)",
             "동반가족": "-",
             "키워드": "선원취업, 해운, 어선"},
    "F-1": {"선행자격": "국내 가족 초청 또는 친척 방문",
            "다음단계": "F-2 거주, F-6 결혼이민 (사실혼 등)",
            "동반가족": "본인이 동반자격",
            "키워드": "방문동거, 가족, 친척"},
    "F-2": {"선행자격": "점수제 80점·고소득·재외동포·난민 등 트랙별",
            "다음단계": "F-5 영주",
            "동반가족": "F-1 동반가족",
            "키워드": "거주, 장기거주, 점수제"},
    "F-3": {"선행자격": "주체류자(E-1~E-7, D-7~D-9 등)의 배우자·미성년 자녀",
            "다음단계": "주체류자 따라 변경",
            "동반가족": "본인이 동반자격",
            "키워드": "동반, 배우자, 자녀"},
    "F-4": {"선행자격": "재외동포법상 동포 (한국계 외국인)",
            "다음단계": "F-5 영주 (2년+ 거소)",
            "동반가족": "F-1 동반",
            "키워드": "재외동포, 한국계, 동포"},
    "F-5": {"선행자격": "D-7~E-7 또는 F-2 5년+ 체류 + 소득·재산 요건",
            "다음단계": "국적취득",
            "동반가족": "F-1, F-2-71 (점수제 자녀)",
            "키워드": "영주, 정착, 영주권"},
    "F-6": {"선행자격": "한국인과 혼인성립",
            "다음단계": "F-5 영주 (2년+ 후)",
            "동반가족": "F-1-12 자녀, F-1-5 부모",
            "키워드": "결혼이민, 한국인 배우자, 가족결합"},
    "G-1": {"선행자격": "난민신청·인도적체류·산재 등 기타 사유",
            "다음단계": "사유 해소 시 자격 정리",
            "동반가족": "G-1 동반",
            "키워드": "기타, 난민, 인도적체류"},
    "H-1": {"선행자격": "관광취업 협정국 국민 (만 18~30세)",
            "다음단계": "단기, 변경 제한적",
            "동반가족": "-",
            "키워드": "관광취업, 워킹홀리데이"},
    "H-2": {"선행자격": "재외동포 (방문취업 자격 부여)",
            "다음단계": "E-7-4 (4년+), F-4 재외동포",
            "동반가족": "-",
            "키워드": "방문취업, 재외동포, 단순노무"},
    "공통": {"선행자격": "-", "다음단계": "-", "동반가족": "-", "키워드": "공통사항, 행정 일반"},
}

SUB_OVERRIDE = {
    "F-6-1": {"선행자격": "한국에서 혼인이 성립된 외국인 배우자",
              "다음단계": "F-5-2 영주 (혼인 2년+ 후)",
              "동반가족": "F-1-12 자녀",
              "키워드": "국민의 배우자, 결혼이민"},
    "F-6-2": {"선행자격": "한국인과 혼인 중 출생 미성년 자녀를 양육하는 외국인 부 또는 모",
              "다음단계": "F-5 영주",
              "동반가족": "F-1-12 자녀",
              "키워드": "자녀양육, 한부모, 결혼이민"},
    "F-6-3": {"선행자격": "국민인 배우자의 사망·실종 등 귀책없는 혼인 단절",
              "다음단계": "F-5 영주",
              "동반가족": "F-1-5 부모",
              "키워드": "혼인단절, 사별, 결혼이민"},
    "E-7-4": {"선행자격": "E-9/E-10/H-2 자격 최근 10년 중 4년+ 체류 + 점수제 200점/300점",
              "다음단계": "F-2-7 점수제, F-5-16 영주",
              "동반가족": "F-3 동반",
              "키워드": "숙련기능, K-point E74, 점수제"},
    "F-2-7": {"선행자격": "D-7~E-7 또는 D-10 자격 + 점수제 80점 이상",
              "다음단계": "F-5-1 영주",
              "동반가족": "F-1-12 자녀",
              "키워드": "점수제 거주, 우수인재"},
    "F-2-R": {"선행자격": "D-7~E-7 또는 F-4 자격 인구감소지역 5년+ 거주",
              "다음단계": "F-5 영주",
              "동반가족": "F-1, F-3-1R",
              "키워드": "지역우수인재, 인구감소지역"},
    "F-2-T": {"선행자격": "GNI 3배+ 고소득 또는 첨단산업 인재",
              "다음단계": "F-5-T 영주",
              "동반가족": "F-3-T 동반",
              "키워드": "탑티어, Top-Tier, 고소득"},
    "F-2-71": {"선행자격": "F-2-7 또는 F-2-7S 자격자의 미성년 자녀",
               "다음단계": "성년 시 점수제 또는 영주 변경",
               "동반가족": "본인이 동반자격",
               "키워드": "점수제 자녀, 동반자녀"},
}


def visa_flow(visa_code: str, parent: str) -> dict[str, str]:
    """비자코드 → 흐름 정보. sub-code override 우선."""
    if " (" in visa_code:
        sub = visa_code.split("(", 1)[1].rstrip(")").strip()
        if sub in SUB_OVERRIDE:
            return SUB_OVERRIDE[sub]
    if parent in PARENT_FLOW:
        return PARENT_FLOW[parent]
    return {"선행자격": "", "다음단계": "", "동반가족": "", "키워드": ""}


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------


def build(manual_kind: str) -> tuple[int, int]:
    norm_path = NORMALIZED_DIR / f"{manual_kind}_manual.md"
    if not norm_path.exists():
        raise SystemExit(f"정규화 출력 없음: {norm_path}")
    text = norm_path.read_text(encoding="utf-8")
    rows = list(iter_row_blocks(text))

    v3_rows = aggregate_rows(rows, manual_kind)

    label = "체류" if manual_kind == "stay" else "사증"
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # 검수용 + 노션검수용 (현재는 동일 내용)
    for suffix in ("검수용", "노션검수용"):
        out = PROCESSED_DIR / f"{label}매뉴얼_{suffix}_v3.csv"
        with out.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=V3_COLUMNS)
            w.writeheader()
            w.writerows(v3_rows)

    return len(rows), len(v3_rows)


def main() -> int:
    for manual in ("stay", "visa"):
        src_n, out_n = build(manual)
        label = "체류" if manual == "stay" else "사증"
        print(f"  {label}: normalized rows {src_n} → v3 rows {out_n}")
    print("\n다음 단계: .venv/bin/python scripts/fill_page_numbers.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
