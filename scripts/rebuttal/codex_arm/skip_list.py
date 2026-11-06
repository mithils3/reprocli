"""Print the comma-separated paper ids a sweep for one model should skip.

A paper is skipped when it has a finished, non-VOID run for the model (report.json, no VOID file), or
a run for the model still in flight (its launcher is alive), so a new sweep never duplicates a paper.

    python skip_list.py --model gpt-6.1-sol
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_run import tagged_pids  # noqa: E402


def skip_ids(runs_dir: Path, model: str) -> list[str]:
    ids: set[str] = set()
    for run in sorted(runs_dir.glob(f"*/*/codex-{model}-*")):
        if (run / "VOID").is_file():
            continue
        if (run / "report.json").is_file() or tagged_pids(run.name):
            ids.add(run.parent.parent.name)
    return sorted(ids)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--runs-dir", default="/work/nvme/bfvr/msalunkhe/reprocli/agent_runs")
    opts = ap.parse_args()
    print(",".join(skip_ids(Path(opts.runs_dir), opts.model)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
