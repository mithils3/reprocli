#!/usr/bin/env python3
"""Open-agent results on each frontier arm's own papers, from the databook CSV.

    python3 rebuttal/scripts/frontier_baselines.py > rebuttal/results/frontier/same_paper_baselines.md
"""
import collections
import csv
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = list(csv.DictReader(open(ROOT / "results/databook/frontier_cells.csv")))
OPEN = [("dsv4", "DeepSeek-V4-Flash"), ("muse", "Muse Spark 1.2"), ("qwen3", "Qwen3.6-27B"), ("minimax", "MiniMax-M2.7")]


def num(x):
    try:
        return float(x)
    except ValueError:
        return 0.0


def wilson(k, n, z=1.959964):
    if n == 0:
        return "-"
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return f"{k}/{n} [{max(0.0, 100 * (c - h)):.0f}%, {min(100.0, 100 * (c + h)):.0f}%]"


arms = collections.defaultdict(list)
for r in ROWS:
    arms[r["arm"]].append(r)

print("# Open agents on each frontier arm's own papers\n")
print(f"Source: rebuttal/results/databook/frontier_cells.csv ({len(ROWS)} graded rows). Reproduced means score 8 or more. "
      "Open-agent columns use the submitted score of that agent on the same papers, an empty cell scoring 0. "
      "Intervals are Wilson 95%.\n")
print("| arm | graded | reproduced | mean score | " + " | ".join(f"{n} reproduced | {n} mean" for _, n in OPEN) + " |")
print("|---|---|---|---|" + "---|---|" * len(OPEN))
for arm, rs in arms.items():
    n = len(rs)
    k = sum(r["reproduced"] == "True" for r in rs)
    cells = [arm, str(n), wilson(k, n), f"{sum(num(r['score']) for r in rs) / n:.2f}"]
    for col, _ in OPEN:
        cells += [f"{sum(num(r[col]) >= 8 for r in rs)}/{n}", f"{sum(num(r[col]) for r in rs) / n:.2f}"]
    print("| " + " | ".join(cells) + " |")

print("\n## Frontier runs by tier\n")
print("| arm | Run | Retrain | Reimplement |")
print("|---|---|---|---|")
tot = collections.Counter()
for arm, rs in arms.items():
    row = []
    for t in ("run", "retrain", "reimplement"):
        sub = [r for r in rs if r["orig_tier"] == t]
        k = sum(r["reproduced"] == "True" for r in sub)
        row.append(f"{k}/{len(sub)}")
        if "x86" not in arm and "nudge" not in arm:
            tot[t, "k"] += k
            tot[t, "n"] += len(sub)
    print(f"| {arm} | " + " | ".join(row) + " |")
print("| all arms on GH200 nodes, continue-prompt runs left out | " + " | ".join(wilson(tot[t, "k"], tot[t, "n"]) for t in ("run", "retrain", "reimplement")) + " |")

print("\n## gpt-6.1-sol, our loop against Codex CLI, papers graded in both\n")
t = {r["paper"]: r for r in arms.get("thin-gpt-6.1-sol", [])}
c = {r["paper"]: r for r in arms.get("codex-gpt-6.1-sol", [])}
both = sorted(set(t) & set(c))
print("| paper | tier | our loop | Codex CLI |")
print("|---|---|---|---|")
for p in both:
    print(f"| {p} | {t[p]['orig_tier']} | {t[p]['score']} | {c[p]['score']} |")
if both:
    same = sum((t[p]["reproduced"] == "True") == (c[p]["reproduced"] == "True") for p in both)
    lo = sum(t[p]["reproduced"] == "True" and c[p]["reproduced"] != "True" for p in both)
    co = sum(c[p]["reproduced"] == "True" and t[p]["reproduced"] != "True" for p in both)
    print(f"\nPapers in both: {len(both)}. Reproduced: our loop {sum(t[p]['reproduced'] == 'True' for p in both)}, "
          f"Codex CLI {sum(c[p]['reproduced'] == 'True' for p in both)}. Same verdict on {same}; "
          f"reproduced only in our loop {lo}, only in Codex CLI {co}. "
          f"Mean score: our loop {sum(num(t[p]['score']) for p in both) / len(both):.2f}, "
          f"Codex CLI {sum(num(c[p]['score']) for p in both) / len(both):.2f}.")

