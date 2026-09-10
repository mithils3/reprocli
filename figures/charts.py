#!/usr/bin/env python3
"""The data charts of Section 5 and Appendix C, as standalone HTML+SVG.

One chart language, shared with the reviewer viewer: no frame, a Fraunces title with a muted Inter subtitle at the right,
Inter with tabular numerals for every label, and the viewer's light palette
in which sage green always means reproduced. The canvas is 680px wide and is
printed at the 5.5in text width, so one px is 0.58pt and the smallest label
(11.5px) prints at 6.7pt. Regenerate with build.py, then check with audit.py.
Usage: charts.py [name ...]"""
import pathlib
import sys

OUT = pathlib.Path(__file__).parent
W = 680
X0, X1 = 22, W - 22          # inner left and right edges

# --------------------------------------------------------------- palette
GREEN = "#4F8A5B"    # reproduced
AMBER = "#B8740C"    # ran, outside tolerance
ROSE = "#C13B54"     # reimplemented without checking
TEAL = "#0F7D74"     # build and dependency failures
VIOLET = "#7548C4"   # wrong artifact measured
CLAY = "#C15F3C"     # wrong experiment
BLUE = "#2F6FC4"     # echoed a shipped number
MAGENTA = "#B23E90"  # never launched
SLATE = "#5F6B7A"    # failed before any number

MODE_COLOR = [GREEN, AMBER, ROSE, TEAL, VIOLET, CLAY, BLUE, MAGENTA, SLATE]

AGENT_COLOR = {
    "DeepSeek-V4-Flash": BLUE,
    "Qwen3.6-27B": VIOLET,
    "MiniMax-M2.7": CLAY,
    "Muse Spark 1.2": TEAL,
    "All agents": SLATE,
}

INK = "#1A1915"
MID = "#3D3B34"
MUTED = "#6B665A"
FAINT = "#938D7E"
LINE = "#DAD5C6"
LINE_STRONG = "#C7C0AD"
TRACK = "#EAE6DA"
SANS = "InterF, sans-serif"
SERIF = "FrauncesF, serif"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=12, fill=INK, family=SANS, weight=400, anchor="start",
         halo=False, tnum=False):
    """Tabular numerals are opt-in, for right-aligned count columns only:
    Inter's tnum feature also widens the hyphen and opens pairs like 47."""
    h = ' stroke="#FFFFFF" stroke-width="3.5" paint-order="stroke"' if halo else ""
    cls = ' class="n"' if tnum else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{h}{cls}>{esc(s)}</text>'
    )


def rect(x, y, w, h, fill, r=2):
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(w, 0):.2f}" height="{h:.2f}" '
        f'rx="{r}" fill="{fill}"/>'
    )


def line(x1, y1, x2, y2, color=LINE, wdt=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="{wdt}"{d}/>'
    )


def dot(x, y, color, r=3):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}"/>'


def head(title, sub=""):
    out = [text(X0, 31, title, 15, INK, SERIF, 600)]
    if sub:
        out.append(text(X1, 31, sub, 11.5, MUTED, SANS, 400, "end"))
    return out


def swatch(x, y, color):
    return rect(x, y, 9, 9, color, 2)


def declutter(rows, gap):
    """rows: list of (pos, payload). Push overlapping positions apart, 1-D."""
    ys = [r[0] for r in rows]
    order = sorted(range(len(rows)), key=lambda i: ys[i])
    v = [ys[i] for i in order]
    for _ in range(120):
        moved = False
        for i in range(len(v) - 1):
            d = v[i + 1] - v[i]
            if d < gap:
                v[i] -= (gap - d) / 2
                v[i + 1] += (gap - d) / 2
                moved = True
        if not moved:
            break
    out = list(rows)
    for slot, i in enumerate(order):
        out[i] = (v[slot], rows[i][1])
    return out


CROP, TOP_CROP, BOT_CROP = 14, 12, 6   # trim the margin the card used to fill


