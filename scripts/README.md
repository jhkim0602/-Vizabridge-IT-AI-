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

## Stage 6 — 검수용 CSV 빌드 (한국어 7컬럼)

```bash
python scripts/build_semantic_csv.py
```

`data/parsed/normalized/*.md` → `data/processed/{체류,사증}매뉴얼_검수용.csv`.

이번 회차의 1차 산출물입니다. 7개 컬럼은 다음과 같습니다:

| 컬럼 | 매핑 |
| --- | --- |
| `비자코드` | `stay_status_code` / `visa_code`. 세부 프로그램은 괄호 (`E-7 (E-7-4)`) |
| `사증·체류` | `manual_type` → `체류` / `사증` |
| `문서유형` | `petition_type / subsection_type` (예: `사증발급 / 제출서류`) |
| `핵심내용` | `applicant_context`, `eligibility`, `target_persons`, `requirements`, `procedure`, `duration_or_validity`, `fees`, `restrictions`, `exceptions`, `quota_or_limit`, `score_criteria`, `obligations`, `inviter_context`, `recommendation_or_approval`, `table_summary`, `table_rows` 중 비어있지 않은 것을 라벨링해 통합 |
| `제출서류` | `common_documents`, `mandatory_documents`, `other_documents` 통합 |
| `예상질문` | `expected_questions` (정규화 스킬이 LLM으로 생성) |
| `출처` | `section_title` \| 원본 HWP 파일명 |

CSV는 `utf-8-sig`로 저장되어 Excel에서 한글이 깨지지 않습니다.

## Stage 7–8 — 챗봇 변환 (이번 회차 미사용)

검수 완료 후 별도 회차에서 진행. 스크립트는 `scripts/build_chatbot_csv.py`,
스킬은 `.claude/skills/vizabridge-enrich-chatbot/`에 보존되어 있습니다.

## Stage 9 — 품질 리포트

```bash
python scripts/quality_report_semantic_manual_csvs.py
```

`output/quality/` 및 `output/review/`에 검수 리포트와 Excel 생성.

## 한 번에 (CLI 결정적 단계만)

```bash
python scripts/parse_hwp_to_markdown.py && \
python scripts/index_markdown_chunks.py
# (여기서 Claude Code 스킬로 정규화)
python scripts/validate_normalization.py && \
python scripts/build_semantic_csv.py && \
python scripts/quality_report_semantic_manual_csvs.py
```

## legacy/

`scripts/legacy/`는 기존 정규식 기반 빌더(`build_semantic_manual_csvs.py`,
`build_chatbot_ready_manual_csvs.py`)를 보관합니다. quality_report가 이 모듈의
상수/분류기 함수를 재사용합니다. 직접 호출하지는 마세요.
