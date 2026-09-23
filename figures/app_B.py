#!/usr/bin/env python3
"""Appendix B resource-profile figures, in the charts.py language.

Numbers of record: tools/anon_viewer/public/data/index.json, the 372 graded
runs behind the Section 5 charts, one dot per run; every field is checked
against the run's own runs/<id>.json.gz record before drawing. Token rates
are the first-party list prices of ~/sweeps/cost-2026-09-07.py (pricefeed
snapshot 2026-08-17), asserted equal to that file when it is on disk, and GPU
time is priced at the $2 per H100-hour of Section 5.1.
Usage: app_B.py [name ...]"""
import ast
import gzip
import json
import math
import pathlib
import sys

FIGS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(FIGS))
from charts import (AGENT_COLOR, FAINT, INK, LINE, LINE_STRONG, MUTED, SANS,
                    TRACK, X0, X1, head, line, page, text)

DATA = pathlib.Path.home() / "PyCharmProjects/reprocli/tools/anon_viewer/public/data"
AGENTS = [("dsv4", "DeepSeek-V4-Flash"), ("qwen3", "Qwen3.6-27B"),
          ("minimax", "MiniMax-M2.7"), ("muse", "Muse Spark 1.2")]
# $ per million tokens: (uncached prompt, cached prompt, completion); None means
# the provider has no cache-read leg, so every prompt token is billed uncached.
PRICE = {
    "dsv4": (0.14, 0.0028, 0.28),
    "qwen3": (0.45, None, 2.70),
    "minimax": (0.30, 0.06, 1.20),
    "muse": (1.25, 0.15, 4.25),
}
GPU = 2.0


def check_rates():
    src = pathlib.Path.home() / "sweeps" / "cost-2026-09-07.py"
    if not src.exists():
        return
    for node in ast.parse(src.read_text()).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "PRICE":
            got = {k: v[:3] for k, v in ast.literal_eval(node.value).items()}
            assert got == PRICE, f"rates drifted from {src}"
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "GPU":
            assert ast.literal_eval(node.value) == GPU, f"GPU rate drifted from {src}"


def load_runs():
    runs = json.loads((DATA / "index.json").read_text())["runs"]
    assert len(runs) == 372, len(runs)
    for r in runs:
        rec = json.load(gzip.open(DATA / "runs" / f"{r['id']}.json.gz"))["run"]
        for k in ("arxiv_id", "model", "tier", "rounds", "duration_s", "spent_h100", "tokens"):
            assert rec[k] == r[k], (r["id"], k)
    return runs


def token_cost(r):
    pin, pc, pout = PRICE[r["model"]]
    t = r["tokens"]
    cached = t["cached"] if pc is not None else 0
    return ((t["prompt"] - cached) * pin + cached * (pc or 0) + t["completion"] * pout) / 1e6


