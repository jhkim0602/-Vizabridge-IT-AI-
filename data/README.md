# Data

`data/`는 정부 HWP 매뉴얼이 검수용 v3 CSV가 되기까지 거치는 단계별 보관소입니다.

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

`normalized/`는 중요한 중간 표현입니다. CSV 컬럼 매핑을 바꾸거나 페이지 번호를 다시 붙일 때, LLM을 다시 실행하지 않고 여기서부터 재생성할 수 있습니다.

## `processed/`

검수자가 사용하는 최종 v3 CSV를 둡니다.

- `체류매뉴얼_검수용_v3.csv`
- `사증매뉴얼_검수용_v3.csv`
- `체류매뉴얼_노션검수용_v3.csv`
- `사증매뉴얼_노션검수용_v3.csv`

한 행은 `(비자코드 × 신청종류)` 1조합입니다. 현재 기준 체류 233행, 사증 130행이며, 각 행은 27컬럼으로 구성됩니다.

CSV는 사람이 직접 편집하기보다 `scripts/` 파이프라인으로 재생성하는 것을 기본으로 합니다. 검수 의견은 `검수상태`, `검수메모` 컬럼에 남기고, 구조적 오류는 `data/parsed/normalized/` 또는 `scripts/build_v3.py` 쪽에서 고치는 방식이 재현성이 좋습니다.
