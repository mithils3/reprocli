"""Contrast coded features between raised and unchanged ICLR 2025 threads.

usage: contrast.py <out_dir with shard_*.json> <corpus_dir> <stats.md> <coded.jsonl>
Rates are the share of threads with the feature; Wilson 95% intervals; threads with no author post
under the review are dropped (the corpus keeps only the review's subtree).
"""
import collections, glob, json, math, sys

out_dir, corpus, stats_md, coded_out = sys.argv[1:5]
rows = []
for f in sorted(glob.glob(f"{out_dir}/shard_*.json")):
    rows += json.load(open(f))["threads"]
dropped = [t for t in rows if not t.get("n_author_posts")]
rows = [t for t in rows if t.get("n_author_posts")]
with open(coded_out, "w") as fh:
    for t in rows:
        fh.write(json.dumps(t) + "\n")


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(100 * (c - h)), round(100 * (c + h)))


G = {g: [t for t in rows if t["group"] == g] for g in ("raised", "unchanged")}
feats = collections.OrderedDict()
for o in ["thanks_then_changes_summary", "thanks_generic", "direct_answer", "restate_reviewer_points", "concession_first", "other"]:
    feats[f"opening: {o}"] = lambda t, o=o: t["opening_move"] == o
for c in ["agree_and_fixed", "agree_partially_scoped", "reframe_as_clarification", "limitation_added_to_paper", "blunt_admission"]:
    feats[f"concession: {c}"] = lambda t, c=c: any(x["style"] == c for x in t["concessions"])
feats["concession: any"] = lambda t: bool(t["concessions"])
for d in ["polite_with_evidence", "points_to_paper_section", "new_experiment", "assertive", "dismissive"]:
    feats[f"disagreement: {d}"] = lambda t, d=d: any(x["style"] == d for x in t["disagreements"])
for e in ["new_experiment", "new_baseline", "ablation", "theory_or_proof", "clarification", "revised_text_pointer", "numbers_table", "citation", "code_or_data_release"]:
    feats[f"evidence: {e}"] = lambda t, e=e: e in t["evidence_added"]
for b in ["per_point_headings", "quotes_reviewer", "uses_tables", "summary_of_revisions", "reminder_nudge"]:
    feats[f"structure: {b}"] = lambda t, b=b: bool(t[b])
feats["has misstep"] = lambda t: bool(t["missteps"])

lines = ["# Raised vs unchanged: coded features", "",
         f"Threads coded {len(rows) + len(dropped)}; dropped {len(dropped)} with no author post under the review "
         f"(raised {sum(t['group']=='raised' for t in dropped)}, unchanged {sum(t['group']=='unchanged' for t in dropped)}). "
         f"Kept: raised n={len(G['raised'])}, unchanged n={len(G['unchanged'])}. Cells: % of threads [Wilson 95%].", "",
         "| feature | raised | unchanged | diff (pts) |", "|---|---|---|---|"]
for name, f in feats.items():
    cell = {}
    for g, xs in G.items():
        k = sum(1 for t in xs if f(t))
        lo, hi = wilson(k, len(xs))
        cell[g] = (round(100 * k / len(xs)) if xs else 0, lo, hi)
    r, u = cell["raised"], cell["unchanged"]
    lines.append(f"| {name} | {r[0]}% [{r[1]}, {r[2]}] | {u[0]}% [{u[1]}, {u[2]}] | {r[0] - u[0]:+d} |")


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


lines += ["", "| quantity | raised median | unchanged median |", "|---|---|---|"]
for q in ["author_words_estimate", "n_author_posts"]:
    lines.append(f"| {q} | {med([t[q] for t in G['raised']])} | {med([t[q] for t in G['unchanged']])} |")
open(stats_md, "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
