> 🌐 **언어:** **한국어** | [English](README_EN.md)

# Vizabridge Visa RAG

대한민국 비자/체류 매뉴얼 **HWP** 원본을 → kordoc Markdown 변환 → **Claude Code 스킬**로 의미 단위 정규화 → **결정적 Python**으로 **사람이 검수 가능한 1차 정리 CSV (v3)** 를 생성하고, **HWP → PDF 변환 + 페이지 fuzzy 매칭**으로 모든 행에 원본 페이지 번호를 부착하는 데이터 전처리 파이프라인.

산출물은 **챗봇/RAG 최종 구조가 아니라, 사람이 원본 매뉴얼 옆에 놓고 검수하기 위한 CSV** 임. 검수 완료 후에 챗봇용 변환을 따로 진행.

## v3 스키마 (27컬럼)

한 행 = **(비자코드 × 신청종류)** 1조합. 같은 비자코드라도 사증발급/체류자격 변경/체류기간 연장 등 신청종류가 다르면 별도 행으로 분리.

| 그룹 | 개수 | 컬럼 |
|---|---|---|
| 식별·분류 | 4 | 비자코드, 상위코드, 사증·체류, 신청종류 |
| 행정 내용 | 14 | 신청상황, 대상자, 자격요건, 절차, 수수료, 기간, 제한, 예외, 의무사항, 점수표, 쿼터, 초청자, 추천·승인기관, 표 데이터 |
| 자료 | 2 | 제출서류, 예상질문 |
| 출처 | 1 | 출처 ("섹션 (p. NNN)" 형식, 페이지 100% 채움) |
| 흐름·검색 | 4 | 선행자격, 다음단계, 동반가족, 키워드 |
| 검수 | 2 | 검수상태, 검수메모 |

## Pipeline

```text
data/raw/*.hwp                                        # 원본 (source of truth)
   │  Stage 1  scripts/parse_hwp_to_markdown.py       # kordoc 변환
   ▼
data/parsed/raw/{stay,visa}_manual.md
   │  Stage 2  scripts/index_markdown_chunks.py       # 청크 분할 + 비자코드 메타
   ▼
data/parsed/chunks/{stay,visa}_chunks_index.jsonl
   │  Stage 3  /vizabridge-normalize                  # LLM 정규화 (Claude Code 스킬)
   ▼
data/parsed/normalized/{stay,visa}_manual.md          # 청크별 row 블록 (커밋)
   │  Stage 4  scripts/validate_normalization.py      # 비자코드·금액 원본 대조
   ▼
data/parsed/validation/{stay,visa}_validation.json
   │  Stage 5  scripts/build_v3.py                    # v3 CSV (27컬럼) 빌드
   ▼
data/processed/{체류,사증}매뉴얼_검수용_v3.csv
data/processed/{체류,사증}매뉴얼_노션검수용_v3.csv
   │  Stage 6  HWP → PDF (LibreOffice + H2Orestart)   # 페이지 매핑 위한 변환
   │           scripts/fill_page_numbers.py            # PDF 텍스트 ↔ CSV 행 fuzzy 매칭
   ▼
v3 CSV의 출처 컬럼에 "p. NNN" 통합 (100% 채움)
```

**LLM 단계는 Stage 3 하나.** 나머지 5단계는 결정적 Python — 같은 입력이면 같은 출력.

## 페이지 출처 매핑 — 기술 상세

### Stage 6 ① HWP → PDF
HWP 는 분산 포맷이라 본문이 ViewText 스트림에 암호화돼 일반 라이브러리로 추출 불가. LibreOffice + H2Orestart Java 확장이 표준 해결책.

```bash
brew install --cask libreoffice
curl -L -o /tmp/H2Orestart.oxt \
  https://github.com/ebandal/H2Orestart/releases/latest/download/H2Orestart.oxt
unopkg add /tmp/H2Orestart.oxt
soffice --headless --convert-to pdf \
        --outdir data/raw/pdf/ "data/raw/*.hwp"
```

