#!/usr/bin/env python3
"""Reproduction agent CLI — runs the MRE for each benchmark entry and writes results."""

"""
python src/run_reproduction_agent.py \
  --benchmark /Users/haochending/reprocli/outputs/neurips_2025_minimax_m2_trial_extracted.jsonl \
  --paper-id 2504.12216 \
  --model gpt-5.5
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from openai import OpenAI

from reprocli_agent.prompt import BenchmarkEntry
from reprocli_agent.loop import run_session
from reprocli_agent.output import ReproResult


def main() -> None:
    args = parse_args()
    client = OpenAI(
        base_url=args.base_url or os.environ.get("OPENAI_BASE_URL"),
        api_key=args.api_key or os.environ.get("OPENAI_API_KEY") or "dummy",
    )
    entries = load_entries(args.benchmark, args.paper_id)
    if not entries:
        msg = (
            f"No entry for --paper-id={args.paper_id}"
            if args.paper_id
            else "Benchmark file is empty"
        )
        sys.exit(msg)

    print(f"Running reproduction agent on {len(entries)} entry(ies)", file=sys.stderr)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("a", encoding="utf-8") as out_f:
        for entry in entries:
            safe_id = entry.custom_id.replace("/", "_")
            workdir = Path(args.workdir) / safe_id
            workdir.mkdir(parents=True, exist_ok=True)
            print(f"[{entry.custom_id}] workdir={workdir}", file=sys.stderr)
            try:
                result = run_session(
                    entry, str(workdir), client, args.model, args.max_rounds
                )
            except Exception as exc:
                result = ReproResult(
                    custom_id=entry.custom_id,
                    reproduction_status="failed",
                    failure_reason=str(exc),
                )
            out_f.write(json.dumps(result.to_dict()) + "\n")
            out_f.flush()
            extra = f"  reason={result.failure_reason}" if result.failure_reason else ""
            print(
                f"[{entry.custom_id}] status={result.reproduction_status}{extra}",
                file=sys.stderr,
            )


def load_entries(path: str, paper_id: str | None) -> list[BenchmarkEntry]:
    entries: list[BenchmarkEntry] = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError as exc:
                print(
                    f"Warning: skipping line {lineno} (JSON error: {exc})",
                    file=sys.stderr,
                )
                continue
            if paper_id and d.get("custom_id") != paper_id:
                continue
            if "central_claim" not in d:
                print(
                    f"Warning: skipping line {lineno} ({d.get('custom_id', '?')}): missing central_claim",
                    file=sys.stderr,
                )
                continue
            entries.append(BenchmarkEntry.from_dict(d))
    return entries


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reproduction agent")
    p.add_argument("--benchmark", required=True, help="Path to benchmark JSONL file")
    p.add_argument("--paper-id", help="Run only this paper (custom_id)")
    p.add_argument("--output", default="outputs/reproduction_results.jsonl")
    p.add_argument("--workdir", default="/tmp/repro-sandboxes")
    p.add_argument("--model", default=os.environ.get("REPRO_MODEL", "gpt-4o"))
    p.add_argument("--max-rounds", type=int, default=30)
    p.add_argument(
        "--base-url", help="OpenAI-compatible base URL (e.g. http://127.0.0.1:8000/v1)"
    )
    p.add_argument("--api-key", help="API key (defaults to OPENAI_API_KEY env var)")
    return p.parse_args()


if __name__ == "__main__":
    main()
