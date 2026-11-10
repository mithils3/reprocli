#!/usr/bin/env python3
"""Raised-minus-unchanged gaps for the 15 blind-coded qualitative features.

usage: qual_blind_stats.py <coded_dir> <blind_key.json> <blind_dir>
Coders saw neither group nor scores. A quote counts as valid when it occurs in the thread file
after whitespace is collapsed. Intervals are Newcombe 95% for a difference of two proportions.
"""
import glob, json, re, sys
from math import sqrt

coded_dir, key_path, blind_dir = sys.argv[1:4]
key = json.load(open(key_path))
FEATS = ["own_shortfall", "evidence_limit", "cited_paper_specifics", "modest_size_word", "promise_for_result",
         "location_only", "sends_elsewhere", "asks_to_specify", "correction", "self_praise", "worked_case",
         "decline", "grants_main", "asks_for_score", "shared_limitation"]
# (label, feature, value counted, restrict to rows where the feature is not "na")
TESTS = [(f, f, "yes", False) for f in FEATS if f not in ("correction", "decline", "cited_paper_specifics")]
TESTS += [("cited_paper_specifics (of threads citing a paper as evidence)", "cited_paper_specifics", "yes", True),
          ("correction bare (all threads)", "correction", "bare", False),
          ("correction bare (of threads that correct the reviewer)", "correction", "bare", True),
          ("correction fixed (all threads)", "correction", "fixed", False),
          ("decline bare (all threads)", "decline", "bare", False),
          ("decline bare (of threads that decline a request)", "decline", "bare", True),
          ("decline with substitute (all threads)", "decline", "substitute", False)]

def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()

def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h

rows, bad, quotes, okq = [], 0, 0, 0
for f in sorted(glob.glob(coded_dir + "/*.jsonl")):
    for line in open(f):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            bad += 1; continue
        if r.get("id") not in key:
            bad += 1; continue
        text = norm(open(f"{blind_dir}/{r['id']}.txt", errors="replace").read())
        for ft in FEATS:
            cell = r.get(ft) or {}
            v = str(cell.get("v", "no")).lower()
            q = cell.get("q") or ""
            if v not in ("no", "na") and q:
                quotes += 1; okq += norm(q)[:120] in text
            r[ft] = v
        r["group"] = key[r["id"]]["group"]; rows.append(r)

seen = {r["id"] for r in rows}
nr = sum(r["group"] == "raised" for r in rows); nu = len(rows) - nr
print(f"threads coded {len(rows)} (unique {len(seen)}): raised {nr}, unchanged {nu}; unusable lines {bad}; "
      f"quotes found verbatim {okq} of {quotes}\n")
print("| feature | raised | unchanged | gap (points) | 95% interval |")
print("|---|---|---|---|---|")
out = []
for label, ft, val, restrict in TESTS:
    R = [r for r in rows if r["group"] == "raised" and (not restrict or r[ft] != "na")]
    U = [r for r in rows if r["group"] == "unchanged" and (not restrict or r[ft] != "na")]
    if not R or not U:
        continue
    kr = sum(r[ft] == val for r in R); ku = sum(r[ft] == val for r in U)
    pr, pu = kr / len(R), ku / len(U)
    lr, ur = wilson(kr, len(R)); lu, uu = wilson(ku, len(U))
    lo = (pr - pu) - sqrt((pr - lr) ** 2 + (uu - pu) ** 2); hi = (pr - pu) + sqrt((ur - pr) ** 2 + (pu - lu) ** 2)
    out.append((abs(pr - pu), f"| {label} | {kr}/{len(R)} = {100*pr:.0f}% | {ku}/{len(U)} = {100*pu:.0f}% | "
                f"{100*(pr-pu):+.0f} | {100*lo:+.0f} to {100*hi:+.0f}{' *' if lo > 0 or hi < 0 else ''} |"))
for _, line in sorted(out, reverse=True):
    print(line)
print("\n* interval excludes zero. With about 20 rows tested, one such row is expected by chance.")
