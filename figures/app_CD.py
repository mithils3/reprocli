#!/usr/bin/env python3
"""Appendix C figures: the verdict derivation as a flow diagram, the anti-cheat
flags by kind and severity, and the auditor's tool rounds per run by verdict.
Data: tools/anon_viewer/public/data (index.json and the per-run gz records),
the same 372 graded runs charts.py uses. Usage: app_CD.py [name ...]"""
import collections
import gzip
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from charts import (AMBER, FAINT, GREEN, INK, LINE, LINE_STRONG, MID, MUTED, ROSE,  # noqa: E402
                    SANS, SLATE, TRACK, W, X0, X1, head, line, page, rect, swatch, text)

DATA = pathlib.Path(os.environ.get(
    "RECLAIM_VIEWER_DATA",
    "/home/mithil/PyCharmProjects/reprocli/tools/anon_viewer/public/data"))

VERDICT_COLOR = {"reproduced": GREEN, "partial": AMBER, "not_reproduced": SLATE,
                 "unverifiable": SLATE, "disqualified": ROSE}
VERDICT_NAME = {"reproduced": "reproduced", "partial": "partial",
                "not_reproduced": "not reproduced", "unverifiable": "unverifiable",
                "disqualified": "disqualified"}


def load_runs():
    runs = json.load(open(DATA / "index.json"))["runs"]
    assert len(runs) == 372, len(runs)
    return runs


# ====================================================== fig: verdict flow
# Rules only: Table tab:rubric and prompts/audit_finalizer.py. No counts.
ARROW = MUTED


def box(b, x, y, w, h, lines, fill="#FFFFFF", stroke=LINE_STRONG, color=INK,
        size=12, weight=400, first_weight=None, first_color=None):
    s = f' stroke="{stroke}" stroke-width="1"' if stroke else ""
    b.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="4" '
             f'fill="{fill}"{s}/>')
    n = len(lines)
    lh = size + 3
    y0 = y + h / 2 - (n - 1) * lh / 2 + size * 0.36
    for i, s_ in enumerate(lines):
        wt = first_weight if (i == 0 and first_weight) else weight
        cl = first_color if (i == 0 and first_color) else color
        b.append(text(x + w / 2, y0 + i * lh, s_, size, cl, SANS, wt, "middle"))


def arrow(b, pts):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    b.append(f'<polyline points="{d}" fill="none" stroke="{ARROW}" stroke-width="1.2" '
             f'stroke-linejoin="round" marker-end="url(#ah)"/>')