def page(name, body, height):
    vw, vh = W - 2 * CROP, height - TOP_CROP - BOT_CROP
    css = """
@font-face { font-family: 'InterF'; src: url('fonts/ttf/Inter-Regular.ttf'); font-weight: 400; }
@font-face { font-family: 'InterF'; src: url('fonts/ttf/Inter-Medium.ttf'); font-weight: 500; }
@font-face { font-family: 'InterF'; src: url('fonts/ttf/Inter-SemiBold.ttf'); font-weight: 600; }
@font-face { font-family: 'FrauncesF'; src: url('fonts/ttf/Fraunces-VF.ttf'); font-weight: 100 900; }
* { margin: 0; padding: 0; }
html { width: %dpx; }
body { width: %dpx; background: #fff; }
svg { display: block; }
text { font-optical-sizing: auto; text-rendering: geometricPrecision; }
text.n { font-variant-numeric: tabular-nums; }
""" % (vw, vw)
    html = (
        '<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n<style>'
        f"{css}</style>\n</head>\n<body>\n"
        f'<svg width="{vw}" height="{vh}" viewBox="{CROP} {TOP_CROP} {vw} {vh}">\n'
        + "\n".join(body)
        + "\n</svg>\n</body>\n</html>\n"
    )
    (OUT / f"{name}.html").write_text(html)
    print(f"wrote {name}.html  {vw}x{vh}")


# ============================================ fig: results by agent and tier
# numbers of record (2026-09-05): tools/anon_viewer/public/data/index.json
# 2026-09-10: all 400 agent-paper cells; the 28 cells without a graded run count
# as failures at score 0 (three at their pinned grade), see tab:missing-cells.
# grant spent = 100 * sum(spent_h100) / sum(budget_h100) over the agent's cells.
RESULTS = [
    ("DeepSeek-V4-Flash", [(14, 34), (9, 33), (4, 33)], [5.29, 5.45, 4.64], 26.2),
    ("Qwen3.6-27B", [(5, 34), (6, 33), (2, 33)], [3.91, 3.58, 3.03], 15.6),
    ("MiniMax-M2.7", [(3, 34), (5, 33), (2, 33)], [3.09, 3.30, 2.70], 10.4),
    ("Muse Spark 1.2", [(9, 34), (9, 33), (5, 33)], [5.47, 5.85, 3.67], 21.8),
    ("All agents", [(31, 136), (29, 132), (13, 132)], [4.44, 4.55, 3.51], 18.5),
]
TIERS = ["Run", "Retrain", "Reimplement"]


TIER_COLOR = [GREEN, AMBER, ROSE]   # Run, Retrain, Reimplement: the viewer's tier chips


def tier_dot(x, y, color):
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="{color}" '
            f'stroke="#FFFFFF" stroke-width="1.6"/>')


