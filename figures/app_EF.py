#!/usr/bin/env python3
"""Appendix E figures on the composition of the 100 evaluation papers.

Reads the frozen eval split (outputs/v6/app_rebuild/eval_100.jsonl, the same
source as tables/gen_eval100.py) and writes two standalone charts in the
charts.py language:
  app_EF_compute_strip   one dot per paper, audited H100-hours by tier
  app_EF_arxiv_months    papers per arXiv month, stacked by tier
Usage: app_EF.py [name ...]; override the lockfile with RECLAIM_LOCKFILE_DIR.
"""
import json
import math
import os
import pathlib
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from charts import (X0, X1, INK, MID, MUTED, FAINT, LINE, LINE_STRONG, TRACK,
                    SANS, TIER_COLOR, head, text, rect, line, swatch, page)

HERE = pathlib.Path(__file__).resolve()
CANDIDATES = [
    pathlib.Path(os.environ["RECLAIM_LOCKFILE_DIR"]) if "RECLAIM_LOCKFILE_DIR" in os.environ else None,
    HERE.parents[2] / "outputs" / "v6" / "app_rebuild",
    pathlib.Path.home() / "PyCharmProjects" / "reprocli" / "outputs" / "v6" / "app_rebuild",
]
EVAL = next(d / "eval_100.jsonl" for d in CANDIDATES if d and (d / "eval_100.jsonl").exists())

TIERS = [("Easy", "Run"), ("Medium", "Retrain"), ("Hard", "Reimplement")]
ROWS = [json.loads(l) for l in EVAL.read_text(encoding="utf-8").splitlines() if l.strip()]
assert len(ROWS) == 100, len(ROWS)


def by_tier(key):
    return [[key(r) for r in ROWS if r["tier"] == t] for t, _ in TIERS]


