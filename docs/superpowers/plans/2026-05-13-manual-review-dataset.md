# Manual Review Dataset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate human-reviewable structured JSONL/CSV datasets and a quality report for the stay and visa manuals.

**Architecture:** Build a deterministic Python pipeline that treats the PDF text layer as the source text and LlamaParse Markdown as structural hints. The pipeline extracts page text, segments it into reviewable administrative items, classifies broad schema fields, validates evidence and coverage, then writes final artifacts under `data/processed/`.

**Tech Stack:** Python standard library, Poppler `pdftotext`, existing LlamaParse Markdown artifacts, `pytest` for unit tests.

---

## File Structure

- Create `scripts/manual_review/schema.py`: field lists, manual metadata, code/name maps, quality constants.
- Create `scripts/manual_review/extract.py`: PDF text extraction, Markdown loading, page segmentation, item classification.
- Create `scripts/manual_review/quality.py`: validation checks and Markdown quality report generation.
- Create `scripts/build_manual_review_dataset.py`: CLI entry point that writes JSONL, CSV, validation errors, samples, and report.
- Create `tests/test_manual_review_schema.py`: schema and suspicious-term tests.
- Create `tests/test_manual_review_extract.py`: segmentation and classification tests.
- Create `tests/test_manual_review_quality.py`: validation/report tests.
- Modify `requirements.txt`: add `pytest` if missing.

### Task 1: Schema Contract

**Files:**
- Create: `scripts/manual_review/schema.py`
- Test: `tests/test_manual_review_schema.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Write failing tests**

```python
from scripts.manual_review.schema import (
    ALL_FIELDS,
    COMMON_FIELDS,
    STAY_FIELDS,
    VISA_FIELDS,
    SUSPICIOUS_TERMS,
    empty_item,
)


def test_all_fields_include_manual_specific_review_fields():
    assert "stay_status_code" in ALL_FIELDS
    assert "visa_code" in ALL_FIELDS
    assert "table_rows" in COMMON_FIELDS
    assert "recommendation_or_approval" in VISA_FIELDS
    assert "score_criteria" in STAY_FIELDS


def test_empty_item_contains_every_field_with_defaults():
    item = empty_item()
    assert set(ALL_FIELDS) == set(item)
    assert item["needs_human_review"] == "false"
    assert item["confidence"] == "0.00"


def test_suspicious_terms_match_known_korean_parse_errors():
    assert {"제목자격", "제목관리과", "제목족적"}.issubset(SUSPICIOUS_TERMS)
```

- [ ] **Step 2: Verify red**

Run: `python3 -m pytest tests/test_manual_review_schema.py -q`

Expected: import failure because `scripts.manual_review.schema` does not exist.

- [ ] **Step 3: Implement schema constants and `empty_item()`**

Create `scripts/manual_review/schema.py` with common/stay/visa fields, manual metadata, suspicious terms, high-value coverage terms, and `empty_item()`.

- [ ] **Step 4: Verify green**

Run: `python3 -m pytest tests/test_manual_review_schema.py -q`

Expected: all tests pass.

### Task 2: Extraction and Classification

**Files:**
- Create: `scripts/manual_review/extract.py`
- Test: `tests/test_manual_review_extract.py`

- [ ] **Step 1: Write failing tests**

```python
from scripts.manual_review.extract import classify_text, item_from_block, split_page_blocks


def test_split_page_blocks_keeps_heading_with_following_text():
    text = "1 각종 체류허가 등에 관한 심사수수료\n수수료 12만원\n\n2 여권 유효기간 범위 내 체류기간 부여 안내\n적용대상 모든 장기 체류자격 외국인"
    blocks = split_page_blocks(text)
    assert len(blocks) == 2
    assert blocks[0].title == "1 각종 체류허가 등에 관한 심사수수료"
    assert "12만원" in blocks[0].text


def test_classify_stay_fee_and_petition_fields():
    result = classify_text("체류자격 변경허가 수수료 10만원", "stay")
    assert result["item_type"] == "fee"
    assert result["subsection_type"] == "수수료"
    assert result["petition_type"] == "체류자격 변경"


def test_item_from_block_preserves_raw_text_and_evidence():
    item = item_from_block(
        manual_key="visa",
        page_no=7,
        title="외 교(A-1)",
        text="외 교(A-1)\n첨부서류\n① 사증발급신청서, 여권, 수수료",
        sequence=1,
    )
    assert item["visa_code"] == "A-1"
    assert item["visa_name_ko"] == "외교"
    assert item["required_documents"]
    assert item["evidence_quote"] in item["raw_text"]