→ `data/raw/pdf/` 에 PDF 두 개 (체류 26 MB / 735쪽, 사증 17 MB / 473쪽). PDF 는 `.gitignore` 되어 GitHub 에 안 올라감 (HWP 가 source of truth).

### Stage 6 ② PDF → 페이지 텍스트 (캐시)
`pdfplumber` 로 각 페이지 텍스트 추출 후 `data/raw/pdf/.cache/{stay,visa}_pages.json` 에 저장. 다음 실행은 캐시 재사용.

### Stage 6 ③ 텍스트 정규화 (매칭 정확도의 핵심)
PDF 추출 텍스트는 원본과 그대로 매칭되지 않음. 3단계 정규화:

```python
def normalize(s):
    s = unicodedata.normalize("NFC", s)              # 자모 합성
    s = re.sub(r"[\s,.·:;()\[\]<>|/_\-]+", "", s)   # 노이즈 제거
    s = re.sub(r"([가-힣])\1+", r"\1", s)            # 한글 중복 자모 압축
                                                     # (LibreOffice 변환 시
                                                     #  "외외 국국 인인" 같은 버그 보정)
    return s
```

**한글 중복 자모 압축이 결정적.** H2Orestart 변환에서 한글 글자가 중복 출력되는 버그가 있음. 이걸 보정 안 하면 매칭률 5% 이하로 떨어짐.

### Stage 6 ④ Fuzzy 매칭 (sliding window + 가중치 투표)
각 v3 행에 대해:

1. 우선순위 컬럼 (`자격요건` → `신청상황` → `제출서류` → `절차` → `제한` → `예외` → `기간` → `대상자`) 에서 텍스트 수집
2. 50자 / 30자 / 18자 sliding window (step 8자) 로 PDF 페이지 텍스트와 `in` 매칭
3. 같은 페이지에 여러 윈도우 매칭되면 점수 누적
4. 직전 행 페이지(`hint`) ± 8쪽 이내 → 2.5배 가산, 60쪽 이상 떨어지면 → 0.15배 페널티 (boilerplate 오매칭 회피)
5. 최고 점수 페이지 = 매칭 결과
6. 1차 실패 시 `출처` 라벨 텍스트로 fallback, 그래도 실패 시 hint 그대로 적용

### Stage 6 ⑤ 인접 페이지 그룹화
한 (비자, 신청종류) 행이 여러 페이지에 걸치면 `p. 442~444` 형태로 표시.

### 결과
- 체류 233/233 행 (100%) — 페이지 매칭 완료
- 사증 130/130 행 (100%) — 페이지 매칭 완료

매뉴얼 개정 시: HWP 갱신 → PDF 재변환 → `scripts/fill_page_numbers.py` 재실행 → 출처 컬럼 자동 갱신.

## 디렉토리 구조

```text
.
├── data/
│   ├── raw/                              # HWP 원본 (수정 금지)
│   │   ├── 260504 체류민원 …  매뉴얼.hwp
│   │   ├── 260504 사증민원 …  매뉴얼.hwp
│   │   └── pdf/                          # HWP→PDF 변환물 (.gitignored)
│   ├── parsed/
│   │   ├── raw/                          # kordoc 출력 (.gitignored)
│   │   ├── chunks/                       # 청크 인덱스 .jsonl (커밋)
│   │   ├── normalized/                   # LLM 정규화 결과 (커밋)
│   │   └── validation/                   # validator 출력 (커밋)
│   └── processed/                        # v3 CSV (커밋)
│       ├── 체류매뉴얼_검수용_v3.csv      # 233행 × 27컬럼
│       ├── 사증매뉴얼_검수용_v3.csv      # 130행 × 27컬럼
│       ├── 체류매뉴얼_노션검수용_v3.csv
│       └── 사증매뉴얼_노션검수용_v3.csv
├── scripts/
│   ├── parse_hwp_to_markdown.py          # Stage 1
│   ├── index_markdown_chunks.py          # Stage 2
│   ├── validate_normalization.py         # Stage 4
│   ├── build_v3.py                       # Stage 5: 정규화 MD → v3 CSV
│   └── fill_page_numbers.py              # Stage 6: 페이지 매핑
├── .claude/skills/
│   └── vizabridge-normalize/             # Stage 3: LLM 정규화 스킬
├── docs/
│   ├── pipeline_strategy.md              # 파이프라인 설계 의사결정
│   └── project_structure.md              # 폴더 구조 정책
└── requirements.txt
```

