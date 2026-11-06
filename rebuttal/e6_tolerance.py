#!/usr/bin/env python3
"""E6: how the reproduced counts move with the match tolerance (reviewer T29u Q2).

Inputs (read only):
  tools/anon_viewer/public/data/index.json     verdict per run (372 runs)
  tools/anon_viewer/public/data/runs/*.json.gz final audit record per run (measured_value,
                                               reference_value, tolerance, value_comparison)
  eval_100.jsonl (lockfile copy)               pinned match_target value/metric per claim
Writes rebuttal/results/e6/{table.csv,moved_runs.csv,summary.json}. README.md is hand-written.

Usage: python3 rebuttal/e6_tolerance.py [path/to/eval_100.jsonl]
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "tools/anon_viewer/public/data"
OUT = REPO / "rebuttal/results/e6"
LOCK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    os.environ.get("RECLAIM_LOCK", Path.home() / "PyCharmProjects/reclaim/data/splits/eval_100.jsonl"))

MODELS = ["run", "retrain", "reimplement"]  # tier order
AGENTS = ["dsv4", "qwen3", "minimax", "muse"]
DEFAULT_TOL = 0.05
# settings: name -> ("rel", fraction) or ("abs", points); claim_stated handled separately
SETTINGS = [("rel1", "rel", 0.01), ("rel2", "rel", 0.02), ("rel5", "rel", 0.05),
            ("rel10", "rel", 0.10), ("abs1", "abs", 1.0), ("abs2", "abs", 2.0),
            ("claim_stated", "claim", None)]
PCT_RE = re.compile(r"%|percent|accuracy|success rate|recall|precision|\bAUC\b|\bF1\b|pass@|win rate|violation rate", re.I)
MARGIN_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:±|\+/-)\s*(\d+(?:\.\d+)?)")

# Partial runs whose only shortfall the auditor names is the number (reviewed by hand from
# value_comparison and rationale; see README). Each must be partial, have a number, miss the
# default 5%, and carry no med/high cheat flag; the script asserts this.
NUMBER_ONLY = {
    "dsv4-reimplement-2511.19808": "clearly misses the bar; low flags only",
    "dsv4-retrain-2510.05874": "C1 is the only failed criterion; low flags only",
    "minimax-run-2504.20571": "real number clearly misses the bar; low flags only",
    "muse-retrain-2510.19314": "band 7 near miss just outside the bar; low flags only",
    "muse-retrain-2510.21363": "point estimate just outside the bar; low flags only",
    "muse-retrain-2511.02652": "clearly misses the bar; low flags only",
    "muse-run-2505.18809": "narrowly outside the bar (6.28%); low flags only",
    "qwen3-run-2505.24873": "clearly misses the bar on the pinned scope; no flags",
    "qwen3-run-2511.00090": "miss on the measured speedup; low flags only",
}
# Record fixes, each checked against the auditor's own value_comparison text.
MEASURED_OVERRIDE = {
    "qwen3-retrain-2506.07673": (37.2, "record has -37.2; value_comparison reads measured 37.20% (sign)"),
    "qwen3-run-2505.11483": (7.887, "record has 7887 bytes; pinned reference is 8.56 kB"),
}


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def load_final_records() -> dict[str, dict]:
    recs = {}
    for f in sorted((DATA / "runs").glob("*.json.gz")):
        d = json.loads(gzip.open(f, "rt", encoding="utf-8").read())
        fin = [e for e in d.get("audit_events", []) if e.get("kind") == "final"]
        recs[d["run"]["id"]] = json.loads(fin[-1]["content"])
    return recs


# Eval papers per tier (lockfile tier: Easy=Run, Medium=Retrain, Hard=Reimplement). Every agent is
# graded on every paper in a tier; an agent with no run for a paper counts as not reproduced.
LOCK_TIER = {"Easy": "run", "Medium": "retrain", "Hard": "reimplement"}


def tier_sizes() -> dict[str, int]:
    rows = [json.loads(line) for line in LOCK.read_text(encoding="utf-8").splitlines() if line.strip()]
    c = Counter(LOCK_TIER[r["tier"]] for r in rows)
    return {t: c[t] for t in MODELS}


def load_lock() -> dict[str, dict]:
    return {r["custom_id"]: r["match_target"] for r in
            (json.loads(line) for line in LOCK.read_text(encoding="utf-8").splitlines() if line.strip())}


def pct_scale(mt: dict, ref: float) -> tuple[bool, float]:
    """(is_percentage_metric, size of one point in the reference's units)."""
    text = f"{mt.get('value', '')} {mt.get('metric', '')}"
    if not PCT_RE.search(text):
        return (False, 1.0)
    if abs(ref) > 1.0:
        return (True, 1.0)  # percent scale, e.g. 89.47
    return (True, 0.01)  # fraction scale, e.g. 0.95 success rate or "~40%" recorded as 0.4


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index = json.loads((DATA / "index.json").read_text(encoding="utf-8"))["runs"]
    recs = load_final_records()
    lock = load_lock()
    assert len(index) == len(recs) == 372, (len(index), len(recs))

    rows, claim_bars = [], {}
    for run in index:
        rid, arx, agent, tier = run["id"], run["arxiv_id"], run["model"], run["tier"]
        verdict = run["audit"]["verdict"]
        rec = dict(recs[rid])
        mt = lock.get(arx, {})
        bar = rec.get("match_bar_kind")
        ref = rec.get("reference_value")
        meas = rec.get("measured_value")
        flags = rec.get("cheat_flags", [])
        if rid in MEASURED_OVERRIDE:
            meas = MEASURED_OVERRIDE[rid][0]
        is_pe = bar == "point_estimate" and meas is not None and ref not in (None, 0)
        pct, unit = pct_scale(mt, ref) if ref not in (None, 0) else (False, 1.0)

        rel = absd = points = None
        if is_pe:
            rel = abs(meas - ref) / abs(ref)
            absd = abs(meas - ref)
            points = absd / unit if pct else None

        # claim-stated margin: the lockfile value states "x ± m"; margin taken as tolerance
        mm = MARGIN_RE.search(str(mt.get("value", "")))
        stated = None
        if mm and ref not in (None, 0) and bar == "point_estimate":
            stated = float(mm.group(2)) / abs(ref)
            claim_bars[arx] = round(stated, 5)

        # recorded tolerance used by the auditor on this run (for the consistency check)
        tol_rec = rec.get("tolerance")
        if tol_rec is None:
            tol_rec = DEFAULT_TOL
        elif tol_rec > 1:  # recorded as a percentage number, e.g. 5.0
            tol_rec = tol_rec / 100.0

        row = {
            "run_id": rid, "model": agent, "tier": tier, "arxiv_id": arx,
            "bar_kind": bar or "", "pct_metric": int(pct), "reference": ref if ref is not None else "",
            "measured": meas if meas is not None else "",
            "rel_gap_pct": round(100 * rel, 3) if rel is not None else "",
            "abs_gap_points": round(points, 3) if points is not None else "",
            "recorded_tol": tol_rec if is_pe else "", "index_verdict": verdict,
            "index_score": run["audit"]["score"], "number_only_partial": int(rid in NUMBER_ONLY),
            "cheat_flags_med_high": sum(1 for f in flags if f.get("severity") in ("med", "high")),
            "_is_pe": is_pe, "_rel": rel, "_abs": absd, "_points": points, "_pct": pct,
            "_stated": stated, "_tol_rec": tol_rec, "_verdict": verdict, "_rid": rid,
            "_arx": arx, "_agent": agent, "_tier": tier,
        }
        rows.append(row)

    # sanity checks on the hand-picked list
    by_id = {r["run_id"]: r for r in rows}
    for rid in NUMBER_ONLY:
        r = by_id[rid]
        assert r["index_verdict"] == "partial" and r["_is_pe"], rid
        assert r["_rel"] > 0.05 and r["cheat_flags_med_high"] == 0, (rid, r["_rel"])

    # verdicts under each setting
    def match_at(r: dict, name: str) -> bool | None:
        if not r["_is_pe"]:
            return None
        if name == "claim_stated":
            tol = r["_stated"] if r["_stated"] is not None else DEFAULT_TOL
            return r["_rel"] <= tol
        kind, val = next((k, v) for n, k, v in SETTINGS if n == name)
        if kind == "abs":
            if r["_pct"]:
                return r["_points"] <= val
            return r["_rel"] <= DEFAULT_TOL
        return r["_rel"] <= val

    moves = []
    for r in rows:
        for name, _, _ in SETTINGS:
            base = r["index_verdict"]
            m = match_at(r, name)
            new = base
            if m is not None:
                if base == "reproduced" and not m:
                    new = "partial"
                elif base == "partial" and r["run_id"] in NUMBER_ONLY and m:
                    new = "reproduced"
            r.setdefault("v", {})[name] = new
            if new != base:
                moves.append({"run_id": r["run_id"], "model": r["model"], "tier": r["tier"],
                              "arxiv_id": r["arxiv_id"], "setting": name, "index_verdict": base,
                              "new_verdict": new, "rel_gap_pct": r["rel_gap_pct"],
                              "abs_gap_points": r["abs_gap_points"],
                              "reason": NUMBER_ONLY.get(r["run_id"], "reproduced run whose number misses this bar")})

    # consistency of the verdict with the number at each run's recorded tolerance
    cons = Counter()
    for r in rows:
        if r["_is_pe"]:
            cons[(r["index_verdict"], "match" if r["_rel"] <= r["_tol_rec"] else "miss")] += 1
    # per-cell counts
    TIER_N = tier_sizes()
    cells = {}
    for a in AGENTS:
        for t in MODELS:
            sub = [r for r in rows if r["model"] == a and r["tier"] == t]
            cell = {"n": TIER_N[t], "runs_present": len(sub)}
            cell["S0_index"] = sum(r["index_verdict"] == "reproduced" for r in sub)
            for name, _, _ in SETTINGS:
                cell[name] = sum(r["v"][name] == "reproduced" for r in sub)
            cells[f"{a}/{t}"] = cell

    def rate_block(name: str) -> dict:
        out = {}
        for k, c in cells.items():
            k_n, lo, hi = c["n"], *wilson(c[name], c["n"])
            out[k] = {"reproduced": c[name], "n": k_n, "rate": round(c[name] / k_n, 4),
                      "wilson95": [round(lo, 4), round(hi, 4)]}
        return out

    settings_out = {name: rate_block(name) for name in ["S0_index"] + [s[0] for s in SETTINGS]}
    tier_best = {}
    for name in ["rel1", "rel2", "rel5", "rel10"]:
        for t in MODELS:
            top = max(cells[f"{a}/{t}"][name] for a in AGENTS)
            tier_best[f"{name}/{t}"] = {"agents_tied_at_top": [a for a in AGENTS if cells[f"{a}/{t}"][name] == top],
                                        "reproduced": top, "n": TIER_N[t],
                                        "rate": round(top / TIER_N[t], 4)}
    # reproduced runs that are not point estimates (no number test, so they never move)
    non_pe = Counter(r["bar_kind"] for r in rows if r["index_verdict"] == "reproduced" and not r["_is_pe"])
    pe_rep = sum(1 for r in rows if r["index_verdict"] == "reproduced" and r["_is_pe"])
    best5 = {t: [a for a in AGENTS if cells[f"{a}/{t}"]["rel5"] == max(cells[f"{b}/{t}"]["rel5"] for b in AGENTS)]
             for t in MODELS}
    falls = {name: [m for m in moves if m["setting"] == name and m["new_verdict"] == "partial"] for name in ["rel1", "rel2", "rel10"]}
    fall_best = {name: [f"{m['run_id']} (best at 5%)" for m in v if m["model"] in best5[m["tier"]]]
                 for name, v in falls.items()}

    # claims: 100 pinned claims
    claims = Counter(mt.get("match_bar_kind") for mt in lock.values())
    stated_claims = {arx: claim_bars[arx] for arx in claim_bars if arx in lock}
    summary = {
        "inputs": {"index": "tools/anon_viewer/public/data/index.json", "runs": "tools/anon_viewer/public/data/runs/*.json.gz",
                   "lockfile": str(LOCK), "lockfile_has_tolerance_field": False},
        "claims": {"lockfile_kinds": dict(claims), "point_estimate_default_5pct": claims["point_estimate"] - len(stated_claims),
                   "point_estimate_stated_margin": stated_claims},
        "auditor_recorded_tolerance_non_default_runs": sum(1 for r in rows if r["_is_pe"] and r["_tol_rec"] != DEFAULT_TOL),
        "consistency_at_recorded_tolerance": {f"{k[0]}/{k[1]}": v for k, v in cons.items()},
        "measured_overrides": {k: {"value": v[0], "reason": v[1]} for k, v in MEASURED_OVERRIDE.items()},
        "number_only_partials": NUMBER_ONLY,
        "tier_sizes": TIER_N,
        "reproduced_overall_index": sum(c["S0_index"] for c in cells.values()),
        "reproduced_point_estimate_index": pe_rep,
        "reproduced_not_point_estimate_index": dict(non_pe),
        "falls_by_setting": {k: len(v) for k, v in falls.items()},
        "falls_at_best_agent_at_5pct": fall_best,
        "best_agent_at_5pct": best5,
        "cells": cells, "settings": settings_out, "best_agent_per_tier": tier_best,
        "moves_by_setting": dict(Counter(m["setting"] for m in moves)),
        "moves_count_total": len(moves),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")

    cols = ["run_id", "model", "tier", "arxiv_id", "bar_kind", "pct_metric", "reference", "measured",
            "rel_gap_pct", "abs_gap_points", "recorded_tol", "index_verdict", "index_score",
            "number_only_partial", "cheat_flags_med_high"] + [s[0] for s in SETTINGS]
    with (OUT / "table.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in sorted(rows, key=lambda r: (r["model"], r["tier"], r["run_id"])):
            w.writerow([r[c] for c in cols[:15]] + [r["v"][s[0]] for s in SETTINGS])
    with (OUT / "moved_runs.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(moves[0].keys()) if moves else ["run_id"])
        w.writeheader()
        for m in sorted(moves, key=lambda m: (m["setting"], m["run_id"])):
            w.writerow(m)
    print(json.dumps({"n_runs": len(rows), "moves": summary["moves_by_setting"],
                      "S0": settings_out["S0_index"], "rel5": settings_out["rel5"] and
                      sum(c["reproduced"] for c in settings_out["rel5"].values())}, indent=0)[:1500])


if __name__ == "__main__":
    main()
