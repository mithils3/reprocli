"""E4 statistics from the 0-10 human-by-auditor matrix. usage: e4_stats.py matrix_0_10.csv index.json summary.json"""
import csv, json, math, sys, collections
M = [[int(x) for x in r[1:]] for r in list(csv.reader(open(sys.argv[1])))[1:]]
n = sum(map(sum, M)); rows = [sum(r) for r in M]; cols = [sum(M[i][j] for i in range(11)) for j in range(11)]
idx = json.load(open(sys.argv[2]))["runs"]
rec = collections.Counter(r["audit"]["score"] for r in idx)
assert cols == [rec[s] for s in range(11)], (cols, rec)
def wil(k, m, z=1.96):
    p = k / m; d = 1 + z*z/m; c = (p + z*z/(2*m)) / d; h = z*math.sqrt(p*(1-p)/m + z*z/(4*m*m)) / d
    return [round(100*(c-h), 1), round(100*(c+h), 1)]
V = lambda s: "reproduced" if s >= 8 else "partial" if s >= 6 else "not_reproduced" if s >= 2 else "unverifiable" if s == 1 else "disqualified"
order = ["reproduced", "partial", "not_reproduced", "unverifiable", "disqualified"]
five = {h: {a: 0 for a in order} for h in order}
for i in range(11):
    for j in range(11): five[V(i)][V(j)] += M[i][j]
tp = sum(M[i][j] for i in range(8, 11) for j in range(8, 11)); ph = sum(rows[8:]); pa = sum(cols[8:])
diag = sum(M[i][i] for i in range(11)); w1 = sum(M[i][j] for i in range(11) for j in range(11) if abs(i-j) <= 1)
mae = sum(abs(i-j)*M[i][j] for i in range(11) for j in range(11)) / n
signed = sum((j-i)*M[i][j] for i in range(11) for j in range(11)) / n
po = sum(M[i][j]*(1-((i-j)/10)**2) for i in range(11) for j in range(11)) / n
pe = sum(rows[i]*cols[j]*(1-((i-j)/10)**2) for i in range(11) for j in range(11)) / n / n
bd = [(i, j, M[i][j]) for i in range(11) for j in range(11) if M[i][j] and (i in (7, 8) or j in (7, 8))]
bd_n = sum(c for *_, c in bd); bd_agree = sum(c for i, j, c in bd if (i >= 8) == (j >= 8))
q0 = sum(M[0]); a0 = cols[0]; b0 = M[0][0]
out = {
 "source": "0-10 matrix supplied by Mithil 2026-11-08 (aggregate table; per-run human label file not on disk); auditor column totals checked equal to the 372 graded runs in tools/anon_viewer/public/data/index.json",
 "n_runs": n, "human_row_totals": rows, "auditor_col_totals": cols,
 "reproduced_ge8": {"tp": tp, "human_pos": ph, "auditor_pos": pa, "precision": round(tp/pa, 3), "precision_wilson95": wil(tp, pa), "recall": round(tp/ph, 3), "recall_wilson95": wil(tp, ph), "f1": round(2*tp/(ph+pa), 3),
   "auditor_yes_human_no": pa-tp, "human_yes_auditor_no": ph-tp},
 "exact_agreement": [diag, n, round(100*diag/n, 1), wil(diag, n)], "within_one": [w1, n, round(100*w1/n, 1)],
 "mae_0_10": round(mae, 2), "mean_auditor_minus_human": round(signed, 2), "quadratic_weighted_kappa": round((po-pe)/(1-pe), 3),
 "verdict_matrix_human_rows": five, "verdict_agreement": [sum(five[v][v] for v in order), n],
 "boundary_7_8": {"runs_either_at_7_or_8": bd_n, "agree_on_reproduced_side": bd_agree, "cells": bd},
 "disqualified_score0_as_high_severity": {"human_0": q0, "auditor_0": a0, "both": b0, "either": q0+a0-b0},
}
json.dump(out, open(sys.argv[3], "w"), indent=1); print(json.dumps({k: v for k, v in out.items() if k not in ("verdict_matrix_human_rows",)}, indent=0)[:2500]); print(json.dumps(five))
