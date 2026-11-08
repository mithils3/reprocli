#!/usr/bin/env python3
"""Rebuttal data book: one Markdown page of every number the ICLR rebuttal replies use.

Run on DeltaAI from the ~/reprocli checkout (stdlib only, read only apart from --out-dir):
    OPENBLAS_NUM_THREADS=1 python3 -I scripts/rebuttal/build_databook.py --out-dir <dir>
Writes <dir>/databook.md and <dir>/frontier_cells.csv.
"""
import argparse
import collections
import csv
import datetime
import io
import json
import math
import os
import re
import subprocess

GRADES = "/work/nvme/bfvr/msalunkhe/rebuttal/grading/grades.jsonl"
E10_STATE = "/work/nvme/bfvr/msalunkhe/rebuttal/e10/state.json"
REPEAT_JOBS = [3540624, 3540625, 3540626, 3540627, 3540628, 3540629, 3540630, 3540631,
               3540632, 3540633, 3540786, 3540787]
CUTOFF = "2026-11-07"
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
RESULTS = os.path.join(REPO, "rebuttal", "results")
ORIGINALS = ["dsv4", "minimax", "muse", "qwen3"]
TIERS = ["run", "retrain", "reimplement"]
PLANNED = collections.OrderedDict([
    ("codex-gpt-6.1-sol", 24), ("codex-gpt-6-astra", 8), ("codex-gpt-6.1-sol-nudge", 8),
    ("thin-gpt-6.1-sol", 12), ("thin-muse-wonder-1.0", 12), ("miniswe", 6)])  # gpt-6.1-terra arms dropped 2026-11-08
TERMINAL = ("COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY", "NODE_FAIL",
            "PREEMPTED", "BOOT_FAIL", "DEADLINE")
RE_RUN_GPU = re.compile(r"run_gpu ok=(True|False) rc=\S+ cost_h100h=(\S+)")
RE_MINI_BLOCK = re.compile(r'^\{\n  "ok": (true|false),.*?^\}', re.M | re.S)
RE_MINI_COST = re.compile(r'"cost_h100_hours": ([0-9.]+)')
RE_RESCORE = re.compile(r"Overall reproduced cells fall from (\d+) to (\d+) of (\d+)")
RE_FLIP = re.compile(r"Correction effect.*?(\d+) of (\d+) cells change reproduced")
FRONT_COLS = ["arm", "model", "paper", "budget", "run_id", "score", "verdict", "reproduced",
              "graded_at", "orig_tier", "dsv4", "minimax", "muse", "qwen3", "orig_empty",
              "orig_best", "diff_vs_best", "agent_assessment", "exit_reason", "queue_wait_min",
              "budget_h100", "spent_h100", "run_dir", "run_dir_found"]


def read_text(path):
    try:
        with io.open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except (IOError, OSError):
        return ""


def load_json(path):
    try:
        with io.open(path, encoding="utf-8") as f:
            return json.load(f)
    except (IOError, OSError, ValueError):
        return {}


