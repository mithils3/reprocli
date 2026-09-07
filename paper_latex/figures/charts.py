#!/usr/bin/env python3
"""The data charts of Section 5 and Appendix C, as standalone HTML+SVG.

One chart language, shared with the reviewer viewer: a white card with a
hairline edge, a Fraunces title with a muted Inter subtitle at the right,
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
CARD = "#FFFFFF"
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


def card(h):
    return (
        f'<rect x="6" y="6" width="{W - 12}" height="{h - 12}" rx="10" fill="{CARD}" '
        f'stroke="{LINE}" stroke-width="1"/>'
    )


def head(title, sub):
    return [text(X0, 31, title, 15, INK, SERIF, 600),
            text(X1, 31, sub, 11.5, MUTED, SANS, 400, "end")]


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


def page(name, body, height):
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
""" % (W, W)
    html = (
        '<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n<style>'
        f"{css}</style>\n</head>\n<body>\n"
        f'<svg width="{W}" height="{height}" viewBox="0 0 {W} {height}">\n'
        + card(height) + "\n" + "\n".join(body)
        + "\n</svg>\n</body>\n</html>\n"
    )
    (OUT / f"{name}.html").write_text(html)
    print(f"wrote {name}.html  {W}x{height}")


# ============================================ fig: results by agent and tier
# numbers of record (2026-09-05): tools/anon_viewer/public/data/index.json
# sweeps[] (n, n_reproduced, mean_score); grant spent = 100 * sum(spent_h100) /
# sum(budget_h100) over the agent's runs.
RESULTS = [
    ("DeepSeek-V4-Flash", [(14, 29), (9, 28), (4, 30)], [6.21, 6.43, 5.10], 32.0),
    ("Qwen3.6-27B", [(5, 34), (6, 26), (2, 30)], [3.91, 4.54, 3.27], 15.5),
    ("MiniMax-M2.7", [(3, 33), (5, 32), (2, 33)], [3.18, 3.41, 2.70], 10.3),
    ("Muse Spark 1.2", [(9, 33), (9, 32), (5, 32)], [5.64, 6.03, 3.78], 21.7),
    ("All agents", [(31, 129), (29, 118), (13, 125)], [4.68, 5.08, 3.69], 19.4),
]
TIERS = ["Run", "Retrain", "Reimplement"]


def fig_results():
    """A matrix: one row per agent, one column per tier, each cell the mean
    audit score over the fraction and bar of runs reproduced, and a last
    column for the share of the granted GPU-hours the agent spent."""
    b = head("results by agent and tier",
             "372 graded runs; grant spent is the share of granted H100-hours")
    tx = [156, 286, 416]      # tier column lefts, 130px each
    gx = 560                  # grant column left, 98px
    barw = 90                 # one track width for every bar
    hy = 60
    for x, tier in zip(tx, TIERS):
        b.append(text(x, hy, tier, 12, INK, SANS, 600))
    b.append(text(gx, hy, "grant spent", 12, INK, SANS, 600))
    b.append(line(X0, hy + 7, X1, hy + 7, LINE_STRONG))

    top, pitch = 72, 49
    for gi, (agent, repro, score, spent) in enumerate(RESULTS):
        y = top + gi * pitch
        total = agent == "All agents"
        ink = MUTED if total else INK
        if total:
            b.append(line(X0, y - 4, X1, y - 4, LINE_STRONG))
        elif gi:
            b.append(line(X0, y - 4, X1, y - 4, LINE))
        b.append(text(X0, y + 21, agent, 12, ink, SANS, 600))
        for x, (n, d), s in zip(tx, repro, score):
            b.append(text(x, y + 16, f"{s:.2f}", 19, ink, SERIF, 600))
            b.append(text(x, y + 31, f"{n}/{d} reproduced", 11, MUTED))
            b.append(rect(x, y + 37, barw, 4, TRACK, 2))
            b.append(rect(x, y + 37, barw * n / d, 4, GREEN, 2))
            b.append(text(x + barw + 8, y + 42.5, f"{round(100 * n / d)}%", 11, ink,
                          SANS, 600))
        b.append(text(gx, y + 16, f"{spent:.1f}%", 19, ink, SERIF, 600))
        b.append(rect(gx, y + 37, barw, 4, TRACK, 2))
        b.append(rect(gx, y + 37, barw * spent / 100, 4, SLATE, 2))

    page("results_by_tier", b, top + 5 * pitch + 12)


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
            b.append(line(X0, y - 6, X1, y - 6, LINE_STRONG))
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
                if cx > bx:
                    b.append(line(cx, y, cx, y + bh, "#FFFFFF", 1))
                s = str(mode[idx])
                if w >= 6.4 * len(s) + 4:
                    b.append(text(cx + w / 2, y + 13, s, 11.5, "#FFFFFF", SANS, 600,
                                  "middle"))
            cx += w
        b.append("</g>")
        b.append(text(bx + bw + 10, y + 13, f"{total} runs", 12, MUTED))

    page("failure_modes", b, top + 3 * pitch + 8 + bh + 20)


