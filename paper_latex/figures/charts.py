#!/usr/bin/env python3
"""The data charts of Section 5 and Appendix C, as standalone HTML+SVG.

One chart language for the paper, shared with the reviewer viewer: a rounded
white card, a bold lowercase Inter title with a gray JetBrains Mono subtitle
beside it, one saturated categorical palette in which green always means
reproduced, a light track behind every bar, and counts set in bold mono inside
each segment where they fit. Every chart uses the same 900px canvas so label
sizes match across figures. Regenerate with build.py after running this.
Usage: charts.py [name ...]"""
import pathlib
import sys

OUT = pathlib.Path(__file__).parent
W = 900

# --------------------------------------------------------------- palette
GREEN = "#1FAE6B"   # reproduced
AMBER = "#E2A430"   # near-miss / partial
PINK = "#E8557C"    # reimplemented without checking
TEAL = "#17B4A6"    # build / dependency failures
PURPLE = "#8B5FE8"  # wrong artifact measured
ORANGE = "#EF7F3B"  # wrong experiment
BLUE = "#3E7DFA"    # echoed a shipped number
MAGENTA = "#DD4FC0" # never launched
SLATE = "#93A0B2"   # failed before any number

MODE_COLOR = [GREEN, AMBER, PINK, TEAL, PURPLE, ORANGE, BLUE, MAGENTA, SLATE]

AGENT_COLOR = {
    "DeepSeek-V4-Flash": BLUE,
    "Qwen3.6-27B": PURPLE,
    "MiniMax-M2.7": ORANGE,
    "Muse Spark 1.2": TEAL,
    "All agents": "#4B5665",
}

INK = "#14141A"
MID = "#4B4B47"
MUTE = "#7C7C75"
TRACK = "#ECECEA"
EDGE = "#E4E4DF"
CARD = "#FFFFFF"
ON_DARK = "#FFFFFF"
ON_LIGHT = "#14141A"
MONO = "JBMono, monospace"
SANS = "InterF, sans-serif"


def w_mono(s, size):
    return len(s) * size * 0.6


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def on(fill):
    r, g, b = (int(fill[i:i + 2], 16) for i in (1, 3, 5))
    return ON_LIGHT if 0.299 * r + 0.587 * g + 0.114 * b > 150 else ON_DARK


def text(x, y, s, size=15, fill=None, family=MONO, weight=400, anchor="start", ls=0,
         halo=False):
    sp = f' letter-spacing="{ls}"' if ls else ""
    if halo:
        sp += ' stroke="#FFFFFF" stroke-width="3.8" paint-order="stroke"'
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill or INK}" text-anchor="{anchor}"'
        f'{sp}>{esc(s)}</text>'
    )


def rect(x, y, w, h, fill, r=3):
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(w, 0):.2f}" height="{h:.2f}" '
        f'rx="{r}" fill="{fill}"/>'
    )


def line(x1, y1, x2, y2, color=None, wdt=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color or EDGE}" stroke-width="{wdt}"{d}/>'
    )


def dot(x, y, color, r=3.4):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}"/>'


def card(x, y, w, h):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{CARD}" '
        f'stroke="{EDGE}" stroke-width="1.3"/>'
    )


def head(x, y, title, sub):
    out = [text(x, y, title, 22, INK, SANS, 800)]
    out.append(text(x + len(title) * 11.6 + 22, y, sub, 14.5, MUTE, MONO, 400))
    return out


