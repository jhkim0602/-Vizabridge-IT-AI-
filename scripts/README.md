# Scripts

v4 CSV 파이프라인을 구성하는 결정적 Python 스크립트.

전체 파이프라인은 **6 단계** — LLM 단계 1개 (Claude Code 스킬) + 결정적 Python 5개.

```
Stage 1: parse_hwp_to_markdown.py   HWP → kordoc → raw MD
Stage 2: index_markdown_chunks.py   raw MD → chunks_index.jsonl
Stage 3: /vizabridge-normalize       청크 → normalized MD (Claude Code 스킬)
Stage 4: validate_normalization.py  normalized MD ↔ raw MD 교차 검증
Stage 5: build_v4.py                 normalized MD → v4 CSV (26컬럼) + XLSX
Stage 6: fill_page_numbers.py        HWP→PDF 변환 후 페이지 매칭
```

## Stage 1 — HWP → kordoc MD

```bash
python scripts/parse_hwp_to_markdown.py            # 증분 (기존 출력 있으면 스킵)
python scripts/parse_hwp_to_markdown.py --force    # 강제 재변환
```

`data/raw/*.hwp` → `data/parsed/raw/{stay,visa}_manual.md`. Node.js 18+ 필요.

## Stage 2 — 청크 분할

```bash
python scripts/index_markdown_chunks.py
```

`data/parsed/raw/*.md` → `data/parsed/chunks/{stay,visa}_chunks_index.jsonl`.
청크 한 개 ≈ 15K chars, top-level `<table>` 경계에서 절단. 비자코드는 청크 메타데이터로 부착.

## Stage 3 — LLM 정규화 (Claude Code 스킬)

Claude Code 세션:
```
/vizabridge-normalize stay
/vizabridge-normalize visa
```

청크 단위 처리, 세션 한도 시 자동 멈춤 → 다음 세션 재개. 진행률은 normalized MD 의 chunk 마커로 추적.

산출물: `data/parsed/normalized/{stay,visa}_manual.md` (커밋)

> **통합행 분리 정책** — 보고서 4.3 「매뉴얼이 묶어 서술한 통합행 분리」에 따라, 같은
> 자격 안에서 매뉴얼이 별도 번호·섹션·국가·분야·협정·지역·sub-code 로 구분한 발급
> 기준은 정규화 단계에서 각각 별도 행으로 분리한다. 예: D-7 주재 → 외국지사 / 해외진출
> / 한·러 / 한·우즈벡 / 한·인도 5행. 이 분리가 정답(ground truth)이며, build 단계는
> 추가 분리하지 않는다.

## Stage 4 — 교차 검증

```bash
python scripts/validate_normalization.py            # 둘 다
python scripts/validate_normalization.py stay       # 하나만
```

정규화 블록의 비자코드/금액/서류명이 원본 청크에 실제 등장하는지 결정적으로 확인.
산출물: `data/parsed/validation/{stay,visa}_validation.json`.

## Stage 5 — v4 CSV + XLSX 빌드

```bash
python scripts/build_v4.py
```

정규화 MD → v4 CSV (26컬럼) + 같은 이름의 XLSX. 같은 `(비자코드, 신청종류)` 묶음을
한 행으로 병합하면서 normalized 필드(`applicant_context`, `eligibility`, ...)를 v4
컬럼(`신청상황`, `자격요건`, ...)으로 매핑. 비자 흐름(`선행자격`/`다음단계`/`동반가족`/
`키워드`)은 부모 비자 코드 단위로 매핑 + 주요 sub-code override. 기간 정보
(`duration_or_validity`)는 `사증유효기간` / `1회부여 체류기간` / `체류상한` 3컬럼으로
자동 분리.

산출물 (보고서 부록 「산출물」 기준):
- `data/processed/사증매뉴얼_최종_v4_26col.csv` (158 행 × 26 컬럼)
- `data/processed/사증매뉴얼_최종_v4_26col.xlsx`
- `data/processed/체류매뉴얼_최종_v4_26col.csv` (275 행 × 26 컬럼)
- `data/processed/체류매뉴얼_최종_v4_26col.xlsx`

## Stage 6 — 페이지 매핑

선행 조건 — HWP → PDF 변환 (1회만 하면 됨):

```bash
brew install --cask libreoffice
curl -L -o /tmp/H2Orestart.oxt \
  https://github.com/ebandal/H2Orestart/releases/latest/download/H2Orestart.oxt
unopkg add /tmp/H2Orestart.oxt
soffice --headless --convert-to pdf --outdir data/raw/pdf/ data/raw/*.hwp
```

매핑 실행:

```bash
python scripts/fill_page_numbers.py            # 둘 다
python scripts/fill_page_numbers.py stay
python scripts/fill_page_numbers.py both --force   # PDF 텍스트 캐시 무시
```

pdfplumber 로 PDF 페이지별 텍스트 추출 후 v4 CSV 각 행의 핵심 컬럼 텍스트와 fuzzy 매칭.
출처 컬럼에 `(p. NNN)` 통합. 100% 채움. CSV 갱신과 동시에 동일 디렉토리의 XLSX 도
재생성된다.

## 새 HWP 받았을 때 전체 재실행

```bash
python scripts/parse_hwp_to_markdown.py --force
python scripts/index_markdown_chunks.py
# Claude Code 세션:
#   /vizabridge-normalize stay
#   /vizabridge-normalize visa
python scripts/validate_normalization.py
python scripts/build_v4.py
soffice --headless --convert-to pdf --outdir data/raw/pdf/ data/raw/*.hwp
python scripts/fill_page_numbers.py
```

## 스키마 / 출처 위치 변경

`build_v4.py` 상단의 `V4_COLUMNS`, `DIRECT_MAP`, `PARENT_FLOW`, `SUB_OVERRIDE` 가
single source of truth. 추가 비자 흐름 매핑 보강 시 `SUB_OVERRIDE` 에 dict 한 항목
추가하면 됨.
