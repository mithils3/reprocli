"""Recount Codex runs from their rollouts, correct the spend ledger, and void errored runs.

    python reconcile_spend.py --since 2026-11-06T18:11:00Z            # dry run: prints the table
    python reconcile_spend.py --since 2026-11-06T18:11:00Z --apply    # appends correction rows, writes VOID

Each run dir is ``<runs-dir>/<arxiv>/<budget>h/codex-<model>-<UTC stamp>-<hex>/``. Its true cost is the
sum over every rollout request (failed turns included). Ledger rows for the run (item YGTR-codex) are
subtracted, and the difference goes in as an YGTR-codex-correction row. Errored runs (report.json
exit_reason "error") get a VOID file, so grading skips them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "src"))

from codex_events import rollout_requests  # noqa: E402
from codex_run import TRANSIENT  # noqa: E402

RUN_NAME = re.compile(r"^codex-(?P<model>.+)-(?P<stamp>\d{8}T\d{6}Z)-[0-9a-f]+$")
KEYS = ("in", "cached", "out")


def void_reason(run: Path) -> str:
    """Why an errored run failed, read from its own logs (never assumed to be a rate limit)."""
    text = ""
    for name in ("agent.full.log", "codex_io/codex_stderr_work.log", "codex_io/codex_stderr_final.log"):
        path = run / name
        if path.is_file():
            text += path.read_text(encoding="utf-8", errors="replace")
    if TRANSIENT.search(text):
        return "rate-limit"
    if "can't start new thread" in text:
        return "thread limit at launch (RuntimeError: can't start new thread)"
    if re.search(r"\bpc\s+0x|fault\s+0x|SIGSEGV", text):
        return "codex native crash (SIGSEGV register dump)"
    return "harness error (no provider or crash signature in logs)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True, help="UTC stamp, e.g. 2026-11-06T18:11:00Z")
    ap.add_argument("--runs-dir", default="/work/nvme/bfvr/msalunkhe/reprocli/agent_runs")
    ap.add_argument("--ledger", default="/work/nvme/bfvr/msalunkhe/rebuttal/spend.jsonl")
    ap.add_argument("--apply", action="store_true")
    opts = ap.parse_args()
    since_key = re.sub(r"[-:]", "", opts.since)  # 2026-11-06T18:11:00Z -> 20261106T181100Z

    ledger_rows = []
    for line in Path(opts.ledger).read_text(encoding="utf-8").splitlines():
        try:
            ledger_rows.append(json.loads(line))
        except ValueError:
            pass
    recorded: dict[str, dict] = {}
    for row in ledger_rows:
        if row.get("item") == "YGTR-codex" and row.get("run_dir"):
            acc = recorded.setdefault(row["run_dir"], {k: 0 for k in KEYS} | {"usd": 0.0})
            acc["in"] += row.get("in", 0)
            acc["cached"] += row.get("cached", 0)
            acc["out"] += row.get("out", 0)
            acc["usd"] += row.get("usd", 0.0)

    corrections, voids = [], []
    runs = sorted(Path(opts.runs_dir).glob("*/*/codex-*"))
    for run in runs:
        m = RUN_NAME.match(run.name)
        if not m or m.group("stamp") < since_key:
            continue
        codex_home = run / "codex_io" / "codex_home"
        rows = rollout_requests(codex_home, m.group("model")) if codex_home.is_dir() else []
        true = {"in": sum(r["input_tokens"] for r in rows), "cached": sum(r["cached_input_tokens"] for r in rows),
                "out": sum(r["output_tokens"] for r in rows), "usd": round(sum(r["usd"] for r in rows), 6)}
        got = recorded.get(str(run), {"in": 0, "cached": 0, "out": 0, "usd": 0.0})
        diff = {k: true[k] - got[k] for k in KEYS} | {"usd": round(true["usd"] - got["usd"], 6)}
        report = run / "report.json"
        status = "-"
        if report.is_file():
            status = json.loads(report.read_text(encoding="utf-8")).get("exit_reason", "?")
        print(f"{run.name} requests={len(rows)} true_usd={true['usd']:.4f} "
              f"recorded_usd={got['usd']:.4f} correction_usd={diff['usd']:+.4f} exit={status}")
        if abs(diff["usd"]) > 1e-6 or any(diff[k] for k in KEYS):
            corrections.append((run, m.group("model"), diff))
        if status == "error":
            voids.append((run, void_reason(run)))

    total = round(sum(d["usd"] for _, _, d in corrections), 6)
    for run, why in voids:
        print(f"VOID {run.name}: {why}")
    print(f"runs={len(runs)} corrections={len(corrections)} total_correction_usd={total:+.4f} voids={len(voids)}")
    if not opts.apply:
        return 0
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with Path(opts.ledger).open("a", encoding="utf-8") as ledger:
        for run, model, diff in corrections:
            ledger.write(json.dumps({"ts": stamp, "item": "YGTR-codex-correction", "provider": "openai",
                                     "model": model, "in": diff["in"], "cached": diff["cached"],
                                     "out": diff["out"], "usd": diff["usd"], "run_dir": str(run),
                                     "reason": "rollout recount (includes failed turns)"}) + "\n")
    for run, why in voids:
        (run / "VOID").write_text(f"reason: {why}; harness: codex-arm (run errored; rerun)\n", encoding="utf-8")
    print(f"applied: ledger rows={len(corrections)} void_files={len(voids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
