import collections, csv, json, math, pathlib

REPO = pathlib.Path("/home/mithil/PyCharmProjects/reprocli")
RESOLVED = pathlib.Path("/home/mithil/sweeps/paper-table-2026-09-05/resolved_modes.json")
INDEX = REPO / "tools/anon_viewer/public/data/index.json"
E6 = REPO / "rebuttal/results/e6/table.csv"
OUT = pathlib.Path(__file__).resolve().parent
FAITHFUL = "near-miss-partial"  # Appendix G "Ran, outside tolerance"
TIERS = ["run", "retrain", "reimplement"]
MODELS = ["dsv4", "qwen3", "minimax", "muse"]


def wilson(k, n, z=1.959964):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * (c - h), 100 * (c + h))


idx = json.load(open(INDEX))
res = json.load(open(RESOLVED))
e6 = list(csv.DictReader(open(E6)))
mode = {r["id"]: r["mode"] for r in res["runs"]}
papers = {p["arxiv_id"]: p["tier"] for p in idx["papers"]}
assert len(papers) == 100, len(papers)

graded = {}
for ir in idx["runs"]:
    key = (ir["model"], ir["tier"], ir["arxiv_id"])
    assert key not in graded
    graded[key] = ir
assert len(graded) == 372 and len(e6) == 372
e6_keys = set()
for r in e6:
    key = (r["model"], r["tier"], r["arxiv_id"])
    assert key not in e6_keys and key in graded
    assert int(r["index_score"]) == graded[key]["audit"]["score"], key
    assert r["run_id"] == graded[key]["id"], key
    e6_keys.add(key)

# 400 cells: each paper sits in one tier and gets all four agents
cells = []
for a, t in papers.items():
    for m in MODELS:
        cells.append((m, t, a))
assert len(cells) == 400
assert all(k[:2] == (k[0], papers[k[2]]) for k in graded)  # graded runs sit in their paper's tier

rows = {}
for c in cells:
    ir = graded.get(c)
    rep = bool(ir) and ir["audit"]["score"] >= 8
    fm = bool(ir) and mode.get(ir["id"]) == FAITHFUL
    rows[c] = dict(graded=bool(ir), rep=rep, fm=fm,
                   score=ir["audit"]["score"] if ir else None,
                   verdict=ir["audit"]["verdict"] if ir else "no graded run",
                   mode=mode.get(ir["id"]) if ir else "no label")
assert not any(v["rep"] and v["fm"] for v in rows.values())

fm_cells = [c for c in cells if rows[c]["fm"]]
out = []
out.append(f"faithful-miss cells (mode {FAITHFUL}): {len(fm_cells)}")
for t in TIERS:
    out.append(f"  tier {t}: {sum(1 for c in fm_cells if c[1] == t)}")
for m in MODELS:
    out.append(f"  model {m}: {sum(1 for c in fm_cells if c[0] == m)}")
rep_total = sum(1 for c in cells if rows[c]["rep"])
clean_total = sum(1 for c in cells if rows[c]["mode"] == "reproduced-clean")
out.append(f"reproduced (score>=8) total: {rep_total}; reproduced-clean mode total: {clean_total}")
out.append(f"no graded run: {sum(1 for c in cells if not rows[c]['graded'])}")
out.append("")


def table(exclude):
    lines = []
    best = {}
    for t in TIERS:
        cands = []
        for m in MODELS:
            grp = [c for c in cells if c[0] == m and c[1] == t]
            n_all = len(grp)
            k = sum(1 for c in grp if rows[c]["rep"])
            nr = sum(1 for c in grp if rows[c]["fm"]) if exclude else 0
            n = n_all - nr
            lo, hi = wilson(k, n)
            lines.append(f"{t:12s} {m:7s} {k:2d} of {n:3d} = {100*k/n:5.1f}%  (n_all {n_all}, removed {nr})")
            cands.append((k / n, m, k, n, lo, hi))
        top = max(cands)
        best[t] = top
    k_all = sum(1 for c in cells if rows[c]["rep"])
    n_all = len(cells) - (len(fm_cells) if exclude else 0)
    lo, hi = wilson(k_all, n_all)
    lines.append(f"{'overall':12s} {'all':7s} {k_all:2d} of {n_all:3d} = {100*k_all/n_all:5.1f}%  Wilson95 {lo:.1f}-{hi:.1f}")
    for t in TIERS:
        p, m, k, n, lo, hi = best[t]
        lines.append(f"best {t:12s} {m:7s} {k} of {n} = {100*p:.1f}%  Wilson95 {lo:.1f}-{hi:.1f}")
    return lines


out.append("BASELINE (all 400 cells as denominators)")
out += table(False)
out.append("")
out.append("AFTER REMOVING FAITHFUL-MISS CELLS FROM DENOMINATORS")
out += table(True)
out.append("")
out.append("FAITHFUL-MISS CELLS (tier, model, paper, verdict, score)")
for c in fm_cells:
    out.append(f"{c[1]} {c[0]} {c[2]} {rows[c]['verdict']} {rows[c]['score']}")

text = "\n".join(out) + "\n"
(OUT / "results.txt").write_text(text)
print(text)
