#!/usr/bin/env python3
"""Appendix A figure: one recorded round as a terminal panel. Data of record:
tools/anon_viewer/public/data/runs/<id>.json.gz, the event transcript of each
run. Writes figures/app_A_round_anatomy.html; render with build.py, check with
audit.py. Usage: app_A.py [round_anatomy]"""
import gzip
import html
import json
import os
import pathlib
import re
import sys

FIGS = pathlib.Path(__file__).resolve().parent

DATA = pathlib.Path(os.path.expanduser(
    "~/PyCharmProjects/reprocli/tools/anon_viewer/public/data"))


def load_run(rid):
    return json.load(gzip.open(DATA / "runs" / f"{rid}.json.gz"))


# ============================================ fig: one round as recorded
# A run_gpu round of a run outside the ten of Appendix H, from an agent other
# than DeepSeek-V4-Flash; Muse Spark 1.2 transcripts carry no reasoning.
RUN_ID = "minimax-retrain-2510.21363"
ROUND = 97
WIDTH = 1280
FAIL = re.compile(r"Traceback|Error|cannot access|finished: [1-9]")

CSS = f"""
@font-face {{ font-family: 'JBMono'; src: url('fonts/ttf/JetBrainsMono-Regular.ttf'); font-weight: 400; }}
@font-face {{ font-family: 'JBMono'; src: url('fonts/ttf/JetBrainsMono-Medium.ttf'); font-weight: 500; }}
@font-face {{ font-family: 'JBMono'; src: url('fonts/ttf/JetBrainsMono-Bold.ttf'); font-weight: 700; }}
:root {{ --navy:#1F3A5F; --teal:#3E8E8C; --gold:#E3B341; --red:#C2483B; --ink:#2E3440; --gray:#6B7280; --cgray:#8C939E; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:{WIDTH}px; font-family:'JBMono',monospace; background:#fff; }}
.wrap {{ width:{WIDTH}px; padding:4px; }}
.term {{ background:#F7F6F3; border:2px solid var(--navy); border-radius:14px; overflow:hidden; }}
.term-bar {{ display:flex; align-items:center; gap:9px; background:#E6E9ED; padding:9px 16px; }}
.dot {{ width:15px; height:15px; border-radius:50%; }}
.term-bar .title {{ font-size:18px; color:var(--gray); margin-left:8px; }}
.term-body {{ position:relative; padding:12px 16px 14px 50px; font-size:19px; line-height:1.5; font-feature-settings:'liga' 0,'calt' 0; }}
.term-body::before {{ content:''; position:absolute; left:27px; top:16px; bottom:16px; width:2.5px; background:#D8DCE1; }}
.ev {{ display:flex; align-items:center; gap:10px; margin:6px 0 1px -32px; }}
.ev:first-child {{ margin-top:0; }}
.ev .kind {{ font-size:17px; font-weight:700; letter-spacing:1.4px; color:#4E5866; white-space:nowrap; background:#F7F6F3; position:relative; z-index:1; padding:0 6px 0 4px; }}
.ev .meta {{ font-size:17px; color:var(--cgray); white-space:nowrap; }}
.ev .pr {{ flex:1; height:1.5px; background:#E4E7EB; }}
.ln {{ position:relative; display:flex; align-items:flex-start; gap:11px; min-height:28px; }}
.ln::before {{ content:''; position:absolute; left:-25px; top:14px; transform:translate(-50%,-50%); width:11px; height:11px; border-radius:50%; background:#fff; border:2.5px solid var(--teal); z-index:1; }}
.ln.th::before {{ background:#fff; border-color:var(--navy); }}
.ln.g::before {{ background:var(--teal); border-color:var(--teal); width:13px; height:13px; }}
.ln.e::before {{ background:var(--red); border-color:var(--red); }}
.ln.o::before {{ background:#fff; border-color:#9AA3AE; }}
.ln.f::before {{ background:var(--navy); border-color:var(--navy); }}
.ln.none::before {{ display:none; }}
.txt {{ white-space:pre-wrap; overflow-wrap:anywhere; flex:1; min-width:0; padding-right:14px; }}
.key {{ color:var(--gray); }}
.think {{ color:var(--navy); font-style:italic; }}
.p {{ color:var(--teal); font-weight:500; }}
.cmd {{ color:var(--ink); }}
.out {{ color:#4A5568; }}
.err {{ color:var(--red); font-weight:500; }}
.el {{ color:var(--cgray); }}
.chips {{ display:flex; flex-wrap:wrap; gap:8px 10px; padding:3px 0 2px; }}
.chip {{ font-size:17px; color:var(--ink); background:#EEF0F2; border:1px solid #D0D5DB; border-radius:6px; padding:1px 9px; white-space:nowrap; }}
.chip.gold {{ font-weight:500; color:#8C6B1F; background:#FCF3D9; border-color:var(--gold); }}
.right {{ margin-left:auto; display:flex; align-items:center; gap:10px; padding-top:2px; }}
.rn {{ font-size:17px; color:var(--cgray); }}
.gpu {{ font-size:17px; font-weight:500; color:var(--teal); background:#E7F0EF; border:1px solid var(--teal); border-radius:6px; padding:2px 9px; }}
.legend {{ display:flex; flex-wrap:wrap; gap:6px 18px; font-size:17px; color:var(--cgray); margin-top:16px; padding-left:4px; }}
.legend span {{ white-space:nowrap; }}
.legend .sw {{ display:inline-block; width:22px; height:14px; vertical-align:-1px; border-radius:4px; background:#FCF3D9; border:1.5px solid var(--gold); }}
"""


def esc(s):
    return html.escape(s, quote=False)


