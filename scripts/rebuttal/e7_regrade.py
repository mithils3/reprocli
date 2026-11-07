#!/usr/bin/env python3
"""E7 sensitivity: re-grade the original cells of the 10 value_wrong papers against the frozen claim
and against the corrected claim, with the pinned auditor (claude-sonnet-5) and the unchanged rubric.

Each (cell, claim) pair is one grade of the cell's original run dir, staged as a one-run runs dir of
symlinks (the grader takes the newest bundle per paper). The claim comes from `--claims`, which the
grader already supports; nothing about default grading changes. A pair already in grades.jsonl is
skipped. Cost appends to the spend ledger (item E7-rescore); submission stops past --cap USD.

Run on DeltaAI from ~/reprocli with the key loaded by pointer:
    source <(rg '^export ANTHROPIC_API_KEY=' ~/.bashrc)
    ~/reprocli/.venv/bin/python scripts/rebuttal/e7_regrade.py [--dry-run] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

RUNS = Path("/work/nvme/bfvr/msalunkhe/reprocli/agent_runs")
ROOT = Path("/work/nvme/bfvr/msalunkhe/rebuttal")
WORK = ROOT / "e7" / "regrade"
GRADES = WORK / "grades.jsonl"
LEDGER = ROOT / "spend.jsonl"
CHECKOUT = Path.home() / "reprocli"
PYTHON = CHECKOUT / ".venv" / "bin" / "python"
MODEL = "claude-sonnet-5"
CELLS = CHECKOUT / "rebuttal/results/e7/rescore_cells.json"
CLAIMS = {"original": ROOT / "e7" / "eval_100.jsonl",
          "corrected": CHECKOUT / "rebuttal/results/e7/corrected_targets.jsonl"}
THREADS = {"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
LOCK = threading.Lock()
spent = 0.0


def done_keys() -> set[tuple[str, str]]:
    if not GRADES.is_file():
        return set()
    rows = (json.loads(line) for line in GRADES.read_text().splitlines() if line.strip())
    return {(r["cell"], r["claim"]) for r in rows}


def append(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with LOCK, path.open("a") as fh:
        fh.write(json.dumps(obj, sort_keys=True) + "\n")


def grade_one(cell: dict, claim: str, stamp: str, cap: float):
    if spent >= cap:
        return cell, claim, None, f"skipped, spend {spent:.2f} reached cap {cap}"
    run_dir = RUNS / cell["run_dir_rel"]
    root = WORK / "stage" / f"{cell['cell']}__{claim}"
    link = root / cell["paper"] / run_dir.parent.name / run_dir.name
    link.parent.mkdir(parents=True, exist_ok=True)
    if not link.is_symlink():
        link.symlink_to(run_dir)
    tag = f"{cell['cell']}__{claim}_{stamp}"
    out = WORK / "out"
    out.mkdir(parents=True, exist_ok=True)
    ext, raw, log = out / f"{tag}_extracted.jsonl", out / f"{tag}_raw.jsonl", out / f"{tag}.log"
    cmd = [str(PYTHON), "-m", "reprocli_claude", "--paper-ids", cell["paper"], "--runs-dir", str(root),
           "--split", "eval", "--claims", str(CLAIMS[claim]), "--model", MODEL, "--workers", "1",
           "--no-stream", "--extracted-output", str(ext), "--output", str(raw)]
    env = dict(os.environ, PYTHONPATH="src", **THREADS)
    with log.open("w") as fh:
        rc = subprocess.run(["nice", "-n", "19"] + cmd, cwd=CHECKOUT, env=env, stdout=fh,
                            stderr=subprocess.STDOUT).returncode
    if rc != 0:
        return cell, claim, None, f"grader exit {rc}, log {log}"
    try:
        raw_row = json.loads(raw.read_text().splitlines()[0])
        ext_row = json.loads(ext.read_text().splitlines()[0])
    except (OSError, IndexError, ValueError) as exc:
        return cell, claim, None, f"no verdict row ({type(exc).__name__}), log {log}"
    if not isinstance(ext_row.get("score"), int):
        return cell, claim, None, f"no integer score ({ext_row.get('score')}), log {log}"
    u = raw_row.get("usage", {})
    now = datetime.now().isoformat(timespec="seconds")
    rec = {"cell": cell["cell"], "claim": claim, "paper": cell["paper"], "score": ext_row["score"],
           "verdict": ext_row.get("verdict"), "reproduced": ext_row.get("reproduced"),
           "auditor_model": MODEL, "cost_usd": u.get("cost_usd"), "graded_at": now,
           "verdicts": str(ext), "raw": str(raw), "run_dir": str(run_dir)}
    led = {"ts": now, "item": "E7-rescore", "provider": "anthropic", "model": MODEL,
           "in": u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0),
           "cached": u.get("cache_read_input_tokens", 0), "out": u.get("output_tokens", 0),
           "usd": u.get("cost_usd"), "custom_id": cell["paper"],
           "note": f"re-grade of {cell['cell']} against the {claim} claim; in = input + cache write",
           "run_dir": str(run_dir)}
    return cell, claim, (rec, led), None


def main() -> int:
    global spent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cap", type=float, default=85.0, help="stop submitting grades past this USD")
    ap.add_argument("--match", help="only cells whose id contains this text")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cells = json.loads(CELLS.read_text())
    missing = [c["cell"] for c in cells if not (RUNS / c["run_dir_rel"] / "report.json").is_file()]
    if missing:
        print(f"no report.json for {missing}", file=sys.stderr)
    done = done_keys()
    todo = [(c, k) for c in cells if not args.match or args.match in c["cell"] for k in CLAIMS
            if (c["cell"], k) not in done]
    if args.limit is not None:
        todo = todo[: args.limit]
    print(f"cells {len(cells)}, grades to run {len(todo)}", file=sys.stderr)
    if args.dry_run:
        for c, k in todo:
            print(f"{c['cell']}\t{k}\t{c['run_dir_rel']}")
        return 0
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set; load it from ~/.bashrc by pointer first")
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    failed = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = [pool.submit(grade_one, c, k, stamp, args.cap) for c, k in todo]
        for fut in as_completed(futs):
            cell, claim, ok, err = fut.result()
            if ok is None:
                failed += 1
                print(f"FAILED {cell['cell']} {claim}: {err}", file=sys.stderr, flush=True)
                continue
            rec, led = ok
            append(GRADES, rec)
            append(LEDGER, led)
            spent += rec["cost_usd"] or 0.0
            print(f"graded {cell['cell']} {claim} score={rec['score']} verdict={rec['verdict']} "
                  f"cost=${rec['cost_usd']} total=${spent:.2f}", file=sys.stderr, flush=True)
    print(f"done: {len(todo) - failed} graded, {failed} failed, spend ${spent:.2f}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
