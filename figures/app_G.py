#!/usr/bin/env python3
"""Appendix G figures in the charts.py language. Usage: app_G.py [name ...]

Data of record: tools/anon_viewer/public/data/index.json (the 372 graded
runs), the per-run records under data/runs/<id>.json.gz, and
~/sweeps/paper-table-2026-09-05/resolved_modes.json (modes, two relabel
passes applied). Rows follow the Appendix G order and MODE_COLOR."""
import collections
import gzip
import json
import os
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from charts import (FAINT, INK, LINE, LINE_STRONG, MID, MODE_COLOR, MUTED,  # noqa: E402
                    SANS, TRACK, X0, X1, head, line, page, rect, swatch, text)

DATA = pathlib.Path(os.path.expanduser("~/PyCharmProjects/reprocli/tools/anon_viewer/public/data"))
RESOLVED = pathlib.Path(os.path.expanduser("~/sweeps/paper-table-2026-09-05/resolved_modes.json"))

SLUGS = ["reproduced-clean", "near-miss-partial", "reimplement-without-validating",
         "environment-fights", "artifact-provenance-mismatch", "scope-substitution",
         "stale-artifact-reliance", "procrastination/wall-kill", "killed-before-the-number"]
NAMES = ["Reproduced", "Ran, outside tolerance", "Reimplemented but did not check the result",
         "Build and dependency failures", "Wrong artifact measured", "Wrong experiment",
         "Echoed a shipped number", "Never launched an experiment",
         "Failed before any number was produced"]
MODELS = [("dsv4", "DeepSeek-V4-Flash"), ("qwen3", "Qwen3.6-27B"),
          ("minimax", "MiniMax-M2.7"), ("muse", "Muse Spark 1.2")]
TIERS = [("run", "Run"), ("retrain", "Retrain"), ("reimplement", "Reimplement")]


def load():
    """Every graded run of index.json joined to its mode of record and to the
    rounds, grant, and spend the run record carries."""
    idx = json.load(open(DATA / "index.json"))
    res = json.load(open(RESOLVED))
    modes = {r["id"]: r for r in res["runs"]}
    runs = []
    for r in idx["runs"]:
        d = json.load(gzip.open(DATA / "runs" / f"{r['id']}.json.gz"))["run"]
        m = modes[r["id"]]
        assert m["mode"] in SLUGS, m["mode"]
        assert d["rounds"] == r["rounds"] and abs(d["spent_h100"] - m["spent_h100"]) < 1e-6
        runs.append({"id": r["id"], "model": d["model"], "tier": d["tier"], "mode": m["mode"],
                     "raw": m["raw_label"], "relabeled": m["relabeled"], "rounds": d["rounds"],
                     "budget": d["budget_h100"], "spent": d["spent_h100"]})
    assert len(runs) == 372 and len(modes) == 372
    return runs


def legend(b, y0, pitch=17):
    cols = [X0, 352]
    for i, name in enumerate(NAMES):
        cx = cols[0] if i < 5 else cols[1]
        y = y0 + (i if i < 5 else i - 5) * pitch
        b.append(swatch(cx, y - 8, MODE_COLOR[i]))
        b.append(text(cx + 15, y, name, 12, MID))
    return y0 + 5 * pitch


def stacked_bar(b, key, bx, y, bw, bh, counts, total):
    b.append(f'<clipPath id="clip{key}"><rect x="{bx}" y="{y}" width="{bw}" '
             f'height="{bh}" rx="4"/></clipPath><g clip-path="url(#clip{key})">')
    b.append(rect(bx, y, bw, bh, TRACK, 0))
    cx = bx
    for mi, n in enumerate(counts):
        w = bw * n / total
        if w > 0:
            b.append(rect(cx, y, w, bh, MODE_COLOR[mi], 0))
            if cx > bx and w >= 4:
                b.append(line(cx, y, cx, y + bh, "#FFFFFF", 1))
            s = str(n)
            if w >= 6.4 * len(s) + 10:
                b.append(text(cx + w / 2, y + bh / 2 + 4.2, s, 11.5, "#FFFFFF", SANS, 600,
                              "middle"))
        cx += w
    b.append("</g>")


