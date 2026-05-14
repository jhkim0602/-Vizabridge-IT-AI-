# Project Structure Guide

이 문서는 비전공자가 저장소를 열었을 때 "어디에 무엇이 있고, 무엇을 실행해야 하며, 무엇을 건드리면 위험한지"를 빠르게 판단할 수 있게 만든 운영 가이드입니다.

## One-Line Summary

비자/체류 HWP 매뉴얼을 kordoc으로 Markdown으로 변환하고, Claude Code 스킬로 의미 단위 정규화한 뒤, 결정적 Python으로 RAG/챗봇용 CSV를 만드는 9단계 데이터 전처리 파이프라인입니다. LLM은 3단계에서만 사용합니다.

## Folder Map

```text
Vizabridge/
├── data/
│   ├── raw/                          # 원본 HWP
│   │   └── legacy_pdf/               # 기존 PDF 백업
│   ├── parsed/
│   │   ├── raw/                      # kordoc → MD (.gitignored)
│   │   ├── chunks/                   # 청크 인덱스 .jsonl (커밋)
│   │   ├── normalized/               # 정규화 MD (커밋) ← LLM 결과
│   │   ├── normalized_chatbot/       # 챗봇 정규화 MD (커밋)
│   │   └── validation/               # validator 산출 .json (커밋)
│   └── processed/                    # 최종 CSV (.gitignored)
├── scripts/
│   └── legacy/                       # 과거 정규식 빌더
├── .claude/skills/
│   ├── vizabridge-normalize/
│   ├── vizabridge-enrich-chatbot/
│   └── vizabridge-repair/
├── notebooks/
├── docs/
├── tests/
├── output/                           # 검수 산출물 (.gitignored)
└── requirements.txt
```

## `data/`

| Folder | 역할 | 직접 수정 여부 | git |
| --- | --- | --- | --- |
| `data/raw/` | 원본 HWP 보관 | 원본 교체 외엔 수정하지 않음 | 커밋 |
| `data/raw/legacy_pdf/` | 과거 PDF 백업 | 보존만 | 커밋 |
| `data/parsed/raw/` | kordoc Markdown | 스크립트가 재생성 | 비커밋 (regenerable) |
| `data/parsed/chunks/` | 청크 인덱스 | 스크립트가 재생성 | 커밋 (작고 유용) |
| `data/parsed/normalized/` | 정규화 MD | Claude Code 스킬이 작성 | **커밋** |
| `data/parsed/normalized_chatbot/` | 챗봇 정규화 MD | 스킬이 작성 | **커밋** |
| `data/parsed/validation/` | validator 산출 | 스크립트 재생성 | 커밋 |
| `data/processed/` | 최종 semantic/chatbot CSV | 스크립트 재생성 | 비커밋 |

**정규화 MD를 커밋하는 이유**: 같은 입력에서 같은 CSV가 나오게 만드는 결정성 보장 장치입니다. LLM이 다시 안 돌아도 됩니다.

## `scripts/`

| Script | 단계 | 역할 |
| --- | --- | --- |
| `parse_hwp_to_markdown.py` | 1 | HWP → kordoc → MD |
| `index_markdown_chunks.py` | 2 | MD → 청크 인덱스 (table 경계 기반) |
| `validate_normalization.py` | 4 | 정규화 MD ↔ 원본 MD 교차 검증 |
| `build_semantic_csv.py` | 6 | 정규화 MD → semantic CSV |
| `build_chatbot_csv.py` | 8 | 챗봇 정규화 MD → chatbot CSV |
| `quality_report_semantic_manual_csvs.py` | 9 | 검수용 리포트 + Excel |

`scripts/legacy/`는 과거 정규식 빌더입니다. 직접 호출하지 않습니다 (quality_report가 상수/분류기 함수만 import).

## `.claude/skills/`

Claude Code 세션에서 `/vizabridge-normalize`, `/vizabridge-enrich-chatbot`, `/vizabridge-repair`로 호출되는 스킬들. SKILL.md + references/ + scripts/ 구조.

| Skill | 단계 | 입력 | 출력 |
| --- | --- | --- | --- |
| `vizabridge-normalize` | 3 | 청크 인덱스 + raw MD | 정규화 MD (append) |
| `vizabridge-repair` | 5 | validator 산출 | 정규화 MD (replace) |
| `vizabridge-enrich-chatbot` | 7 | semantic CSV | 챗봇 정규화 MD (append) |

각 스킬은 청크/행 단위로 처리하고 진행률을 마커로 기록하므로 세션 한도에 닿으면 다음 세션에서 자연스럽게 재개됩니다.

## `output/`

검수 산출물. Git에는 올리지 않습니다.

| Folder | 내용 |
| --- | --- |
| `output/quality/` | 품질 요약 CSV, 검수 후보 CSV, Markdown 리포트 |
| `output/review/` | 사람이 필터링하면서 볼 수 있는 Excel 파일 |

## `notebooks/`

분석/시각화 도구. 운영 경로 아님.

| Notebook | 역할 |
| --- | --- |
| `03_review_semantic_manual_csvs.ipynb` | 최종 CSV 분포, 누락률, 검수 후보 확인 |

(과거 `01_setup_llamaparse_api_key.ipynb`, `02_parse_pdfs_with_llamaparse.ipynb`은 제거됨 — kordoc은 API 키도, 별도 노트북도 필요 없음.)

## `docs/`

| Document | 내용 |
| --- | --- |
| `data_columns.md` | 최종 CSV 컬럼 정의 |
| `data_preprocessing_runbook.md` | 재생성/검수 실행 절차 |
| `pipeline_strategy.md` | 왜 이 파이프라인을 선택했는가 |
| `project_structure.md` | 이 문서 |
| `superpowers/specs/` | 설계 사양서 |

## `tests/`

```bash
.venv/bin/python -m pytest tests -q
```

정제 규칙이 깨지지 않게 막는 안전장치. 기존 테스트는 legacy 빌더 기준이라 일부 미적용 — 새 파이프라인용 테스트는 점진 추가.

## Maintenance Checklist

HWP 또는 정규화 규칙을 바꾼 뒤:

1. `python scripts/parse_hwp_to_markdown.py` (필요 시 `--force`)
2. `python scripts/index_markdown_chunks.py`
3. Claude Code에서 `/vizabridge-normalize stay`, `/vizabridge-normalize visa`
4. `python scripts/validate_normalization.py`
5. 필요 시 `/vizabridge-repair` → 다시 validator
6. `python scripts/build_semantic_csv.py`
7. Claude Code에서 `/vizabridge-enrich-chatbot stay`, `/vizabridge-enrich-chatbot visa`
8. `python scripts/build_chatbot_csv.py`
9. `python scripts/quality_report_semantic_manual_csvs.py`

## Practical Rule

최종 CSV를 직접 손으로 수정하지 않습니다. 문제는 보통 세 곳 중 하나입니다.

- kordoc 파싱이 깨진 경우: `data/parsed/raw/`의 MD 확인. HWP 자체 문제일 수도 있음.
- 의미 분류 규칙이 부족한 경우: `.claude/skills/vizabridge-normalize/references/*.md` 수정 → 해당 청크 재실행
- 검수 후보 기준이 과하거나 약한 경우: `scripts/quality_report_semantic_manual_csvs.py`의 `row_issues()` 수정

이렇게 해야 같은 HWP를 다시 처리해도 같은 품질의 CSV를 재현할 수 있습니다.
