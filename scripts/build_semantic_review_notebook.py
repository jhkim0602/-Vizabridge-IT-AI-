#!/usr/bin/env python3
"""Create a human-review notebook for semantic immigration manual CSVs.

The notebook is generated as plain ipynb JSON so it does not depend on
nbformat/matplotlib. Pandas computes the review tables and the notebook embeds
HTML bar charts that render in Jupyter.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "03_review_semantic_manual_csvs.ipynb"


FILES = {
    "stay_current": PROCESSED_DIR / "stay_manual_clean.csv",
    "visa_current": PROCESSED_DIR / "visa_manual_clean.csv",
    "stay_semantic": PROCESSED_DIR / "stay_manual_semantic_clean.csv",
    "visa_semantic": PROCESSED_DIR / "visa_manual_semantic_clean.csv",
}


def html_bar_table(df: pd.DataFrame, label_col: str, value_col: str, title: str, max_rows: int = 20) -> str:
    data = df.head(max_rows).copy()
    max_value = max(float(data[value_col].max() or 1), 1.0)
    rows = []
    for _, row in data.iterrows():
        label = str(row[label_col])
        value = int(row[value_col])
        pct = max(value / max_value * 100, 2)
        rows.append(
            f"""
            <tr>
              <td class="label">{label}</td>
              <td class="bar-cell"><div class="bar" style="width:{pct:.1f}%"></div></td>
              <td class="value">{value:,}</td>
            </tr>
            """
        )
    return f"""
    <style>
      .semantic-review h3 {{ margin: 18px 0 8px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }}
      .semantic-review table {{ border-collapse: collapse; width: 100%; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 13px; }}
      .semantic-review th, .semantic-review td {{ border-bottom: 1px solid #e5e7eb; padding: 6px 8px; vertical-align: top; }}
      .semantic-review .label {{ width: 220px; white-space: nowrap; }}
      .semantic-review .bar-cell {{ width: 60%; }}
      .semantic-review .bar {{ height: 16px; background: #2f6f7e; border-radius: 3px; }}
      .semantic-review .value {{ width: 90px; text-align: right; font-variant-numeric: tabular-nums; }}
    </style>
    <div class="semantic-review">
      <h3>{title}</h3>
      <table>
        <thead><tr><th>{label_col}</th><th>distribution</th><th>{value_col}</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """


def df_to_html(df: pd.DataFrame, title: str, max_colwidth: int = 180) -> str:
    display_df = df.copy()
    for col in display_df.columns:
        display_df[col] = display_df[col].map(
            lambda value: str(value)[: max_colwidth - 1] + "…" if len(str(value)) > max_colwidth else value
        )
    table = display_df.to_html(index=False, escape=True)
    return f"<div class='semantic-review'><h3>{title}</h3>{table}</div>"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str).fillna("")


def make_output_html(html: str) -> dict:
    return {"output_type": "display_data", "data": {"text/html": html}, "metadata": {}}


def make_code_cell(source: str, outputs: list[dict] | None = None) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": outputs or [],
        "source": source.splitlines(keepends=True),
    }


def make_markdown_cell(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def main() -> None:
    frames = {name: read_csv(path) for name, path in FILES.items()}

    overview_rows = []
    for manual in ["stay", "visa"]:
        current = frames[f"{manual}_current"]
        semantic = frames[f"{manual}_semantic"]
        overview_rows.append(
            {
                "manual": manual,
                "current_rows": len(current),
                "semantic_rows": len(semantic),
                "semantic_review_rows": int((semantic["needs_human_review"] == "true").sum()),
                "semantic_review_pct": f"{(semantic['needs_human_review'] == 'true').mean() * 100:.1f}%",
                "nonempty_code_rows": int(semantic["visa_code"].astype(bool).sum()),
                "unique_codes": semantic.loc[semantic["visa_code"].astype(bool), "visa_code"].nunique(),
            }
        )
    overview = pd.DataFrame(overview_rows)

    schema = pd.DataFrame(
        [
            ("manual_type", "사증민원/체류민원 구분"),
            ("source_pdf", "원본 PDF 파일명"),
            ("source_section_path", "문서 구조 기반 근거 경로"),
            ("visa_code", "비자/체류자격 코드. 체류 매뉴얼도 검색 통합을 위해 이 컬럼을 사용"),
            ("visa_name_ko", "코드의 한국어 명칭"),
            ("petition_type", "사증발급, 사증발급인정서, 체류자격 변경, 체류기간 연장 등 민원유형"),
            ("topic_type", "대상, 요건, 제출서류, 절차, 제한, 예외, 기간 등 지식 주제"),
            ("applicant_context", "하위 약호나 신청자 맥락"),
            ("answer_summary", "사람이 읽는 정리문"),
            ("ai_search_text", "사용자 표현 매칭/임베딩용 확장 검색 텍스트"),
            ("evidence_quote", "검수용 짧은 근거"),
            ("source_raw_text", "검수용 원문 조각"),
            ("needs_human_review", "표/복수코드/장문/분류약함 등 검수 필요 여부"),
        ],
        columns=["column", "review_meaning"],
    )

    charts: list[tuple[str, str]] = []
    for manual in ["stay", "visa"]:
        semantic = frames[f"{manual}_semantic"]
        for col in ["topic_type", "petition_type", "visa_code"]:
            counts = semantic[col].replace("", "COMMON").value_counts().reset_index()
            counts.columns = [col, "rows"]
            charts.append((f"{manual} semantic rows by {col}", html_bar_table(counts, col, "rows", f"{manual}: {col}")))

    review_samples = []
    for manual in ["stay", "visa"]:
        semantic = frames[f"{manual}_semantic"]
        sample = semantic[semantic["needs_human_review"] == "true"][
            [
                "manual_type",
                "visa_code",
                "visa_name_ko",
                "petition_type",
                "topic_type",
                "source_section_path",
                "review_notes",
                "answer_summary",
            ]
        ].head(30)
        review_samples.append((manual, sample))

    focus_rows = []
    focus_codes = ["D-8", "D-8-1", "D-8-4S", "E-7", "E-7-4", "F-6", "F-6-1", "F-6-2"]
    for manual in ["stay", "visa"]:
        semantic = frames[f"{manual}_semantic"]
        focus = semantic[semantic["visa_code"].isin(focus_codes)][
            [
                "manual_type",
                "visa_code",
                "visa_name_ko",
                "petition_type",
                "topic_type",
                "applicant_context",
                "answer_summary",
                "needs_human_review",
            ]
        ].head(80)
        focus_rows.append((manual, focus))

    query_checks = []
    phrases = [
        "외국인이 한국에서 법인을 만들고 살려면",
        "한국 회사가 외국 전문인력을 채용하려면",
        "한국인과 결혼한 외국인은",
    ]
    for manual in ["stay", "visa"]:
        semantic = frames[f"{manual}_semantic"]
        for phrase in phrases:
            hits = semantic[semantic["ai_search_text"].str.contains(phrase, regex=False, na=False)]
            top_codes = ", ".join(hits["visa_code"].head(8).tolist())
            query_checks.append({"manual": manual, "phrase": phrase, "hits": len(hits), "top_codes": top_codes})
    query_df = pd.DataFrame(query_checks)

    cells = [
        make_markdown_cell(
            "# Semantic manual CSV review\n\n"
            "이 노트북은 기존 page/chunk clean CSV와 새 semantic clean CSV를 사람이 검수하기 쉽게 비교합니다. "
            "시각화는 pandas로 집계한 결과를 HTML bar chart로 렌더링합니다."
        ),
        make_code_cell(
            "from pathlib import Path\n"
            "import pandas as pd\n\n"
            "ROOT = Path('..').resolve()\n"
            "processed = ROOT / 'data' / 'processed'\n"
            "stay_current = pd.read_csv(processed / 'stay_manual_clean.csv', dtype=str).fillna('')\n"
            "visa_current = pd.read_csv(processed / 'visa_manual_clean.csv', dtype=str).fillna('')\n"
            "stay_semantic = pd.read_csv(processed / 'stay_manual_semantic_clean.csv', dtype=str).fillna('')\n"
            "visa_semantic = pd.read_csv(processed / 'visa_manual_semantic_clean.csv', dtype=str).fillna('')"
        ),
        make_code_cell("overview", [make_output_html(df_to_html(overview, "Current CSV vs semantic CSV overview"))]),
        make_code_cell("schema", [make_output_html(df_to_html(schema, "Semantic schema review map", 240))]),
    ]

    for title, chart_html in charts:
        cells.append(make_code_cell(f"# {title}", [make_output_html(chart_html)]))

    cells.append(make_code_cell("query_df", [make_output_html(df_to_html(query_df, "Search intent sanity checks", 220))]))

    for manual, sample in review_samples:
        cells.append(make_code_cell(f"# {manual} rows needing human review", [make_output_html(df_to_html(sample, f"{manual}: review queue", 220))]))

    for manual, focus in focus_rows:
        cells.append(make_code_cell(f"# {manual} D-8/E-7/F-6 focus rows", [make_output_html(df_to_html(focus, f"{manual}: D-8/E-7/F-6 focus sample", 220))]))

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK_PATH.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
    print(NOTEBOOK_PATH)


if __name__ == "__main__":
    main()