print("\n## Share of the GPU grant used\n")
# The continue-prompt runs repeat three papers of the Codex CLI arm, so pooled counts leave them out.
gh = [r for r in ROWS if "x86" not in r["arm"] and "nudge" not in r["arm"]]
pct = [100 * num(r["spent_h100"]) / num(r["budget_h100"]) for r in gh if num(r["spent_h100"]) > 0]
idx = json.load(open(ROOT.parent / "tools/anon_viewer/public/data/index.json"))["runs"]
papers = {r["paper"] for r in gh}
opn = [100 * r["spent_h100"] / r["budget_h100"] for r in idx if r["arxiv_id"] in papers and r["budget_h100"]]
print(f"Frontier runs on GH200 nodes with a recorded spend: {len(pct)} of {len(gh)}; median {statistics.median(pct):.1f}% of the grant, "
      f"{sum(p < 5 for p in pct)} of {len(pct)} under 5%. Open agents, submitted runs on the same {len(papers)} papers: "
      f"{len(opn)} runs, median {statistics.median(opn):.1f}% of the grant.")
rep = [100 * num(r["spent_h100"]) / num(r["budget_h100"]) for r in gh if r["reproduced"] == "True"]
fail = [100 * num(r["spent_h100"]) / num(r["budget_h100"]) for r in gh if r["reproduced"] != "True"]
print(f"Frontier runs that reproduce: median {statistics.median(rep):.1f}% ({len(rep)} runs); that do not: median {statistics.median(fail):.1f}% "
      f"and mean {statistics.mean(fail):.1f}% ({len(fail)} runs). By tier, median: "
      + ", ".join(f"{t} {statistics.median([100 * num(r['spent_h100']) / num(r['budget_h100']) for r in gh if r['orig_tier'] == t]):.1f}%" for t in ("run", "retrain", "reimplement")) + ".")

print("\n## Pooled over the frontier runs on GH200 nodes, continue-prompt runs left out\n")
k = sum(r["reproduced"] == "True" for r in gh)
print(f"Frontier: {wilson(k, len(gh))}. " + " ".join(f"{n}: {wilson(sum(num(r[c]) >= 8 for r in gh), len(gh))}." for c, n in OPEN[:2]))
print("By tier, open agents on the same runs: " + "; ".join(
    f"{t} " + ", ".join(f"{n} {sum(num(r[c]) >= 8 for r in gh if r['orig_tier'] == t)}/{sum(r['orig_tier'] == t for r in gh)}" for c, n in OPEN[:2])
    for t in ("run", "retrain", "reimplement")) + ".")
for name, keep in (("Papers that some open agent reproduced", lambda r: num(r["orig_best"]) >= 8), ("Papers that no open agent reproduced", lambda r: num(r["orig_best"]) < 8)):
    s = [r for r in gh if keep(r)]
    ps = {r["paper"] for r in s}
    hit = {r["paper"] for r in s if r["reproduced"] == "True"}
    print(f"{name}: {len(ps)} papers, {len(s)} frontier runs, reproduced {wilson(sum(r['reproduced'] == 'True' for r in s), len(s))} "
          f"({len(hit)} papers by at least one frontier run); " + ", ".join(f"{n} {sum(num(r[c]) >= 8 for r in s)}/{len(s)}" for c, n in OPEN[:2]) + ". "
          + "By arm: " + "; ".join(f"{a} {sum(r['reproduced'] == 'True' for r in s if r['arm'] == a)}/{sum(r['arm'] == a for r in s)}"
                                    f" (DeepSeek-V4-Flash {sum(num(r['dsv4']) >= 8 for r in s if r['arm'] == a)})" for a in dict.fromkeys(r["arm"] for r in s)) + ".")
allp = {r["paper"] for r in gh}
print(f"Papers reproduced by at least one frontier run: {len({r['paper'] for r in gh if r['reproduced'] == 'True'})} of {len(allp)}.")
nd = [r for r in ROWS if "nudge" in r["arm"]]
cx = {r["paper"]: r for r in arms.get("codex-gpt-6.1-sol", [])}
print("Continue-prompt runs against the unprompted Codex CLI run: " + "; ".join(
    f"{r['paper']} score {r['score']} with {num(r['spent_h100']):.2f} of {num(r['budget_h100']):.0f} H100-h (unprompted {cx[r['paper']]['score']} with {num(cx[r['paper']]['spent_h100']):.2f})" for r in nd if r["paper"] in cx) + ".")

print("\n## Paper 2506.08898 (Retrain, 32 H100-hour grant)\n")
fr = [r for r in gh if r["paper"] == "2506.08898"]
print("Frontier runs: " + "; ".join(f"{r['arm']} score {r['score']}, {num(r['spent_h100']):.2f} H100-h" for r in fr) + ".")
print("Open agents: " + "; ".join(f"{r['model']} score {r['audit'].get('score')}, {r['spent_h100']:.1f} H100-h" for r in idx if r["arxiv_id"] == "2506.08898") + ".")