def fig_verdict_flow():
    b = head("from the auditor's report to the verdict of record",
             "the two integrity checks run before the band")
    b.append(f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" '
             f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
             f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{ARROW}"/></marker></defs>')
    cx = (X0 + X1) / 2
    # input
    box(b, cx - 245, 48, 490, 38,
        ["auditor's report on one run",
         "a raw score of 0 to 10, flags each marked low, med or high, execution verified or not"],
        first_weight=600, color=MUTED, size=11.5)
    arrow(b, [(cx, 86), (cx, 104)])
    # decision 1
    box(b, cx - 165, 104, 330, 30, ["any high-severity flag, or a raw score of 0?"],
        fill=TRACK, stroke=None, weight=600)
    lx = 82
    arrow(b, [(cx - 165, 119), (lx, 119), (lx, 150)])
    b.append(text((cx - 165 + lx) / 2, 114, "yes", 11.5, MUTED, SANS, 500, "middle"))
    box(b, X0, 150, 120, 50, ["score set to 0", "a higher reported", "score is kept"],
        color=MID, size=11.5, first_weight=600, first_color=INK)
    arrow(b, [(lx, 200), (lx, 296)])
    arrow(b, [(cx, 134), (cx, 164)])
    b.append(text(cx + 6, 153, "no", 11.5, MUTED, SANS, 500))
    # decision 2
    box(b, cx - 100, 164, 200, 30, ["execution verified?"], fill=TRACK, stroke=None,
        weight=600)
    bx, hx = 210, 470
    arrow(b, [(cx - 100, 179), (bx, 179), (bx, 214)])
    b.append(text((cx - 100 + bx) / 2, 174, "no", 11.5, MUTED, SANS, 500, "middle"))
    arrow(b, [(cx + 100, 179), (hx, 179), (hx, 214)])
    b.append(text((cx + 100 + hx) / 2, 174, "yes", 11.5, MUTED, SANS, 500, "middle"))
    box(b, bx - 70, 214, 140, 36, ["a score of 6 or more", "is set to 1"], color=MID,
        size=11.5, first_weight=600, first_color=INK)
    box(b, hx - 70, 214, 140, 36, ["the score stands", "verdict by band"], color=MID,
        size=11.5, first_weight=600, first_color=INK)
    # branches into the verdict band
    arrow(b, [(bx, 250), (bx, 296)])
    b.append(text(bx - 6, 280, "1", 11.5, MUTED, SANS, 500, "end"))
    arrow(b, [(bx + 40, 250), (bx + 40, 272), (300, 272), (300, 296)])
    b.append(text(275, 267, "2 to 5", 11.5, MUTED, SANS, 500, "middle"))
    arrow(b, [(hx - 50, 250), (hx - 50, 272), (380, 272), (380, 296)])
    b.append(text(400, 267, "1 to 5", 11.5, MUTED, SANS, 500, "middle"))
    arrow(b, [(hx, 250), (hx, 296)])
    b.append(text(hx + 6, 280, "6 to 7", 11.5, MUTED, SANS, 500))
    arrow(b, [(hx + 50, 250), (hx + 50, 272), (599, 272), (599, 296)])
    b.append(text(560, 267, "8 to 10", 11.5, MUTED, SANS, 500, "middle"))
    # terminals, in the score order of the score distribution
    terms = [("disqualified", "score 0", ROSE), ("unverifiable", "score 1, no execution", SLATE),
             ("not reproduced", "score 1 to 5", SLATE), ("partial", "score 6 to 7", AMBER),
             ("reproduced", "score 8 to 10", GREEN)]
    tw, gap = 120.8, 8
    for i, (name, sub, c) in enumerate(terms):
        x = X0 + i * (tw + gap)
        box(b, x, 296, tw, 36, [name, sub], fill=c, stroke=None, color="#FFFFFF",
            size=11, first_weight=600)
    page("app_CD_verdict_flow", b, 350)


# ============================================ fig: flags by kind and severity
KIND_NAME = [
    ("other_provenance_break", "other provenance break"),
    ("wrong_split_scale_dataset", "wrong split, scale, or dataset"),
    ("self_scored_or_fabricated", "self-scored or fabricated"),
    ("cherry_picked_metric", "cherry-picked metric"),
    ("stale_artifact", "stale artifact"),
    ("echoed_prose_number", "echoed prose number"),
    ("hardcoded_constant", "hardcoded constant"),
    ("retrieved_benchmark_answer", "retrieved benchmark answer"),
]
SEV = [("low", SLATE), ("med", AMBER), ("high", ROSE)]


def fig_flag_kinds():
    runs = load_runs()
    by = collections.defaultdict(collections.Counter)
    zeroed = collections.defaultdict(set)
    total = 0
    for r in runs:
        for f in r["audit"]["flags"]:
            by[f["kind"]][f["severity"]] += 1
            total += 1
            if f["severity"] == "high":
                zeroed[f["kind"]].add(r["id"])
    known = {k for k, _ in KIND_NAME}
    assert set(by) <= known, set(by) - known
    assert all(s in ("low", "med", "high") for c in by.values() for s in c), by
    rows = sorted(KIND_NAME, key=lambda kn: (-sum(by[kn[0]].values()), kn[1]))
    n_dq = len({rid for s in zeroed.values() for rid in s})
    b = head("anti-cheat flags by kind and severity",
             f"{total} flags on {len(runs)} graded runs")
    ky = 56
    for kx, (sev, c), label in zip((X0, X0 + 70, X0 + 150), SEV,
                                   ("low", "med", "high, zeroes the score")):
        b.append(swatch(kx, ky - 8, c))
        b.append(text(kx + 15, ky, label, 12, MID))
    bx, bw, bh, pitch, top = 214, 310, 16, 26, 96
    vmax = max(sum(by[k].values()) for k, _ in KIND_NAME)
    b.append(text(bx + bw + 12, top - 12, "flags", 11.5, MUTED, SANS, 600))
    b.append(text(X1, top - 26, "runs", 11.5, MUTED, SANS, 600, "end"))
    b.append(text(X1, top - 12, "disqualified", 11.5, MUTED, SANS, 600, "end"))
    for i, (kind, name) in enumerate(rows):
        y = top + i * pitch
        n = sum(by[kind].values())
        b.append(text(bx - 12, y + 12, name, 12, INK if n else FAINT, SANS, 500, "end"))
        x = bx
        for sev, c in SEV:
            w = bw * by[kind][sev] / vmax
            if w > 0:
                b.append(rect(x, y, w, bh, c, 0))
                if x > bx:
                    b.append(line(x, y, x, y + bh, "#FFFFFF", 1))
                s = str(by[kind][sev])
                if w >= 6.4 * len(s) + 8:
                    b.append(text(x + w / 2, y + 12, s, 11.5, "#FFFFFF", SANS, 600, "middle"))
            x += w
        b.append(text(bx + bw + 12, y + 12, str(n), 12, INK if n else FAINT, SANS, 600,
                      tnum=True))
        z = len(zeroed[kind])
        b.append(text(X1, y + 12, str(z) if z else "0", 12, ROSE if z else FAINT, SANS, 600,
                      "end", tnum=True))
    y = top + len(rows) * pitch
    b.append(line(X0, y + 2, X1, y + 2, LINE))
    b.append(text(X1, y + 18, f"{n_dq} distinct runs carry a high flag, every one disqualified; "
                  "a run counts under each kind it carries", 11.5, MUTED, SANS, 400, "end"))
    page("app_CD_flag_kinds", b, y + 36)


# ========================================= fig: auditor tool rounds by verdict
# A tool round is a round of the auditor's own loop with at least one tool call;
# the loop is capped at 25 rounds (Appendix B).
CAP = 25
VERDICT_ORDER = ["reproduced", "partial", "not_reproduced", "unverifiable", "disqualified"]


def audit_rounds(run_id):
    ev = json.load(gzip.open(DATA / "runs" / f"{run_id}.json.gz"))["audit_events"]
    return len({e["round_index"] for e in ev if e["kind"] == "call_start"})


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def fig_auditor_effort():
    runs = load_runs()
    per = collections.defaultdict(list)
    for r in runs:
        per[r["audit"]["verdict"]].append(audit_rounds(r["id"]))
    assert set(per) == set(VERDICT_ORDER), set(per)
    assert max(max(v) for v in per.values()) <= CAP
    b = head("auditor tool rounds per run, by verdict",
             f"{len(runs)} graded runs; bars scaled within each row")
    top, pitch, bar_h = 60, 52, 36
    px, pw = 150, X1 - 150
    binw = pw / CAP
    for i, v in enumerate(VERDICT_ORDER):
        y = top + i * pitch
        xs = per[v]
        hist = collections.Counter(xs)
        hmax = max(hist.values())
        c = VERDICT_COLOR[v]
        m = median(xs)
        # the median sits in the label column so no bar lies under a label
        b.append(text(X0, y + 13, VERDICT_NAME[v], 12, c, SANS, 600))
        b.append(text(X0, y + 27, f"{len(xs)} runs", 11.5, MUTED))
        b.append(text(X0, y + 41, f"median {m:g}", 11.5, INK, SANS, 600))
        base = y + bar_h + 2
        b.append(line(px, base + 0.5, px + pw, base + 0.5, LINE))
        for k in range(1, CAP + 1):
            n = hist.get(k, 0)
            if n:
                h = bar_h * n / hmax
                b.append(rect(px + (k - 1) * binw + 1, base - h, binw - 2, h, c, 0))
        mx = px + (m - 0.5) * binw
        b.append(line(mx, y - 4, mx, base + 4, INK, 1.2, "3 2"))
    base = top + (len(VERDICT_ORDER) - 1) * pitch + bar_h + 2
    for k in (1, 5, 10, 15, 20, CAP):
        b.append(text(px + (k - 0.5) * binw, base + 17, str(k), 11.5, FAINT, SANS, 400,
                      "middle"))
    b.append(text(px + pw / 2, base + 33, "tool rounds the auditor spent on the run, cap 25",
                  11.5, MUTED, SANS, 400, "middle"))
    page("app_CD_auditor_effort", b, base + 48)


CHARTS = {
    "app_CD_verdict_flow": fig_verdict_flow,
    "app_CD_flag_kinds": fig_flag_kinds,
    "app_CD_auditor_effort": fig_auditor_effort,
}

if __name__ == "__main__":
    for n in sys.argv[1:] or CHARTS:
        CHARTS[n]()
