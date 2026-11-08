"""Raised vs unchanged contrasts from the outcome-blind recode.

usage: blind_stats.py <out4_dir> <key.json> <withdrawn.txt> <blind_stats.md> <blind_rows.jsonl> <blind_evidence.md>
Coders saw no group, score or reviewer follow-up (build_blind.py); the group comes from key.json here.
Thread rows: % of threads [Wilson 95%] and the raised-minus-unchanged difference [Newcombe 95%].
Point rows: share of points sitting in raised threads, thread-cluster bootstrap 95% (2,000, seed 22528).
"""
import collections, glob, json, math, random, statistics, sys
from pathlib import Path

out4, key_path, wd_path, md, rows_out, ev_out = sys.argv[1:7]
key = json.load(open(key_path))
withdrawn = set(Path(wd_path).read_text().split())


def truth(v):
    return v is True or (isinstance(v, str) and v.strip().lower() == "true")


T = []
for f in sorted(glob.glob(f"{out4}/blind_*.json")):
    for t in json.load(open(f))["threads"]:
        k = key.get(t.get("id"))
        if not k or k["file"] in withdrawn:
            continue
        t["group"], t["file"] = k["group"], k["file"]
        for b in ("per_point_headings", "quotes_reviewer", "uses_tables", "summary_of_revisions", "reminder_nudge"):
            t[b] = truth(t.get(b))
        for p in t.get("points", []):
            p["has_numbers"], p["location_given"] = truth(p.get("has_numbers")), truth(p.get("location_given"))
        T.append(t)
seen = set(); T = [t for t in T if not (t["id"] in seen or seen.add(t["id"]))]
with open(rows_out, "w") as fh:
    for t in T:
        fh.write(json.dumps(t) + "\n")
G = {g: [t for t in T if t["group"] == g] for g in ("raised", "unchanged")}


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def row(name, pred):
    a = [pred(t) for t in G["raised"]]; b = [pred(t) for t in G["unchanged"]]
    k1, n1, k2, n2 = sum(a), len(a), sum(b), len(b)
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1); l2, u2 = wilson(k2, n2)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2); hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    flag = " *" if lo > 0 or hi < 0 else ""
    pc = lambda x: round(100 * x)
    return f"| {name} | {k1}/{n1} = {pc(p1)}% [{pc(l1)}, {pc(u1)}] | {k2}/{n2} = {pc(p2)}% [{pc(l2)}, {pc(u2)}] | {pc(d):+d} [{pc(lo):+d}, {pc(hi):+d}]{flag} |"


nr, nu = len(G["raised"]), len(G["unchanged"])
L = ["# Outcome-blind recode: raised vs unchanged", "",
     f"Threads coded blind: {len(T)} (raised {nr}, unchanged {nu}). Coders saw the review, the authors' general response and the authors' posts; "
     "the group, the scores, reviewer follow-ups and author sentences about a score change were removed (build_blind.py). "
     "Each cell: count/threads = share [Wilson 95%]; diff = raised minus unchanged in points [Newcombe 95%]; * marks a difference whose interval excludes 0.", "",
     "## Reply features (thread level)", "", "| feature | raised | unchanged | diff |", "|---|---|---|---|"]
for b in ("summary_of_revisions", "per_point_headings", "quotes_reviewer", "uses_tables", "reminder_nudge"):
    L.append(row(b, lambda t, b=b: t[b]))
L.append(row("any concession", lambda t: bool(t.get("concessions"))))
L.append(row("any disagreement", lambda t: bool(t.get("disagreements"))))
L.append(row("any misstep flagged", lambda t: bool(t.get("missteps"))))
L.append(row("more than one author post", lambda t: (t.get("n_author_posts") or 0) > 1))
L += ["", "## Opening move of the first post", "", "| opening | raised | unchanged | diff |", "|---|---|---|---|"]
for m in ("thanks_then_changes_summary", "thanks_generic", "direct_answer", "restate_reviewer_points", "concession_first", "other"):
    L.append(row(m, lambda t, m=m: t.get("opening_move") == m))
