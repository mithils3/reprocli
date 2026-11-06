"""Tabulate GPU-budget use, spend, and stop reason for each finished frontier run.

Reads run dirs (read only) on DeltaAI and writes run_usage.csv and run_usage_summary.md.
Stdlib only, Python 3.6 compatible. Usage on DeltaAI:
  python3 -I scripts/rebuttal/run_usage_table.py --out-dir <dir>
"""
import argparse
import csv
import datetime
import io
import json
import os
import re
import statistics
import sys

RUNS_ROOT = "/work/nvme/bfvr/msalunkhe/reprocli/agent_runs"
SWEEPS_ROOT = "/work/nvme/bfvr/msalunkhe/rebuttal/sweeps"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SUBSET = os.path.join(REPO, "rebuttal", "subset.json")
EXCLUDE_PAPERS = {"2511.07099", "2510.21323"}
RUN_PREFIXES = ("codex-gpt-6.1-sol-", "codex-gpt-6.1-terra-", "codex-gpt-6-astra-", "miniswe-")

RE_TS = re.compile(r"^\[(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)\]", re.M)
RE_RUN_GPU = re.compile(r"run_gpu ok=(True|False) rc=\S+ cost_h100h=(\S+)")
RE_DONE = re.compile(r"DONE exit_reason=(\S+) usd=([0-9.]+) requests=\d+ resumes=(\d+)")
RE_MINI_BLOCK = re.compile(r'^\{\n  "ok": (true|false),.*?^\}', re.M | re.S)
RE_MINI_COST = re.compile(r'"cost_h100_hours": ([0-9.]+)')

COLUMNS = ["arm", "model", "arxiv_id", "tier", "budget_h100h", "gpu_h100h_used",
           "pct_budget_used", "n_gpu_calls", "n_gpu_ok", "wall_minutes", "usd",
           "exit_reason", "resumes", "agent_assessment", "blockers_first_120_chars"]


def read_text(path):
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def load_json(path):
    if not os.path.exists(path):
        return {}
    return json.loads(read_text(path))


def tier_map(subset_path):
    data = load_json(subset_path)
    out = {}
    for key in ("core", "extension"):
        for row in data.get(key, []):
            out[row["paper_id"]] = row["tier"]
    return out


def gpu_calls(log):
    """Return (ok flags, cost list) for every run_gpu result in a Codex-arm or miniswe-arm log."""
    codex = RE_RUN_GPU.findall(log)
    if codex:
        return [flag == "True" for flag, _ in codex], [float(c) if c != "None" else 0.0 for _, c in codex]
    oks, costs = [], []
    for m in RE_MINI_BLOCK.finditer(log):
        if '"tool": "run_gpu"' not in m.group(0):
            continue
        oks.append(m.group(1) == "true")
        c = RE_MINI_COST.search(m.group(0))
        costs.append(float(c.group(1)) if c else 0.0)
    return oks, costs


