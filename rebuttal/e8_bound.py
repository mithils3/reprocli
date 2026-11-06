#!/usr/bin/env python3
"""E8: how much of the failure the GH200/aarch64 host could explain.

Inputs:
  ~/sweeps/paper-table-2026-09-05/resolved_modes.json   per-run labels (372 runs)
  paper_latex/tables/eval100.tex (lines 1-121, read only)  the 100 papers and tiers
  tools/anon_viewer/public/data/index.json              run metrics used to match DeltaAI dirs
  rebuttal/results/e8/stats_index.tsv                   DeltaAI stats.json rows (598), copied from
                                                        /work/nvme/bfvr/msalunkhe/rebuttal/e8_stats_index.tsv
Writes rebuttal/results/e8/{bound.csv, build_failures.csv, empty_cells.csv, summary.json}.
Usage: python3 rebuttal/e8_bound.py
"""
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESOLVED = Path.home() / "sweeps/paper-table-2026-09-05/resolved_modes.json"
EVAL = REPO / "paper_latex/tables/eval100.tex"
INDEX = REPO / "tools/anon_viewer/public/data/index.json"
OUT = REPO / "rebuttal/results/e8"
STATS = OUT / "stats_index.tsv"

MODELS = ["dsv4", "minimax", "muse", "qwen3"]
TIERS = {"Run": "run", "Retrain": "retrain", "Reimplement": "reimplement"}
DEN = {"run": 34, "retrain": 33, "reimplement": 33}  # per agent, from eval100 (34/33/33)
ENV_MODE = "environment-fights"  # the build and dependency label in resolved_modes.json
Z = 1.959964

# Transcript review of the 24 build-and-dependency runs (see README for the rules).
# class: A = aarch64-caused, O = other environment, E = agent error.
# kind: explicit = tool message or named artifact; stated = agent attributes it to aarch64.
ASSESS = {
    "dsv4-reimplement-2511.20906": ("A", "stated", "aarch64/Grace node. mujoco_py (free-mujoco-py) is known-absent x86-pinned; prebuilt mujoco binaries are x86"),
    "qwen3-run-2505.10978": ("A", "stated", "The textworld build fails on aarch64."),
    "qwen3-run-2505.24864": ("A", "explicit", "(e.g., manylinux_2_39_aarch64) and you require torch==2.5.1+cu124 ... aarch64 platform doesn't have cu124 wheels"),
    "qwen3-run-2506.20671": ("A", "explicit", "The spconv issue is that there's no aarch64 wheel."),
    "qwen3-retrain-2504.13146": ("A", "stated", "I need to install ... but flash-attn won't work on aarch64."),
    "qwen3-retrain-2506.20233": ("A", "stated", "The jaxlib installed from PyPI is CPU-only for aarch64."),
    "qwen3-retrain-2505.02391": ("A", "explicit", "(e.g., manylinux_2_39_aarch64) and you require tensordict==0.6.2"),
    "qwen3-reimplement-2505.24452": ("O", "none", "PyTorch 2.13.0 LRScheduler API incompatibility (torch API version, not arch)"),
    "qwen3-reimplement-2410.15392": ("A", "stated", "pytorch3d which is KNOWN-ABSENT on aarch64"),
    "minimax-run-2504.20571": ("A", "explicit", "only x86_64 manylinux wheels for the early versions (vllm)"),
    "minimax-run-2506.20671": ("A", "explicit", "Wheels are available for spconv ... manylinux_2_17_x86_64 only"),
    "minimax-run-2503.18430": ("O", "none", "ImportError mmcv _ext ... undefined symbol (torch ABI mismatch); borderline, agent mentions aarch64 CUDA wheel"),
    "minimax-run-2502.05795": ("E", "none", "TypeError: HfApi.list_models() got an unexpected keyword argument 'direction'"),
    "minimax-run-2505.14766": ("A", "stated", "torch==2.7.0 likely installed from default PyPI (CPU-only for aarch64)"),
    "minimax-run-2505.24873": ("A", "explicit", "The decord==0.6 has no aarch64 wheel (manylinux2010_x86_64 only)"),
    "minimax-run-2505.10978": ("A", "explicit", "The ni compiler binary is compiled for x86_64 but we're on aarch64 (GH200)"),
    "minimax-run-2505.14827": ("A", "explicit", "vllm-0.6.1.post1-cp38-abi3-manylinux1_x86_64.whl won't work on aarch64"),
    "minimax-retrain-2510.19314": ("O", "none", "ModuleNotFoundError fixed by installing tqdm in the agent venv; salloc partition error"),
    "minimax-retrain-2508.21046": ("E", "none", "assert not (cfg.load_in_8bit and cfg.load_in_4bit) in agent config"),
    "minimax-reimplement-2512.02339": ("E", "none", "Error: Repo id must be in the form 'repo_name' ... 'datasets/Threshold500/davis2017'"),
    "muse-run-2505.14827": ("A", "explicit", "ERROR: No matching distribution found for vllm==0.8.5 (sdist metadata build also failed)"),
    "muse-run-2506.20671": ("A", "explicit", "spconv-cu113 won't have wheel on aarch64; open3d (manylinux_2_39_aarch64 hint)"),
    "muse-retrain-2410.19933": ("O", "none", "dependency pin changes; aarch64 cited only as the numpy pin reason"),
    "muse-reimplement-2506.20024": ("O", "none", "ModuleNotFoundError: No module named 'torch' / 'requests' in the run venv"),
}