def median(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


# ------------------------------------------------------------- swarm marks
# Every dot is a run and no two dots overlap: centers sit at least 2R apart
# inside a row, rows are 4px clear of each other, and both are asserted.
R = 1.8
STEP = 2 * R + 0.2
CLEAR = 4.0
CENTERS = []


def swarm(xs, max_dy):
    """Beeswarm offsets: dots placed in x order, each at the smallest |dy| that
    clears every dot already placed (candidates are the axis and the tangent
    positions against each neighbour), so density reads as height. A dot with
    no clear slot inside the band is a fallback, and the caller asserts none."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    placed, out, fallbacks = [], [0.0] * len(xs), 0
    for i in order:
        x = xs[i]
        near = [(px, pdy) for px, pdy in placed if abs(px - x) < STEP]
        cands = [0.0]
        for px, pdy in near:
            h = math.sqrt(max(STEP * STEP - (px - x) ** 2, 0.0)) + 1e-6
            cands += [pdy + h, pdy - h]
        cands = sorted((c for c in cands if abs(c) <= max_dy), key=lambda c: (abs(c), c))

        def gap(c):
            return min([math.hypot(px - x, pdy - c) for px, pdy in near] or [1e9])
        dy = next((c for c in cands if gap(c) >= STEP - 1e-6), None)
        if dy is None:
            dy = max([0.0, max_dy, -max_dy] + cands, key=gap)
            fallbacks += 1
        placed.append((x, dy))
        out[i] = dy
    return out, fallbacks


def band(xs):
    """Smallest half-height (0.5px steps) at which the swarm places every dot."""
    for k in range(0, 200):
        if swarm(xs, k * 0.5)[1] == 0:
            return k * 0.5
    raise AssertionError("no band fits")


def mark(x, y, color):
    CENTERS.append((x, y))
    return (f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{R}" fill="{color}" '
            f'stroke="#FFFFFF" stroke-width="0.7"/>')


def check_marks():
    pts = sorted(CENTERS)
    worst = 1e9
    for i, (x, y) in enumerate(pts):
        for x2, y2 in pts[i + 1:]:
            if x2 - x >= 2 * R:
                break
            worst = min(worst, math.hypot(x2 - x, y2 - y))
    assert worst >= 2 * R, f"dot centers {worst:.2f}px apart, under {2 * R}"
    CENTERS.clear()
    return worst


def median_tick(b, x, cy, h=13):
    b.append(line(x, cy - h / 2, x, cy + h / 2, "#FFFFFF", 4))
    b.append(line(x, cy - h / 2, x, cy + h / 2, INK, 1.6))


def positions(px, pw, lo, hi, vals):
    return [px + pw * (math.log10(v) - lo) / (hi - lo) for v in vals]


def strip(b, xs, cy, color, max_dy, mx):
    """One beeswarm row, the median ticked at mx."""
    dys, fallbacks = swarm(xs, max_dy)
    assert fallbacks == 0, fallbacks
    for x, dy in zip(xs, dys):
        b.append(mark(x, cy + dy, color))
    median_tick(b, mx, cy)


def log_axis(b, px, pw, lo, hi, top, bottom, ticks, label):
    for v, s in ticks:
        x = px + pw * (math.log10(v) - lo) / (hi - lo)
        b.append(line(x, top, x, bottom, TRACK))
        b.append(text(x, bottom + 15, s, 11.5, FAINT, SANS, 400, "middle"))
    b.append(line(px, bottom + 0.5, px + pw, bottom + 0.5, LINE))
    if label:
        b.append(text(px + pw / 2, bottom + 33, label, 11.5, MUTED, SANS, 400, "middle"))


def fmt_tokens(v):
    if v >= 1e6:
        return f"{v / 1e6:.1f}M"
    if v >= 1e3:
        return f"{v / 1e3:.0f}k"
    return f"{v:.0f}"


# ============================================ fig: tokens per run by agent
# Three rows per agent on one shared log axis, so completion sits about 1.6 to
# 1.9 decades below prompt at the median, narrowest for Muse Spark 1.2, and
# cached prompt reads as most of the prompt for the three agents that cache.
# Each row is a rug with one tick per run, a bar over the middle half of runs,
# and the median, all centered on the row's one baseline.
KINDS = [("prompt", "prompt"), ("cached", "cached"), ("completion", "completion")]
RUG_OPACITY = 0.45   # the dial: 0.45 loud, 0.25 quiet, 0 leaves only the bar and median
PITCH, HEAD_GAP = 18, 28
TOK_Y = []


def quantile(s, q):
    i = (len(s) - 1) * q
    lo_i = math.floor(i)
    hi_i = min(lo_i + 1, len(s) - 1)
    return s[lo_i] + (s[hi_i] - s[lo_i]) * (i - lo_i)


def rug_row(b, xs, cy, color):
    TOK_Y.append((cy, cy))
    if RUG_OPACITY <= 0:
        return
    for x in xs:
        b.append(f'<line x1="{x:.2f}" y1="{cy - 5:.2f}" x2="{x:.2f}" y2="{cy + 5:.2f}" '
                 f'stroke="{color}" stroke-width="0.9" stroke-opacity="{RUG_OPACITY}"/>')


def iqr_bar(b, x25, x75, cy, color):
    y = cy - 1.75
    TOK_Y.append((y + 1.75, cy))
    b.append(f'<rect x="{x25:.2f}" y="{y:.2f}" width="{x75 - x25:.2f}" height="3.5" '
             f'fill="{color}"/>')


def tok_median(b, x, cy):
    TOK_Y.append(((cy - 5.5 + cy + 5.5) / 2, cy))
    b.append(f'<line x1="{x:.2f}" y1="{cy - 5.5:.2f}" x2="{x:.2f}" y2="{cy + 5.5:.2f}" '
             f'stroke="#FFFFFF" stroke-width="3.2"/>')
    b.append(f'<line x1="{x:.2f}" y1="{cy - 5.5:.2f}" x2="{x:.2f}" y2="{cy + 5.5:.2f}" '
             f'stroke="{INK}" stroke-width="1.6"/>')


def name_width(s):
    from PIL import ImageFont
    return ImageFont.truetype(str(FIGS / "fonts/ttf/Inter-SemiBold.ttf"), 12).getlength(s)


def fig_tokens(runs):
    b = head("tokens per run by agent", "372 graded runs")
    px, pw, lo, hi = 92, 510, 3.4, 8.0
    ticks = [(1e4, "10k"), (1e5, "100k"), (1e6, "1M"), (1e7, "10M"), (1e8, "100M")]
    b.append(text(X1, 54, "median", 11.5, MUTED, SANS, 600, "end"))
    x10k = positions(px, pw, lo, hi, [ticks[0][0]])[0]
    cy, blocks, rows_cy = 50, [], []
    for i, (key, name) in enumerate(AGENTS):
        if i:
            cy += HEAD_GAP
        rs = [r for r in runs if r["model"] == key]
        c = AGENT_COLOR[name]
        b.append(text(X0, cy + 4, name, 12, c, SANS, 600))
        b.append(text(X0 + name_width(name) + 8, cy + 4, f"{len(rs)} runs", 11.5, FAINT))
        first = cy + PITCH
        for field, label in KINDS:
            cy += PITCH
            rows_cy.append(cy)
            vals = sorted(r["tokens"][field] for r in rs)
            b.append(text(px - 10, cy + 4, label, 11.5, MUTED, SANS, 400, "end"))
            if max(vals) == 0:
                # the note starts 8px right of the first gridline so no line crosses it
                b.append(text(x10k + 8, cy + 4, "not reported", 11.5, FAINT))
                b.append(text(X1, cy + 4, "\u2013", 11.5, FAINT, SANS, 400, "end"))
                continue
            assert 10 ** lo < vals[0] and vals[-1] < 10 ** hi, (name, field, vals[0], vals[-1])
            xs = positions(px, pw, lo, hi, vals)
            x25, x75, xm = positions(px, pw, lo, hi, [quantile(vals, 0.25),
                                                       quantile(vals, 0.75), median(vals)])
            rug_row(b, xs, cy, c)
            iqr_bar(b, x25, x75, cy, c)
            tok_median(b, xm, cy)
            b.append(text(X1, cy + 4, fmt_tokens(median(vals)), 11.5, INK, SANS, 600,
                          "end", tnum=True))
        blocks.append((first - 9, cy + 9))
    assert all(abs(y - c) < 1e-6 for y, c in TOK_Y), TOK_Y
    TOK_Y.clear()
    bottom = cy + 11
    grid = []  # gridlines go under the marks, broken at the agent headers
    for top, bot in blocks[:-1]:
        for v, _ in ticks:
            x = positions(px, pw, lo, hi, [v])[0]
            grid.append(line(x, top, x, bot, TRACK))
    log_axis(grid, px, pw, lo, hi, blocks[-1][0], bottom, ticks, "tokens per run, log scale")
    b[1:1] = grid
    print("app_B_tokens: row cy", [round(y, 1) for y in rows_cy])
    page("app_B_tokens", b, math.ceil(bottom + 46))


# ================================================= fig: cost per run by agent
# Left: total cost per run (tokens at the provider rate plus GPU time at $2 per
# H100-hour). Right: token cost over GPU cost per run, with the parity line at
# 1 (dashed) and, over the runs that have a ratio, a count of those on the token
# side. One row pitch for all four agents, sized to the densest swarm.
def fig_cost(runs):
    b = head("cost per run by agent",
             "372 graded runs; tokens at provider rates, GPU time at $2 per H100-hour")
    lx, lw, llo, lhi = 146, 156, -2.0, 2.0
    rx, rw, rlo, rhi = 346, 250, -3.0, 2.0
    hy, top = 62, 72
    rows = []
    for key, name in AGENTS:
        rs = [r for r in runs if r["model"] == key]
        tok = [token_cost(r) for r in rs]
        gpu = [r["spent_h100"] * GPU for r in rs]
        total = [a + g for a, g in zip(tok, gpu)]
        ratio = [a / g for a, g in zip(tok, gpu) if g > 0]
        omitted = [r for r, g in zip(rs, gpu) if g == 0]
        lxs = positions(lx, lw, llo, lhi, total)
        rxs = positions(rx, rw, rlo, rhi, ratio)
        rows.append((name, rs, total, ratio, omitted, lxs, rxs, max(band(lxs), band(rxs))))
    half = max(row[-1] for row in rows)
    pitch = 2 * half + 2 * R + CLEAR
    bottom = top + 4 * pitch
    b.append(text(lx, hy, "total cost per run", 12, INK, SANS, 600))
    b.append(text(rx, hy, "token cost over GPU cost", 12, INK, SANS, 600))
    b.append(text(X1, hy, "tokens cost more", 11.5, MUTED, SANS, 600, "end"))
    grid = []
    log_axis(grid, lx, lw, llo, lhi, top - 2, bottom,
             [(0.01, "$0.01"), (0.1, "$0.10"), (1, "$1"), (10, "$10"), (100, "$100")], "")
    log_axis(grid, rx, rw, rlo, rhi, top - 2, bottom,
             [(0.001, "0.001"), (0.01, "0.01"), (0.1, "0.1"), (1, "1"), (10, "10"),
              (100, "100")], "")
    xp = rx + rw * (0 - rlo) / (rhi - rlo)
    grid.append(line(xp, top - 2, xp, bottom, LINE_STRONG, 1.2, "4 3"))
    b[1:1] = grid
    skipped = []
    for i, (name, rs, total, ratio, omitted, lxs, rxs, _) in enumerate(rows):
        c = AGENT_COLOR[name]
        cy = top + i * pitch + pitch / 2
        b.append(text(X0, cy + 4, name, 12, INK, SANS, 600))
        strip(b, lxs, cy, c, half, positions(lx, lw, llo, lhi, [median(total)])[0])
        strip(b, rxs, cy, c, half, positions(rx, rw, rlo, rhi, [median(ratio)])[0])
        over = sum(v > 1 for v in ratio)
        b.append(text(X1, cy + 4, f"{over} of {len(ratio)}", 11.5, INK, SANS, 600, "end",
                      tnum=True))
        skipped += [(name, r["arxiv_id"]) for r in omitted]
    # axis titles sit 33px under the axis, the log_axis offset, so the tick row
    # keeps 4px of clearance in both figures
    b.append(text(lx + lw / 2, bottom + 33, "dollars per run, log scale", 11.5, MUTED, SANS,
                  400, "middle"))
    b.append(text(rx, bottom + 33, "GPU side", 11.5, MUTED))
    b.append(text(rx + rw, bottom + 33, "token side", 11.5, MUTED, SANS, 400, "end"))
    assert skipped == [("MiniMax-M2.7", "2505.18809")], skipped
    b.append(text(X0, bottom + 53,
                  f"one {skipped[0][0]} run ({skipped[0][1]}) spent no GPU time, so it "
                  "has a total cost at left and no ratio or count at right", 11.5, FAINT))
    print(f"app_B_cost: closest dot centers {check_marks():.2f}px, row pitch {pitch:.1f}px")
    page("app_B_cost", b, math.ceil(bottom + 65))


CHARTS = {"app_B_tokens": fig_tokens, "app_B_cost": fig_cost}

if __name__ == "__main__":
    check_rates()
    RUNS = load_runs()
    for n in sys.argv[1:] or CHARTS:
        CHARTS[n](RUNS)
