"""출처·라인범위 lookup 헬퍼.

`data/parsed/chunks/{manual}_chunks_index.jsonl` 의 chunk_id → 라인범위
매핑을 한 번 로드한 뒤, 각 row 의 chunk_id 를 받아
``data/parsed/raw/{manual}_manual.md:start-end`` 형식 문자열로 돌려준다.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_chunk_lines(index_path: Path) -> dict[str, tuple[int, int]]:
    """chunks_index.jsonl 을 읽고 chunk_id → (start_line, end_line) 을 돌려준다."""
    out: dict[str, tuple[int, int]] = {}
    if not index_path.exists():
        return out
    with index_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            cid = obj.get("chunk_id")
            if not cid:
                continue
            out[cid] = (int(obj.get("start_line", 0)), int(obj.get("end_line", 0)))
    return out


def line_range_label(chunk_id: str, chunk_lines: dict[str, tuple[int, int]], manual_key: str) -> str:
    """chunk_id → "data/parsed/raw/{manual}_manual.md:start-end".

    매핑이 없거나 라인 정보가 부족하면 빈 문자열.
    """
    rng = chunk_lines.get(chunk_id)
    if not rng:
        return ""
    start, end = rng
    if start <= 0 or end <= 0:
        return ""
    return f"data/parsed/raw/{manual_key}_manual.md:{start}-{end}"