L += ["", "## Register of the first post", "", "| register | raised | unchanged | diff |", "|---|---|---|---|"]
for r in ("formal_neutral", "warm", "deferential", "defensive", "terse"):
    L.append(row(r, lambda t, r=r: t.get("register") == r))
L += ["", "## Evidence added (any in the thread)", "", "| evidence | raised | unchanged | diff |", "|---|---|---|---|"]
for e in ("new_experiment", "new_baseline", "ablation", "theory_or_proof", "clarification", "revised_text_pointer", "numbers_table", "citation", "code_or_data_release"):
    L.append(row(e, lambda t, e=e: e in (t.get("evidence_added") or [])))
L += ["", "## Concession style (any in the thread)", "", "| style | raised | unchanged | diff |", "|---|---|---|---|"]
for s in ("agree_and_fixed", "agree_partially_scoped", "reframe_as_clarification", "limitation_added_to_paper", "blunt_admission"):
    L.append(row(s, lambda t, s=s: any(c.get("style") == s for c in t.get("concessions") or [])))
L += ["", "## Disagreement style (any in the thread)", "", "| style | raised | unchanged | diff |", "|---|---|---|---|"]
for s in ("polite_with_evidence", "points_to_paper_section", "new_experiment", "assertive", "dismissive"):
    L.append(row(s, lambda t, s=s: any(c.get("style") == s for c in t.get("disagreements") or [])))
med = lambda g, f: statistics.median(f(t) for t in G[g])
L += ["", "| quantity | raised median | unchanged median |", "|---|---|---|"]
for name, f in [("author posts", lambda t: t.get("n_author_posts") or 0), ("author words (coder estimate)", lambda t: t.get("author_words_estimate") or 0),
                ("review points", lambda t: len(t.get("points", []))), ("concessions", lambda t: len(t.get("concessions") or [])),
                ("disagreements", lambda t: len(t.get("disagreements") or []))]:
    L.append(f"| {name} | {med('raised', f)} | {med('unchanged', f)} |")

# point level
P = [{**p, "tid": t["id"], "group": t["group"], "file": t["file"]} for t in T for p in t.get("points", [])]
by_t = collections.defaultdict(list)
for p in P:
    by_t[p["tid"]].append(p)
TIDS = list(by_t)
rng = random.Random(22528)


def share(pred, sel=lambda p: True):
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
    return n, round(100 * est), round(100 * bs[int(0.025 * len(bs))]), round(100 * bs[int(0.975 * len(bs)) - 1])


base = share(lambda p: True)
MOVES = ["new_experiment", "new_analysis_existing_data", "text_revision", "clarification_only", "concede_and_scope",
         "disagree_with_evidence", "disagree_without_evidence", "defer_future_work", "not_addressed"]
L += ["", "## Reviewer points: answer move", "",
      f"Points {len(P)} in {len(TIDS)} threads. Raised share of all points: {base[1]}% [{base[2]}, {base[3]}]. "
      "Each cell: points n, share of those points that sit in a raised thread [thread-cluster bootstrap 95%]. "
      "A cell whose interval sits wholly above the baseline goes with raised threads more than the average point.", "",
      "| move | n | raised share |", "|---|---|---|"]
for m in MOVES:
    n, e, lo, hi = share(lambda p, m=m: p.get("author_move") == m)
    L.append(f"| {m} | {n} | {e}% [{lo}, {hi}] |")
addr = lambda p: p.get("author_move") != "not_addressed"
L += ["", "## Answer features, addressed points", "", "| feature | n | raised share |", "|---|---|---|"]
for name, pred in [("has_numbers", lambda p: p["has_numbers"]), ("no numbers", lambda p: not p["has_numbers"]),
                   ("location_given", lambda p: p["location_given"]), ("no location", lambda p: not p["location_given"]),
                   ("answer_words >= 150", lambda p: (p.get("answer_words") or 0) >= 150),
                   ("answer_words < 150", lambda p: (p.get("answer_words") or 0) < 150)]:
    n, e, lo, hi = share(pred, addr)
    L.append(f"| {name} | {n} | {e}% [{lo}, {hi}] |")
