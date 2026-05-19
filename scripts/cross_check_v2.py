#!/usr/bin/env python3
"""v2 CSV ↔ raw MD cross-check.

지정된 (visa_code, petition_type) 묶음 10개에 대해:
- v2 CSV의 해당 행 찾기
- 행에서 채워진 핵심 컬럼 1~2개 sample 출력
- ``원문발췌`` 컬럼 vs raw MD 의 ``원본 라인범위`` 텍스트 비교 (verbatim 여부)
- 불일치 발견 시 보고
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "parsed" / "raw"

INPUT_FILES = {
    "stay": ("체류매뉴얼_검수용_v2.csv", "stay_manual.md"),
    "visa": ("사증매뉴얼_검수용_v2.csv", "visa_manual.md"),
}

# (manual_key, visa_code_match, petition_type, hint) — 10건
SAMPLES = [
    ("stay", "F-6 (F-6-1)", "체류자격 변경", "F-6-1 변경"),
    ("stay", "E-7-4", "체류자격 변경", "E-7-4 K-point E74"),
    ("visa", "D-2", "사증발급", "D-2 사증발급"),
    ("visa", "A-1", "사증발급", "A-1 사증발급"),
    ("stay", "F-5", "체류자격 변경", "F-5 변경"),
    ("visa", "C-3-3", "사증발급", "C-3-3 의료관광"),
    ("visa", "D-8", "사증발급", "D-8 사증발급"),
    ("visa", "E-9", "사증발급", "E-9 사증발급"),
    ("stay", "F-4", "체류자격 부여", "F-4 부여"),
    ("stay", "H-2", "체류기간 연장", "H-2 연장"),
]


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def find_row(
    rows: list[dict[str, str]], code: str, petition: str
) -> tuple[dict[str, str] | None, str]:
    """비자코드 + 신청종류 행 찾기. (row, match_kind) 반환.

    match_kind: 'exact_code+pet' / 'contains+pet' / 'base+pet' /
                'exact_code(any_pet)' / 'base(any_pet)' / 'none'
    """
    # 1순위: 비자코드 정확 일치 + 신청종류 일치
    for r in rows:
        if r.get("비자코드", "").strip() == code and r.get("신청종류", "").strip() == petition:
            return r, "exact_code+pet"
    # 2순위: 비자코드 포함 + 신청종류 일치
    for r in rows:
        if code in r.get("비자코드", "") and r.get("신청종류", "").strip() == petition:
            return r, "contains+pet"
    # 3순위: 상위코드 일치 + 신청종류 일치
    base = code.split("(", 1)[0].strip()
    for r in rows:
        if r.get("상위코드", "").strip() == base and r.get("신청종류", "").strip() == petition:
            return r, "base+pet"
    # 4순위 fallback: 비자코드 정확 일치, 신청종류 무시
    for r in rows:
        if r.get("비자코드", "").strip() == code:
            return r, "exact_code(any_pet)"
    # 5순위 fallback: 비자코드 포함, 신청종류 무시
    for r in rows:
        if code in r.get("비자코드", ""):
            return r, "contains(any_pet)"
    # 6순위 fallback: 상위코드 일치
    for r in rows:
        if r.get("상위코드", "").strip() == base:
            return r, "base(any_pet)"
    return None, "none"


_RANGE_RE = re.compile(r"(\d+)\s*[-~]\s*(\d+)")


def parse_ranges(value: str) -> list[tuple[int, int]]:
    """``원본 라인범위`` 컬럼: 여러 ``stay_manual.md:123-145`` 가
    줄바꿈 또는 콤마로 묶일 수 있다. 모든 (start, end) 페어 추출.
    """
    if not value:
        return []
    return [(int(s), int(e)) for s, e in _RANGE_RE.findall(value)]


def read_md_lines(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as f:
        return f.read().splitlines()


def extract_md(lines: list[str], start: int, end: int) -> str:
    s = max(1, start) - 1
    e = min(len(lines), end)
    return "\n".join(lines[s:e])


_QUOTE_MAP = str.maketrans({
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "·": "·",
})


def normalize(text: str) -> str:
    """비교용 정규화: 인용부호 통일 + 마크다운 헤더(``#``)/리스트(``-``)
    프리픽스 제거 + 공백 압축.
    """
    text = text.translate(_QUOTE_MAP)
    # 줄별로 markdown header prefix 제거
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        # 헤더 ``#`` / ``##`` ... 제거
        line = re.sub(r"^#+\s*", "", line)
        # 빈 줄은 스킵
        if line:
            cleaned_lines.append(line)
    joined = " ".join(cleaned_lines)
    return re.sub(r"\s+", " ", joined).strip()


def summarize_filled(row: dict[str, str], cols: list[str], maxlen: int = 80) -> list[str]:
    out: list[str] = []
    for c in cols:
        v = (row.get(c) or "").strip()
        if v:
            short = v.replace("\n", " ⏎ ")
            if len(short) > maxlen:
                short = short[:maxlen] + "..."
            out.append(f"    {c}: {short}")
        if len(out) >= 2:
            break
    return out


def cross_check_one(manual_key: str, code: str, petition: str, hint: str) -> dict[str, object]:
    csv_name, md_name = INPUT_FILES[manual_key]
    rows = load_rows(SRC_DIR / csv_name)
    md_lines = read_md_lines(RAW_DIR / md_name)

    row, match_kind = find_row(rows, code, petition)
    if not row:
        return {
            "manual": manual_key,
            "code": code,
            "petition": petition,
            "found": False,
            "match_kind": match_kind,
            "issues": ["행을 찾지 못함"],
        }

    excerpt = (row.get("원문발췌") or "").strip()
    rng_str = (row.get("원본 라인범위") or "").strip()
    ranges = parse_ranges(rng_str)

    issues: list[str] = []
    verbatim = None
    md_snippet_total_len = 0

    sentence_match_rate: float | None = None
    if ranges:
        # 라인범위가 여러 개일 수 있으므로 모두 합쳐서 비교 대상으로 둠.
        slices = [extract_md(md_lines, s, e) for s, e in ranges]
        md_concat = "\n".join(slices)
        md_snippet_total_len = len(md_concat)
        if excerpt:
            norm_md = normalize(md_concat)
            # 1) contiguous verbatim 판정
            norm_exc = normalize(excerpt)
            verbatim = norm_exc in norm_md

            # 2) 문장 단위 매칭 — 원문발췌의 각 줄(공백 정규화 후)이 MD에 substring 으로 있는지.
            #    excerpt 는 builder 가 라인 범위 안의 비연속 sentence 를 concat 하므로,
            #    contiguous 가 아니더라도 sentence-level 매칭이 verbatim 의 실질적 지표.
            raw_chunks = [
                normalize(c)
                for c in re.split(r"[\n]+", excerpt)
                if normalize(c)
            ]
            matched = [c for c in raw_chunks if c and c in norm_md]
            sentence_match_rate = len(matched) / len(raw_chunks) if raw_chunks else 0.0

            if not verbatim:
                if sentence_match_rate is not None and sentence_match_rate >= 0.9:
                    issues.append(
                        f"non-contiguous verbatim (sentence-match {sentence_match_rate*100:.0f}%)"
                    )
                elif sentence_match_rate is not None and sentence_match_rate >= 0.5:
                    issues.append(
                        f"partial sentence-match {sentence_match_rate*100:.0f}% — 일부 sentence 가 라인범위에 없음"
                    )
                else:
                    issues.append(
                        f"낮은 sentence-match {sentence_match_rate*100:.0f}% — 라인범위와 본문 불일치 의심"
                    )
    else:
        issues.append(f"라인범위 파싱 실패: {rng_str!r}")

    # 채움 샘플 컬럼: 행정 내용 그룹 중 자격요건/제출서류/수수료/기간/제한
    sample_cols = ["자격요건", "제출서류", "수수료", "기간", "제한", "절차", "대상"]
    samples = summarize_filled(row, sample_cols)

    # match_kind 가 신청종류를 만족하지 못한 경우 이슈 추가
    if match_kind in ("exact_code(any_pet)", "contains(any_pet)", "base(any_pet)"):
        issues.append(
            f"신청종류 mismatch: spec={petition!r}, actual={row.get('신청종류','')!r} "
            f"(match_kind={match_kind})"
        )

    return {
        "manual": manual_key,
        "code": code,
        "actual_code": row.get("비자코드", ""),
        "actual_petition": row.get("신청종류", ""),
        "petition": petition,
        "match_kind": match_kind,
        "hint": hint,
        "found": True,
        "section": row.get("섹션", ""),
        "range": rng_str,
        "verbatim": verbatim,
        "issues": issues,
        "samples": samples,
        "excerpt_len": len(excerpt),
        "md_len": md_snippet_total_len,
        "sentence_match_rate": sentence_match_rate,
    }


def write_report(results: list[dict]) -> Path:
    out_path = ROOT / "output" / "quality" / "v2" / "v2_cross_check_report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# v2 ↔ raw MD cross-check 보고서",
        "",
        f"- 샘플 수: {len(results)}",
        "",
        "## 컬럼",
        "- match_kind: exact_code+pet (best) / contains+pet / base+pet / *(any_pet) (fallback)",
        "- verbatim(contiguous): 원문발췌가 라인범위 내 연속 substring으로 발견되는가",
        "- sentence-match: 원문발췌의 sentence 중 라인범위 내 substring 비율",
        "",
        "| # | manual | spec code | spec petition | actual code | actual petition | match_kind | verbatim | sentence-match | 이슈 |",
        "|---:|---|---|---|---|---|---|:---:|---:|---|",
    ]
    for i, r in enumerate(results, 1):
        if not r["found"]:
            lines.append(
                f"| {i} | {r['manual']} | {r['code']} | {r['petition']} | (행 없음) | - | "
                f"{r.get('match_kind','none')} | - | - | 행 못 찾음 |"
            )
            continue
        smr = r.get("sentence_match_rate")
        smr_str = f"{smr*100:.0f}%" if smr is not None else "n/a"
        iss = "; ".join(r["issues"]) if r["issues"] else ""
        lines.append(
            f"| {i} | {r['manual']} | {r['code']} | {r['petition']} | "
            f"{r['actual_code']} | {r['actual_petition']} | {r['match_kind']} | "
            f"{'O' if r['verbatim'] else 'X'} | {smr_str} | {iss} |"
        )
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def main() -> int:
    results = [cross_check_one(*s) for s in SAMPLES]

    print("\n=== v2 ↔ raw MD cross-check (10건) ===\n")
    contiguous_verbatim = 0
    high_sentence_match = 0  # >= 0.9
    issue_count = 0
    for r in results:
        head = f"[{r['manual']}] {r['code']} / {r['petition']}"
        if not r["found"]:
            print(f"{head}  → 행 못 찾음 (match_kind={r.get('match_kind')})")
            issue_count += 1
            continue
        section = r['section'].replace('\n', ' | ')
        rng = r['range'].replace('\n', ' ; ')
        print(f"{head}")
        print(
            f"  실제 비자코드: {r['actual_code']} (신청={r['actual_petition']}, "
            f"match={r['match_kind']}) | 섹션: {section[:80]} | 라인범위: {rng[:90]}"
        )
        smr = r.get("sentence_match_rate")
        smr_str = f"{smr*100:.0f}%" if smr is not None else "n/a"
        print(
            f"  verbatim(contiguous): {r['verbatim']}  | sentence-match: {smr_str}"
            f"  | 원문발췌 len={r['excerpt_len']} / MD slice len={r['md_len']}"
        )
        for s in r["samples"]:
            print(s)
        if r["verbatim"]:
            contiguous_verbatim += 1
        if smr is not None and smr >= 0.9:
            high_sentence_match += 1
        if r["issues"]:
            for iss in r["issues"]:
                print(f"  ⚠ {iss}")
            if not (smr is not None and smr >= 0.9 and r.get("match_kind", "").endswith("+pet")):
                issue_count += 1
        print()
    print(
        f"=== 요약: contiguous-verbatim {contiguous_verbatim}/10, "
        f"sentence-match≥90% {high_sentence_match}/10, 이슈 {issue_count}/10 ==="
    )
    report_path = write_report(results)
    print(f"보고서: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
