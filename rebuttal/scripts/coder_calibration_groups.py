#!/usr/bin/env python3
"""Open-agent share of two mode groups as the blind coder labels them, plus frontier counts.

Reads rebuttal/results/frontier/coder_calibration.csv (paper_mode = paper label, primary = blind
coder label, one row per coded open-agent run) and rebuttal/results/frontier/failure_modes.csv
(primary = blind coder label, one row per failing frontier run). Stdlib only.

    nice -n 19 python3 rebuttal/scripts/coder_calibration_groups.py
"""
import csv, math, random, sys
from collections import Counter
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "results" / "frontier"
SIZES = {"near-miss-partial": 76, "reimplement-without-validating": 63, "environment-fights": 24,
         "artifact-provenance-mismatch": 38, "scope-substitution": 46, "stale-artifact-reliance": 9,
         "procrastination/wall-kill": 13, "killed-before-the-number": 31}
TOTAL = 300
SEED, B = 20261109, 5000
A = {"reimplement-without-validating", "artifact-provenance-mismatch", "stale-artifact-reliance"}
BG = {"procrastination/wall-kill", "killed-before-the-number"}
NL = {"procrastination/wall-kill"}
RELABEL = {"6cef06": ("procrastination/wall-kill", "killed-before-the-number")}


def wilson(k, n, z=1.959964):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def reweight(strata, inset):
    """strata: {paper slug: [coder labels]}. Returns sum(size x k/n) / TOTAL."""
    return sum(SIZES[s] * sum(x in inset for x in strata[s]) / len(strata[s]) for s in SIZES) / TOTAL


def bootstrap(strata, inset):
    rng = random.Random(SEED)
    flags = {s: [x in inset for x in strata[s]] for s in SIZES}
    vals = []
    for _ in range(B):
        t = 0.0
        for s in SIZES:
            f = flags[s]
            n = len(f)
            t += SIZES[s] * sum(f[rng.randrange(n)] for _ in range(n)) / n
        vals.append(t / TOTAL)
    vals.sort()
    return vals[int(0.025 * B)], vals[int(0.975 * B) - 1]


def pct(x):
    return f"{100 * x:.1f}%"


def main():
    rows = [r for r in csv.DictReader((D / "coder_calibration.csv").open()) if r["primary"]]
    strata = {s: [r["primary"] for r in rows if r["paper_mode"] == s] for s in SIZES}
    n_scored = sum(len(v) for v in strata.values())
    assert n_scored == 50, n_scored

    # Sanity: Never launched alone must reproduce the 13.8% in coder_calibration.md.
    nl_est = reweight(strata, NL)
    assert abs(100 * nl_est - 13.8) <= 0.2, nl_est

    fr = list(csv.DictReader((D / "failure_modes.csv").open()))
    labels = []
    for r in fr:
        lab = r["primary"]
        key = r["run_id"][-6:]
        if key in RELABEL and lab == RELABEL[key][0]:
            lab = RELABEL[key][1]  # hand re-read, see results/frontier/never_launched_check.md
        labels.append(lab)
    N = len(fr)
    cnt = Counter(labels)
    other = sum(c for lab, c in cnt.items() if lab not in A and lab not in BG)
    nA, nB = sum(cnt[l] for l in A), sum(cnt[l] for l in BG)
    assert nA + nB + other == N == 27, (nA, nB, other, N)

    out = []
    w = out.append
    w("# Open-agent share of two mode groups, blind-coder reweighting")
    w("")
    w("Each group is scored as the share of the 300 labelled failing open-agent cells, using the paper's "
      "eight failing-mode sizes as strata. Within each stratum the share is the fraction of the coded sample rows "
      "that the blind coder labels in the group, and the estimate is sum(size x fraction) / 300, with a stratified "
      "bootstrap (5,000 resamples, seed 20261109). Frontier counts are the failing frontier runs in failure_modes.csv "
      "under the blind coder, with one hand relabel applied and a Wilson 95% interval.")
    w("")
    w("| Group | Open agents, paper labels (count/300, %, Wilson 95%) | Open agents, blind coder (reweighted %, bootstrap 95%) | Frontier runs, blind coder (count/N, %, Wilson 95%) |")
    w("|---|---|---|---|")
    for name, grp, nf in (("A. Number without a valid measurement", A, nA),
                          ("B. Ended without a number", BG, nB)):
        paper_k = {"A": 63 + 38 + 9, "B": 13 + 31}[name[0]]  # paper-label counts from the strata sizes
        pl, ph = wilson(paper_k, TOTAL)
        est = reweight(strata, grp)
        bl, bh = bootstrap(strata, grp)
        fl, fh = wilson(nf, N)
        w(f"| {name} | {paper_k}/300, {pct(paper_k / TOTAL)}, {pct(pl)} to {pct(ph)} | "
          f"{pct(est)}, {pct(bl)} to {pct(bh)} | {nf}/{N}, {pct(nf / N)}, {pct(fl)} to {pct(fh)} |")
    w("")
    terms = []
    for s in SIZES:
        k = sum(x in A for x in strata[s])
        terms.append(f"{SIZES[s]} x {k}/{len(strata[s])} ({s})")
    total_a = reweight(strata, A)
    w("Worked example, Group A: " + " + ".join(terms) + f" = {sum(SIZES[s] * sum(x in A for x in strata[s]) / len(strata[s]) for s in SIZES):.2f}, "
      f"and that divided by 300 is {pct(total_a)}.")
    w("")
    w(f"Sanity check: the same code on Never launched alone gives {pct(nl_est)}, matching the 13.8% in coder_calibration.md.")
    w("")
    w(f"Frontier check: Group A {nA} + Group B {nB} + other modes {other} = {N} failing rows in failure_modes.csv. "
      f"The 6cef06 run is counted as killed-before-the-number. Sample: {n_scored} coded open-agent runs.")
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
