#!/usr/bin/env python3
"""Grade the finished frontier-arm runs with the pinned auditor (claude-sonnet-5).

A run is gradeable when its bundle has report.json and no VOID file. Each run is
staged as a one-run runs dir of symlinks, because the grader takes the newest
bundle per paper. A run already in grades.jsonl is skipped, so a second pass
grades only what is new. Verdicts append one line per run to grades.jsonl; the
Anthropic cost appends to the spend ledger.

Run on DeltaAI from ~/reprocli with the key loaded by pointer:
    source <(rg '^export ANTHROPIC_API_KEY=' ~/.bashrc)
    ~/reprocli/.venv/bin/python scripts/rebuttal/grade_arms.py [--dry-run] [--match TEXT] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

RUNS = Path("/work/nvme/bfvr/msalunkhe/reprocli/agent_runs")
ROOT = Path("/work/nvme/bfvr/msalunkhe/rebuttal")
GRADING = ROOT / "grading"
GRADES = GRADING / "grades.jsonl"
FAILURES = GRADING / "failures.jsonl"
LEDGER = ROOT / "spend.jsonl"
CHECKOUT = Path.home() / "reprocli"
PYTHON = CHECKOUT / ".venv" / "bin" / "python"
MODEL = "claude-sonnet-5"
# Mithil's cap on all Anthropic spend in the rebuttal ledger (2026-11-07): $200 total.
ANTHROPIC_CAP_USD = 200.0
EST_GRADE_USD = 3.0
SKIP_PAPERS = {"2511.07099", "2510.21323"}
ARM_RE = re.compile(
    r"^(?P<arm>codex-gpt-6\.1-sol-nudge|codex-gpt-6\.1-terra-nudge|codex-gpt-6-astra-nudge|codex-gpt-6\.1-sol|codex-gpt-6\.1-terra|codex-gpt-6-astra|miniswe)"
    r"-(?:\d{4}\.\d{4,5}-)?\d{8}T\d{6}Z?"
)
# Thin-harness run ids (core-a-<paper>-<hash>) carry no model, so the arm comes from the sweep log that started them.
THIN_LOGS = {"thin-astra-x86.log": "thin-gpt-6-astra-x86", "thin-sol-x86.log": "thin-gpt-6.1-sol-x86", "thin-astra-core.log": "thin-gpt-6-astra", "thin-sol-core.log": "thin-gpt-6.1-sol", "thin-musew-core.log": "thin-muse-wonder-1.0",
             "thin-terra-core.log": "thin-gpt-6.1-terra"}
THREADS = {"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}


def thin_arms() -> dict[str, str]:
    arms = {}
    for name, arm in THIN_LOGS.items():
        log = ROOT / name
        if log.is_file():
            for rid in re.findall(r"\(run_id=([^)\s]+)\)", log.read_text(errors="replace")):
                arms[rid] = arm
    return arms


def candidates(match: str | None) -> list[dict]:
    found = []
    thin = thin_arms()
    for paper_dir in sorted(RUNS.iterdir()):
        if not paper_dir.is_dir() or paper_dir.name in SKIP_PAPERS:
            continue
        for run_dir in sorted(paper_dir.glob("*h/*")):
            m = ARM_RE.match(run_dir.name)
            arm = m["arm"] if m else thin.get(run_dir.name)
            if not arm or not run_dir.is_dir() or (match and match not in run_dir.name):
                continue
            if not (run_dir / "report.json").is_file() or (run_dir / "VOID").exists():
                continue
            found.append({"arm": arm, "paper": paper_dir.name, "budget": run_dir.parent.name,
                          "run_id": run_dir.name, "run_dir": run_dir})
    return found


def graded_ids() -> set[str]:
    if not GRADES.is_file():
        return set()
    return {json.loads(line)["run_id"] for line in GRADES.read_text().splitlines() if line.strip()}


def append(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(obj, sort_keys=True) + "\n")


def stage(c: dict) -> Path:
    root = GRADING / c["arm"] / c["run_id"]
    link = root / c["paper"] / c["budget"] / c["run_id"]
    link.parent.mkdir(parents=True, exist_ok=True)
    if not link.is_symlink():
        link.symlink_to(c["run_dir"])
    return root


def grade_one(c: dict, stamp: str) -> tuple[dict, dict | None, str | None]:
    root = stage(c)
    out = GRADING / "out"
    logs = GRADING / "logs"
    out.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    tag = f"{c['run_id']}_{stamp}"
    ext, raw, log = out / f"{tag}_extracted.jsonl", out / f"{tag}_raw.jsonl", logs / f"{tag}.log"
    cmd = [str(PYTHON), "-m", "reprocli_claude", "--paper-ids", c["paper"], "--runs-dir", str(root),
           "--split", "eval", "--model", MODEL, "--workers", "1", "--no-stream",
           "--extracted-output", str(ext), "--output", str(raw)]
    env = dict(os.environ, PYTHONPATH="src", **THREADS)
    with log.open("w") as fh:
        rc = subprocess.run(cmd, cwd=CHECKOUT, env=env, stdout=fh, stderr=subprocess.STDOUT).returncode
    if rc != 0:
        return c, None, f"grader exit {rc}, log {log}"
    try:
        raw_row = json.loads(raw.read_text().splitlines()[0])
        ext_row = json.loads(ext.read_text().splitlines()[0])
    except (OSError, IndexError, ValueError) as exc:
        return c, None, f"no verdict row ({type(exc).__name__}), log {log}"
    if c["run_id"] not in raw_row.get("bundle", "") or not isinstance(ext_row.get("score"), int):
        return c, None, f"no integer score (score={ext_row.get('score')}), log {log}"
    usage = raw_row.get("usage", {})
    now = datetime.now().isoformat(timespec="seconds")
    rec = {"arm": c["arm"], "model": c["arm"].removeprefix("codex-").removeprefix("thin-"), "paper": c["paper"],
           "budget": c["budget"], "run_id": c["run_id"], "score": ext_row["score"],
           "verdict": ext_row.get("verdict"), "reproduced": ext_row.get("reproduced"),
           "auditor_model": MODEL, "cost_usd": usage.get("cost_usd"), "graded_at": now,
           "verdicts": str(ext), "raw": str(raw), "run_dir": str(c["run_dir"])}
    led = {"ts": now, "item": "frontier-grade", "provider": "anthropic", "model": MODEL,
           "in": usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0),
           "cached": usage.get("cache_read_input_tokens", 0), "out": usage.get("output_tokens", 0),
           "usd": usage.get("cost_usd"), "arm": c["arm"], "custom_id": c["paper"],
           "note": f"grade of {c['arm']} run {c['run_id']}; in = input + cache write",
           "run_dir": str(c["run_dir"])}
    return c, {**rec, "_ledger": led}, None


def anthropic_spent() -> float:
    total = 0.0
    if LEDGER.is_file():
        for line in LEDGER.read_text(errors="replace").splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("provider") == "anthropic":
                total += float(d.get("usd") or 0)
    return total


_gate = threading.Lock()
_inflight = [0]


def gated_grade(c: dict, stamp: str):
    with _gate:
        spent = anthropic_spent()
        if spent + (_inflight[0] + 1) * EST_GRADE_USD > ANTHROPIC_CAP_USD:
            return c, None, f"skipped: Anthropic cap ${ANTHROPIC_CAP_USD:.0f} (spent ${spent:.2f}, {_inflight[0]} in flight)"
        _inflight[0] += 1
    try:
        return grade_one(c, stamp)
    finally:
        with _gate:
            _inflight[0] -= 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--match", help="grade only run ids containing this text")
    ap.add_argument("--limit", type=int, help="grade at most this many pending runs")
    ap.add_argument("--workers", type=int, default=3, help="grades run concurrently (default 3)")
    ap.add_argument("--dry-run", action="store_true", help="list pending runs and stop")
    args = ap.parse_args()

    done = graded_ids()
    allc = candidates(args.match)
    todo = [c for c in allc if c["run_id"] not in done]
    if args.limit is not None:
        todo = todo[: args.limit]
    print(f"gradeable {len(allc)}, already graded {len(done & {c['run_id'] for c in allc})}, "
          f"to grade {len(todo)}", file=sys.stderr)
    if args.dry_run:
        for c in todo:
            print(f"{c['arm']}\t{c['paper']}\t{c['budget']}\t{c['run_id']}")
        return 0
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set; load it from ~/.bashrc by pointer first")

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    failed = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(gated_grade, c, stamp) for c in todo]
        for fut in as_completed(futures):
            c, rec, err = fut.result()
            if rec is None and err and err.startswith("skipped: Anthropic cap"):
                print(f"{c['run_id']}: {err}", file=sys.stderr)
                continue
            if rec is None:
                failed += 1
                append(FAILURES, {"run_id": c["run_id"], "arm": c["arm"], "paper": c["paper"], "error": err})
                print(f"FAILED {c['run_id']}: {err}", file=sys.stderr)
                continue
            ledger = rec.pop("_ledger")
            append(GRADES, rec)
            append(LEDGER, ledger)
            print(f"graded {c['run_id']} score={rec['score']} verdict={rec['verdict']} "
                  f"cost=${rec['cost_usd']}", file=sys.stderr)
    print(f"done: {len(todo) - failed} graded, {failed} failed", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
