#!/usr/bin/env python3
"""Appendix H trace figures for the ten annotated runs, in the charts.py
language with the run_timelines marks. Usage: app_H2.py [--dump]

  app_H2_resource_trace  cumulative compute charge and wall-clock by round
  app_H2_auditor_trace   the auditor's calls in order, colored by what it opened

Data of record: ~/sweeps/vignettes-2026-09-06/vignettes.json (the ten runs,
decisive round, first graded-pipeline launch) and tools/anon_viewer/public/
data/runs/<id>.json.gz (run record, events, audit_events). Compute charged is
budget_h100 minus remaining_h100 after each call, normalised by the record's
spent_h100, which is also the figure printed at right; wall-clock is t_rel_s
normalised by the run's last timestamp."""
import gzip
import json
import pathlib
import re
import sys

FIGS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(FIGS))
from charts import (FAINT, INK, LINE_STRONG, MID, MUTED, SANS, X0, X1,   # noqa: E402
                    head, line, page, rect, text)

HOME = pathlib.Path.home()
VIG = HOME / "sweeps/vignettes-2026-09-06/vignettes.json"
RUNS = HOME / "PyCharmProjects/reprocli/tools/anon_viewer/public/data/runs"

# ------------------------------------------------- the run_timelines marks
# Every color below is one Figure 21 already prints. They are declared in
# ~/sweeps/vignettes-2026-09-06/make_fig_portrait.py (COL at line 10, the
# :root variables at line 82, the audit chips at lines 95 to 97, the lane
# rail at line 101, the legend ink at line 113) and reach the paper through
# figures/run_timelines.html. charts.py does not carry them, so this block is
# a second palette beside it; lifting it into charts.py and importing it here
# takes an edit to charts.py, which is outside this lane, so the block is kept
# whole and in one place to make that lift a single move. None of these values
# is a MODE_COLOR, which carries a fixed failure mode in Appendix G.
NAVY = "#1F3A5F"       # write or edit code; the decisive-round diamond
EXEC = "#3E8E8C"       # execute
GOLD = "#E3B341"       # install, download, build
RED = "#C2483B"        # the first graded-pipeline launch
READ = "#AEB6C1"       # read and plan
RT_SLATE = "#5B6470"   # the run_timelines legend ink
LANE_BG = "#F2F4F7"    # the rail a track is drawn on
CHIP = {               # the pinned audit chip: ink, fill, border
    "reproduced": ("#2A6B40", "#E6F3EA", "#3C8252"),
    "partial": ("#8C6B1F", "#FCF3D9", GOLD),
    "not_reproduced": ("#8F3229", "#F9E8E6", RED),
    "disqualified": ("#8F3229", "#F9E8E6", RED),
}
WORD = {"reproduced": "reproduced", "partial": "partial",
        "not_reproduced": "not reproduced", "disqualified": "disqualified"}


def load():
    out = []
    for v in json.load(open(VIG)):
        d = json.load(gzip.open(RUNS / f"{v['run_id']}.json.gz"))
        out.append((v, d["run"], d["events"], d["audit_events"]))
    return out


# ------------------------------------------------------------ shared lane label
def label(b, y, v, run):
    b.append(text(X0, y + 4, str(v["n"]), 12, INK, SANS, 600))
    b.append(text(X0 + 17, y - 2, v["agent"], 12, INK, SANS, 600))
    b.append(text(X0 + 17, y + 11.5, f"{v['tier']} · {v['arxiv']}", 11.5, MUTED))


def diamond(b, x, y, s=5):
    pts = f"{x:.1f},{y - s:.1f} {x + s:.1f},{y:.1f} {x:.1f},{y + s:.1f} {x - s:.1f},{y:.1f}"
    b.append(f'<polygon points="{pts}" fill="{NAVY}" stroke="#FFFFFF" stroke-width="1.5"/>')


def triangle(b, x, y, s=5):
    pts = f"{x - s:.1f},{y + s:.1f} {x + s:.1f},{y + s:.1f} {x:.1f},{y - s + 1:.1f}"
    b.append(f'<polygon points="{pts}" fill="{RED}"/>')