# ============================================ fig: score and spending by cap
# numbers of record (2026-09-03): pinned grades over the 12 sweeps of record;
# band = the run's budget; spent = sum(spent_h100) / sum(budget_h100) per cell.
BANDS, BANDRUNS = [8, 32, 96], [228, 102, 42]
COMPUTE = [
    ("DeepSeek-V4-Flash", [6.21, 5.67, 4.44], [43.3, 43.9, 16.7]),
    ("Qwen3.6-27B", [4.18, 3.79, 2.22], [31.8, 20.5, 2.6]),
    ("MiniMax-M2.7", [3.62, 2.50, 1.92], [27.3, 11.9, 2.3]),
    ("Muse Spark 1.2", [5.91, 4.55, 3.08], [39.5, 32.6, 6.1]),
    ("All agents", [4.97, 4.04, 2.86], [35.4, 26.4, 6.5]),
]


def fig_compute():
    """The same matrix as the results figure: one row per agent, three cap
    columns for mean audit score and three for the share of the granted hours
    spent, each cell a number over a bar on a 0 to 10 or 0 to 100 track."""
    b = head("score and spending by compute band",
             "bands named by their H100-hour ceiling; 228, 102, and 42 runs")
    cx = [166, 248, 330, 426, 508, 590]   # cell lefts, 82px each, 14px between groups
    barw = 66
    for x, label in ((cx[0], "mean audit score, 0 to 10"), (cx[3], "grant spent, %")):
        b.append(text(x, 54, label, 12, INK, SANS, 600))
    for i, x in enumerate(cx):
        b.append(text(x, 69, f"{BANDS[i % 3]} H100-h", 11.5, MUTED, SANS, 500))
    b.append(line(cx[0], 75, cx[2] + barw, 75, LINE_STRONG))
    b.append(line(cx[3], 75, cx[5] + barw, 75, LINE_STRONG))

    top, pitch = 84, 40
    for gi, (agent, score, spent) in enumerate(COMPUTE):
        y = top + gi * pitch
        total = agent == "All agents"
        ink = MUTED if total else INK
        if total:
            b.append(line(X0, y - 4, X1, y - 4, LINE_STRONG))
        elif gi:
            b.append(line(X0, y - 4, X1, y - 4, LINE))
        b.append(text(X0, y + 19, agent, 12, ink, SANS, 600))
        cells = [(v, v / 10, f"{v:.2f}") for v in score] + \
                [(v, v / 100, f"{v:.1f}") for v in spent]
        for x, (v, frac, s) in zip(cx, cells):
            b.append(text(x, y + 19, s, 19, ink, SERIF, 600))
            b.append(rect(x, y + 27, barw, 4, TRACK, 2))
            b.append(rect(x, y + 27, barw * frac, 4, SLATE, 1))

    page("compute_bands", b, top + 5 * pitch + 10)


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
