# Scripts

반복 실행하는 정제·CSV 생성 코드를 둡니다. 노트북은 결과 확인 도구이고, 운영 경로는 이 폴더입니다.

전체 파이프라인은 **9 단계**, 그중 LLM 작업은 Claude Code 스킬로 분리되어 있습니다.

```
Stage 1: scripts/parse_hwp_to_markdown.py           HWP → kordoc → raw MD
Stage 2: scripts/index_markdown_chunks.py           raw MD → chunks_index.jsonl
Stage 3: /vizabridge-normalize                       chunks → normalized MD (Claude Code skill)
Stage 4: scripts/validate_normalization.py          normalized MD ↔ raw MD 교차 검증
Stage 5: /vizabridge-repair                          flagged chunks 수리 (조건부)
Stage 6: scripts/build_semantic_csv.py              normalized MD → semantic CSV
Stage 7: /vizabridge-enrich-chatbot                 semantic CSV → normalized chatbot MD
Stage 8: scripts/build_chatbot_csv.py               normalized chatbot MD → chatbot CSV
Stage 9: scripts/quality_report_semantic_manual_csvs.py  검수용 리포트/Excel
```

LLM은 stages 3, 5, 7 에서만 사용합니다. 나머지는 결정적 Python.

## Stage 1 — HWP를 kordoc으로 Markdown 변환

```bash
python scripts/parse_hwp_to_markdown.py            # 증분 (기존 출력 존재 시 스킵)
python scripts/parse_hwp_to_markdown.py --force    # 강제 재변환
```

`data/raw/*.hwp` → `data/parsed/raw/{stay,visa}_manual.md`. Node.js 18+ 필요.

## Stage 2 — 청크 분할

```bash
python scripts/index_markdown_chunks.py
```

`data/parsed/raw/*.md` → `data/parsed/chunks/{stay,visa}_chunks_index.jsonl`.

청크 1개 ≈ 15K chars 목표, top-level `<table>` 경계에서 절단. 비자코드는 청크별 메타데이터로 부착 (한 청크에 여러 코드 가능).

## Stage 3 — 의미 단위 정규화 (Claude Code 스킬)

Claude Code 세션에서:

```
/vizabridge-normalize stay
/vizabridge-normalize visa
```

청크 단위로 처리하며 세션 한도 시 자동 멈춤, 다음 세션에서 재개. 진행률은 normalized MD의 chunk 마커로 추적.

산출물: `data/parsed/normalized/{stay,visa}_manual.md` (커밋 대상)

## Stage 4 — 교차 검증

```bash
python scripts/validate_normalization.py            # 둘 다
python scripts/validate_normalization.py stay       # 하나만
```

정규화 블록의 비자코드/금액/서류명이 원본 청크에 실제 등장하는지 결정적으로 확인. 산출물: `data/parsed/validation/{stay,visa}_validation.json`.

## Stage 5 — 수리 (조건부, Claude Code 스킬)

validator가 flag한 청크가 있을 때만:

```
/vizabridge-repair stay
/vizabridge-repair visa
```

수리한 후 다시 validate.

## Stage 6 — semantic CSV 빌드

```bash
python scripts/build_semantic_csv.py
```

`data/parsed/normalized/*.md` → `data/processed/{stay,visa}_manual_semantic_clean.csv`.

## Stage 7 — chatbot 풍부화 (Claude Code 스킬)

```
/vizabridge-enrich-chatbot stay
/vizabridge-enrich-chatbot visa
```

semantic CSV의 각 행에 상황 태그, 자연어 키워드, 라우팅 힌트, 검색 텍스트 추가. 산출물: `data/parsed/normalized_chatbot/{stay,visa}_manual.md` (커밋 대상).

## Stage 8 — chatbot CSV 빌드

```bash
python scripts/build_chatbot_csv.py
```

`data/parsed/normalized_chatbot/*.md` → `data/processed/{stay,visa}_manual_chatbot_ready.csv`.

## Stage 9 — 품질 리포트

```bash
python scripts/quality_report_semantic_manual_csvs.py
```

`output/quality/` 및 `output/review/`에 검수 리포트와 Excel 생성. semantic CSV에 review 컬럼은 추가하지 않습니다.

## 한 번에 (CLI 결정적 단계만)

```bash
python scripts/parse_hwp_to_markdown.py && \
python scripts/index_markdown_chunks.py
# (여기서 Claude Code 스킬로 정규화)
python scripts/validate_normalization.py && \
python scripts/build_semantic_csv.py
# (여기서 Claude Code 스킬로 챗봇 풍부화)
python scripts/build_chatbot_csv.py && \
python scripts/quality_report_semantic_manual_csvs.py
```

## legacy/

`scripts/legacy/`는 기존 정규식 기반 빌더(`build_semantic_manual_csvs.py`,
`build_chatbot_ready_manual_csvs.py`)를 보관합니다. quality_report가 이 모듈의
상수/분류기 함수를 재사용합니다. 직접 호출하지는 마세요.