# ============================================ fig: mode by agent and tier
def fig_agent_tier(runs):
    """Twelve normalized stacked bars, one per agent and tier, so the reader
    sees which modes concentrate where. Counts print inside segments wide
    enough to hold them; the row total is at the right."""
    ct = collections.Counter((r["model"], r["tier"], r["mode"]) for r in runs)
    b = head("primary failure mode by agent and tier", "share of the sweep's graded runs")
    top = legend(b, 58) + 8
    bx, bh, pitch, gap = 236, 16, 22, 12
    bw = X1 - bx - 58
    y = top
    for gi, (mk, mname) in enumerate(MODELS):
        if gi:
            b.append(line(X0, y - gap / 2, X1, y - gap / 2, LINE))
        b.append(text(X0, y + pitch + bh / 2 + 4.5, mname, 12.5, INK, SANS, 600))
        for ti, (tk, tname) in enumerate(TIERS):
            counts = [ct[(mk, tk, s)] for s in SLUGS]
            total = sum(counts)
            ry = y + ti * pitch
            b.append(text(bx - 10, ry + bh / 2 + 4.2, tname, 12, MUTED, SANS, 400, "end"))
            stacked_bar(b, f"{mk}{tk}", bx, ry, bw, bh, counts, total)
            b.append(text(bx + bw + 8, ry + bh / 2 + 4.2, f"{total} runs", 11.5, MUTED))
        y += 3 * pitch + gap
    page("app_G_agent_tier", b, y - gap + 12)