def must_json(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def must_match(rx, text, path):
    m = rx.search(text)
    if not m:
        raise SystemExit("pattern %s not found in %s" % (rx.pattern, path))
    return m.groups()


def to_float(x, default=""):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def wilson(k, n, z=1.959964):
    if not n:
        return 0.0, 0.0
    p = float(k) / n
    den = 1 + z * z / n
    mid = (p + z * z / (2.0 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4.0 * n * n)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


def ratio_ci(k, n):
    lo, hi = wilson(k, n)
    rate = 100.0 * k / n if n else 0.0
    return "%d/%d = %.1f%% [%.1f, %.1f]" % (k, n, rate, 100 * lo, 100 * hi)


def ci_pct(pair):
    return "[%.1f, %.1f]" % (100 * pair[0], 100 * pair[1])


def cell(x):
    s = "" if x is None else str(x)
    return s.replace("|", "/").replace("\n", " ")


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(cell(c) for c in r) + " |")
    return lines


def load_e6(path):
    """arxiv_id -> {"tier": tier, "scores": {model: index_score}}; a missing model cell is absent."""
    out = {}
    with io.open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = out.setdefault(r["arxiv_id"], {"tier": r["tier"], "scores": {}})
            d["scores"][r["model"]] = int(to_float(r["index_score"], 0))
    return out


def e6_reproduced_by_tier(path):
    counts = collections.Counter()
    with io.open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["index_verdict"] == "reproduced":
                counts[r["tier"]] += 1
    return counts


def gpu_costs(log):
    """Per-call H100-hours of run_gpu calls, read the same way as scripts/rebuttal/run_usage_table.py."""
    codex = RE_RUN_GPU.findall(log)
    if codex:
        return [to_float(c, 0.0) for _, c in codex]
    costs = []
    for m in RE_MINI_BLOCK.finditer(log):
        if '"tool": "run_gpu"' in m.group(0):
            c = RE_MINI_COST.search(m.group(0))
            costs.append(float(c.group(1)) if c else 0.0)
    return costs


def frontier_row(g, e6):
    paper = g.get("paper", "")
    orig = e6.get(paper, {"tier": "", "scores": {}})
    scores = [int(orig["scores"].get(m, 0)) for m in ORIGINALS]
    empty = [m for m in ORIGINALS if m not in orig["scores"]]
    run_dir = g.get("run_dir", "")
    found = os.path.isdir(run_dir)
    run_id = g.get("run_id", "")
    rep = load_json(os.path.join(run_dir, "report.json")) if found else {}
    budget = to_float(str(g.get("budget", "")).rstrip("h"))
    if run_id.startswith("core-a-"):
        st = load_json(os.path.join(run_dir, "stats.json")) if found else {}
        spent = to_float(st.get("spent_h100"))
        budget = to_float(st.get("budget_h100"), budget)
        queue = ""
    else:
        cr = load_json(os.path.join(run_dir, "codex_run.json")) if found else {}
        queue = cr.get("queue_wait_minutes", "")
        spent = round(sum(gpu_costs(read_text(os.path.join(run_dir, "agent.full.log")))), 4) if found else ""
    score = int(g.get("score", 0))
    best = max(scores)
    return {
        "arm": g.get("arm", ""), "model": g.get("model", ""), "paper": paper,
        "budget": g.get("budget", ""), "run_id": run_id, "score": score,
        "verdict": g.get("verdict", ""), "reproduced": bool(g.get("reproduced")),
        "graded_at": g.get("graded_at", ""), "orig_tier": orig["tier"],
        "dsv4": scores[0], "minimax": scores[1], "muse": scores[2], "qwen3": scores[3],
        "orig_empty": "/".join(empty), "orig_best": best, "diff_vs_best": score - best,
        "agent_assessment": rep.get("agent_assessment", ""), "exit_reason": rep.get("exit_reason", ""),
        "queue_wait_min": queue, "budget_h100": budget, "spent_h100": spent,
        "run_dir": run_dir, "run_dir_found": "yes" if found else "no",
    }


def frontier_rows(e6):
    rows = []
    for line in read_text(GRADES).splitlines():
        if not line.strip():
            continue
        g = json.loads(line)
        if str(g.get("graded_at", "")) >= CUTOFF:
            rows.append(frontier_row(g, e6))
    return rows


def arm_table(rows):
    arms = list(PLANNED) + sorted(set(r["arm"] for r in rows) - set(PLANNED))
    out = []
    for a in arms:
        rs = [r for r in rows if r["arm"] == a]
        n = len(rs)
        k = sum(1 for r in rs if r["reproduced"])
        lo, hi = wilson(k, n)
        rate = "%d/%d [%.1f, %.1f]" % (k, n, 100 * lo, 100 * hi) if n else "- (n=0)"
        mean = "%.2f" % (sum(r["score"] for r in rs) / float(n)) if n else "-"
        paired = "%.2f (n=%d)" % (sum(r["diff_vs_best"] for r in rs) / float(n), n) if n else "- (n=0)"
        cnr = sum(1 for r in rs if r["agent_assessment"] == "could_not_run")
        out.append([a, PLANNED.get(a, "not planned"), "%d" % n, rate, mean, paired, cnr])
    return out


def frontier_md(rows):
    lines = ["## 1. Frontier arms (replies: General, YGTR W1)", "",
             "Rate: reproduced / graded [Wilson 95%]. Paired diff: arm score minus the best original "
             "agent score on the same paper, mean (n); a missing original cell scores 0. "
             "spent_h100: thin runs from stats.json, codex and miniswe runs summed from run_gpu lines "
             "in agent.full.log. queue_wait_min: codex_run.json, codex runs only.", ""]
    lines += md_table(["arm", "planned", "graded", "reproduced rate", "mean score",
                       "paired diff (n)", "could_not_run"], arm_table(rows))
    lines += ["", "Per-run rows (one per grades.jsonl row since %s):" % CUTOFF, ""]
    body = []
    for r in rows:
        body.append([r["arm"], r["model"], r["paper"], r["budget"], r["run_id"], r["score"],
                     r["verdict"], r["reproduced"], r["orig_tier"], r["dsv4"], r["minimax"],
                     r["muse"], r["qwen3"], r["orig_best"], r["diff_vs_best"],
                     r["agent_assessment"], r["exit_reason"], r["queue_wait_min"],
                     r["budget_h100"], r["spent_h100"]])
    lines += md_table(["arm", "model", "paper", "budget", "run_id", "score", "verdict", "reproduced",
                       "orig tier", "dsv4", "minimax", "muse", "qwen3", "orig best", "diff",
                       "agent_assessment", "exit_reason", "queue_wait_min", "budget_h100",
                       "spent_h100"], body)
    return lines


def static_md(e6_counts):
    rows = []

    def add(item, slot, number, source):
        rows.append([item, slot, number, source, "final"])

    d = "rebuttal/results/"
    s5 = must_json(os.path.join(RESULTS, "e5", "summary.json"))
    src = d + "e5/summary.json"
    add("E5 agent log entries checked", "rqBN", "{:,} of {:,}".format(s5["entries_checked"], s5["entries_total"]), src)
    add("E5 log entries unmatched", "rqBN", s5["entries_unmatched"], src)
    add("E5 log entries explained", "rqBN", s5["entries_explained"], src)
    add("E5 runs with a write into evidence/", "rqBN", "%d of %d" % (s5["runs_with_write_to_evidence_dir"], s5["runs_checked"]), src)
    add("E5 runs with late evidence/ mtime", "rqBN", "%d of %d" % (s5["runs_with_late_mtime"], s5["runs_checked"]), src)
    add("E5 run dirs not in index", "rqBN", "%d of %d" % (s5["run_dirs_not_in_index"], s5["run_dirs_found"]), src)

    s6 = must_json(os.path.join(RESULTS, "e6", "summary.json"))
    cells = must_json(os.path.join(RESULTS, "e8", "summary.json"))["reproduction_check"]["cells"]
    src = d + "e6/summary.json"
    add("E6 reproduced cells at 5% (index)", "tolerance", "%d of %d" % (s6["reproduced_overall_index"], cells), src)
    add("E6 reproduced point estimates", "tolerance", "%d of %d" % (s6["reproduced_point_estimate_index"], s6["reproduced_overall_index"]), src)
    for t in TIERS:
        b = s6["best_agent_per_tier"]["rel5/" + t]
        add("E6 best agent at 5%%, %s tier" % t, "tolerance", "%s %s" % ("/".join(b["agents_tied_at_top"]), ratio_ci(b["reproduced"], b["n"])), src)

    s7 = must_json(os.path.join(RESULTS, "e7", "summary.json"))["step3"]
    src = d + "e7/summary.json"
    add("E7 v3: all four step-3 questions yes", "rqBN", "%d of %d %s" % (s7["all_four_yes"], s7["n"], ci_pct(s7["all_four_wilson95"])), src)
    md = read_text(os.path.join(RESULTS, "e7", "rescore_summary.md"))
    src = d + "e7/rescore_summary.md"
    a, b, n = must_match(RE_RESCORE, md, src)
    add("E7 rescore: reproduced cells, paper targets to corrected targets", "rqBN", "%s to %s of %s" % (a, b, n), src)
    k, n = must_match(RE_FLIP, md, src)
    add("E7 rescore: cells that flip reproduced on correction", "rqBN", "%s of %s" % (k, n), src)

    s8 = must_json(os.path.join(RESULTS, "e8", "summary.json"))
    src = d + "e8/summary.json"
    rc = s8["reproduction_check"]
    add("E8 reproduced cells, reproduction check", "YGTR Q3", "%d of %d" % (rc["reproduced_total"], rc["cells"]), src)
    for t in TIERS:
        bt = s8["bound_best_per_tier_all_env_removed"][t]
        add("E8 best agent, environment runs removed, %s" % t, "YGTR Q3",
            "%s %d/%d = %.1f%% %s" % (bt["agent"], bt["reproduced"], bt["den"], 100 * bt["rate"], ci_pct(bt["wilson95"])), src)
    add("E8 empty cells", "YGTR Q3", s8["empty_cells"]["total"], src)
    add("E8 build-dependency runs", "YGTR Q3", s8["build_dependency_runs"]["total"], src)
    with io.open(os.path.join(RESULTS, "e8", "empty_cells_traced.csv"), newline="", encoding="utf-8") as f:
        classes = collections.Counter(r["cause_class"] for r in csv.DictReader(f))
    total = sum(classes.values())
    add("E8 empty-cell trace, classes A/B/C/D", "YGTR Q3",
        "A %d, B %d, C %d, D %d (of %d)" % (classes["A"], classes["B"], classes["C"], classes["D"], total),
        d + "e8/empty_cells_traced.csv")

    s9 = must_json(os.path.join(RESULTS, "e9", "summary.json"))["tiers"]
    src = d + "e9/summary.json"
    for t in TIERS:
        x = s9[t]
        add("E9 %s runs scanned of runs in index" % t, "YGTR Q2", "%d of %d" % (x["runs_scanned"], x["runs_in_index"]), src)
        add("E9 %s runs with a primary-source hit" % t, "YGTR Q2", "%d of %d scanned" % (x["runs_with_primary_hit"], x["runs_scanned"]), src)
        add("E9 %s reproduced runs with a hit" % t, "YGTR Q2",
            "%d of %d (reproduced rows, e6 table)" % (len(x["reproduced_runs_with_any_primary_hit"]), e6_counts[t]),
            src + " and " + d + "e6/table.csv")

    lines = ["## 2. Static results (final)", ""]
    return lines + md_table(["item", "reply slot", "number", "source file", "status"], rows)


def job_ids_in(obj, out):
    """Collect numeric values of keys whose name contains 'job' (value or list), at any depth."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if "job" in k.lower():
                vals = v if isinstance(v, list) else [v]
                out.extend(str(x) for x in vals if re.match(r"^\d+$", str(x)))
            else:
                job_ids_in(v, out)
    elif isinstance(obj, list):
        for v in obj:
            job_ids_in(v, out)
    return out


def sacct_map(job_ids, with_start):
    """JobID -> [JobName, State, Elapsed(, Start)] from sacct, one row per allocation (-X)."""
    if not job_ids:
        return {}
    fields = "JobID,JobName%24,State,Elapsed" + (",Start" if with_start else "")
    cmd = ["sacct", "-X", "-n", "-P", "-j", ",".join(str(j) for j in job_ids), "-o", fields]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if res.returncode != 0:
        raise SystemExit("sacct failed: " + res.stderr.strip())
    out = {}
    for line in res.stdout.splitlines():
        parts = line.split("|")
        if parts and parts[0] and parts[0] not in out:
            out[parts[0]] = parts[1:]
    return out


def e10_md():
    state = must_json(E10_STATE)
    ids = list(collections.OrderedDict.fromkeys(job_ids_in(state, [])))
    got = sacct_map(ids, False)
    rows = []
    for j in ids:
        v = got.get(j)
        name, st, el = (v[0], v[1], v[2]) if v else ("", "not found", "")
        rows.append([j, name, st, el, "final" if st == "COMPLETED" else "pending"])
    lines = ["## 3. E10 re-execution", "",
             "Source: %s job ids; sacct -X -n -P -j <ids> -o JobID,JobName%%24,State,Elapsed. "
             "Pending until COMPLETED." % E10_STATE, ""]
    return lines + md_table(["job", "name", "state", "elapsed", "status"], rows)


def repeat_md():
    got = sacct_map(REPEAT_JOBS, True)
    rows = []
    for j in REPEAT_JOBS:
        v = got.get(str(j))
        name, st, el, start = (v[0], v[1], v[2], v[3]) if v else ("", "not found", "", "")
        done = any(st.startswith(t) for t in TERMINAL)
        rows.append([j, name, st, el, start, "finished" if done else "pending"])
    lines = ["## 4. Repeat and rerun jobs (YGTR Q3, W2)", "",
             "Source: sacct -X -n -P -j <12 ids> -o JobID,JobName%24,State,Elapsed,Start. "
             "Not graded here.", ""]
    return lines + md_table(["job", "name", "state", "elapsed", "start", "status"], rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    e6_path = os.path.join(RESULTS, "e6", "table.csv")
    e6 = load_e6(e6_path)
    rows = frontier_rows(e6)

    with io.open(os.path.join(args.out_dir, "frontier_cells.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FRONT_COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = ["# Rebuttal data book", "",
             "Generated at %s UTC by scripts/rebuttal/build_databook.py. Frontier rows: %d "
             "(grades.jsonl rows with graded_at >= %s). Intervals: Wilson score 95%%." % (stamp, len(rows), CUTOFF),
             ""]
    lines += frontier_md(rows) + [""]
    lines += static_md(e6_reproduced_by_tier(e6_path)) + [""]
    lines += e10_md() + [""]
    lines += repeat_md() + [""]
    with io.open(os.path.join(args.out_dir, "databook.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("frontier_rows=%d" % len(rows))


if __name__ == "__main__":
    main()