## 사용법

### 신규 매뉴얼 처리 (전체 흐름)

```bash
# Python 환경
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Node.js 18+ 필요 (kordoc)
node --version

# Stage 1~2: HWP → MD → 청크
python scripts/parse_hwp_to_markdown.py
python scripts/index_markdown_chunks.py

# Stage 3: LLM 정규화 (Claude Code 세션에서)
#   /vizabridge-normalize stay
#   /vizabridge-normalize visa

# Stage 4: 검증
python scripts/validate_normalization.py

# Stage 5: v3 CSV 빌드
python scripts/build_v3.py

# Stage 6: 페이지 매핑
#   1) HWP → PDF 변환 (LibreOffice + H2Orestart 설치 후 1회)
soffice --headless --convert-to pdf --outdir data/raw/pdf/ data/raw/*.hwp
#   2) PDF 페이지 텍스트 ↔ CSV 행 매칭
python scripts/fill_page_numbers.py
```

### 페이지만 재갱신 (HWP 그대로, 매뉴얼 개정 X)

```bash
python scripts/fill_page_numbers.py both --force   # 캐시 무시하고 PDF 다시 추출
```

## 검수 워크플로 (Notion)

1. GitHub `data/processed/` 폴더에서 `{체류,사증}매뉴얼_노션검수용_v3.csv` 다운로드
2. Notion 페이지에서 `/` → "Import" → CSV 선택
3. 자동 import 후 컬럼 type 전환:
   - 검수상태 → Status (옵션: 미검수 / 검수중 / 검수완료)
   - 사증·체류 / 신청종류 / 상위코드 → Select
4. 뷰 추가: 필터 `검수상태 = 미검수`, 정렬 `상위코드`
5. 검수자가 행마다 PDF 페이지 점프(`출처` 컬럼의 `p. NNN`) → 원본 대조 → 검수상태 변경

## 데이터 품질 검증

- Stage 4 (validator): 정규화 row 의 비자코드·금액·서류명이 원본 청크에 실제 등장하는지 결정적으로 확인
- 페이지 매칭률: 체류 100% / 사증 100% (행마다 `p. NNN` 부착)
- 8개 핵심 사실 cross-check 통과 (F-6 2026 소득요건, E-7-4 200점/2,600만원, D-2-5 2년 초과 불가, F-5-1 5년 체류, F-2-7 80점, E-9 16개 송출국, H-1 만 18~30세, F-4 단순노무 제한)

## 디자인 결정

- **행 단위 = (비자코드 × 신청종류)**: 한 비자에 모든 신청종류 합치면 한 셀 5,000자 폭주. 분리해야 검수자가 OK/NG 행 단위 판정 가능.
- **27 컬럼 분리**: 클라이언트 피드백 "구획 한 컬럼 X, 각 항목 별도 컬럼 O" 반영. 빈 셀이 늘어나지만 누락 ZERO 원칙 충족.
- **페이지 컬럼 통합**: 별도 `페이지` 컬럼이 아닌 `출처` 안에 `(p. NNN)` 포함 → 검수자 시야 한 곳에.
- **노션·검수용 동일**: Notion 으로 import 후 컬럼 type 만 전환하면 그대로 사용 가능 → 두 파일을 별도 관리할 필요 X (현재는 호환성 위해 둘 다 유지).
- **흐름 매핑**: 비자 코드별 선행자격/다음단계/동반가족이 표준화돼 있어 부모 코드 단위로 매핑 + 주요 sub-code (F-6-1/2/3, E-7-4, F-2-7/R/T/71 등) 는 override.

상세 설계 의사결정은 [docs/pipeline_strategy.md](docs/pipeline_strategy.md), 폴더 정책은 [docs/project_structure.md](docs/project_structure.md).
