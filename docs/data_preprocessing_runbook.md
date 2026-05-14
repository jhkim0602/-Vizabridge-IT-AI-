# Data Preprocessing Runbook

원본 HWP에서 최종 CSV까지의 9단계 운영 절차입니다.

## Objective

HWP 원본 → kordoc Markdown → 정규화 MD → semantic CSV → 챗봇 CSV → 품질 리포트. LLM은 3단계에서만 사용하고 (Claude Code 스킬), 나머지는 모두 결정적 Python입니다.

최종 CSV는 RAG/챗봇 전처리의 입력으로 사용됩니다. PDF 페이지 번호, 원문 근거, raw text, review 컬럼은 절대 포함하지 않습니다.

## Output Files

Semantic clean CSV:

- `data/processed/stay_manual_semantic_clean.csv`
- `data/processed/visa_manual_semantic_clean.csv`

Chatbot-ready CSV:

- `data/processed/stay_manual_chatbot_ready.csv`
- `data/processed/visa_manual_chatbot_ready.csv`

검수 산출물:

- `output/quality/semantic_manual_quality_report.md`
- `output/quality/*_manual_review_candidates.csv`
- `output/review/{stay,visa}_manual_review.xlsx`

## Method

1. 원본 HWP를 `data/raw/`에 두기 (기존 PDF는 `data/raw/legacy_pdf/`로 백업)
2. `python scripts/parse_hwp_to_markdown.py` — kordoc subprocess로 `data/parsed/raw/{stay,visa}_manual.md` 생성
3. `python scripts/index_markdown_chunks.py` — top-level `<table>` 경계로 청크 분할, 각 청크에 발견 비자코드 메타데이터 부착
4. Claude Code 세션에서 `/vizabridge-normalize stay` / `/vizabridge-normalize visa` — 청크별로 정규화 MD에 행 블록을 append. 세션 끊겨도 재개 가능
5. `python scripts/validate_normalization.py` — 비자코드/금액/서류명이 원본 청크에 실제 등장하는지 결정적 검증, `data/parsed/validation/*.json` 산출
6. 필요 시 Claude Code 세션에서 `/vizabridge-repair stay` / `/vizabridge-repair visa` — 플래그된 청크만 교체. 그 후 다시 validate
7. `python scripts/build_semantic_csv.py` — 정규화 MD를 파싱해 `data/processed/*_semantic_clean.csv` 작성
8. Claude Code 세션에서 `/vizabridge-enrich-chatbot stay` / `/vizabridge-enrich-chatbot visa` — semantic CSV의 각 행에 상황 태그/자연어 키워드/라우팅 힌트 추가
9. `python scripts/build_chatbot_csv.py` — 챗봇 정규화 MD를 파싱해 `data/processed/*_chatbot_ready.csv` 작성
10. `python scripts/quality_report_semantic_manual_csvs.py` — 자동 품질검사와 검수용 Excel 생성

## Rebuild Commands

처음부터:

```bash
python scripts/parse_hwp_to_markdown.py
python scripts/index_markdown_chunks.py

# Claude Code 세션에서:
#   /vizabridge-normalize stay
#   /vizabridge-normalize visa

python scripts/validate_normalization.py

# 필요 시 Claude Code 세션에서:
#   /vizabridge-repair stay
#   /vizabridge-repair visa
# python scripts/validate_normalization.py   # 다시

python scripts/build_semantic_csv.py

# Claude Code 세션에서:
#   /vizabridge-enrich-chatbot stay
#   /vizabridge-enrich-chatbot visa

python scripts/build_chatbot_csv.py
python scripts/quality_report_semantic_manual_csvs.py
```

정규화 MD가 이미 커밋되어 있는 상태(LLM 재실행 불필요):

```bash
python scripts/parse_hwp_to_markdown.py    # raw MD 재생성
python scripts/index_markdown_chunks.py     # 청크 인덱스 재생성 (해시 검증용)
python scripts/validate_normalization.py    # 검증
python scripts/build_semantic_csv.py        # CSV 빌드
python scripts/build_chatbot_csv.py
python scripts/quality_report_semantic_manual_csvs.py
```

## Resume Across Sessions

정규화 스킬과 챗봇 풍부화 스킬은 모두 청크/행 단위로 진행률을 정규화 MD의 마커로 기록합니다. 세션 한도에 닿거나 사용자가 중단해도 다음 세션에서 같은 명령으로 자연스럽게 이어집니다.

진행률 조회:

```bash
python .claude/skills/vizabridge-normalize/scripts/show_progress.py stay
python .claude/skills/vizabridge-enrich-chatbot/scripts/show_progress.py stay
```

수리 필요 청크 조회:

```bash
python .claude/skills/vizabridge-repair/scripts/show_flagged.py stay
```

## Cleanup Rule

`data/processed/`에는 다음 두 종류 CSV만 둡니다. 그 외 review/debug CSV는 두지 않습니다.

- `{stay,visa}_manual_semantic_clean.csv`
- `{stay,visa}_manual_chatbot_ready.csv`

검수용 Excel은 `output/review/` (git 제외), 품질 리포트는 `output/quality/` (git 제외).