def swatch(x, y, color, size=11, r=3):
    return rect(x, y, size, size, color, r)


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
@font-face { font-family: 'JBMono'; src: url('fonts/ttf/JetBrainsMono-Regular.ttf'); font-weight: 400; }
@font-face { font-family: 'JBMono'; src: url('fonts/ttf/JetBrainsMono-Medium.ttf'); font-weight: 500; }
@font-face { font-family: 'JBMono'; src: url('fonts/ttf/JetBrainsMono-Bold.ttf'); font-weight: 700; }
@font-face { font-family: 'InterF'; src: url('fonts/ttf/Inter-Regular.ttf'); font-weight: 400; }
@font-face { font-family: 'InterF'; src: url('fonts/ttf/Inter-Medium.ttf'); font-weight: 500; }
@font-face { font-family: 'InterF'; src: url('fonts/ttf/Inter-SemiBold.ttf'); font-weight: 600; }
@font-face { font-family: 'InterF'; src: url('fonts/ttf/Inter-ExtraBold.ttf'); font-weight: 800; }
* { margin: 0; padding: 0; }
html { width: %dpx; }
body { width: %dpx; background: #fff; }
svg { display: block; }
""" % (W, W)
    html = (
        '<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n<style>'
        f"{css}</style>\n</head>\n<body>\n"
        f'<svg width="{W}" height="{height}" viewBox="0 0 {W} {height}">\n'
        + "\n".join(body)
        + "\n</svg>\n</body>\n</html>\n"
    )
    (OUT / f"{name}.html").write_text(html)
    print(f"wrote {name}.html  {W}x{height}")


# ======================================================== fig1: results by tier
RESULTS = [
    ("DeepSeek-V4-Flash", [(14, 29), (9, 28), (4, 30)], [6.21, 6.43, 5.10], 32.0),
    ("Qwen3.6-27B", [(5, 34), (6, 26), (2, 30)], [3.91, 4.54, 3.27], 15.5),
    ("MiniMax-M2.7", [(3, 33), (5, 32), (2, 33)], [3.18, 3.41, 2.70], 10.3),
    ("Muse Spark 1.2", [(9, 33), (9, 32), (5, 32)], [5.64, 6.03, 3.78], 21.7),
    ("All agents", [(31, 129), (29, 118), (13, 125)], [4.68, 5.08, 3.69], 19.4),
]
TIERS = ["Run", "Retrain", "Reimplement"]


def band_color(score):
    return GREEN if score >= 8 else AMBER if score >= 6 else SLATE


def fig_results():
    b = [card(8, 8, W - 16, 0)]
    x0 = 30
    b += head(x0, 42, "reproduction and audit score", "372 graded runs, by agent and tier")

    # threshold key, one line
    ky = 64
    b.append(text(x0, ky, "score", 12, MUTE, MONO, 500, ls=0.4))
    kx = x0 + 46
    for c, lab in ((GREEN, "8+ reproduced"), (AMBER, "6+ partial or better"), (SLATE, "below 6")):
        b.append(dot(kx, ky - 4, c, 3.6))
        b.append(text(kx + 9, ky, lab, 12, MID, MONO, 400))
        kx += 9 + w_mono(lab, 12) + 20

    lab_x = x0 + 166          # agent name, right-aligned
    tier_x = lab_x + 16 + 86  # tier name, right-aligned
    p1x, p1w = tier_x + 14, 128
    p2x, p2w = p1x + p1w + 10 + 84 + 24, 96
    p3x, p3w = p2x + p2w + 10 + 32 + 26, 96
    top, bh, gap, ggap = 96, 11, 4, 6
    gh = 3 * bh + 2 * gap
    pitch = gh + ggap

    b.append(text(p1x, top - 14, "reproduced", 12.5, MUTE, MONO, 500, ls=0.5))
    b.append(text(p2x, top - 14, "mean score (0–10)", 12.5, MUTE, MONO, 500, ls=0.4))
    b.append(text(p3x, top - 14, "grant spent (0–100%)", 12.5, MUTE, MONO, 500, ls=0.4))

    for gi, (agent, repro, score, spent) in enumerate(RESULTS):
        gy = top + gi * pitch
        if agent == "All agents":
            b.append(line(x0, gy - 8, W - 30, gy - 8))
        acol = AGENT_COLOR[agent]
        b.append(dot(lab_x - w_mono(agent, 14) - 12, gy + gh / 2 + 1, acol, 3.6))
        b.append(text(lab_x, gy + gh / 2 + 5, agent, 14, INK, MONO, 700, "end"))
        for ti, tier in enumerate(TIERS):
            y = gy + ti * (bh + gap)
            n, d = repro[ti]
            pct = round(100 * n / d)
            b.append(text(tier_x, y + bh - 2, tier, 12.5, MUTE, MONO, 400, "end"))
            b.append(rect(p1x, y, p1w, bh, TRACK, bh / 2))
            b.append(rect(p1x, y, max(p1w * n / d, 3), bh, GREEN, bh / 2))
            b.append(text(p1x + p1w + 10, y + bh - 2, f"{n}/{d}", 13, MUTE))
            b.append(text(p1x + p1w + 10 + w_mono(f"{n}/{d} ", 13), y + bh - 2,
                          f"{pct}%", 13, INK, MONO, 700))
            b.append(rect(p2x, y, p2w, bh, TRACK, bh / 2))
            b.append(rect(p2x, y, max(p2w * score[ti] / 10.0, 3), bh, band_color(score[ti]), bh / 2))
            for tick_v in (6, 8):
                tx = p2x + p2w * tick_v / 10.0
                b.append(line(tx, y - 1.5, tx, y + bh + 1.5, "#FFFFFF", 1.4))
            b.append(text(p2x + p2w + 10, y + bh - 2, f"{score[ti]:.2f}", 13, INK, MONO, 700))
        sy = gy + gh / 2 - bh / 2
        b.append(rect(p3x, sy, p3w, bh, TRACK, bh / 2))
        b.append(rect(p3x, sy, max(p3w * spent / 100.0, 3), bh, acol, bh / 2))
        b.append(text(p3x + p3w + 10, sy + bh - 2, f"{spent:.1f}%", 13, INK, MONO, 700))

    h = top + 4 * pitch + gh + 22
    b[0] = card(8, 8, W - 16, h - 16)
    page("results_by_tier", b, h)


# ========================================================= fig2: failure modes
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
SMALL = 24  # px: below this, label moves off-segment


def fig_modes():
    b = [card(8, 8, W - 16, 0)]
    x0 = 30
    b += head(x0, 42, "primary failure mode by tier", "one mode per run, 372 graded runs")

    # legend: an OUTCOMES kicker over the 2 outcome modes (inline, since both
    # names are short), then a PROCESS FAILURES kicker over the remaining 7,
    # laid out in two columns. The kickers bound exactly the rows they name.
    lcol = 424
    k1_y = 60
    b.append(text(x0, k1_y, "OUTCOMES", 12, MUTE, MONO, 700, ls=1.1))
    b.append(line(x0, k1_y + 5, x0 + 96, k1_y + 5, "#D8D8D2", 4))
    row_out_y = k1_y + 18
    b.append(swatch(x0, row_out_y - 9, MODE_COLOR[0]))
    b.append(text(x0 + 17, row_out_y, MODES[0][0], 13, MID))
    out2_x = x0 + 150
    b.append(swatch(out2_x, row_out_y - 9, MODE_COLOR[1]))
    b.append(text(out2_x + 17, row_out_y, MODES[1][0], 13, MID))

    k2_y = row_out_y + 18
    b.append(text(x0, k2_y, "PROCESS FAILURES", 12, MUTE, MONO, 700, ls=1.1))
    b.append(line(x0, k2_y + 5, x0 + 172, k2_y + 5, "#D8D8D2", 4))
    lrow = 21
    proc_y = k2_y + 18
    proc_idx = list(range(2, 9))  # modes 3..9, split 4 left / 3 right
    for j, i in enumerate(proc_idx):
        col, row = (0, j) if j < 4 else (1, j - 4)
        cx = x0 + col * lcol
        y = proc_y + row * lrow
        b.append(swatch(cx, y - 9, MODE_COLOR[i]))
        b.append(text(cx + 17, y, MODES[i][0], 13, MID))

    top = proc_y + 3 * lrow + 14
    bar_x, bar_w, bh, pitch = x0 + 108, 610, 22, 40
    for si, (label, idx, total) in enumerate(STACKS):
        y = top + si * pitch
        if label == "All agents":
            b.append(line(x0, y - 12, W - 30, y - 12))
        b.append(text(bar_x - 12, y + bh - 6, label, 14.5, INK, MONO, 700, "end"))

        # geometry per segment
        segs = []
        cx = bar_x
        for mi, mode in enumerate(MODES):
            w = bar_w * mode[idx] / total
            segs.append((cx, w, mode[idx], mi))
            cx += w

        b.append(f'<clipPath id="clip{si}"><rect x="{bar_x}" y="{y}" '
                 f'width="{bar_w}" height="{bh}" rx="6"/></clipPath>')
        b.append(f'<g clip-path="url(#clip{si})">')
        b.append(rect(bar_x, y, bar_w, bh, TRACK, 6))
        for scx, w, n, mi in segs:
            if w > 0.3:
                b.append(rect(scx, y, w, bh, MODE_COLOR[mi], 0))
            if w >= SMALL:
                b.append(text(scx + w / 2, y + bh - 7, str(n), 13.5,
                              on(MODE_COLOR[mi]), MONO, 700, "middle"))
        b.append("</g>")

        # small/zero segments: labelled off-bar with a leader, x-declutter
        smalls = [(scx + w / 2, n, mi) for scx, w, n, mi in segs if w < SMALL]
        if smalls:
            placed = declutter([(c, (n, mi)) for c, n, mi in smalls], 17)
            for slot_x, (n, mi) in placed:
                col = MODE_COLOR[mi]
                ly2 = y - 8
                # true center for the leader (match by mi within this row)
                true_c = next(scx + w / 2 for scx, w, nn, mmi in segs if mmi == mi)
                b.append(line(slot_x, ly2 + 3, true_c, y - 1, col, 1.2))
                b.append(dot(true_c, y, col, 1.8))
                b.append(text(slot_x, ly2, str(n), 12, col, MONO, 700, "middle"))

        b.append(text(bar_x + bar_w + 12, y + bh - 6, f"{total} runs", 13, MUTE))

    h = top + 3 * pitch + bh + 16
    b[0] = card(8, 8, W - 16, h - 16)
    page("failure_modes", b, h)


# ========================================================= fig3: compute bands
BANDS, BANDRUNS = [8, 32, 96], [228, 102, 42]
COMPUTE = [
    ("DeepSeek-V4-Flash", [6.21, 5.67, 4.44], [43.3, 43.9, 16.7]),
    ("Qwen3.6-27B", [4.18, 3.79, 2.22], [31.8, 20.5, 2.6]),
    ("MiniMax-M2.7", [3.62, 2.50, 1.92], [27.3, 11.9, 2.3]),
    ("Muse Spark 1.2", [5.91, 4.55, 3.08], [39.5, 32.6, 6.1]),
    ("All agents", [4.97, 4.04, 2.86], [35.4, 26.4, 6.5]),
]


def slope_panel(b, px, pw, top, ph, label, ymax, series, fmt):
    xs = [px + i * (pw / 2) for i in range(3)]

    def Y(v):
        return top + ph - ph * v / ymax

    b.append(text(px - 30, top - 13, label, 12.5, MUTE, MONO, 500, ls=0.5))
    for frac in (0, 0.25, 0.5, 0.75, 1.0):
        gy = top + ph - ph * frac
        b.append(line(px - 30, gy, px + pw + 6, gy, EDGE if frac == 0 else TRACK))
    for name, vals in series:
        c = AGENT_COLOR[name]
        dash = ' stroke-dasharray="5 4"' if name == "All agents" else ""
        wdt = 3.0 if name == "All agents" else 2.3
        pts = " ".join(f"{x:.1f},{Y(v):.1f}" for x, v in zip(xs, vals))
        b.append(f'<polyline points="{pts}" fill="none" stroke="{c}" '
                 f'stroke-width="{wdt}" stroke-linejoin="round"{dash}/>')
        for x, v in zip(xs, vals):
            b.append(f'<circle cx="{x:.1f}" cy="{Y(v):.1f}" r="3.4" fill="{c}"/>')
    for ly_, (name, val) in declutter([(Y(v[1]) - 13, (n, v[1])) for n, v in series], 16.5):
        b.append(text(xs[1], ly_, fmt(val), 12, AGENT_COLOR[name], MONO, 700, "middle",
                      halo=True))
    for ly_, (name, val) in declutter([(Y(v[0]), (n, v[0])) for n, v in series], 16.5):
        c, y0 = AGENT_COLOR[name], Y(dict((n_, v_[0]) for n_, v_ in series)[name])
        if abs(ly_ - y0) > 4:
            b.append(line(xs[0] - 8, ly_, xs[0] - 3, y0, c, 0.9))
        b.append(text(xs[0] - 12, ly_ + 4, fmt(val), 12, c, MONO, 700, "end"))
    for ly_, (name, val) in declutter([(Y(v[2]), (n, v[2])) for n, v in series], 16.5):
        c, y0 = AGENT_COLOR[name], Y(dict((n_, v_[2]) for n_, v_ in series)[name])
        if abs(ly_ - y0) > 4:
            b.append(line(xs[2] + 8, ly_, xs[2] + 3, y0, c, 0.9))
        b.append(text(xs[2] + 12, ly_ + 4, fmt(val), 12, c, MONO, 700))
        b.append(text(xs[2] + 12 + w_mono(fmt(val) + " ", 12), ly_ + 4, name, 12, c,
                      MONO, 500))
    for x, band, n in zip(xs, BANDS, BANDRUNS):
        b.append(text(x, top + ph + 28, str(band), 14.5, INK, MONO, 700, "middle"))
        b.append(text(x, top + ph + 43, f"{n} runs", 11.5, MUTE, MONO, 400, "middle"))


def fig_compute():
    b = [card(8, 8, W - 16, 0)]
    x0 = 30
    b += head(x0, 42, "score and spending by compute cap", "per-paper cap, H100-hours")
    top, ph = 88, 152
    slope_panel(b, x0 + 58, 190, top, ph, "mean audit score", 8.0,
                [(n, s) for n, s, _ in COMPUTE], lambda v: f"{v:.2f}")
    slope_panel(b, x0 + 487, 186, top, ph, "grant spent (%)", 50.0,
                [(n, g) for n, _, g in COMPUTE], lambda v: f"{v:.1f}")
    b.append(line(x0 + 440, 60, x0 + 440, top + ph + 38, TRACK))
    h = top + ph + 62
    b[0] = card(8, 8, W - 16, h - 16)
    page("compute_bands", b, h)


# =================================================== score distribution
# numbers of record: audit.score over the 372 runs of
# tools/anon_viewer/public/data/index.json, read 2026-09-07.
HIST = [53, 10, 47, 17, 72, 14, 60, 26, 52, 16, 5]
HIST_KEY = [("disqualified (0)", PINK), ("not reproduced (1 to 5)", SLATE),
            ("partial (6 to 7)", AMBER), ("reproduced (8 to 10)", GREEN)]


def score_color(s):
    return PINK if s == 0 else SLATE if s <= 5 else AMBER if s <= 7 else GREEN


def fig_scores():
    b = [card(8, 8, W - 16, 0)]
    x0 = 30
    b += head(x0, 42, "score distribution", "372 graded runs")
    kx = x0
    for name, color in HIST_KEY:
        b.append(swatch(kx, 58, color))
        b.append(text(kx + 17, 67, name, 13, MID))
        kx += 17 + w_mono(name, 13) + 24

    top, ph = 96, 132
    colw, gapw = 58, 17
    hx = x0 + 14
    ymax = max(HIST)
    for s, n in enumerate(HIST):
        x = hx + s * (colw + gapw)
        hgt = ph * n / ymax
        b.append(rect(x, top + ph - hgt, colw, hgt, score_color(s), 5))
        b.append(text(x + colw / 2, top + ph - hgt - 8, str(n), 13.5, INK, MONO, 700,
                      "middle"))
        b.append(text(x + colw / 2, top + ph + 21, str(s), 14.5, MID, MONO, 700,
                      "middle"))
    b.append(line(x0, top + ph + 1, W - 30, top + ph + 1, EDGE))
    b.append(text(x0 + 14 + (11 * colw + 10 * gapw) / 2, top + ph + 40,
                  "audit score, 0 to 10", 12.5, MUTE, MONO, 400, "middle"))
    h = top + ph + 56
    b[0] = card(8, 8, W - 16, h - 16)
    page("score_distribution", b, h)


CHARTS = {
    "results_by_tier": fig_results,
    "failure_modes": fig_modes,
    "compute_bands": fig_compute,
    "score_distribution": fig_scores,
}

if __name__ == "__main__":
    for n in sys.argv[1:] or CHARTS:
        CHARTS[n]()
