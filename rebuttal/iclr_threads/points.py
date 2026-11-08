"""Point-level analysis: which answers go with raised threads, by concern type.

usage: points.py <out2_dir> <points_stats.md> <points.jsonl> <evidence_points.md>
Unit is the reviewer point; points cluster in threads, so every interval is a thread-cluster
bootstrap (2,000 resamples, seed 22528). "Raised share" = share of points that sit in a raised
thread. Baseline = raised share over all points. Threads with no author post are dropped.
"""
import collections, glob, json, random, statistics, sys
from pathlib import Path

out2, md, rows_out, ev_out = sys.argv[1:5]
threads = []
for f in sorted(glob.glob(f"{out2}/pts_*.json")) + sorted(glob.glob(f"{out2}/ctl_*.json")):
    threads += json.load(open(f))["threads"]
threads = [t for t in threads if any(p.get("author_move") != "not_addressed" for p in t.get("points", []))]
P = []
for ti, t in enumerate(threads):
    for p in t["points"]:
        P.append({**p, "tid": ti, "group": t["group"], "file": t["file"]})
with open(rows_out, "w") as fh:
    for p in P:
        fh.write(json.dumps(p) + "\n")

def truth(v):
    return v is True or (isinstance(v, str) and v.strip().lower() == "true")


for p in P:
    p["has_numbers"] = truth(p.get("has_numbers")); p["location_given"] = truth(p.get("location_given"))
rng = random.Random(22528)
by_t = collections.defaultdict(list)
for p in P:
    by_t[p["tid"]].append(p)
TIDS = list(by_t)


def share(pred, sel=lambda p: True):
    """raised share among selected points matching pred, with cluster-bootstrap 95% interval."""
    def stat(tids):
        k = n = 0
        for t in tids:
            for p in by_t[t]:
                if sel(p) and pred(p):
                    n += 1; k += p["group"] == "raised"
        return (k / n if n else float("nan")), n
    est, n = stat(TIDS)
    if n == 0:
        return 0, 0, 0, 0
    bs = sorted(x for x in (stat(rng.choices(TIDS, k=len(TIDS)))[0] for _ in range(2000)) if x == x)
    lo, hi = bs[int(0.025 * len(bs))], bs[int(0.975 * len(bs)) - 1]
    return n, round(100 * est), round(100 * lo), round(100 * hi)


nr = sum(t["group"] == "raised" for t in threads)
base = share(lambda p: True)
L = ["# Reviewer points: answer moves and raised threads", "",
     f"Threads with an author answer: {len(threads)} (raised {nr}, unchanged {len(threads) - nr}); points {len(P)}. "
     f"Raised share of all points: {base[1]}% [{base[2]}, {base[3]}]. Each cell: points n, raised share % [thread-cluster bootstrap 95%]. "
     "A move whose interval sits above the baseline goes with raised threads more than the average point does.", ""]

TYPES = sorted({p["type"] for p in P}, key=lambda x: -sum(q["type"] == x for q in P))
MOVES = ["new_experiment", "new_analysis_existing_data", "text_revision", "clarification_only", "concede_and_scope",
         "disagree_with_evidence", "disagree_without_evidence", "defer_future_work", "not_addressed"]
L += ["## Answer move, all points", "", "| move | n | raised share |", "|---|---|---|"]
for m in MOVES:
    n, e, lo, hi = share(lambda p, m=m: p["author_move"] == m)
    L.append(f"| {m} | {n} | {e}% [{lo}, {hi}] |")
L += ["", "## Answer features, all addressed points", "", "| feature | n | raised share |", "|---|---|---|"]
addr = lambda p: p["author_move"] != "not_addressed"
for name, pred in [("has_numbers", lambda p: p.get("has_numbers")), ("no numbers", lambda p: not p.get("has_numbers")),
                   ("location_given", lambda p: p.get("location_given")), ("no location", lambda p: not p.get("location_given")),
                   ("answer_words >= 150", lambda p: (p.get("answer_words") or 0) >= 150),
                   ("answer_words < 150", lambda p: (p.get("answer_words") or 0) < 150)]:
    n, e, lo, hi = share(pred, addr)
    L.append(f"| {name} | {n} | {e}% [{lo}, {hi}] |")
L += ["", "## Major points left unaddressed", ""]
for g in ("raised", "unchanged"):
    maj = [p for p in P if p["group"] == g and p.get("severity") == "major"]
    L.append(f"- {g}: {sum(p['author_move'] == 'not_addressed' for p in maj)} of {len(maj)} major points not addressed")