L += ["", "## Major points left unaddressed", ""]
for g in ("raised", "unchanged"):
    maj = [p for p in P if p["group"] == g and p.get("severity") == "major"]
    k = sum(p.get("author_move") == "not_addressed" for p in maj); lo, hi = wilson(k, len(maj))
    L.append(f"- {g}: {k} of {len(maj)} major points not addressed ({round(100 * k / len(maj))}% [{round(100 * lo)}, {round(100 * hi)}])")
TYPES = sorted({p.get("type") for p in P}, key=lambda x: -sum(q.get("type") == x for q in P))
L += ["", "## By concern type: answer move (moves with n >= 12)", ""]
for ty in TYPES:
    sel = lambda p, ty=ty: p.get("type") == ty
    n, e, lo, hi = share(lambda p: True, sel)
    L += [f"### {ty}: {n} points, raised share {e}% [{lo}, {hi}]", "", "| move | n | raised share |", "|---|---|---|"]
    for m in MOVES:
        c = share(lambda p, m=m: p.get("author_move") == m, sel)
        if c[0] >= 12:
            L.append(f"| {m} | {c[0]} | {c[1]}% [{c[2]}, {c[3]}] |")
    L.append("")
Path(md).write_text("\n".join(L) + "\n")
print("\n".join(L))

link = lambda f: "https://openreview.net/forum?id=" + f.split("-")[2]
E = ["# Blind-coded evidence (verbatim author sentences; group joined after coding)", ""]
for g, k in (("raised", 12), ("unchanged", 8)):
    for style in ("agree_and_fixed", "agree_partially_scoped", "reframe_as_clarification", "limitation_added_to_paper", "blunt_admission"):
        xs = [(c["verbatim"], t["file"]) for t in G[g] for c in t.get("concessions") or [] if c.get("style") == style]
        rng.shuffle(xs)
        E.append(f"## Concessions, {style}, {g} ({len(xs)}; {min(k, len(xs))} shown)")
        E += [f'- "{v}" ({link(f)})' for v, f in xs[:k]] + [""]
    for style in ("polite_with_evidence", "points_to_paper_section", "new_experiment", "assertive", "dismissive"):
        xs = [(c["verbatim"], t["file"]) for t in G[g] for c in t.get("disagreements") or [] if c.get("style") == style]
        rng.shuffle(xs)
        E.append(f"## Disagreements, {style}, {g} ({len(xs)}; {min(k, len(xs))} shown)")
        E += [f'- "{v}" ({link(f)})' for v, f in xs[:k]] + [""]
for g in ("raised", "unchanged"):
    for fld, k in (("opening_first_sentence", 25), ("closing_sentence", 20), ("structure_template", 25)):
        xs = [(t.get(fld), t["file"]) for t in G[g] if t.get(fld)]
        rng.shuffle(xs)
        E.append(f"## {fld}, {g} ({k} shown)")
        E += [f'- "{v}" ({link(f)})' for v, f in xs[:k]] + [""]
    xs = [(s, t["file"]) for t in G[g] for s in t.get("best_phrases") or []]; rng.shuffle(xs)
    E.append(f"## best_phrases, {g} (40 shown)"); E += [f'- "{v}" ({link(f)})' for v, f in xs[:40]] + [""]
    xs = [(s, t["file"]) for t in G[g] for s in t.get("missteps") or []]; rng.shuffle(xs)
    E.append(f"## missteps, {g} (25 shown)"); E += [f'- "{v}" ({link(f)})' for v, f in xs[:25]] + [""]
for ty in TYPES:
    E.append(f"## Point answers: {ty}")
    for g in ("raised", "unchanged"):
        xs = [p for p in P if p.get("type") == ty and p["group"] == g and p.get("answer_first_sentence")]
        rng.shuffle(xs)
        E.append(f"### {g} ({len(xs)} answered; 8 shown)")
        E += [f'- [{p.get("author_move")}] concern: {p.get("concern")}. Answer opens: "{p["answer_first_sentence"]}" ({link(p["file"])})' for p in xs[:8]]
    E.append("")
Path(ev_out).write_text("\n".join(E) + "\n")
