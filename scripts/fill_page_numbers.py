#!/usr/bin/env python3
"""v4 CSV 의 출처 컬럼에 PDF 페이지 번호를 통합한다.

흐름:
1. HWP → PDF 변환 결과 (`data/raw/pdf/*.pdf`) 를 pdfplumber 로 페이지별 텍스트 추출
2. 캐시 (`data/raw/pdf/.cache/{stay,visa}_pages.json`) 에 저장 (재실행 시 빠름)
3. 각 v4 CSV 행의 핵심 컬럼(자격요건/신청상황/절차/제출서류 등) 텍스트를
   PDF 페이지 텍스트와 fuzzy 매칭하여 페이지 번호 결정
4. 출처 컬럼을 `"<섹션> (p. NNN)"` 형식으로 갱신
5. 동기화: CSV 갱신 후 동일 디렉토리의 xlsx 도 재생성

매칭 알고리즘 핵심:
- 텍스트 정규화: NFC + 구두점 제거 + 한글 중복 자모 압축 (`외외 → 외`)
  (LibreOffice + H2Orestart 변환에서 발생하는 문자 중복 버그 보정)
- 슬라이딩 윈도우 (50→30→18자) + 점수 투표
- 직전 행과 가까운 페이지 가중치 (±8쪽 이내 2.5배, 60쪽+ 0.15배) — boilerplate 오매칭 회피
- 인접 페이지 그룹화 (`p. 442~444` 형식)
- 1차 실패 시 출처 라벨·핵심 컬럼 텍스트로 fallback

용법:
    .venv/bin/python scripts/fill_page_numbers.py
    .venv/bin/python scripts/fill_page_numbers.py stay
    .venv/bin/python scripts/fill_page_numbers.py both --force

선행 조건:
- HWP → PDF 변환 완료 (`brew install --cask libreoffice` + H2Orestart oxt)
- v4 CSV 생성 (`scripts/build_v4.py`)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Optional

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
PDF_DIR = ROOT / "data" / "raw" / "pdf"
CACHE_DIR = PDF_DIR / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PDFS = {
    "stay": Path(os.environ.get("STAY_PDF", str(PDF_DIR / "260504 체류민원 자격별 안내 매뉴얼.pdf"))),
    "visa": Path(os.environ.get("VISA_PDF", str(PDF_DIR / "260504 사증민원 자격별 안내 매뉴얼.pdf"))),
}

CSV_PATHS = {
    "stay": [PROCESSED / "체류매뉴얼_최종_v4_26col.csv"],
    "visa": [PROCESSED / "사증매뉴얼_최종_v4_26col.csv"],
}


# ---------------------------------------------------------------------------
# 텍스트 정규화 (매칭 정확도의 핵심)
# ---------------------------------------------------------------------------

# HWP → PDF 변환 시 발생하는 한글 자음 중복 (외외 / 국국 / 인인) 압축
DUP_KOREAN_RE = re.compile(r"([가-힣])\1+")
# 공백·구두점·괄호·구분자 제거 (PDF 변환에서 일관되지 않게 렌더링됨)
NOISE_RE = re.compile(r"[\s,.·:;()\[\]【】「」『』<>＜＞|/＼\-_]+")


def normalize(text: str) -> str:
    """매칭용 정규화: NFC → 노이즈 제거 → 한글 중복 압축."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = NOISE_RE.sub("", text)
    text = DUP_KOREAN_RE.sub(r"\1", text)
    return text


# ---------------------------------------------------------------------------
# PDF → 페이지별 텍스트 (캐시)
# ---------------------------------------------------------------------------


def extract_pages(pdf_path: Path, cache_path: Path, force: bool = False) -> dict[int, str]:
    """PDF 페이지별 텍스트 추출. JSON 캐시 사용."""
    if cache_path.exists() and not force:
        try:
            with cache_path.open(encoding="utf-8") as f:
                data = json.load(f)
            arr = data.get("pages", [])
            return {i + 1: normalize(t) for i, t in enumerate(arr)}
        except Exception:
            pass
    print(f"  PDF 추출 중: {pdf_path.name}")
    pages: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    with cache_path.open("w", encoding="utf-8") as f:
        json.dump({"pages": pages}, f, ensure_ascii=False)
    print(f"  캐시 저장: {cache_path}  ({len(pages)} 페이지)")
    return {i + 1: normalize(t) for i, t in enumerate(pages)}


# ---------------------------------------------------------------------------
# 페이지 매칭
# ---------------------------------------------------------------------------


