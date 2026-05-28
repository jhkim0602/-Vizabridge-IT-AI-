# Project Structure Guide

이 문서는 저장소를 처음 여는 사람이 "어디에 무엇이 있고, 무엇을 실행해야 하며, 무엇을 직접 수정하면 위험한지"를 빠르게 판단할 수 있게 만든 운영 가이드입니다.

## One-Line Summary

정부 비자·체류 HWP 매뉴얼을 kordoc Markdown으로 변환하고, Claude Code 스킬로 행정 의미를 정규화한 뒤, 결정적 Python으로 **검수 가능한 26컬럼 v4 CSV/XLSX** (사증 158행 / 체류 275행)와 원본 페이지 출처를 생성하는 6단계 데이터 파이프라인입니다. LLM은 Stage 3에서만 사용합니다.

## Folder Map

```text
Vizabridge/
├── data/
│   ├── raw/                          # HWP 원본, HWP→PDF 변환물
│   ├── parsed/
│   │   ├── raw/                      # kordoc Markdown
│   │   ├── chunks/                   # 청크 인덱스 .jsonl
│   │   ├── normalized/               # LLM 정규화 Markdown
│   │   └── validation/               # validator JSON
│   └── processed/                    # 최종 v4 CSV/XLSX
├── docs/
│   ├── diagrams/                     # README/설계 이미지 + DBML 스키마
│   ├── report/                       # 결과보고서 PDF (최종 제출본)
│   ├── pipeline_strategy.md          # 파이프라인 설계 배경
│   └── project_structure.md          # 이 문서
├── scripts/                          # 결정적 Python 파이프라인
├── tests/                            # CSV 품질 회귀 테스트
├── .claude/skills/                   # Claude Code 정규화/수리 스킬
├── .agents/skills/                   # 동일 스킬의 codex/copilot 위치
├── interview/                        # 별도 Next.js 인터뷰 앱 (관련 X)
└── requirements.txt
```

## `data/`

| Folder | 역할 | 직접 수정 여부 | git |
| --- | --- | --- | --- |
| `data/raw/` | 원본 HWP와 페이지 매핑용 PDF 변환물 | HWP 원본 교체 외엔 수정하지 않음 | HWP 커밋, `raw/pdf/`는 비커밋 |
| `data/parsed/raw/` | kordoc Markdown | 스크립트가 재생성 | 커밋 |
| `data/parsed/chunks/` | 청크 인덱스 | 스크립트가 재생성 | 커밋 |
| `data/parsed/normalized/` | LLM 정규화 Markdown | Claude Code 스킬이 작성 | **커밋** |
| `data/parsed/validation/` | validator 산출 JSON | 스크립트가 재생성 | 커밋 |
| `data/processed/` | 최종 v4 CSV/XLSX | 스크립트가 재생성 | 커밋 |

`data/parsed/normalized/`는 이 프로젝트의 중간 표현입니다. CSV 컬럼 매핑, 페이지 매칭, 검수용 포맷을 바꿀 때 LLM을 다시 실행하지 않고 여기서부터 재생성할 수 있습니다. 보고서 4.3 「통합행 분리」 정책은 이 단계에서 적용됩니다.

## `scripts/`

| Script | Stage | 역할 |
| --- | ---: | --- |
| `parse_hwp_to_markdown.py` | 1 | HWP → kordoc → Markdown |
| `index_markdown_chunks.py` | 2 | Markdown → table 경계 기반 청크 인덱스 |
| `validate_normalization.py` | 4 | 정규화 Markdown ↔ 원본 Markdown 교차 검증 |
| `build_v4.py` | 5 | 정규화 Markdown → 26컬럼 v4 CSV + XLSX |
| `fill_page_numbers.py` | 6 | PDF 페이지 텍스트 ↔ CSV 행 fuzzy 매칭, `출처` 페이지 보강 + XLSX 동기화 |

Stage 3은 Python 스크립트가 아니라 Claude Code 스킬 `/vizabridge-normalize`가 담당합니다.

## `.claude/skills/` · `.agents/skills/`

Claude Code (`/vizabridge-normalize`) 세션과 Codex/Copilot 에이전트가 호출하는 동일한 로컬 스킬입니다. 두 디렉토리는 동기화되어 있습니다.

| Skill | 역할 | 입력 | 출력 |
| --- | --- | --- | --- |
| `vizabridge-normalize` | 청크를 행정 의미 row 블록으로 정규화 | `data/parsed/chunks/`, `data/parsed/raw/` | `data/parsed/normalized/` |
| `vizabridge-repair` | validator가 지적한 정규화 블록 수리 | `data/parsed/validation/` | `data/parsed/normalized/` |

> 챗봇 풍부화 스킬(`vizabridge-enrich-chatbot`)은 본 1차 전처리 산출물 다음 단계(임베딩·검색·챗봇 응답)에 속하므로 본 저장소 범위에서 제외했습니다. 보고서 6.2 「JSON/RAG 변환 시 주의사항」 참고.

## `docs/`

| Document | 내용 |
| --- | --- |
| `pipeline_strategy.md` | HWP source of truth, LLM/결정적 단계 분리, 청크 전략 |
| `project_structure.md` | 이 문서 |
| `diagrams/` | README에 삽입되는 아키텍처·파이프라인·스키마 이미지 (DBML 원본 포함) |
| `report/Vizabridge_데이터전처리_결과보고서.pdf` | 1차 데이터 전처리 결과보고서 (최종 제출본) |

## `tests/`

```bash
python -m pytest tests -q
```

테스트는 최종 v4 CSV의 행수(158/275)·컬럼수(26)·컬럼 채움률(보고서 부록 B)·핵심 사실이 깨지지 않게 막는 안전장치입니다. 문서만 수정한 경우에도 릴리즈 전에는 한 번 실행하는 편이 좋습니다.

## Maintenance Checklist

HWP 원본이나 정규화 규칙을 바꾼 뒤:

1. `python scripts/parse_hwp_to_markdown.py` 또는 `python scripts/parse_hwp_to_markdown.py --force`
2. `python scripts/index_markdown_chunks.py`
3. Claude Code에서 `/vizabridge-normalize stay`, `/vizabridge-normalize visa`
4. `python scripts/validate_normalization.py`
5. 필요 시 `/vizabridge-repair stay` 또는 `/vizabridge-repair visa`
6. `python scripts/build_v4.py`
7. HWP→PDF 변환 후 `python scripts/fill_page_numbers.py`
8. `python -m pytest tests -q`

## Practical Rule

최종 CSV를 직접 손으로 고치는 것을 기본 운영 방식으로 삼지 않습니다. 문제는 보통 세 곳 중 하나에서 고칩니다.

- 원본 변환이 깨진 경우: `data/parsed/raw/` Markdown 확인 후 Stage 1부터 재실행
- 의미 정규화가 틀린 경우: `data/parsed/normalized/` 블록을 수리하거나 `/vizabridge-repair` 실행
- v4 컬럼 매핑이 틀린 경우: `scripts/build_v4.py`의 `V4_COLUMNS`, `DIRECT_MAP`, `PARENT_FLOW`, `SUB_OVERRIDE` 수정

이렇게 해야 같은 HWP에서 같은 CSV를 재현할 수 있습니다.