def wall_minutes(log):
    stamps = [datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ") for s in RE_TS.findall(log)]
    if len(stamps) < 2:
        return ""
    return round((max(stamps) - min(stamps)).total_seconds() / 60.0, 1)


def budget_of(run_dir, dirname):
    cr = load_json(os.path.join(run_dir, "codex_run.json"))
    if "budget_h100_hours" in cr:
        return float(cr["budget_h100_hours"])
    st = load_json(os.path.join(run_dir, "stats.json"))
    if "budget_h100" in st:
        return float(st["budget_h100"])
    m = re.search(r"/([0-9.]+)h/", dirname + "/")
    return float(m.group(1)) if m else ""


def usd_of(run_dir, done_usd):
    if done_usd is not None:
        return done_usd
    u = load_json(os.path.join(run_dir, "usage.json"))
    if "totals" in u and "usd" in u["totals"]:
        return u["totals"]["usd"]
    return u.get("usd", "")


def model_of(run_dir, run_id):
    for name in ("codex_run.json", "usage.json", "stats.json"):
        m = load_json(os.path.join(run_dir, name)).get("model")
        if m:
            return m
    return re.sub(r"-\d{8}T.*$", "", run_id)


def done_fields(log):
    found = RE_DONE.findall(log)
    if not found:
        return None, None, None
    reason, usd, resumes = found[-1]
    return reason, float(usd), int(resumes)


def build_row(run_dir, run_id, tiers):
    log = read_text(os.path.join(run_dir, "agent.full.log"))
    rep = load_json(os.path.join(run_dir, "report.json"))
    arxiv = os.path.basename(os.path.dirname(os.path.dirname(run_dir)))
    budget = budget_of(run_dir, os.path.dirname(run_dir))
    oks, costs = gpu_calls(log)
    used = sum(costs)
    exit_reason, done_usd, resumes = done_fields(log)
    if exit_reason is None:
        exit_reason = load_json(os.path.join(run_dir, "stats.json")).get("exit_reason", "")
    blockers = " ".join(str(rep.get("blockers", "")).split())[:120]
    arm = "codex" if run_id.startswith("codex-") else "miniswe"
    return {
        "arm": arm,
        "model": model_of(run_dir, run_id),
        "arxiv_id": arxiv,
        "tier": tiers.get(arxiv, ""),
        "budget_h100h": budget,
        "gpu_h100h_used": round(used, 6),
        "pct_budget_used": round(100.0 * used / budget, 2) if budget else "",
        "n_gpu_calls": len(oks),
        "n_gpu_ok": sum(oks),
        "wall_minutes": wall_minutes(log),
        "usd": usd_of(run_dir, done_usd),
        "exit_reason": exit_reason,
        "resumes": "" if resumes is None else resumes,
        "agent_assessment": rep.get("agent_assessment", ""),
        "blockers_first_120_chars": blockers,
        "_dir": run_dir,
        "_costs": costs,
    }


def find_runs(runs_root):
    out = []
    for dirpath, dirnames, filenames in os.walk(runs_root):
        depth = dirpath[len(runs_root):].count(os.sep)
        if depth > 3:
            dirnames[:] = []
            continue
        run_id = os.path.basename(dirpath)
        if depth == 3 and run_id.startswith(RUN_PREFIXES):
            out.append((dirpath, run_id))
    return out


def check_thin(sweeps_root):
    """Thin-harness API runs. No parser is written for them yet, so any finished one stops the script."""
    found = []
    if not os.path.isdir(sweeps_root):
        return found
    for sweep in os.listdir(sweeps_root):
        if not sweep.endswith("-thin"):
            continue
        for run in os.listdir(os.path.join(sweeps_root, sweep)):
            d = os.path.join(sweeps_root, sweep, run)
            if os.path.exists(os.path.join(d, "report.json")) and not os.path.exists(os.path.join(d, "VOID")):
                if not run.startswith("smoke-"):
                    found.append(d)
    return found


def summarize(rows):
    lines = ["# Frontier run budget use", "",
             "Source: run_usage.csv, built by scripts/rebuttal/run_usage_table.py from the run dirs.",
             "pct_budget_used = gpu_h100h_used / budget_h100h x 100, where gpu_h100h_used is the sum of",
             "cost_h100h over every run_gpu line in agent.full.log.", "",
             "| model | runs | median % of GPU budget used | runs under 10% | exit reasons |",
             "|---|---|---|---|---|"]
    by_model = {}
    for r in rows:
        by_model.setdefault(r["model"], []).append(r)
    for model in sorted(by_model):
        rs = by_model[model]
        pcts = [float(r["pct_budget_used"]) for r in rs]
        under = sum(1 for p in pcts if p < 10.0)
        reasons = {}
        for r in rs:
            reasons[r["exit_reason"]] = reasons.get(r["exit_reason"], 0) + 1
        rtxt = ", ".join("%s %d" % (k, v) for k, v in sorted(reasons.items()))
        lines.append("| %s | %d | %.2f | %d of %d | %s |" % (
            model, len(rs), statistics.median(pcts), under, len(rs), rtxt))
    ex = next(r for r in rows if r["n_gpu_calls"] and r["budget_h100h"])
    costs = ex["_costs"]
    lines += ["", "## Worked example", "",
              "Run %s, %s, budget %s H100-h. Its %d run_gpu costs sum to %s = %g H100-h:" % (
                  ex["arxiv_id"], ex["model"], ex["budget_h100h"], len(costs),
                  " + ".join("%g" % c for c in costs), ex["gpu_h100h_used"]),
              "",
              "%g / %g x 100 = %.2f%% of budget." % (ex["gpu_h100h_used"], float(ex["budget_h100h"]),
                                                    float(ex["pct_budget_used"]))]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", default=RUNS_ROOT)
    ap.add_argument("--sweeps-root", default=SWEEPS_ROOT)
    ap.add_argument("--subset", default=SUBSET)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    if check_thin(args.sweeps_root):
        sys.exit("thin-harness run dirs with report.json found; add a parser before running")

    tiers = tier_map(args.subset)
    rows = []
    for run_dir, run_id in find_runs(args.runs_root):
        if os.path.exists(os.path.join(run_dir, "VOID")) or not os.path.exists(os.path.join(run_dir, "report.json")):
            continue
        arxiv = os.path.basename(os.path.dirname(os.path.dirname(run_dir)))
        if run_id.startswith("smoke-") or arxiv in EXCLUDE_PAPERS:
            continue
        rows.append(build_row(run_dir, run_id, tiers))
    rows.sort(key=lambda r: (r["arm"], r["model"], r["arxiv_id"], r["budget_h100h"]))

    os.makedirs(args.out_dir, exist_ok=True)
    with io.open(os.path.join(args.out_dir, "run_usage.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with io.open(os.path.join(args.out_dir, "run_usage_summary.md"), "w", encoding="utf-8") as f:
        f.write(summarize(rows))
    print("rows", len(rows))


if __name__ == "__main__":
    main()