# ============================================ fig: rounds and spend at exit
def swarm(xs, r, lanes):
    """Beeswarm offsets: each dot takes the lane nearest the centre line in
    which it touches no dot already placed; x keeps its true value. When every
    lane is taken it goes to the lane where its nearest neighbour is farthest,
    so no dot ends up under another."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    placed, dy = [], [0.0] * len(xs)
    cand = [0.0]
    for k in range(1, lanes + 1):
        cand += [k * (2 * r + 0.3), -k * (2 * r + 0.3)]
    for i in order:
        x = xs[i]
        best, best_gap = cand[0], -1.0
        for c in cand:
            gap = min(((x - px) ** 2 + (c - py) ** 2 for px, py in placed),
                      default=(2 * r) ** 2)
            if gap >= (2 * r) ** 2:
                best = c
                break
            if gap > best_gap:
                best, best_gap = c, gap
        placed.append((x, best))
        dy[i] = best
    return dy


def strip_panel(b, px, pw, rows, vmax, ticks, top, pitch, unit, title, r=2.0):
    def X(v):
        return px + pw * min(v, vmax) / vmax
    bottom = top + len(rows) * pitch
    b.append(text(px, top - 10, title, 12, INK, SANS, 600))
    for t in ticks:
        b.append(line(X(t), top - 2, X(t), bottom, TRACK))
        b.append(text(X(t), bottom + 14, f"{t}{unit}", 11.5, FAINT, SANS, 400, "middle"))
    for ri, (vals, color) in enumerate(rows):
        cy = top + ri * pitch + pitch / 2
        xs = [X(v) for v in vals]
        for x, d in zip(xs, swarm(xs, r, 4)):
            b.append(f'<circle cx="{x:.1f}" cy="{cy + d:.1f}" r="{r}" fill="{color}" '
                     f'fill-opacity="0.85"/>')
        med = X(statistics.median(vals))
        b.append(line(med, cy - pitch / 2 + 2, med, cy + pitch / 2 - 2, INK, 1.6))


LABEL2 = {
    "Reimplemented but did not check the result": ["Reimplemented but did not", "check the result"],
    "Build and dependency failures": ["Build and dependency", "failures"],
    "Never launched an experiment": ["Never launched", "an experiment"],
    "Failed before any number was produced": ["Failed before any number", "was produced"],
}


def fig_exit(runs):
    """Two dot strips per mode, every graded run as one dot: the rounds the
    run used and the share of its H100 grant it had spent when it exited."""
    b = head("rounds used and grant spent at exit, by primary mode",
             "one dot per run; 372 graded runs")
    ky = 56
    b.append(line(X0 + 3, ky - 10, X0 + 3, ky + 1, INK, 1.6))
    b.append(text(X0 + 12, ky, "median of the mode", 12, MID))
    top, pitch = 84, 38
    lx = 186
    for i, name in enumerate(NAMES):
        cy = top + i * pitch + pitch / 2
        lines = LABEL2.get(name, [name])
        for k, s in enumerate(lines):
            dy = (k - (len(lines) - 1) / 2) * 13.5
            b.append(text(lx, cy + 4.2 + dy, s, 11.5, INK, SANS, 500, "end"))
        if i:
            b.append(line(X0, top + i * pitch, X1 - 14, top + i * pitch, TRACK))
    p1, pw1 = lx + 20, 172
    p2 = p1 + pw1 + 38
    pw2 = X1 - 14 - p2
    by_mode = [[r for r in runs if r["mode"] == s] for s in SLUGS]
    strip_panel(b, p1, pw1, [([r["rounds"] for r in rs], c) for rs, c in zip(by_mode, MODE_COLOR)],
                300, [0, 100, 200, 300], top, pitch, "", "rounds at exit")
    strip_panel(b, p2, pw2,
                [([100 * r["spent"] / r["budget"] for r in rs], c) for rs, c in zip(by_mode, MODE_COLOR)],
                100, [0, 25, 50, 75, 100], top, pitch, "%", "grant spent at exit")
    page("app_G_exit_by_mode", b, top + 9 * pitch + 30)


# ============================================ fig: the two relabel passes
def fig_relabel(runs):
    """A flow from the label each relabeled run carried to its mode of
    record, one ribbon per label and destination, width in runs."""
    rel = [r for r in runs if r["relabeled"]]
    assert len(rel) == 36
    flows = collections.Counter((r["raw"].replace("_", "-"), r["mode"]) for r in rel)
    left_tot = collections.Counter()
    for (raw, _), n in flows.items():
        left_tot[raw] += n
    right_tot = collections.Counter()
    for (_, mode), n in flows.items():
        right_tot[mode] += n

    def dominant(raw):
        best = max((n, -SLUGS.index(m)) for (rw, m), n in flows.items() if rw == raw)
        return -best[1]
    lefts = sorted(left_tot, key=lambda rw: (dominant(rw), -left_tot[rw], rw))

    b = head("the two relabel passes", "36 runs re-read against the definitions")
    b.append(text(X0, 58, "label the run carried", 12, INK, SANS, 600))
    b.append(text(X1, 58, "mode of record", 12, INK, SANS, 600, "end"))
    unit, gap = 6.0, 8.5
    top = 74
    lxn, rxn, nw = 240, 392, 7
    ly, lpos = top, {}
    for rw in lefts:
        h = unit * left_tot[rw]
        lpos[rw] = ly
        b.append(rect(lxn, ly, nw, h, LINE_STRONG, 1))
        b.append(text(lxn - 8, ly + h / 2 + 4.2, f"{rw}  {left_tot[rw]}", 11.5, MID, SANS, 400, "end"))
        ly += h + gap
    rgap = (ly - gap - top - unit * 36) / 8
    ry, rpos = top, {}
    for mi, s in enumerate(SLUGS):
        h = unit * right_tot[s]
        rpos[s] = ry
        b.append(rect(rxn, ry, nw, h, MODE_COLOR[mi], 1))
        b.append(text(rxn + nw + 8, ry + h / 2 + 4.2, NAMES[mi], 11.5, INK, SANS, 400))
        b.append(text(X1, ry + h / 2 + 4.2, str(right_tot[s]), 11.5, INK, SANS, 600, "end",
                      tnum=True))
        ry += h + rgap
    lcur = dict(lpos)
    rcur = dict(rpos)
    order = sorted(flows, key=lambda k: (lefts.index(k[0]), SLUGS.index(k[1])))
    ribbons = []
    for raw, mode in order:
        h = unit * flows[(raw, mode)]
        y0, y1 = lcur[raw], rcur[mode]
        lcur[raw] += h
        rcur[mode] += h
        ribbons.append((raw, mode, y0, y1, h))
    # right-side stacking in mode order of the left column keeps the ribbons
    # into one mode from crossing each other
    rcur = dict(rpos)
    for mi, s in enumerate(SLUGS):
        for k, (raw, mode, y0, y1, h) in enumerate(ribbons):
            if mode != s:
                continue
            ribbons[k] = (raw, mode, y0, rcur[s], h)
            rcur[s] += h
    xa, xb = lxn + nw, rxn
    mx = (xa + xb) / 2
    for raw, mode, y0, y1, h in ribbons:
        c = MODE_COLOR[SLUGS.index(mode)]
        b.append(f'<path d="M{xa},{y0:.1f} C{mx},{y0:.1f} {mx},{y1:.1f} {xb},{y1:.1f} '
                 f'L{xb},{y1 + h:.1f} C{mx},{y1 + h:.1f} {mx},{y0 + h:.1f} {xa},{y0 + h:.1f} Z" '
                 f'fill="{c}" fill-opacity="0.45"/>')
    page("app_G_relabel_flow", b, ly - gap + 16)


CHARTS = {
    "app_G_agent_tier": fig_agent_tier,
    "app_G_exit_by_mode": fig_exit,
    "app_G_relabel_flow": fig_relabel,
}

if __name__ == "__main__":
    runs = load()
    for n in sys.argv[1:] or CHARTS:
        CHARTS[n](runs)