def swarm(xs, d):
    """Beeswarm offsets: place dots in x order at the smallest |dy| that keeps
    every pair at least d apart, in half steps so columns interlock."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    placed, dys = [], [0.0] * len(xs)
    for i in order:
        x = xs[i]
        for step in range(0, 60):
            found = None
            for sign in (1, -1):
                dy = sign * step * d / 2
                if all((x - px) ** 2 + (dy - py) ** 2 >= d * d - 1e-6 for px, py in placed):
                    found = dy
                    break
            if found is not None:
                break
        placed.append((x, found))
        dys[i] = found
    return dys


# ======================================= fig: audited compute, one dot per paper
FLOOR, CEIL = 0.01, 100.0
BANDS = [8, 32, 96]


def fig_compute_strip():
    b = head("audited compute of the 100 evaluation papers by tier",
             "one dot per paper; bar at the tier median")
    hours = by_tier(lambda r: r["audited_h100_hours"])
    px, slot_w, gap = 118, 26, 18
    lx0, lx1 = px + slot_w + gap, X1 - 6
    slot_cx = px + slot_w / 2

    def X(h):
        return lx0 + (lx1 - lx0) * (math.log10(h) - math.log10(FLOOR)) / (math.log10(CEIL) - math.log10(FLOOR))

    top, pitch, r = 76, 66, 3.5
    d = 2 * r + 1.2
    bottom = top + 3 * pitch
    # band labels above the rows, boundaries as strong lines, decades faint
    # the first span starts at the slot, since papers under the floor are in band 0 to 8
    edges = [px] + [X(v) for v in BANDS]
    for i, name in enumerate(["0 to 8", "8 to 32", "32 to 96"]):
        b.append(text((edges[i] + edges[i + 1]) / 2, top - 10, name, 11.5, MUTED, SANS, 500, "middle"))
    b.append(text(X0, top - 10, "band", 11.5, MUTED, SANS, 500))
    for v in (FLOOR, 0.1, 1):
        b.append(line(X(v), top - 2, X(v), bottom, TRACK))
    for v in BANDS:
        b.append(line(X(v), top - 2, X(v), bottom, LINE_STRONG))
    b.append(line(slot_cx, top - 2, slot_cx, bottom, TRACK, 1, "2 3"))
    b.append(line(px, bottom + 0.5, lx1, bottom + 0.5, LINE))
    for (tier, label), vals, color in zip(TIERS, hours, TIER_COLOR):
        y = top + TIERS.index((tier, label)) * pitch
        cy = y + pitch / 2
        b.append(text(X0, cy - 1, label, 12.5, INK, SANS, 600))
        b.append(text(X0, cy + 13, f"{len(vals)} papers", 11.5, MUTED))
        if label != "Reimplement":
            b.append(line(px, y + pitch, lx1, y + pitch, TRACK))
        med = sorted(vals)[len(vals) // 2] if len(vals) % 2 else (
            sorted(vals)[len(vals) // 2 - 1] + sorted(vals)[len(vals) // 2]) / 2
        mx = slot_cx if med < FLOOR else X(med)
        b.append(rect(mx - 1.2, y + 5, 2.4, pitch - 10, MID, 1))
        low = [h for h in vals if h < FLOOR]
        high = [h for h in vals if h >= FLOOR]
        for k, _ in enumerate(low):
            b.append(f'<circle cx="{slot_cx:.1f}" cy="{cy + (k - (len(low) - 1) / 2) * d:.1f}" '
                     f'r="{r}" fill="{color}" stroke="#FFFFFF" stroke-width="1.2"/>')
        xs = [X(h) for h in high]
        for x, dy in zip(xs, swarm(xs, d)):
            b.append(f'<circle cx="{x:.1f}" cy="{cy + dy:.1f}" r="{r}" fill="{color}" '
                     f'stroke="#FFFFFF" stroke-width="1.2"/>')
    ay = bottom + 16
    b.append(text(slot_cx, ay, f"<{FLOOR:g}", 11.5, MUTED, SANS, 400, "middle"))
    for v, s in ((0.1, "0.1"), (1, "1")):
        b.append(text(X(v), ay, s, 11.5, FAINT, SANS, 400, "middle"))
    for v in BANDS:
        b.append(text(X(v), ay, str(v), 11.5, INK, SANS, 600, "middle"))
    b.append(text((lx0 + lx1) / 2, ay + 16, "audited H100-hours, log scale", 11.5, MUTED, SANS, 400, "middle"))
    page("app_EF_compute_strip", b, ay + 30)


# ============================================ fig: papers per arXiv month
def fig_arxiv_months():
    b = head("arXiv posting month of the 100 evaluation papers",
             "month from the arXiv identifier, stacked by tier")
    counts = Counter((r["custom_id"][:4], r["tier"]) for r in ROWS)
    months = sorted({r["custom_id"][:4] for r in ROWS})
    first, last = months[0], months[-1]
    y0, m0 = 2000 + int(first[:2]), int(first[2:])
    y1, m1 = 2000 + int(last[:2]), int(last[2:])
    keys = []
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        keys.append(f"{y - 2000:02d}{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    for kx, (tier, label), color in zip((X0, X0 + 62, X0 + 144), TIERS, TIER_COLOR):
        b.append(swatch(kx, 48, color))
        b.append(text(kx + 15, 56, label, 12, MID))
    top, ph = 84, 118
    slot = (X1 - X0) / len(keys)
    bw = slot - 5
    ymax = max(sum(counts[(k, t)] for t, _ in TIERS) for k in keys)
    base = top + ph
    for i, k in enumerate(keys):
        x = X0 + i * slot + (slot - bw) / 2
        yy = base
        total = 0
        for (tier, _), color in zip(TIERS, TIER_COLOR):
            n = counts[(k, tier)]
            if not n:
                continue
            h = ph * n / ymax
            yy -= h
            b.append(rect(x, yy, bw, h, color, 0))
            if total:
                b.append(line(x, yy + h, x + bw, yy + h, "#FFFFFF", 1))
            total += n
        if total:
            b.append(text(x + bw / 2, yy - 5, str(total), 11.5, INK, SANS, 600, "middle"))
        mm = int(k[2:])
        if mm in (1, 4, 7, 10):
            b.append(text(x + bw / 2, base + 15, ["Jan", "Apr", "Jul", "Oct"][(mm - 1) // 3],
                          11.5, FAINT, SANS, 400, "middle"))
        if mm == 1 and i:
            b.append(line(X0 + i * slot, base - ph - 4, X0 + i * slot, base + 30, LINE, 1, "2 3"))
    b.append(line(X0, base + 0.5, X1, base + 0.5, LINE))
    years = sorted({k[:2] for k in keys})
    for yr in years:
        idx = [i for i, k in enumerate(keys) if k[:2] == yr]
        cx = X0 + (idx[0] + idx[-1] + 1) / 2 * slot
        b.append(text(cx, base + 31, f"20{yr}", 12, INK, SANS, 600, "middle"))
    page("app_EF_arxiv_months", b, base + 44)


CHARTS = {
    "app_EF_compute_strip": fig_compute_strip,
    "app_EF_arxiv_months": fig_arxiv_months,
}

if __name__ == "__main__":
    for n in sys.argv[1:] or CHARTS:
        CHARTS[n]()
