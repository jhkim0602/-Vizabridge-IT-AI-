#!/usr/bin/env python3
"""Stage 1 of the Vizabridge pipeline: HWP → Markdown via kordoc.

Reads every ``*.hwp`` in ``data/raw/`` (top-level only — ``data/raw/legacy_pdf/``
is intentionally excluded) and runs ``npx kordoc`` to produce a Markdown copy
under ``data/parsed/raw/<manual_key>_manual.md``.

The Markdown produced here is the source-of-truth for every later stage. It is
not opened or modified by humans; subsequent stages chunk it, normalize it via
the Claude Code skill, and finally build CSVs from the normalized output.

Usage:
    .venv/bin/python scripts/parse_hwp_to_markdown.py            # incremental
    .venv/bin/python scripts/parse_hwp_to_markdown.py --force    # re-parse all

Requires Node.js >= 18 with npx available.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PARSED_RAW_DIR = PROJECT_ROOT / "data" / "parsed" / "raw"


MANUAL_KEY_KEYWORDS = {
    "체류민원": "stay",
    "사증민원": "visa",
}


@dataclass
class HwpJob:
    source: Path
    manual_key: str
    output: Path


def derive_manual_key(hwp_path: Path) -> str:
    for keyword, key in MANUAL_KEY_KEYWORDS.items():
        if keyword in hwp_path.name:
            return key
    raise SystemExit(
        f"파일명에서 manual_key를 알 수 없습니다: {hwp_path.name}. "
        f"파일명에 {list(MANUAL_KEY_KEYWORDS)} 중 하나가 포함돼야 합니다."
    )


def discover_jobs() -> list[HwpJob]:
    hwps = sorted(p for p in RAW_DIR.glob("*.hwp") if p.is_file())
    if not hwps:
        raise SystemExit(f"HWP 파일이 없습니다: {RAW_DIR}")
    jobs: list[HwpJob] = []
    seen_keys: set[str] = set()
    for hwp in hwps:
        manual_key = derive_manual_key(hwp)
        if manual_key in seen_keys:
            raise SystemExit(
                f"같은 manual_key({manual_key})가 두 번 등장합니다. 한 매뉴얼당 HWP 하나만 두세요."
            )
        seen_keys.add(manual_key)
        jobs.append(
            HwpJob(
                source=hwp,
                manual_key=manual_key,
                output=PARSED_RAW_DIR / f"{manual_key}_manual.md",
            )
        )
    return jobs


def check_node_environment() -> None:
    for binary in ("node", "npx"):
        if shutil.which(binary) is None:
            raise SystemExit(
                f"{binary}를 찾을 수 없습니다. Node.js 18+ 설치 후 다시 실행하세요."
            )
    result = subprocess.run(
        ["node", "--version"], check=True, capture_output=True, text=True
    )
    version = result.stdout.strip().lstrip("v")
    major = int(version.split(".")[0])
    if major < 18:
        raise SystemExit(f"Node.js {major} (필요: 18 이상). 업그레이드 후 다시 실행하세요.")


def is_up_to_date(job: HwpJob) -> bool:
    if not job.output.exists():
        return False
    return job.output.stat().st_mtime >= job.source.stat().st_mtime


def parse_one(job: HwpJob) -> None:
    job.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"  변환: {job.source.name}", flush=True)
    print(f"    → {job.output.relative_to(PROJECT_ROOT)}", flush=True)
    completed = subprocess.run(
        ["npx", "--yes", "kordoc", str(job.source), "-o", str(job.output), "--silent"],
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            f"kordoc 실패 (exit={completed.returncode}): {job.source.name}"
        )
    if not job.output.exists() or job.output.stat().st_size == 0:
        raise SystemExit(f"출력 파일 비어 있음: {job.output}")


def main() -> int:
    parser = argparse.ArgumentParser(description="HWP → Markdown (kordoc)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="출력이 입력보다 최신이어도 강제 재변환",
    )
    args = parser.parse_args()

    check_node_environment()
    jobs = discover_jobs()

    print(f"발견한 HWP {len(jobs)}개:")
    for job in jobs:
        print(f"  [{job.manual_key}] {job.source.name} ({job.source.stat().st_size/1024:.0f} KB)")
    print()

    processed = 0
    skipped = 0
    for job in jobs:
        if not args.force and is_up_to_date(job):
            print(f"  스킵 (최신): {job.output.relative_to(PROJECT_ROOT)}")
            skipped += 1
            continue
        parse_one(job)
        size_kb = job.output.stat().st_size / 1024
        print(f"    {size_kb:.0f} KB 생성")
        processed += 1

    print()
    print(f"완료: 변환 {processed}, 스킵 {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