# ================================================== fig: resource trace
def resource_series(run, events):
    """Per round: compute charged so far (share of the run's spent_h100 of record)
    and wall-clock so far (share of the run's last timestamp), both at the end of
    the round. The event stream's last remaining_h100 falls short of the record in
    runs 5 and 7, so those two areas stop below the lane top."""
    n = run["rounds"]
    charged, tmax = [0.0] * n, [0.0] * n
    cur = 0.0
    for e in events:
        ri = e.get("round_index")
        if ri is None or ri >= n:
            continue
        if e["kind"] == "call_result" and e.get("remaining_h100") is not None:
            cur = run["budget_h100"] - e["remaining_h100"]
        charged[ri] = max(charged[ri], cur)
        if e.get("t_rel_s") is not None:
            tmax[ri] = max(tmax[ri], e["t_rel_s"])
    for i in range(1, n):                      # carry forward through idle rounds
        charged[i] = max(charged[i], charged[i - 1])
        tmax[i] = max(tmax[i], tmax[i - 1])
    tend = max(tmax) or 1.0
    spent = run["spent_h100"] or 1.0
    return [c / spent for c in charged], [t / tend for t in tmax]


def fig_resource(data):
    b = head("compute and wall-clock of the ten annotated runs by round",
             "share of the run's total")
    ky = 54
    b.append(rect(X0, ky - 9, 14, 10, LANE_BG, 2))   # the key is the mark: EXEC at
    b.append(f'<rect x="{X0}" y="{ky - 9}" width="14" height="10" rx="2" '
             f'fill="{EXEC}" fill-opacity="0.6"/>')     # 0.6 over the lane, as drawn
    b.append(text(X0 + 20, ky, "H100-hours charged", 12, MID))
    b.append(line(190, ky - 4, 206, ky - 4, NAVY, 1.8))
    b.append(text(211, ky, "wall-clock", 12, MID))
    diamond(b, 296, ky - 4)
    b.append(text(306, ky, "decisive round", 12, MID))
    triangle(b, 412, ky - 4)
    b.append(text(422, ky, "first graded-pipeline launch", 12, MID))

    tx0, tx1 = 190, X1 - 108
    maxr = max(run["rounds"] for _, run, _, _ in data)
    unit = (tx1 - tx0) / maxr
    # lane height and pitch of run_timelines, scaled to this canvas: the gutter
    # above each lane carries the decisive mark, clear of the lane below
    top, pitch, lh = 76, 56, 32
    for i, (v, run, events, _) in enumerate(data):
        y0 = top + i * pitch
        cy = y0 + lh / 2
        label(b, cy, v, run)
        n = run["rounds"]
        b.append(rect(tx0, y0, n * unit, lh, LANE_BG, 3))
        comp, wall = resource_series(run, events)

        def X(r):
            return tx0 + r * unit

        def Y(f):
            return y0 + lh - lh * min(f, 1.0)
        pts = [f"{X(0):.1f},{y0 + lh:.1f}"]
        for r in range(n):
            pts.append(f"{X(r):.1f},{Y(comp[r]):.1f}")
            pts.append(f"{X(r + 1):.1f},{Y(comp[r]):.1f}")
        pts.append(f"{X(n):.1f},{y0 + lh:.1f}")
        b.append(f'<polygon points="{" ".join(pts)}" fill="{EXEC}" fill-opacity="0.6"/>')
        wp = []
        for r in range(n):
            wp.append(f"{X(r):.1f},{Y(wall[r]):.1f}")
            wp.append(f"{X(r + 1):.1f},{Y(wall[r]):.1f}")
        b.append(f'<polyline points="{" ".join(wp)}" fill="none" stroke="{NAVY}" '
                 f'stroke-width="1.6" stroke-linejoin="round"/>')
        fr, dr = v["first_experiment_round"], v["decisive_round"]
        triangle(b, X(fr + 0.5), y0 + lh - 2, 4)
        dx = X(dr + 0.5)
        b.append(line(dx, y0 - 3, dx, y0, NAVY, 1))
        diamond(b, dx, y0 - 8, 4.5)
        b.append(text(dx + 8, y0 - 3.5, f"R{dr}", 11.5, NAVY, SANS, 600))
        rx = tx1 + 10
        b.append(text(rx, cy - 1, f"{run['spent_h100']:.1f} of {run['budget_h100']:.0f} H100-h",
                      11.5, INK, SANS, 600))
        b.append(text(rx, cy + 12.5, f"{run['duration_s'] / 3600:.1f} h wall-clock", 11.5, MUTED))
    ay = top + len(data) * pitch - pitch + lh + 8
    b.append(line(tx0, ay, tx0 + maxr * unit, ay, LINE_STRONG, 1))
    for t in range(0, maxr + 1, 25):
        b.append(line(tx0 + t * unit, ay, tx0 + t * unit, ay + 4, LINE_STRONG, 1))
        b.append(text(tx0 + t * unit, ay + 16, str(t), 11.5, FAINT, SANS, 400, "middle"))
    b.append(text(tx0 + maxr * unit / 2, ay + 30, "round", 11.5, MUTED, SANS, 400, "middle"))
    page("app_H2_resource_trace", b, ay + 38)


