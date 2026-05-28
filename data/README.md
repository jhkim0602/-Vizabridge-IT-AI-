# Data

`data/`는 정부 HWP 매뉴얼이 v4 CSV (사증 158행 / 체류 275행, 26컬럼)가 되기까지
거치는 단계별 보관소입니다.

## `raw/`

원본 HWP와 페이지 매핑용 PDF 변환물을 둡니다.

- `*.hwp`가 source of truth입니다.
- 원본 HWP는 사람이 직접 수정하지 않습니다.
- `raw/pdf/`는 HWP를 LibreOffice + H2Orestart로 변환한 PDF와 `pdfplumber` 캐시를 둘 수 있습니다.
- 새 매뉴얼이 나오면 파일명을 유지할지, 날짜가 들어간 새 파일로 둘지 먼저 정합니다.

## `parsed/`

파이프라인 중간 산출물을 둡니다.

- `raw/`: kordoc이 HWP를 Markdown/HTML table 형태로 변환한 결과
- `chunks/`: top-level table 경계와 약 15K chars 기준으로 나눈 청크 인덱스
- `normalized/`: Claude Code `/vizabridge-normalize` 스킬이 만든 정규화 Markdown
- `validation/`: `scripts/validate_normalization.py`가 만든 원본 교차 검증 결과

`normalized/`는 중요한 중간 표현입니다. CSV 컬럼 매핑을 바꾸거나 페이지 번호를 다시
붙일 때, LLM을 다시 실행하지 않고 여기서부터 재생성할 수 있습니다. 보고서 4.3
「통합행 분리」 정책에 따라, 같은 자격 안에서 매뉴얼이 별도 번호·섹션으로 구분한
발급 기준은 이 단계에서 각각 별도 행으로 분리됩니다 (총 24건의 통합행을 매뉴얼 원문
구조 기준으로 재구성).

## `processed/`

검수자·후속 단계가 사용하는 최종 v4 CSV/XLSX 를 둡니다.

- `사증매뉴얼_최종_v4_26col.csv` (158 행 × 26 컬럼)
- `사증매뉴얼_최종_v4_26col.xlsx`
- `체류매뉴얼_최종_v4_26col.csv` (275 행 × 26 컬럼)
- `체류매뉴얼_최종_v4_26col.xlsx`

한 행은 `(비자코드 × 신청종류)` 1조합입니다. 26컬럼 구성은 보고서 2.1 「26 컬럼
한눈에」 카테고리 6 분류를 따릅니다 — 식별·자격(5) / 신청조건(3) / 기간(3) /
절차·서류(6) / 관계·제한(7) / 메타(2).

CSV/XLSX 는 사람이 직접 편집하기보다 `scripts/` 파이프라인으로 재생성하는 것을
기본으로 합니다. 구조적 오류는 `data/parsed/normalized/` 또는
`scripts/build_v4.py` 쪽에서 고치는 방식이 재현성이 좋습니다.

검수 워크플로(검수상태·검수메모 컬럼)는 본 1차 전처리 산출물에는 포함하지 않습니다.
검수자는 Notion import 후 별도 컬럼을 추가해 운영하시면 됩니다 — 본 CSV 는
ground-truth 데이터 계층, Notion 워크플로는 표시·운영 계층으로 분리합니다.
