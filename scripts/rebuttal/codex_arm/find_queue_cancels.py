"""List Codex runs whose agent signalled or cancelled a pending GPU allocation.

    python find_queue_cancels.py --since 2026-11-06T18:11:00Z [--runs-dir DIR]

A match is an agent shell command that kills a process by pid, or calls scancel or pkill, in
its own agent.full.log. Prints one line per match; VOID marking is done by the caller.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

RUN_NAME = re.compile(r"^codex-(?P<model>.+)-(?P<stamp>\d{8}T\d{6}Z)-[0-9a-f]+$")
EXEC = re.compile(r"\] exec rc=[^:]*: (?P<cmd>.*)$")
CANCEL = re.compile(r"\bkill\b(\s+-\w+)?\s+\d+|\bscancel\b|\bpkill\b")


def matches(run: Path) -> list[str]:
    hits = []
    log = run / "agent.full.log"
    if not log.is_file():
        return hits
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        m = EXEC.search(line)
        if m and CANCEL.search(m.group("cmd")):
            hits.append(m.group("cmd")[:160])
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True)
    ap.add_argument("--runs-dir", default="/work/nvme/bfvr/msalunkhe/reprocli/agent_runs")
    opts = ap.parse_args()
    since = re.sub(r"[-:]", "", opts.since)
    for run in sorted(Path(opts.runs_dir).glob("*/*/codex-*")):
        m = RUN_NAME.match(run.name)
        if not m or m.group("stamp") < since:
            continue
        hits = matches(run)
        if hits:
            status = "VOID" if (run / "VOID").is_file() else ("finished" if (run / "report.json").is_file() else "running")
            print(f"{run.parent.parent.name}\t{run.name}\t{status}\t{len(hits)}\t{hits[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
