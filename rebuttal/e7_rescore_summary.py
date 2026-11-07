#!/usr/bin/env python3
"""E7 rescore: join the per-cell regrades with the paper's cell results and write
rebuttal/results/e7/rescore_corrected.csv and the numbers for rescore_summary.md.

Inputs: rebuttal/results/e7/rescore_cells.json (38 cells with a run, paper score and verdict),
        grades.jsonl copied from DeltaAI (/work/nvme/bfvr/msalunkhe/rebuttal/e7/regrade/grades.jsonl),
        rebuttal/results/e6/summary.json (per agent and tier reproduced counts, 400 cells).
Usage: python3 rebuttal/e7_rescore_summary.py GRADES_JSONL
"""
import csv, json, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "rebuttal/results/e7"
cells = json.loads((OUT / "rescore_cells.json").read_text())
grades = {}
for line in Path(sys.argv[1]).read_text().splitlines():
    if line.strip():
        g = json.loads(line)
        grades[(g["cell"], g["claim"])] = g
e6 = json.loads((REPO / "rebuttal/results/e6/summary.json").read_text())

rows = []
for c in cells:
    o, k = grades.get((c["cell"], "original")), grades.get((c["cell"], "corrected"))
    rows.append({
        "paper": c["paper"], "agent": c["agent"], "tier": c["tier"], "cell": c["cell"],
        "old_score": c["old_score"], "old_verdict": c["old_verdict"],
        "regrade_original_score": o and o["score"], "regrade_original_verdict": o and o["verdict"],
        "regrade_corrected_score": k and k["score"], "regrade_corrected_verdict": k and k["verdict"],
        "old_reproduced": c["old_verdict"] == "reproduced",
        "regrade_original_reproduced": o and o["verdict"] == "reproduced",
        "regrade_corrected_reproduced": k and k["verdict"] == "reproduced",
    })
fields = list(rows[0])
with (OUT / "rescore_corrected.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

done = [r for r in rows if r["regrade_original_verdict"] and r["regrade_corrected_verdict"]]
print(f"cells {len(rows)}, both regrades present {len(done)}")
S = lambda key: sum(1 for r in done if r[key])
print("reproduced: old", S("old_reproduced"), "regrade-orig", S("regrade_original_reproduced"),
      "regrade-corrected", S("regrade_corrected_reproduced"))
flip = lambda a, b: [r for r in done if r[a] != r[b]]
print("old->regrade-orig changes:", [(r["cell"], r["old_verdict"], r["regrade_original_verdict"]) for r in flip("old_reproduced", "regrade_original_reproduced")])
print("regrade-orig->corrected changes:", [(r["cell"], r["regrade_original_verdict"], r["regrade_corrected_verdict"]) for r in flip("regrade_original_reproduced", "regrade_corrected_reproduced")])
print("old->corrected changes:", [(r["cell"], r["old_verdict"], r["regrade_corrected_verdict"]) for r in flip("old_reproduced", "regrade_corrected_reproduced")])

tiers, agents = ["run", "retrain", "reimplement"], ["dsv4", "qwen3", "minimax", "muse"]
den = e6["tier_sizes"]
base = {(a, t): e6["cells"][f"{a}/{t}"]["S0_index"] for a in agents for t in tiers}
def counts(flag):
    cnt = dict(base)
    for r in done:
        key = (r["agent"], r["tier"])
        cnt[key] += int(bool(r[flag])) - int(r["old_reproduced"])
    return cnt
for name, flag in [("paper", "old_reproduced"), ("regrade_original", "regrade_original_reproduced"),
                   ("regrade_corrected", "regrade_corrected_reproduced")]:
    cnt = counts(flag)
    print(name)
    for t in tiers:
        top = max(cnt[(a, t)] for a in agents)
        print(f"  {t}: " + ", ".join(f"{a} {cnt[(a, t)]}" for a in agents) + f" | best {top}/{den[t]} by {[a for a in agents if cnt[(a, t)] == top]}")