def spread(xs, gap=14, step=6.0):
    """Vertical offsets for dots whose x positions collide, so every tier
    stays visible while x keeps its true value."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    groups, cur = [], [order[0]]
    for i in order[1:]:
        if xs[i] - xs[cur[-1]] < gap:
            cur.append(i)
        else:
            groups.append(cur)
            cur = [i]
    groups.append(cur)
    dy = [0.0] * len(xs)
    for g in groups:
        for k, i in enumerate(g):
            dy[i] = (k - (len(g) - 1) / 2) * 2 * step
    return dy


def dot_panel(b, px, pw, rows, vmax, ticks, top, pitch, unit):
    """One dot-plot panel: a row per agent, one dot per tier on a shared axis,
    the three dots joined by a hairline so the spread reads at a glance."""
    def X(v):
        return px + pw * v / vmax
    bottom = rows[-1][0] + pitch - 6
    for t in ticks:
        b.append(line(X(t), top - 4, X(t), bottom, TRACK))
        b.append(text(X(t), bottom + 14, f"{t}{unit}", 11, FAINT, SANS, 400, "middle"))
    for y, vals in rows:
        cy = y + pitch / 2 - 3
        xs = [X(v) for v in vals]
        dys = spread(xs)
        pts = sorted(zip(xs, dys))
        if pts[-1][0] - pts[0][0] >= 12:
            path = " ".join(f"{x:.1f},{cy + dy:.1f}" for x, dy in pts)
            b.append(f'<polyline points="{path}" fill="none" stroke="{LINE_STRONG}" '
                     f'stroke-width="1.5" stroke-linejoin="round"/>')
        for x, dy, c in zip(xs, dys, TIER_COLOR):
            b.append(tier_dot(x, cy + dy, c))


def fig_results():
    """Two dot-plot panels, reproduction rate and mean audit score, one row per
    agent and one dot per tier, plus a strip for the share of the grant spent.
    The exact values are in the appendix results table."""
    b = head("reproduction rate and audit score by agent and tier", "400 agent-paper cells")
    ky = 56
    for x, tier, c in zip((X0, X0 + 60, X0 + 140), TIERS, TIER_COLOR):
        b.append(tier_dot(x + 4, ky - 4, c))
        b.append(text(x + 14, ky, tier, 12, MID))
    p1, p2, pw = 160, 384, 176
    gx = 574
    hy = 78
    b.append(text(p1, hy, "reproduced, % of cells", 12, INK, SANS, 600))
    b.append(text(p2, hy, "mean audit score", 12, INK, SANS, 600))
    b.append(text(gx, hy, "grant spent", 12, INK, SANS, 600))

    top, pitch = 88, 26
    rows = []
    for gi, (agent, repro, score, spent) in enumerate(RESULTS):
        y = top + gi * pitch + (8 if agent == "All agents" else 0)
        rows.append((y, agent, repro, score, spent))
    for y, agent, repro, score, spent in rows:
        total = agent == "All agents"
        ink = MUTED if total else INK
        cy = y + pitch / 2 - 3
        if total:
            b.append(line(X0, y - 6, X1, y - 6, LINE_STRONG))
        b.append(text(X0, cy + 4.5, agent, 12, ink, SANS, 600))
        b.append(rect(gx, cy - 2, 40, 4, TRACK, 2))
        b.append(rect(gx, cy - 2, 40 * spent / 100, 4, SLATE, 1))
        b.append(text(gx + 50, cy + 4.5, f"{spent:.1f}%", 11.5, ink, SANS, 600))
    dot_panel(b, p1, pw, [(y, [100 * n / d for n, d in r]) for y, _, r, _, _ in rows],
              50, [0, 10, 20, 30, 40, 50], top, pitch, "%")
    dot_panel(b, p2, pw, [(y, sc) for y, _, _, sc, _ in rows],
              8, [0, 2, 4, 6, 8], top, pitch, "")
    page("results_by_tier", b, rows[-1][0] + pitch + 22)


# ============================================== fig: failure modes by tier
# numbers of record (2026-09-05): ~/sweeps/paper-table-2026-09-05/
# resolved_modes.json; rows in the order of Appendix G.
MODES = [
    ("Reproduced", 30, 29, 13, 72),
    ("Ran, outside tolerance", 24, 37, 15, 76),
    ("Reimplemented but did not check the result", 14, 11, 38, 63),
    ("Build and dependency failures", 13, 6, 5, 24),
    ("Wrong artifact measured", 18, 9, 11, 38),
    ("Wrong experiment", 8, 14, 24, 46),
    ("Echoed a shipped number", 7, 2, 0, 9),
    ("Never launched an experiment", 1, 2, 10, 13),
    ("Failed before any number was produced", 14, 8, 9, 31),
]
STACKS = [("Run", 1, 129), ("Retrain", 2, 118), ("Reimplement", 3, 125),
          ("All agents", 4, 372)]


def fig_modes():
    """A legend that doubles as the all-tier count table, then one stacked
    bar per tier with the count printed inside every segment wide enough to
    hold it, and an all-agents bar ruled off below."""
    b = head("primary failure mode by tier", "one primary mode per run; 372 graded runs")
    cols = [(X0, 330), (352, X1)]
    ly, lp = 58, 17
    for i, mode in enumerate(MODES):
        cx, cend = cols[0] if i < 5 else cols[1]
        y = ly + (i if i < 5 else i - 5) * lp
        b.append(swatch(cx, y - 8, MODE_COLOR[i]))
        b.append(text(cx + 15, y, mode[0], 12, MID))
        b.append(text(cend, y, str(mode[4]), 12, INK, SANS, 600, "end", tnum=True))

    top, bx, bw, bh, pitch = ly + 5 * lp + 10, 130, 470, 18, 27
    for si, (label, idx, total) in enumerate(STACKS):
        y = top + si * pitch
        if label == "All agents":
            y += 8
            b.append(line(X0, y - 8.5, X1, y - 8.5, LINE_STRONG))
        b.append(text(bx - 12, y + 13, label, 12.5, MUTED if idx == 4 else INK,
                      SANS, 600, "end"))
        b.append(f'<clipPath id="clip{si}"><rect x="{bx}" y="{y}" width="{bw}" '
                 f'height="{bh}" rx="4"/></clipPath><g clip-path="url(#clip{si})">')
        b.append(rect(bx, y, bw, bh, TRACK, 0))
        cx = bx
        for mi, mode in enumerate(MODES):
            w = bw * mode[idx] / total
            if w > 0:
                b.append(rect(cx, y, w, bh, MODE_COLOR[mi], 0))
                if cx > bx and w >= 4:
                    b.append(line(cx, y, cx, y + bh, "#FFFFFF", 1))
                s = str(mode[idx])
                if w >= 6.4 * len(s) + 8:
                    b.append(text(cx + w / 2, y + 13, s, 11.5, "#FFFFFF", SANS, 600,
                                  "middle"))
            cx += w
        b.append("</g>")
        b.append(text(bx + bw + 8, y + 13, f"{total} runs", 12, MUTED))

    page("failure_modes", b, top + 3 * pitch + 8 + bh + 20)


# ============================================ fig: score and spending by cap
# numbers of record (2026-09-10): all 400 cells, the 28 without a graded run at
# score 0; band = the paper's cap; spent = sum(spent_h100) / sum(budget_h100).
BANDS, BANDRUNS = [8, 32, 96], [236, 116, 48]
COMPUTE = [
    ("DeepSeek-V4-Flash", [6.00, 4.10, 3.33], [42.0, 34.0, 13.5]),
    ("Qwen3.6-27B", [4.03, 3.14, 1.83], [31.0, 23.4, 3.1]),
    ("MiniMax-M2.7", [3.56, 2.41, 1.92], [26.8, 12.0, 2.3]),
    ("Muse Spark 1.2", [5.61, 4.55, 3.08], [38.9, 32.6, 6.1]),
    ("All agents", [4.80, 3.55, 2.54], [34.7, 25.5, 6.2]),
]


def slope_panel(b, ax, xs, top, ph, label, ymax, ticks, series, fmt):
    """One slope panel: gridlines with axis numerals at ax, three points per
    agent at xs, value labels at both ends with a leader where a label had to
    move off its point."""
    px, pw = xs[0] - 40, xs[2] - xs[0] + 48

    def Y(v):
        return top + ph - ph * v / ymax
    b.append(text(px, top - 12, label, 12, INK, SANS, 600))
    for t in ticks:
        b.append(line(px, Y(t), px + pw, Y(t), LINE if t == 0 else TRACK))
        b.append(text(ax, Y(t) + 4, str(t), 11, FAINT, SANS, 400, "end"))
    for name, vals in series:
        c = AGENT_COLOR[name]
        total = name == "All agents"
        pts = " ".join(f"{x:.1f},{Y(v):.1f}" for x, v in zip(xs, vals))
        dash = ' stroke-dasharray="6 4" stroke-dashoffset="2"' if total else ""
        b.append(f'<polyline points="{pts}" fill="none" stroke="{c}" '
                 f'stroke-width="{2.4 if total else 2.1}" stroke-linejoin="round"{dash}/>')
    # white discs under every point first, then the colored dots, so no
    # ring erases a neighbouring series' marker
    for name, vals in series:
        for x, v in zip(xs, vals):
            b.append(dot(x, Y(v), "#FFFFFF", 4.2))
    for name, vals in series:
        for x, v in zip(xs, vals):
            b.append(dot(x, Y(v), AGENT_COLOR[name], 3))
    for col, anchor, sg in ((0, "end", -1), (2, "start", 1)):
        placed = declutter([(Y(v[col]), (n, v[col])) for n, v in series], 13.5)
        shift = max(0, max(ly for ly, _ in placed) - (top + ph - 6))
        shift -= max(0, (top + 6) - (min(ly for ly, _ in placed) - shift))
        for ly, (name, val) in placed:
            ly -= shift
            c, y0 = AGENT_COLOR[name], Y(dict(series)[name][col])
            if abs(ly - y0) > 3:
                b.append(line(xs[col] + sg * 6, y0, xs[col] + sg * 20, ly, c, 0.9))
            b.append(text(xs[col] + sg * 23, ly + 4, fmt(val), 11.5, c, SANS, 600, anchor,
                          halo=True))
    for x, band, n in zip(xs, BANDS, BANDRUNS):
        b.append(text(x, top + ph + 18, str(band), 12, INK, SANS, 600, "middle"))
        b.append(text(x, top + ph + 31, f"{n} cells", 11, FAINT, SANS, 400, "middle"))


def fig_compute():
    """Two slope panels over the three compute bands, one line per agent:
    mean audit score on the left, share of the granted hours on the right."""
    b = head("score and spending by compute band")
    ky = 56
    for kx, (name, c) in zip((X0, 170, 284, 406, 534), AGENT_COLOR.items()):
        total = name == "All agents"
        b.append(line(kx, ky - 4, kx + 16, ky - 4, c, 2.4, "4 3" if total else None))
        b.append(text(kx + 21, ky, name, 12, MID))
    top, ph = 88, 112
    slope_panel(b, 44, [102, 184, 266], top, ph, "mean audit score", 8, [0, 2, 4, 6, 8],
                [(n, sc) for n, sc, _ in COMPUTE], lambda v: f"{v:.2f}")
    slope_panel(b, 372, [440, 522, 604], top, ph, "grant spent, %", 50,
                [0, 10, 20, 30, 40, 50], [(n, g) for n, _, g in COMPUTE],
                lambda v: f"{v:.1f}")
    page("compute_bands", b, top + ph + 46)


# ================================================== fig: score distribution
# numbers of record: audit.score over the 372 runs of
# tools/anon_viewer/public/data/index.json, read 2026-09-07.
HIST = [53, 10, 47, 17, 72, 14, 60, 26, 52, 16, 5]
HIST_KEY = [("disqualified (0)", ROSE), ("not reproduced (1 to 5)", SLATE),
            ("partial (6 to 7)", AMBER), ("reproduced (8 to 10)", GREEN)]


def score_color(s):
    return ROSE if s == 0 else SLATE if s <= 5 else AMBER if s <= 7 else GREEN


def fig_scores():
    b = head("score distribution", "372 graded runs")
    for i, (name, color) in enumerate(HIST_KEY):
        kx = X0 + i * (X1 - X0) / 4
        b.append(swatch(kx, 48, color))
        b.append(text(kx + 15, 56, name, 12, MID))
    top, ph, colw, gapw = 84, 110, 44, 12
    hx = X0 + ((X1 - X0) - (11 * colw + 10 * gapw)) / 2
    ymax = max(HIST)
    for s, n in enumerate(HIST):
        x = hx + s * (colw + gapw)
        hgt = ph * n / ymax
        b.append(rect(x, top + ph - hgt, colw, hgt, score_color(s), 0))
        b.append(text(x + colw / 2, top + ph - hgt - 6, str(n), 11.5, INK, SANS, 600,
                      "middle"))
        b.append(text(x + colw / 2, top + ph + 16, str(s), 12, INK, SANS, 600, "middle"))
    b.append(line(X0, top + ph + 0.5, X1, top + ph + 0.5, LINE))
    b.append(text((X0 + X1) / 2, top + ph + 31, "audit score, 0 to 10", 11.5, MUTED,
                  SANS, 400, "middle"))
    page("score_distribution", b, top + ph + 52)


CHARTS = {
    "results_by_tier": fig_results,
    "failure_modes": fig_modes,
    "compute_bands": fig_compute,
    "score_distribution": fig_scores,
}

if __name__ == "__main__":
    for n in sys.argv[1:] or CHARTS:
        CHARTS[n]()
