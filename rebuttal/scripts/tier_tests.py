#!/usr/bin/env python3
"""Reproduced counts per tier after the rebuttal corrections, with two-proportion z tests between tiers.

    python3 rebuttal/scripts/tier_tests.py > rebuttal/results/tiers/tier_tests.md
"""
import collections
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNS = json.load(open(REPO / "tools/anon_viewer/public/data/index.json"))["runs"]
N = {"run": 34, "retrain": 33, "reimplement": 33}
AGENTS = ["dsv4", "muse", "qwen3", "minimax"]
# Corrections of record (replies.md Sources, General): one new Muse Spark grade, two checkpoint runs,
# two runs on the corrected target of 2505.23747.
ADD = [("muse", "run", "2503.23035")]
DROP = ["muse-retrain-2508.21046", "minimax-reimplement-2505.12677", "dsv4-run-2505.23747", "minimax-run-2505.23747"]


def wilson(k, n, z=1.959964):
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return f"{k}/{n} = {100 * p:.0f}% [{100 * (c - h):.0f}%, {100 * (c + h):.0f}%]"


def z2(k1, n1, k2, n2):
    p = (k1 + k2) / (n1 + n2)
    return (k1 / n1 - k2 / n2) / math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))


rep = {(r["model"], r["tier"], r["arxiv_id"]) for r in RUNS if r["audit"].get("reproduced") and r["id"] not in DROP}
rep |= set(ADD)
cell = collections.Counter((m, t) for m, t, _ in rep)
union = {t: len({p for m, tt, p in rep if tt == t}) for t in N}
print("# Tier comparisons after the rebuttal corrections\n")
print(f"Source: tools/anon_viewer/public/data/index.json (372 graded runs), plus {ADD}, minus {DROP}. "
      f"Reproduced cells: {len(rep)} of 400. z is the two-proportion z statistic with a pooled variance.\n")
print("| row | Run | Retrain | Reimplement | z Run vs Reimplement | z Retrain vs Reimplement | z Run vs Retrain |")
print("|---|---|---|---|---|---|---|")


def line(name, k, n):
    print(f"| {name} | " + " | ".join(wilson(k[t], n[t]) for t in N) +
          f" | {z2(k['run'], n['run'], k['reimplement'], n['reimplement']):.2f}"
          f" | {z2(k['retrain'], n['retrain'], k['reimplement'], n['reimplement']):.2f}"
          f" | {z2(k['run'], n['run'], k['retrain'], n['retrain']):.2f} |")


for a in AGENTS:
    line(a, {t: cell[a, t] for t in N}, N)
line("papers reproduced by at least one agent", union, N)
line("all four agents pooled (cells; not independent within a paper)",
     {t: sum(cell[a, t] for a in AGENTS) for t in N}, {t: 4 * N[t] for t in N})


# Mean audit score per agent and tier on the original targets, empty cells at 0, with the two new Muse Spark grades.
T975 = {33: 2.0345, 32: 2.0369, 99: 1.9842, 135: 1.9777, 131: 1.9782, 399: 1.9659}  # t quantiles for df = n - 1
# two Muse Spark 1.2 audits (e8/regrade_muse.json) and the one nonzero D-cell regrade (e8/regrade_dcells.json)
NEW_SCORES = {("muse", "run", "2503.23035"): 8, ("muse", "reimplement", "2510.08177"): 6, ("qwen3", "reimplement", "2511.19808"): 2}


def mean_ci(xs):
    n = len(xs)
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    h = T975[n - 1] * sd / math.sqrt(n)
    return f"{m:.2f} [{m - h:.2f}, {m + h:.2f}]"


scores = collections.defaultdict(list)
for r in RUNS:
    scores[r["model"], r["tier"]].append(r["audit"].get("score") or 0)
for (m, t, _), v in NEW_SCORES.items():
    scores[m, t].append(v)
print("\n## Mean audit score (0 to 10), 95% t-interval over the tier's papers\n")
print("| agent | Run | Retrain | Reimplement | all 100 papers |")
print("|---|---|---|---|---|")
for a in AGENTS:
    cells, allx = [], []
    for t in N:
        xs = scores[a, t] + [0] * (N[t] - len(scores[a, t]))
        assert len(xs) == N[t], (a, t, len(scores[a, t]))
        allx += xs
        cells.append(mean_ci(xs))
    print(f"| {a} | " + " | ".join(cells) + f" | {mean_ci(allx)} |")
cells, allx = [], []
for t in N:
    xs = []
    for a in AGENTS:
        xs += scores[a, t] + [0] * (N[t] - len(scores[a, t]))
    allx += xs
    cells.append(mean_ci(xs))
print("| all agents (cells) | " + " | ".join(cells) + f" | {mean_ci(allx)} |")