def find_page(needle: str, pages: dict[int, str], hint: Optional[int] = None) -> Optional[int]:
    """슬라이딩 윈도우 + 점수 투표 + hint 가중치."""
    if not needle or len(needle) < 8:
        return None
    n = normalize(needle)
    for win in (50, 30, 18):
        if len(n) < win:
            continue
        candidates: dict[int, float] = {}
        step = 8
        for start in range(0, len(n) - win + 1, step):
            snippet = n[start : start + win]
            for page_num, page_text in pages.items():
                if snippet in page_text:
                    score = 1.0
                    if hint is not None:
                        d = abs(page_num - hint)
                        if d <= 8:
                            score *= 2.5
                        elif d > 60:
                            score *= 0.15
                    candidates[page_num] = candidates.get(page_num, 0) + score
        if candidates:
            return sorted(candidates.items(), key=lambda x: (-x[1], abs(x[0] - (hint or 0))))[0][0]
    return None


def page_num_from_string(s: str) -> Optional[int]:
    m = re.search(r"\d+", s or "")
    return int(m.group()) if m else None


def previous_page_hint(rows: list[dict[str, str]], i: int) -> Optional[int]:
    """앞쪽에서 페이지 정보가 채워진 행의 페이지 번호 추출 (같은 상위코드 우선)."""
    parent = rows[i].get("상위코드", "")
    for off in range(1, 30):
        for j in (i - off, i + off):
            if 0 <= j < len(rows):
                pg = page_num_from_string(rows[j].get("출처", "").split("p. ")[-1])
                if pg and rows[j].get("상위코드") == parent:
                    return pg
    # 같은 부모 없으면 그냥 가까운 행
    for off in range(1, 30):
        for j in (i - off, i + off):
            if 0 <= j < len(rows):
                pg = page_num_from_string(rows[j].get("출처", "").split("p. ")[-1])
                if pg:
                    return pg
    return None


SEARCH_COLUMNS = ("자격요건", "신청상황", "제출서류", "절차", "제한", "예외", "기간", "대상자")


def assign_pages(csv_path: Path, pages: dict[int, str]) -> tuple[int, int]:
    with csv_path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
        rows = list(reader)
    if not rows:
        return 0, 0

    prev_page: Optional[int] = None
    matched = 0
    for i, r in enumerate(rows):
        original_src = r.get("출처", "").strip()
        # 출처에 이미 페이지가 있으면 유지
        if "p." in original_src:
            matched += 1
            m = re.search(r"p\.\s*(\d+)", original_src)
            if m:
                prev_page = int(m.group(1))
            continue

        # 1) 핵심 컬럼 텍스트로 매칭
        hint = prev_page or previous_page_hint(rows, i)
        page: Optional[int] = None
        for col in SEARCH_COLUMNS:
            text = r.get(col, "").strip()
            if not text:
                continue
            page = find_page(text, pages, hint=hint)
            if page:
                break

        # 2) 출처 섹션 라벨로 fallback
        if not page and original_src:
            page = find_page(original_src, pages, hint=hint)

        # 3) hint 그대로 사용
        if not page and hint:
            page = hint

        # 출처 컬럼 갱신
        if page:
            if prev_page and abs(page - prev_page) <= 3 and prev_page != page:
                lo, hi = min(prev_page, page), max(prev_page, page)
                tag = f"p. {lo}~{hi}"
            else:
                tag = f"p. {page}"
            r["출처"] = f"{original_src} ({tag})" if original_src else tag
            prev_page = page
            matched += 1

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # XLSX 동기화 — 검수자가 Excel/Notion 으로 바로 열 수 있도록.
    try:
        import pandas as pd

        xlsx = csv_path.with_suffix(".xlsx")
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        df.to_excel(xlsx, index=False, engine="openpyxl")
    except Exception as e:  # pandas/openpyxl 미설치여도 csv는 갱신됐으므로 경고만
        print(f"  (xlsx 동기화 실패: {e})")

    return matched, len(rows)


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("manual", nargs="?", default="both", choices=["stay", "visa", "both"])
    p.add_argument("--stay-pdf", type=Path, default=DEFAULT_PDFS["stay"])
    p.add_argument("--visa-pdf", type=Path, default=DEFAULT_PDFS["visa"])
    p.add_argument("--force", action="store_true", help="PDF 텍스트 캐시 무시")
    args = p.parse_args()

    targets = ["stay", "visa"] if args.manual == "both" else [args.manual]

    for k in targets:
        pdf_path = getattr(args, f"{k}_pdf")
        if not pdf_path.exists():
            print(f"  PDF 없음 — 건너뜀: {pdf_path}")
            continue
        cache = CACHE_DIR / f"{k}_pages.json"
        pages = extract_pages(pdf_path, cache, force=args.force)
        for csv_path in CSV_PATHS[k]:
            if not csv_path.exists():
                print(f"  CSV 없음 — 건너뜀: {csv_path}")
                continue
            matched, total = assign_pages(csv_path, pages)
            pct = 100 * matched // total if total else 0
            print(f"  {csv_path.name}: {matched}/{total} ({pct}%) 페이지 매칭")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
