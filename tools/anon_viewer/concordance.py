r"""Concordance between the exported data and the paper (SPEC.md section 7).

Reads `public/data/index.json` and nothing else, then prints one PASS or FAIL
line per row of the section 7 table with both values, followed by the primary
failure mode by tier in the shape of the paper's `tab:failure-modes`, once per
agent and once pooled. `export.py` runs this last and copies both blocks into
`export_report.md`.

A FAIL is reported, never patched: the exporter prints it and still exits 0.

    python3 concordance.py [path/to/index.json]
"""

import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INDEX = os.path.join(HERE, "public", "data", "index.json")

# The paper's numbers of record: abstract, introduction and the
# `% numbers of record` block of paper_latex/iclr2027_conference.tex,
# filled 2026-08-24 and 2026-08-27, band and roster rows refilled 2026-09-03
# when Muse Spark 1.2 joined the roster.
PAPER = {
    "dsv4_by_tier": "14/29 (48%), 9/28 (32%), 4/30 (13%)",
    "retrain_matched": "MiniMax-M2.7 5/32 (16%), Qwen3.6-27B 6/26 (23%), "
                       "Muse Spark 1.2 9/32 (28%), DeepSeek-V4 9/28 (32%)",
    "retrain_means": "3.41 (MiniMax-M2.7) to 6.43 (DeepSeek-V4)",
    "failed_spend": "mean 45%, median 27.4%, n=60 (15+19+26)",
    "band_96": "mean spend 6.5%, 1 of 42 reproduced",
    "retrain_near_miss": "15 of 28 near-miss-partial, 15 of 19 misses",
    "retrain_partial": "22 of 28 score 6 or better",
    "papers": "100 papers, 34 run / 33 retrain / 33 reimplement",
    "agents": "4",
}
TIERS = ["run", "retrain", "reimplement"]


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def pct(part, whole):
    return "%d%%" % round(100.0 * part / whole) if whole else "n/a"


def _sweep(index, key):
    for sweep in index.get("sweeps") or []:
        if sweep["key"] == key:
            return sweep
    return {"key": key, "n": 0, "n_reproduced": 0, "mean_score": None}


def _name(index, model_key):
    for model in index.get("models") or []:
        if model["key"] == model_key:
            return model["name"]
    return model_key


def _fraction(run):
    budget = run.get("budget_h100")
    if not budget:
        return None
    return (run.get("spent_h100") or 0) / budget


def checks(index):
    """One dict per row of the SPEC section 7 table."""
    runs = index.get("runs") or []
    rows = []

    parts = []
    for tier in TIERS:
        sweep = _sweep(index, "dsv4-" + tier)
        parts.append("%d/%d (%s)" % (sweep["n_reproduced"], sweep["n"],
                                     pct(sweep["n_reproduced"], sweep["n"])))
    rows.append({"name": "DeepSeek-V4 reproduced by tier",
                 "paper": PAPER["dsv4_by_tier"], "computed": ", ".join(parts)})

    parts = []
    for model in ("minimax", "qwen3", "muse", "dsv4"):
        sweep = _sweep(index, model + "-retrain")
        parts.append("%s %d/%d (%s)" % (_name(index, model), sweep["n_reproduced"],
                                        sweep["n"],
                                        pct(sweep["n_reproduced"], sweep["n"])))
    rows.append({"name": "Retrain matched-number range",
                 "paper": PAPER["retrain_matched"], "computed": ", ".join(parts)})

    means = [(s["mean_score"], s["model"]) for s in (_sweep(index, m + "-retrain")
             for m in ("minimax", "qwen3", "muse", "dsv4")) if s.get("mean_score") is not None]
    if means:
        low, high = min(means), max(means)
        computed = "%.2f (%s) to %.2f (%s)" % (low[0], _name(index, low[1]),
                                               high[0], _name(index, high[1]))
    else:
        computed = "no scores"
    rows.append({"name": "Retrain mean audit score range",
                 "paper": PAPER["retrain_means"], "computed": computed})

    failed = [r for r in runs if r["model"] == "dsv4" and not r["audit"]["reproduced"]]
    fractions = [f for f in (_fraction(r) for r in failed) if f is not None]
    per_tier = [sum(1 for r in failed if r["tier"] == tier) for tier in TIERS]
    if fractions:
        computed = "mean %s, median %.1f%%, n=%d (%s)" % (
            pct(sum(fractions), len(fractions)),
            100 * statistics.median(fractions), len(failed),
            "+".join(str(n) for n in per_tier))
    else:
        computed = "no failed runs"
    rows.append({"name": "Failed-run spend", "paper": PAPER["failed_spend"],
                 "computed": computed})

    band = [r for r in runs if r.get("budget_h100") == 96]
    fractions = [f for f in (_fraction(r) for r in band) if f is not None]
    reproduced = sum(1 for r in band if r["audit"]["reproduced"])
    computed = "mean spend %.1f%%, %d of %d reproduced" % (
        100 * sum(fractions) / len(fractions) if fractions else 0.0,
        reproduced, len(band))
    rows.append({"name": "96 H100-hour band", "paper": PAPER["band_96"],
                 "computed": computed,
                 "note": "the paper and the export both pool every run of the "
                         "twelve sweeps whose budget is 96"})

    retrain = [r for r in runs if r["sweep"] == "dsv4-retrain"]
    misses = [r for r in retrain if not r["audit"]["reproduced"]]
    near = [r for r in retrain if r["mode"] == "near-miss-partial"]
    near_miss = [r for r in near if not r["audit"]["reproduced"]]
    rows.append({"name": "Retrain near-miss", "paper": PAPER["retrain_near_miss"],
                 "computed": "%d of %d near-miss-partial, %d of %d misses"
                             % (len(near), len(retrain), len(near_miss), len(misses))})

    six = [r for r in retrain if (r["audit"]["score"] or 0) >= 6]
    rows.append({"name": "Retrain verified partial", "paper": PAPER["retrain_partial"],
                 "computed": "%d of %d score 6 or better" % (len(six), len(retrain))})

    papers = index.get("papers") or []
    counts = [sum(1 for p in papers if p.get("tier") == tier) for tier in TIERS]
    rows.append({"name": "Papers", "paper": PAPER["papers"],
                 "computed": "%d papers, %d run / %d retrain / %d reimplement"
                             % (len(papers), counts[0], counts[1], counts[2])})

    rows.append({"name": "Agents", "paper": PAPER["agents"],
                 "computed": str(len(index.get("models") or []))})

    for row in rows:
        row["ok"] = row["paper"] == row["computed"]
    return rows