L += ["", "## By concern type: answer move (rows with n >= 15)", ""]
for ty in TYPES:
    sel = lambda p, ty=ty: p["type"] == ty
    n, e, lo, hi = share(lambda p: True, sel)
    L += [f"### {ty}: {n} points, raised share {e}% [{lo}, {hi}]", "", "| move | n | raised share |", "|---|---|---|"]
    for m in MOVES:
        c = share(lambda p, m=m: p["author_move"] == m, sel)
        if c[0] >= 15:
            L.append(f"| {m} | {c[0]} | {c[1]}% [{c[2]}, {c[3]}] |")
    L.append("")
L += ["## Reviewer status where the reviewer named the point (coders differ on blanket replies; read as a weak signal)", "",
      "| move | named points | resolved | partly | unresolved |", "|---|---|---|---|---|"]
for m in MOVES[:-1]:
    xs = [p for p in P if p["author_move"] == m and p.get("reviewer_status") in ("resolved", "partly", "unresolved")]
    if xs:
        c = collections.Counter(p["reviewer_status"] for p in xs)
        L.append(f"| {m} | {len(xs)} | {round(100 * c['resolved'] / len(xs))}% | {round(100 * c['partly'] / len(xs))}% | {round(100 * c['unresolved'] / len(xs))}% |")
L += ["", "## Tone register of the first reply (thread level)", "", "| register | raised | unchanged |", "|---|---|---|"]
G = {g: [t for t in threads if t["group"] == g] for g in ("raised", "unchanged")}
for r in ["formal_neutral", "warm", "deferential", "defensive", "terse"]:
    a = [round(100 * sum(t.get("tone", {}).get("register") == r for t in G[g]) / len(G[g])) for g in ("raised", "unchanged")]
    L.append(f"| {r} | {a[0]}% | {a[1]}% |")
L += ["", "| quantity | raised median | unchanged median |", "|---|---|---|",
      f"| points per thread | {statistics.median(len(t['points']) for t in G['raised'])} | {statistics.median(len(t['points']) for t in G['unchanged'])} |",
      f"| words per addressed point | {statistics.median(p.get('answer_words') or 0 for p in P if p['group'] == 'raised' and addr(p))} | "
      f"{statistics.median(p.get('answer_words') or 0 for p in P if p['group'] == 'unchanged' and addr(p))} |"]
Path(md).write_text("\n".join(L) + "\n")
print("\n".join(L))

link = lambda p: "https://openreview.net/forum?id=" + p["file"].split("-")[2]
E = ["# Point-level evidence", ""]
for ty in TYPES:
    E.append(f"## {ty}")
    for g in ("raised", "unchanged"):
        xs = [p for p in P if p["type"] == ty and p["group"] == g and p.get("answer_first_sentence")]
        rng.shuffle(xs)
        E.append(f"### {g} ({len(xs)} answered points; 10 shown)")
        for p in xs[:10]:
            q = f' Reviewer: "{p["reviewer_status_quote"]}"' if p.get("reviewer_status_quote") else ""
            E.append(f'- [{p["author_move"]}, {p["reviewer_status"]}] concern: {p["concern"]}. Answer opens: "{p["answer_first_sentence"]}"{q} ({link(p)})')
    E.append("")
E.append("## First-reply layouts (structure_template), raised, 40 shown")
xs = [t for t in G["raised"] if t.get("tone", {}).get("structure_template")]
rng.shuffle(xs)
E += [f"- {t['tone']['structure_template']}" for t in xs[:40]]
E.append("\n## First-reply layouts, unchanged, 25 shown")
xs = [t for t in G["unchanged"] if t.get("tone", {}).get("structure_template")]
rng.shuffle(xs)
E += [f"- {t['tone']['structure_template']}" for t in xs[:25]]
for g, k in (("raised", 30), ("unchanged", 20)):
    E.append(f"\n## Closing sentences of the first reply, {g}, {k} shown")
    xs = [t for t in G[g] if t.get("tone", {}).get("closing_sentence")]
    rng.shuffle(xs)
    E += [f'- "{t["tone"]["closing_sentence"]}"' for t in xs[:k]]
    E.append(f"\n## Follow-up patterns, {g}, {k} shown")
    xs = [t for t in G[g] if t.get("tone", {}).get("follow_up_pattern")]
    rng.shuffle(xs)
    E += [f"- {t['tone']['follow_up_pattern']}" for t in xs[:k]]
Path(ev_out).write_text("\n".join(E) + "\n")