# ================================================== fig: auditor trace
# What the auditor opened or ran, by call. classify() keeps the seven keys the
# --dump rule prints; the figure draws them in four classes, because a cell is
# about 2mm wide in print and only three neutral steps hold apart from each
# other and from the lane at that size. Every value already exists in the
# paper: the three read classes are charts.py inks with the run_timelines
# legend slate between them, so neighbouring steps differ in hue as well as
# lightness, and they get no failure-mode color, since those carry fixed mode
# meanings in Appendix G. The run_timelines execution teal marks the one class
# where the auditor ran something itself, and a housekeeping call draws no
# cell, so the lane shows through.
CATS = [
    ("read", FAINT, "the report and its evidence"),
    ("source", RT_SLATE, "the code and the paper's source"),
    ("transcript", INK, "the agent's transcript"),
    ("recompute", EXEC, "recomputed or diffed"),
    ("noop", None, "housekeeping"),
]
GROUP = {"report": "read", "evidence": "read", "code": "source",
         "paper": "source", "transcript": "transcript",
         "recompute": "recompute", "noop": "noop"}
CAT_COLOR = {k: c for k, c, _ in CATS}
FLAG_COLOR = {"high": RED, "med": GOLD, "medium": GOLD, "low": READ}

RE_REPORT = re.compile(r"report\.json|REPORT\.md|plan\.md|metrics_summary\.json|CONFIG_NOTES|audit\.json")
RE_TRANSCRIPT = re.compile(r"agent\.log|agent\.full\.log|trajectory\.jsonl")
RE_PAPER = re.compile(r"reference/latex")
RE_CODE = re.compile(r"reference/supplement|workspace/repo\b(?!/(saved_results|logs))|workspace/SemCoT/(?!results)|workspace/repro_dlrt|workspace/\S*\.py|leaderboard\.py|find workspace|ls workspace")
RE_EVIDENCE = re.compile(r"evidence/|commands\.log|saved_results|workspace/repo/logs|SemCoT/results|stats\.json|rescore_verify|eval_42\.json|ls -la$|ls /work")
RE_PY = re.compile(r"python3? (-c|- <<)")
RE_RUN = re.compile(r"python3? evidence/\S+\.py|(?:^|&&\s*|;\s*)diff\s")
RE_ARITH = re.compile(r"mean|sum\(|exp\(|rel|abs\(|band|2\*\*|len\(|\*100|/1e9|/len")
RE_HOUSE = re.compile(r"^echo done|rm -f evidence/audit_recompute|ls evidence \| grep audit|print\(pandas\.__version__")


def classify(e):
    tool = e.get("tool_name", "")
    cmd = " ".join(str(e.get("command") or e.get("path") or e.get("args") or "").split())
    if tool == "write_run_file":
        return "recompute"
    if tool == "list_run_files":
        return "evidence"
    if RE_HOUSE.search(cmd):
        return "noop"
    if RE_RUN.search(cmd) or (RE_PY.search(cmd) and RE_ARITH.search(cmd)):
        return "recompute"
    if RE_TRANSCRIPT.search(cmd):
        return "transcript"
    if RE_PAPER.search(cmd):
        return "paper"
    if RE_REPORT.search(cmd):
        return "report"
    if RE_CODE.search(cmd):
        return "code"
    if RE_EVIDENCE.search(cmd):
        return "evidence"
    return "noop"


def audit_calls(audit_events):
    """[(round_index, category, tool_name, command)] in order, and the
    number of auditor rounds and its last timestamp."""
    calls = []
    for e in audit_events:
        if e["kind"] == "call_start":
            cmd = " ".join(str(e.get("command") or e.get("path") or e.get("args") or "").split())
            calls.append((e["round_index"], classify(e), e.get("tool_name"), cmd))
    nrounds = max(e["round_index"] for e in audit_events) + 1
    tend = max(e.get("t_rel_s") or 0 for e in audit_events)
    return calls, nrounds, tend