```

- [ ] **Step 2: Verify red**

Run: `python3 -m pytest tests/test_manual_review_extract.py -q`

Expected: import failure because `extract.py` does not exist.

- [ ] **Step 3: Implement extraction functions**

Implement:
- `split_page_blocks(text: str) -> list[Block]`
- `classify_text(text: str, manual_key: str) -> dict[str, str]`
- `item_from_block(...) -> dict[str, str]`
- `extract_pdf_pages(pdf_path: Path) -> list[str]` using `pdftotext -layout`
- `build_items(limit_pages: bool = False) -> list[dict[str, str]]`

- [ ] **Step 4: Verify green**

Run: `python3 -m pytest tests/test_manual_review_extract.py -q`

Expected: all tests pass.

### Task 3: Quality Validation

**Files:**
- Create: `scripts/manual_review/quality.py`
- Test: `tests/test_manual_review_quality.py`

- [ ] **Step 1: Write failing tests**

```python
from scripts.manual_review.quality import quality_summary, validate_items


def test_validate_items_flags_missing_raw_text_and_bad_evidence():
    items = [{
        "item_id": "stay-000001",
        "manual_type": "체류민원",
        "raw_text": "",
        "evidence_quote": "없는 근거",
        "section_title": "제목자격 변경",
        "normalized_text": "",
        "needs_human_review": "false",
        "review_notes": "",
    }]
    errors = validate_items(items)
    messages = " ".join(error["message"] for error in errors)
    assert "empty raw_text" in messages
    assert "suspicious term" in messages


def test_quality_summary_reports_counts_and_coverage():
    items = [{
        "manual_type": "사증민원",
        "item_type": "visa_rule",
        "subsection_type": "대상",
        "visa_code": "C-3",
        "raw_text": "단기방문(C-3)",
        "evidence_quote": "단기방문(C-3)",
        "needs_human_review": "false",
    }]
    report = quality_summary(items, [])
    assert "Rows by manual_type" in report
    assert "C-3" in report
```

- [ ] **Step 2: Verify red**

Run: `python3 -m pytest tests/test_manual_review_quality.py -q`

Expected: import failure because `quality.py` does not exist.

- [ ] **Step 3: Implement validators and report**

Implement:
- `validate_items(items) -> list[dict[str, str]]`
- `quality_summary(items, errors) -> str`
- counters by manual type, item type, subsection type,
- suspicious term reporting,
- evidence containment reporting,
- high-value coverage reporting.

- [ ] **Step 4: Verify green**

Run: `python3 -m pytest tests/test_manual_review_quality.py -q`

Expected: all tests pass.

### Task 4: CLI and Final Artifacts

**Files:**
- Create: `scripts/build_manual_review_dataset.py`
- Test through full command execution.

- [ ] **Step 1: Implement CLI**

The command must write:
- `data/processed/manual_review_items.jsonl`
- `data/processed/manual_review_items.csv`
- `data/processed/manual_review_samples.csv`
- `data/processed/manual_review_validation_errors.jsonl`
- `data/processed/manual_review_quality_report.md`

- [ ] **Step 2: Run unit tests**

Run: `python3 -m pytest tests -q`

Expected: all tests pass.

- [ ] **Step 3: Run sample extraction**

Run: `python3 scripts/build_manual_review_dataset.py --sample`

Expected: artifacts are generated for critical sample pages and the report includes sample mode.

- [ ] **Step 4: Run full extraction**

Run: `python3 scripts/build_manual_review_dataset.py`

Expected: final artifacts are generated for both manuals.

- [ ] **Step 5: Completion audit**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
for path in [
    "data/processed/manual_review_items.jsonl",
    "data/processed/manual_review_items.csv",
    "data/processed/manual_review_quality_report.md",
]:
    p = Path(path)
    print(path, p.exists(), p.stat().st_size if p.exists() else 0)
PY
```

Expected: all three required artifacts exist and have non-zero size.

## Self-Review

- Spec coverage: tasks cover schema, broad manual-specific fields, source evidence, automated checks, and final JSONL/CSV/report artifacts.
- Placeholder scan: no implementation placeholders are left in the plan.
- Type consistency: functions and field names are consistent across tasks.