def lines(rows):
    """Stdout form: one PASS or FAIL line per check, both values on it."""
    out = []
    for row in rows:
        out.append("%s | %s | paper: %s | computed: %s"
                   % ("PASS" if row["ok"] else "FAIL", row["name"], row["paper"],
                      row["computed"]))
        if not row["ok"] and row.get("note"):
            out.append("       %s" % row["note"])
    return out


def table(rows):
    """Report form."""
    out = ["| check | paper says | computed | |", "|---|---|---|---|"]
    for row in rows:
        out.append("| %s | %s | %s | %s |"
                   % (row["name"], row["paper"], row["computed"],
                      "PASS" if row["ok"] else "**FAIL**"))
    notes = [row for row in rows if not row["ok"]]
    if notes:
        out.append("")
        for row in notes:
            out.append("- %s: %s" % (row["name"],
                                     row.get("note") or "the paper and the export "
                                     "disagree; the data is left as exported"))
    return out


def mode_table(index, model_key=None):
    """Primary failure mode by tier, the shape of the paper's tab:failure-modes."""
    modes = [m["key"] for m in index.get("modes") or []]
    runs = [r for r in (index.get("runs") or [])
            if model_key is None or r["model"] == model_key]
    title = ("All agents pooled" if model_key is None
             else _name(index, model_key)) + " (n=%d)" % len(runs)
    out = ["**%s**" % title, "",
           "| mode | Run | Retrain | Reimplement | All |", "|---|---|---|---|---|"]
    for mode in modes:
        cells = [sum(1 for r in runs if r["mode"] == mode and r["tier"] == tier)
                 for tier in TIERS]
        out.append("| %s | %d | %d | %d | %d |"
                   % (mode, cells[0], cells[1], cells[2], sum(cells)))
    totals = [sum(1 for r in runs if r["tier"] == tier) for tier in TIERS]
    out.append("| **total** | %d | %d | %d | %d |"
               % (totals[0], totals[1], totals[2], sum(totals)))
    out.append("")
    return out


def report(index_path):
    """(concordance table, failure-mode tables, PASS/FAIL lines, number of
    FAILs, number of checks), from the written index and nothing else."""
    index = load(index_path)
    rows = checks(index)
    tables = []
    for model in index.get("models") or []:
        tables += mode_table(index, model["key"])
    tables += mode_table(index, None)
    return (table(rows), tables, lines(rows),
            sum(1 for row in rows if not row["ok"]), len(rows))


def main(argv):
    path = argv[1] if len(argv) > 1 else DEFAULT_INDEX
    if not os.path.exists(path):
        sys.exit("no index at " + path)
    rows = checks(load(path))
    for line in lines(rows):
        print(line)
    print("")
    _table, modes, _checked, fails, _n = report(path)
    for line in modes:
        print(line)
    print("%d of %d checks pass" % (len(rows) - fails, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