def chip(b, x, cy, verdict, score):
    ink, bg, border = CHIP[verdict]
    s = f"{score} {WORD[verdict]}"
    w = 12 + 6.6 * len(s)
    b.append(f'<rect x="{x:.1f}" y="{cy - 9:.1f}" width="{w:.1f}" height="18" rx="5" '
             f'fill="{bg}" stroke="{border}" stroke-width="1"/>')
    b.append(text(x + 6, cy + 4, s, 11.5, ink, SANS, 600))
    return w


def fig_auditor(data):
    b = head("the auditor's session on each annotated run",
             "one cell per tool call in order, a gap at each new round")
    ky = 54
    kx = X0
    for i, (key, color, name) in enumerate(CATS):
        if i == 3:
            ky, kx = ky + 18, X0
        if color:
            b.append(rect(kx, ky - 9, 10, 10, color, 2))
        else:                       # the key is the mark: the lane showing through
            b.append(rect(kx, ky - 9, 10, 10, LANE_BG, 2))
            b.append(f'<rect x="{kx + 0.5}" y="{ky - 8.5}" width="9" height="9" rx="2" '
                     f'fill="none" stroke="{LINE_STRONG}" stroke-width="1"/>')
        b.append(text(kx + 15, ky, name, 11.5, MID))
        kx += 15 + 6.1 * len(name) + 16
    # the flags key is a second legend, on its own row below the cell keys
    ky2 = ky + 18
    em = 6.28
    b.append(text(X0, ky2, "flags raised", 11.5, MID))
    fx = X0 + em * len("flags raised") + 12
    for sev, name in (("high", "high"), ("med", "medium"), ("low", "low")):
        b.append(f'<circle cx="{fx + 4:.1f}" cy="{ky2 - 4}" r="3.6" fill="{FLAG_COLOR[sev]}"/>')
        b.append(text(fx + 13, ky2, name, 11.5, MID))
        fx += 13 + em * len(name) + 12

    tx0 = 190
    right_w = 186
    tx1 = X1 - right_w
    maxc = max(len(audit_calls(ae)[0]) for _, _, _, ae in data)
    unit = (tx1 - tx0) / maxc
    top, pitch, lh = ky2 + 24, 38, 24
    for i, (v, run, _, ae) in enumerate(data):
        y0 = top + i * pitch
        cy = y0 + lh / 2
        label(b, cy, v, run)
        calls, nr, tend = audit_calls(ae)
        b.append(rect(tx0, y0, len(calls) * unit + 1, lh, LANE_BG, 3))
        prev = None
        for k, (ri, cat, tool, cmd) in enumerate(calls):
            gap = 2.5 if (prev is not None and ri != prev) else 0
            prev = ri
            x, cw = tx0 + k * unit + 1 + gap, unit - 1.5 - gap
            g = GROUP[cat]
            if g != "noop":         # housekeeping leaves the lane showing through
                b.append(rect(x, y0 + 2, cw, lh - 4, CAT_COLOR[g], 1.5))
        au = run["audit"]
        rx = tx1 + 12
        w = chip(b, rx, cy, au["verdict"], au["score"])
        fx = rx + w + 10
        for f in au["flags"]:
            b.append(f'<circle cx="{fx + 4:.1f}" cy="{cy:.1f}" r="3.6" fill="{FLAG_COLOR[f["severity"]]}"/>')
            fx += 9
    ay = top + len(data) * pitch - pitch + lh + 8
    b.append(line(tx0, ay, tx0 + maxc * unit, ay, LINE_STRONG, 1))
    for t in range(0, maxc + 1, 5):
        b.append(line(tx0 + t * unit, ay, tx0 + t * unit, ay + 4, LINE_STRONG, 1))
        b.append(text(tx0 + t * unit, ay + 16, str(t), 11.5, FAINT, SANS, 400, "middle"))
    b.append(text(tx0 + maxc * unit / 2, ay + 30, "tool call", 11.5, MUTED, SANS, 400, "middle"))
    page("app_H2_auditor_trace", b, ay + 38)


def dump(data):
    for v, run, _, ae in data:
        calls, nr, tend = audit_calls(ae)
        print(f"== {v['n']} {v['run_id']}  rounds={nr}  calls={len(calls)}  {tend:.0f}s  "
              f"flags={[f['severity'] for f in run['audit']['flags']]}")
        for ri, cat, tool, cmd in calls:
            print(f"  r{ri:>2} {cat:<10} [{tool}] {cmd[:150]}")


if __name__ == "__main__":
    data = load()
    if "--dump" in sys.argv:
        dump(data)
    else:
        fig_resource(data)
        fig_auditor(data)