def ev_head(kind, meta):
    return (f'<div class="ev"><span class="kind">{esc(kind)}</span>'
            f'<span class="meta">{esc(meta)}</span><span class="pr"></span></div>')


def ln(cls, body, right=""):
    r = f'<span class="right">{right}</span>' if right else ""
    return f'<div class="ln {cls}"><span class="txt">{body}</span>{r}</div>'


def fmt(v):
    return "null" if v is None else json.dumps(v)


def fig_round_anatomy():
    d = load_run(RUN_ID)
    run, ev = d["run"], d["events"]
    rd = [e for e in ev if e["round_index"] == ROUND]
    nxt = [e for e in ev if e["round_index"] == ROUND + 1 and e["kind"] == "round_open"]
    op, = [e for e in rd if e["kind"] == "round_open"]
    cs, = [e for e in rd if e["kind"] == "call_start"]
    cr, = [e for e in rd if e["kind"] == "call_result"]
    assert cs["tool_name"] == "run_gpu" and not cr["truncated"]
    body = []
    body.append(ev_head("round_open", f"seq {op['seq']} · round_index {op['round_index']} · "
                        f"role {op['role']} · t_rel_s {op['t_rel_s']}"))
    body.append(ln("th", f'<span class="key">reasoning </span>'
                   f'<span class="think">{esc(op["reasoning"].strip())}</span>',
                   f'<span class="rn">r{ROUND}</span>'))
    body.append(ev_head("call_start", f"seq {cs['seq']} · tool_name {cs['tool_name']} · "
                        f"detail_kind {cs['detail_kind']} · t_rel_s {cs['t_rel_s']}"))
    body.append(ln("g", f'<span class="key">command </span><span class="p">$ </span>'
                   f'<span class="cmd">{esc(cs["command"].strip())}</span>',
                   f'<span class="gpu">GPU</span><span class="rn">r{ROUND}</span>'))
    body.append(ev_head("call_result", f"seq {cr['seq']} · t_rel_s {cr['t_rel_s']} · "
                        f"truncated {fmt(cr['truncated'])}"))
    chips = [("ok", cr["ok"], ""), ("rc", cr["rc"], ""),
             ("cost_h100", cr["cost_h100"], " gold"),
             ("remaining_h100", cr["remaining_h100"], " gold")]
    body.append(ln("f", '<span class="chips">' + "".join(
        f'<span class="chip{g}">{k} {fmt(v)}</span>' for k, v, g in chips) + "</span>"))
    lines = cr["stdout"].rstrip("\n").split("\n")
    # head + a contiguous elided middle + tail, so the elision count is exactly
    # the lines of the record that the panel does not print.
    keep_head, keep_tail = 1, 11
    elided = len(lines) - keep_head - keep_tail
    shown = [(i, s) for i, s in enumerate(lines) if i < keep_head or i >= len(lines) - keep_tail]
    first, any_bad = True, False
    for i, s in shown:
        if i == len(lines) - keep_tail and elided > 0:
            body.append(ln("none", f'<span class="el">⋯ {elided} lines of stdout elided</span>'))
        bad = bool(FAIL.search(s))
        any_bad = any_bad or bad
        label = '<span class="key">stdout </span>' if first else '<span class="key">       </span>'
        first = False
        # a blank stdout line keeps its row and loses its rail marker
        cls = "none" if not s.strip() else ("e" if bad else "o")
        body.append(ln(cls, label + f'<span class="{"err" if bad else "out"}">{esc(s)}</span>'))
    if nxt:
        n = nxt[0]
        body.append(ev_head("round_open", f"seq {n['seq']} · round_index {n['round_index']} · "
                            f"role {n['role']} · t_rel_s {n['t_rel_s']}"))
        body.append(ln("th", f'<span class="key">reasoning </span>'
                       f'<span class="think">{esc(n["reasoning"].strip())}</span>',
                       f'<span class="rn">r{ROUND + 1}</span>'))
    # spend as of this round, so the title closes against the remaining_h100 chip
    spent = run["budget_h100"] - cr["remaining_h100"]
    title = (f"{RUN_ID} · event transcript · round {ROUND} of {run['rounds']} · "
             f"{spent:.1f} of {run['budget_h100']:.0f} H100-h spent by this round")
    legend = ['<span><span style="color:#1F3A5F;">&#9675;</span> <i>reasoning</i></span>',
              '<span><span style="color:#3E8E8C;">&#9679;</span> GPU command</span>',
              '<span><span style="color:#1F3A5F;">&#9679;</span> result fields</span>',
              '<span><span style="color:#9AA3AE;">&#9675;</span> stdout</span>']
    if any_bad:
        legend.append('<span><span style="color:#C2483B;">&#9679;</span> failure</span>')
    legend += ['<span><span class="sw"></span> metered fields</span>',
               '<span>t_rel_s = seconds since launch</span>']
    page = (f'<!DOCTYPE html>\n<html><head><meta charset="utf-8"><style>{CSS}</style></head>'
            f'<body><div class="wrap"><div class="term"><div class="term-bar">'
            '<span class="dot" style="background:#DF7065;"></span>'
            '<span class="dot" style="background:#EEC252;"></span>'
            '<span class="dot" style="background:#6BB770;"></span>'
            f'<span class="title">{esc(title)}</span></div>'
            f'<div class="term-body">{"".join(body)}</div></div>'
            f'<div class="legend">{"".join(legend)}</div></div></body></html>\n')
    out = FIGS / "app_A_round_anatomy.html"
    out.write_text(page)
    print(f"wrote {out.name}  stdout lines {len(lines)}, shown {len(shown)}, failure lines {any_bad}")


FIGS_MAP = {"round_anatomy": fig_round_anatomy}

if __name__ == "__main__":
    for n in sys.argv[1:] or FIGS_MAP:
        FIGS_MAP[n]()