def wilson(k, n):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def eval_tiers():
    tiers = {}
    for i, line in enumerate(EVAL.read_text().splitlines(), 1):
        if i > 121:
            break
        m = re.match(r"\s*(\d{4}\.\d{4,5})\s*&\s*(Run|Retrain|Reimplement)\s*&", line)
        if m:
            tiers[m.group(1)] = TIERS[m.group(2)]
    assert len(tiers) == 100, len(tiers)
    return tiers


def stats_rows():
    rows = []
    for line in STATS.read_text().splitlines():
        if line.strip():
            rows.append(line.split("\t"))
    return rows


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def inum(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def match_dirs(runs, rows, index_runs):
    """Map each of the 372 runs to its stats row by (arxiv, spent, tokens, tool_calls)."""
    by_key = defaultdict(list)
    for r in rows:
        by_key[(r[1], fnum(r[4]), inum(r[5]), inum(r[6]))].append(r)
    dir_of, matched = {}, set()
    for x in index_runs:
        key = (x["arxiv_id"], round(x["spent_h100"], 4), x["tokens"]["total"], x["tool_calls"])
        hits = by_key.get(key, [])
        assert len(hits) == 1, (x["id"], len(hits))
        dir_of[x["id"]] = hits[0]
        matched.add(hits[0][0])
    return dir_of, matched


def prefix(path):
    rid = path.split("/")[-2]
    m = re.search(r"\d{4}\.\d{4,5}", rid)
    return rid[: m.start() - 1] if m else rid


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    runs = json.loads(RESOLVED.read_text())["runs"]
    index_runs = json.loads(INDEX.read_text())["runs"]
    rows = stats_rows()
    tiers = eval_tiers()
    dir_of, matched = match_dirs(runs, rows, index_runs)

    # Step 1: reproduction check against the paper's denominators.
    rep = Counter((r["model"], r["tier"]) for r in runs if r["audit_verdict"] == "reproduced")
    cnt = Counter((r["model"], r["tier"]) for r in runs)
    env = [r for r in runs if r["mode"] == ENV_MODE]
    env_k = Counter((r["model"], r["tier"]) for r in env)
    aarch_k = Counter((r["model"], r["tier"]) for r in env if ASSESS[r["id"]][0] == "A")
    total_rep = sum(rep.values())
    assert total_rep == 73 and len(runs) == 372 and len(env) == 24

    # Step 2: build-and-dependency runs, in the paper's denominator.
    bf_rows = []
    for r in sorted(env, key=lambda r: (r["model"], r["tier"], r["id"])):
        cls, kind, note = ASSESS[r["id"]]
        d = dir_of[r["id"]]
        bf_rows.append({
            "run_id": r["id"], "model": r["model"], "tier": r["tier"], "arxiv_id": r["id"].split("-")[-1],
            "audit_verdict": r["audit_verdict"], "audit_score": r["audit_score"],
            "class": cls, "evidence_kind": kind, "evidence": note, "run_dir": d[0].replace("/stats.json", ""),
        })

    # Step 4: bounds, with Wilson 95% intervals. Denominator = paper cells (34 or 33 per agent-tier).
    bound_rows = []
    for m in MODELS:
        for t in ["run", "retrain", "reimplement"]:
            D = DEN[t]
            r = rep[(m, t)]
            k_all = env_k[(m, t)]
            k_a = aarch_k[(m, t)]
            lo0, hi0 = wilson(r, D)
            lo1, hi1 = wilson(r, D - k_all)
            lo2, hi2 = wilson(r, D - k_a)
            bound_rows.append({
                "model": m, "tier": t, "paper_den": D, "reproduced": r,
                "paper_rate": round(r / D, 4), "paper_lo": round(lo0, 4), "paper_hi": round(hi0, 4),
                "env_runs": k_all, "aarch64_runs": k_a,
                "bound_all_den": D - k_all, "bound_all_rate": round(r / (D - k_all), 4),
                "bound_all_lo": round(lo1, 4), "bound_all_hi": round(hi1, 4),
                "bound_a_den": D - k_a, "bound_a_rate": round(r / (D - k_a), 4),
                "bound_a_lo": round(lo2, 4), "bound_a_hi": round(hi2, 4),
            })
    assert sum(b["paper_den"] for b in bound_rows) == 400

    # Step 5: the 28 empty cells.
    done = {(r["model"], r["id"].split("-")[-1]) for r in runs}
    prefix_agents = defaultdict(set)
    for r in runs:
        prefix_agents[prefix(dir_of[r["id"]][0])].add(r["model"])
    unmatched = [row for row in rows if row[0] not in matched]
    empty = []
    for m in MODELS:
        for p, t in tiers.items():
            if (m, p) in done:
                continue
            own = [u for u in unmatched if u[1] == p and m in prefix_agents.get(prefix(u[0]), set())]
            orphan = [u for u in unmatched if u[1] == p and prefix(u[0]) not in prefix_agents]
            anyd = [u for u in rows if u[1] == p]
            if p == "2510.20725" and not anyd:
                cat, detail = "prompt-rendering bug, never started (no run directory)", "no DeltaAI directory for this paper"
            elif any(u[2] == "natural" for u in own) and p in ("2503.23035", "2510.08177"):
                cat = "audit never returned (run finished)"
                detail = "; ".join(f"{u[2]} {u[3]} rounds, {u[5]} tokens" for u in own)
            elif any(u[2] == "natural" for u in own):
                cat = "run finished, no entry in set"
                detail = "; ".join(f"{u[2]} {u[3]} rounds, {u[5]} tokens" for u in own)
            elif any(u[2] == "context_budget" for u in own):
                cat = "context limit reached, no entry in set"
                detail = "; ".join(f"{u[2]} {u[3]} rounds, {u[5]} tokens" for u in own)
            elif own:
                cat = "launch error only, no entry in set"
                detail = "; ".join(f"{u[2]} {u[3]} rounds" for u in own)
            elif orphan:
                cat = "no own run directory; orphan launch errors on paper"
                detail = f"{len(orphan)} unattributed directories (agent unknown)"
            else:
                cat, detail = "no run directory on record", "no directory for this agent and paper"
            empty.append({"model": m, "arxiv_id": p, "tier": t, "category": cat, "detail": detail})
    assert len(empty) == 28, len(empty)
    outside = {(e["model"], e["arxiv_id"]) for e in empty if e["category"].startswith(("prompt", "audit never"))}
    assert len(outside) == 6

    def write(name, data):
        with open(OUT / name, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)

    write("bound.csv", bound_rows)
    write("build_failures.csv", bf_rows)
    write("empty_cells.csv", empty)

    best = {t: max((b for b in bound_rows if b["tier"] == t), key=lambda b: b["bound_all_rate"]) for t in DEN}
    summary = {
        "reproduction_check": {"reproduced_total": total_rep, "cells": len(runs) + len(empty), "runs": len(runs),
                               "per_agent_tier": {f"{m}-{t}": [rep[(m, t)], DEN[t]] for m in MODELS for t in DEN}},
        "build_dependency_runs": {"total": len(env), "by_agent": dict(Counter(r["model"] for r in env)),
                                  "by_tier": dict(Counter(r["tier"] for r in env)),
                                  "class_counts": dict(Counter(v[0] for k, v in ASSESS.items() if k in {r["id"] for r in env})),
                                  "explicit_aarch64_minimax_run": sum(1 for r in env if r["model"] == "minimax" and r["tier"] == "run" and ASSESS[r["id"]][:2] == ("A", "explicit"))},
        "bound_best_per_tier_all_env_removed": {t: {"agent": b["model"], "reproduced": b["reproduced"], "den": b["bound_all_den"], "rate": b["bound_all_rate"], "wilson95": [b["bound_all_lo"], b["bound_all_hi"]]} for t, b in best.items()},
        "empty_cells": {"total": len(empty), "by_category": dict(Counter(e["category"] for e in empty))},
        "outside_agent_cells": sorted(f"{m} {p}" for m, p in outside),
        "method": "Wilson 95% (z=1.959964). Numerator = paper reproduced count (env runs are never reproduced). Denominator = paper cell count minus removed runs; empty cells stay in the denominator unless the run is removed.",
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["reproduction_check"]["per_agent_tier"]))
    print(json.dumps(summary["build_dependency_runs"], indent=1))
    print(json.dumps(summary["empty_cells"], indent=1))


if __name__ == "__main__":
    main()
