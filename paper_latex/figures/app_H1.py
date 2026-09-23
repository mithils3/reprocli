#!/usr/bin/env python3
"""Appendix H decisive-round panels, one per annotated run, in the run-card language of
~/sweeps/vignettes-2026-09-06/make_cards.py: the agent's words at the decisive round, the
tool call it issued, the tool result, and one adjacent round that carries the story.
Every displayed fragment between … marks is checked verbatim (after whitespace collapse)
against that round's event transcript, the CARD_SPEC.md rule.
The .pdf LaTeX includes is cropped to the body, so no panel puts dead space on the page.
The .png preview is padded out to build.py's 1280x720 viewport, as every figure in this
directory is, and the white band under the terminal is that padding, not the panel.
Usage: app_H1.py [n ...] -> figures/app_H1_zoom_<n>.html"""
import gzip
import html
import json
import os
import pathlib
import re
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from charts import OUT  # noqa: E402  figures/ output dir

DATA = os.path.expanduser('~/PyCharmProjects/reprocli/tools/anon_viewer/public/data/runs')
VIG = json.load(open(os.path.expanduser('~/sweeps/vignettes-2026-09-06/vignettes.json')))
WIDTH = 1280
COLS = 88          # widest display line: 21px JetBrains Mono lays out at a 13px advance in the 1148px text column
CMD_COLS = 85      # a call line also carries the 2-char $ prompt and the 10px gap: (1148 - 10 - 26) / 13
E = '…'
KEY_TINT_ALPHA = .45   # gold fill behind a '*' key result line; lower to tone it down

CSS = f'''
@font-face {{ font-family: 'JBMono'; src: url('fonts/ttf/JetBrainsMono-Regular.ttf'); font-weight: 400; }}
@font-face {{ font-family: 'JBMono'; src: url('fonts/ttf/JetBrainsMono-Medium.ttf'); font-weight: 500; }}
@font-face {{ font-family: 'JBMono'; src: url('fonts/ttf/JetBrainsMono-Bold.ttf'); font-weight: 700; }}
@font-face {{ font-family: 'InterF'; src: url('fonts/ttf/Inter-Regular.ttf'); font-weight: 400; }}
@font-face {{ font-family: 'InterF'; src: url('fonts/ttf/Inter-SemiBold.ttf'); font-weight: 600; }}
:root {{ --navy:#1F3A5F; --teal:#3E8E8C; --gold:#E3B341; --red:#C2483B; --ink:#2E3440; --gray:#6B7280; --cgray:#8C939E; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:{WIDTH}px; font-family:'InterF',sans-serif; background:#fff; text-rendering:geometricPrecision; }}
.wrap {{ width:{WIDTH}px; padding:4px; }}
.term {{ background:#F7F6F3; border:2px solid var(--navy); border-radius:14px; overflow:hidden; }}
.term-bar {{ display:flex; align-items:center; gap:9px; background:#E6E9ED; padding:9px 16px; }}
.dot {{ width:15px; height:15px; border-radius:50%; }}
.term-bar .title {{ font-family:'JBMono',monospace; font-size:21px; color:var(--gray); margin-left:8px; }}
.term-body {{ padding:8px 10px 10px 10px; font-family:'JBMono',monospace; font-size:21px; line-height:27px; font-feature-settings:'liga' 0,'calt' 0; }}
.blk {{ padding:5px 8px 6px 8px; border-radius:8px; margin:0 -4px; }}
.blk + .blk {{ margin-top:5px; }}
.blk.key {{ background:rgba(227,179,65,.22); border:1.5px solid rgba(140,107,31,.55); }}
.rh {{ display:flex; align-items:center; gap:10px; margin-bottom:2px; }}
.rh .pt {{ font-size:21px; font-weight:600; letter-spacing:0.8px; color:#8A919C; white-space:nowrap; }}
.rh .pr {{ flex:1; height:1.5px; background:#E4E7EB; }}
.blk.key .rh .pr {{ background:rgba(140,107,31,.35); }}
.row {{ display:grid; grid-template-columns:92px 1fr; align-items:baseline; }}
.g {{ font-size:21px; font-weight:600; letter-spacing:0.8px; color:#8A919C; white-space:nowrap; padding-top:1px; }}
.t {{ white-space:pre; }}
.think {{ color:var(--navy); font-style:italic; }}
.p {{ color:var(--teal); font-weight:500; white-space:pre; }}
.cmd {{ color:var(--ink); }}
.out {{ color:#4A5568; }}
.err {{ color:var(--red); font-weight:500; }}
.el {{ color:var(--cgray); }}
.kl {{ background:rgba(227,179,65,.5); color:var(--ink); font-weight:500; border-radius:3px; padding:0 1px 0 3px; margin:0 -1px 0 -3px; }}
.t.key {{ background:rgba(227,179,65,{KEY_TINT_ALPHA}); color:var(--ink); font-weight:500; border-radius:3px; padding:0 3px; margin:0 0 2px -3px; justify-self:start; }}
.call {{ display:flex; align-items:baseline; gap:10px; }}
.call .t {{ flex:1; }}
.right {{ margin-left:auto; display:flex; align-items:center; gap:10px; white-space:nowrap; }}
.rn {{ font-size:21px; color:var(--cgray); }}
.gpu {{ font-size:21px; font-weight:500; color:var(--teal); background:#E7F0EF; border:1px solid var(--teal); border-radius:6px; padding:1px 9px; }}
.tag {{ font-size:21px; font-weight:500; color:#8C6B1F; background:#FCF3D9; border:1px solid var(--gold); border-radius:6px; padding:1px 9px; }}
.tn {{ font-size:21px; color:var(--gray); background:#EEF0F2; border:1px solid #D8DCE1; border-radius:6px; padding:1px 9px; }}
.meta {{ display:flex; justify-content:flex-end; font-size:21px; color:var(--cgray); white-space:pre; margin-top:1px; }}
.legend {{ display:flex; flex-wrap:wrap; gap:4px 30px; font-family:'JBMono',monospace; font-size:21px; color:var(--cgray); margin-top:4px; padding-left:4px; }}
.legend span {{ white-space:nowrap; }}
.legend .err {{ font-weight:500; }}
.legend .sw {{ display:inline-block; width:22px; height:14px; vertical-align:-1px; border-radius:4px; background:rgba(227,179,65,.22); border:1.5px solid rgba(140,107,31,.55); }}
'''


def esc(s):
    return html.escape(s, quote=False)


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from strings(v)


def load(run_id):
    d = json.load(gzip.open(f'{DATA}/{run_id}.json.gz'))
    per, ev = {}, {}
    for e in d['events']:
        per.setdefault(e['round_index'], []).append(norm(' '.join(strings(e))))
        ev.setdefault(e['round_index'], []).append(e)
    return d['run'], {k: ' '.join(v) for k, v in per.items()}, ev


def frags(text):
    return [norm(f) for f in text.split(E) if norm(f)]


def check(corpus, rid, r, text, cols=COLS):
    for f in frags(text):
        assert f in corpus, f'{rid} r{r}: not verbatim: {f!r}'
    assert len(text) <= cols, f'{rid} r{r}: {len(text)} chars > {cols}: {text!r}'


def wrap(s):
    return textwrap.wrap(s, COLS, break_long_words=False, break_on_hyphens=False)


def elide(s, keep=CMD_COLS):
    """Head and tail of one over-long line around a single … mark."""
    s = s.split('\n')[0]
    if len(s) <= keep:
        return s
    h = keep - 33
    return s[:h].rstrip() + f' {E} ' + s[-30:].lstrip()


# ------------------------------------------------------------- the excerpts
# One entry per vignette: blocks in transcript order. agent: the agent's own words at that
# round (reasoning, or the visible message; Muse Spark 1.2 has only a one-line opener), each
# entry wrapped to the column; cmd: lines of the tool call (None = first line of the command,
# elided); res: tool output lines, a leading '!' sets the line in the error red; ci: which call
# in the round (default 0). Everything is verbatim from the round with … for elisions.
# Red carries one meaning here and in the run cards, the `err` kind of CARD_SPEC.md: a line of
# tool output that shows a failure. The decisive block starts after the fragment its run card
# already prints, so the panel adds what the card elides instead of repeating it.
P = {}

P['dsv4-run-2410.18164'] = [
    dict(r=53, agent=[
        "… The simplest robust minimal fix: at the end of predict_proba, after concatenating, normalize to 2D.",
    ], cmd=['cd … && grep -n "Ensure pred_val is always\\|…" src/tabdpt/classifier.py'],
        res=['152:        # Ensure pred_val is always (n_samples, n_classes) even for a single sample.',
             '153:        if pred_val.ndim == 1:',
             '155:        return pred_val']),
    dict(r=77, agent=['Let me run the verification on the held GPU session.'],
         cmd=['… python /repro/workspace/verify_fix.py > /repro/evidence/verify_fix2.log 2>&1 …'],
         res=['[vowel] pred_val.shape=(99, 11) (expect (n, 11)) t=6.9s', '[vowel] OK', '…',
              '[Devnagari] pred_val.shape=(9200, 46) (expect (n, 46)) t=341.6s', '[Devnagari] OK',
              'FIX VERIFY DONE']),
]

P['dsv4-run-2502.05795'] = [
    dict(r=21, agent=["The forward lowercases NORM_TYPE (`'lns'`) but the branch checks `norm_type == 'LNS'` — a case mismatch that would make the LNS branch dead code and crash with `use_cache=True`."],
         cmd=['… diff /repro/reference/…/modeling_llama.py peft_pretraining/modeling_llama.py && …',
              '… grep -n "NORM_TYPE\\|norm_type" peft_pretraining/modeling_llama.py | head -40'],
         res=['…', '427c427', "<         elif norm_type == 'cod':", '---', ">         elif norm_type == 'LNS':", '…',
              "403:        norm_type = os.getenv('NORM_TYPE', 'pre').lower()"]),
    dict(r=22, agent=[
        "… So running `bash run_130m.sh LNS 3` on the released repo would NOT actually apply LNS. This is a genuine bug in the released code.",
    ], cmd=['… cp /repro/reference/supplement/…/modeling_llama.py /tmp/modeling_ref.py &&',
            '  NORM_TYPE=cod POST_NUM=3 .venv/bin/python -c "… print(\'REFERENCE cod version …'],
        res=['…', '!cannot allocate memory for thread-local data: ABORT', '…']),
]

P['muse-retrain-2510.23577'] = [
    dict(r=24, agent=['Gamma bug spotted — applying the fix and queuing the full Wikipedia training run.'],
         cmd=['grep -n "gamma\\|HistoricalDecoder" /repro/workspace/repo/train_link_prediction.py', '…'],
         res=['---FILE_EDIT_NEEDED---', '…',
              'link_predictor = HistoricalDecoder(input_dim1=node_raw_features.shape[1], …',
              '    hidden_dim=node_raw_features.shape[1], output_dim=1, device=args.device)']),
    dict(r=31, key='gamma=args.gamma', agent=['Training pipeline patched — installing final dependencies and launching the Wikipedia AP verification.'],
         cmd=['uv pip install --python /repro/workspace/.venv/bin/python py-tgb dill 2>&1 | tail -30', '…',
              'grep -n "HistoricalDecoder" /repro/workspace/repo/train_link_prediction.py -A2'],
         res=['Installed 8 packages in 724ms', '…', '---check train gamma fix---',
              '128:    link_predictor = HistoricalDecoder(input_dim1=node_raw_features.shape[1], …',
              '129-  hidden_dim=node_raw_features.shape[1], output_dim=1, … gamma=args.gamma)',
              "54:    parser.add_argument('--gamma', type=float, default=0.9, …"]),
]

P['dsv4-retrain-2504.12463'] = [
    dict(r=91, agent=['Let me run the debug script in the held session.'],
         cmd=['… cd /repro/workspace/repo && … python debug_sdpa.py 2>&1 | tail -6'],
         res=['SDPA out shape: (2, 16, 64, 64) expected (2, 16, 64, 64)', '!manual NaN: False SDPA NaN: True',
              '!max abs diff: nan', '*True=allowed convention max diff: 0.0009765625']),
    dict(r=93, agent=['Mask inversion fixed. Let me re-run the probe to verify non-NaN loss matching the global probe (it10=7.98, it15=6.27) and confirm the speedup.'],
         cmd=['… $PY deepy.py train.py configs/probe.yml > /repro/evidence/probe_sdpa2.log 2>&1'],
         res=['iteration        5/      15 | … lm_loss: 1.064303E+01 | … nan iterations:   0 |',
              'iteration       10/      15 | … lm_loss: 7.981583E+00 | … nan iterations:   0 |',
              'iteration       15/      15 | … lm_loss: 6.272543E+00 | … nan iterations:   0 |']),
]

P['muse-run-2505.14766'] = [
    dict(r=24, agent=["Benchmark scope is clear — pulling Toto's 151M checkpoint and the BOOMlet dataset for live verification."],
         cmd=['uv pip install --python /repro/workspace/.venv/bin/python -e repo 2>&1 | tail -30 …'],
         res=['…', ' - torch==2.13.0+cu129', ' + torch==2.7.0', ' + tornado==6.5.8',
              ' + toto-ts==0.2.0 (from file:///repro/workspace/repo) …']),
    dict(r=25, agent=[],
         cmd=['… python -c "… print(torch.__version__); print(torch.cuda.is_available())" 2>&1',
              'uv pip list --python /repro/workspace/.venv/bin/python 2>&1 | grep -i torch …'],
         res=['!2.7.0+cpu', '!False', '…', 'torch                     2.7.0', '…',
              'torchvision               0.28.0+cu129']),
]

P['dsv4-run-2503.18430'] = [
    dict(r=91, agent=['Let me re-run the validation on the held session (still held, ~143 min left).'],
         cmd=['… python tools/chunked_coco_eval.py --validate 3000 … | grep -E "chunk |…|allclose|…'],
         res=['chunk 27/27 (204 cats) in 10.1s', '*precision allclose: True | max abs diff: 0.0',
              "chunked stats: ['0.500', '0.556', '0.521', '0.215', '0.307', '0.582']"]),
    dict(r=92, agent=[
        '… the chunked evaluation produces EXACTLY the same precision array as the full pycocotools COCOeval on the 3000-image subset.',
    ], cmd=['… python tools/chunked_coco_eval.py --full 2>&1 | tee …/full_chunked_eval.log | …'],
        res=['chunked eval total 3955.9s',
             '===== FINAL RESULT (COCO AP @ maxDets=300) =====',
             'bbox_mAP_copypaste: 0.463 0.515 0.484 0.184 0.298 0.518']),
]

P['minimax-retrain-2510.24940'] = [
    dict(r=10, agent=[],
         cmd=['… main.py --mode semcot --dataset svamp --config small --use_best_params …',
              '  … 2>&1 | tee /repro/evidence/semcot_svamp_run.log'],
         res=['Traceback (most recent call last):', '…', '    os.makedirs(self.cache_dir, exist_ok=True)',
              "!OSError: [Errno 30] Read-only file system: '/home/[user]/.triton'"]),
    dict(r=12, agent=[
        "… I'm weighing whether to run another full experiment with the full SVAMP test set, but that would cost around 2.1 H100-hours and eat into my remaining budget of 31 H100-hours.",
    ], cmd=['grep "acc =" /repro/evidence/semcot_svamp_run.log'],
        res=['[timestamp] [INFO] eval_temp = 0.1 | acc = 0.39 | ave_sample_time = 0.9249867737293244',
             '[timestamp] [INFO] eval_temp = 0.3 | acc = 0.39 | ave_sample_time = 0.8739698052406311', '…',
             '[timestamp] [INFO] eval_temp = 0.9 | acc = 0.315 | ave_sample_time = 0.8138951849937439']),
]

P['qwen3-run-2506.02392'] = [
    dict(r=35, agent=[
        'The gap is the same with and without MVDF (2.86%), which seems wrong. Let me look more carefully at the `--MVDF False` argument - since argparse with `type=bool` converts any string to True.',
        '… With `type=bool`, `"False"` string evaluates to `bool("False")` which is `True`. This is a known argparse bug.',
    ]),
    dict(r=36, agent=[
        'And the MVDF ablation (tab:ablation_aug):', '- w/o MVDF: 3.25% for TSP5K', '- POMO aug: 2.22%',
        '- TTPL-MVDF: 2.86%',
        "So the 3.25% corresponds to TTPL projection WITHOUT MVDF, which is exactly what I'm running. I got 2.86% which is actually better than the reported 3.25%.",
    ], cmd=['… python lehd/TSP/test_tsp.py \\ --problem_size 5000 \\ --coor_projection False \\',
            '  --MVDF False \\ --RRC_budget 0 \\ 2>&1 | tee /repro/evidence/tsp5k_no_proj_run.log'],
        res=["[timestamp] test_tsp.py(142) : model_params{… 'knearest': True, 'coor_projection': True}",
             '[timestamp] TSPTester.py(143) :  Gap: 2.7210%']),
]

P['minimax-retrain-2505.21077'] = [
    dict(r=96, agent=['Let me run the layer-skip approach benchmark. This should give a much larger speedup since it actually skips the attention computation entirely.'],
         cmd=['… /repro/workspace/.venv/bin/python /repro/evidence/nbl_patch.py 2>&1'],
         res=['NBL Throughput Benchmark (layer-skip approach)', '  Baseline: 32.82 tokens/s (30.47 ms/token)',
              '  NBL-8:    32.95 tokens/s (30.35 ms/token)']),
    dict(r=99, agent=[
        '… When the DecoderLayer adds `attn_output + residual`, the result = residual (identity).',
        '… This way I get the performance benefit of avoiding the actual computation while keeping the cache interface intact.',
    ], cmd=None, res=[]),
]

P['muse-reimplement-2506.17475'] = [
    dict(r=34, agent=[],
         cmd=["cat > /tmp/test_heavyball_optimizer.py << 'PY'", '…', '        self.mu = 1 - gamma', '…',
              '            # v = (1-gamma) v - lr * grad', '            v.mul_(self.mu).add_(p.grad, alpha=-self.lr)',
              '            # p = p + lr * v', '            p.data.add_(v, alpha=self.lr)'],
         res=[]),
    dict(r=37, agent=[],
         cmd=['… --mode lowrank --pretrained --epochs 20 … --lr 0.001 --momentum 0.9 --rank 100'],
         res=['Compressed 7662228 orig 134301514 cr 94.29% total 7662228', '…',
              'Epoch 20/20 tr_loss 0.0960 tr_acc 96.75 te_loss 0.4619 te_acc 88.46 time 5.0s',
              'BEST acc 89.02']),
]


# ---------------------------------------------------------------- rendering
def hl(ln, key):
    """Escape one line; set the spec's key phrase, where the line carries it, on the gold keyline."""
    if not key or key not in ln:
        return esc(ln)
    a, b = ln.split(key, 1)
    return f'{esc(a)}<span class="kl">{esc(key)}</span>{esc(b)}'


def row(label, body):
    return f'<div class="row"><span class="g">{label}</span>{body}</div>'


def fmt_meta(res):
    parts = []
    if res.get('rc') is not None:
        parts.append(f'rc {res["rc"]}')
    if res.get('duration_s'):
        parts.append(f'{res["duration_s"]:g} s')
    if res.get('cost_h100'):
        parts.append(f'{res["cost_h100"]:g} H100-h')
    return ' · '.join(parts)


def block(rid, corpus, events, spec, dr):
    r = spec['r']
    body = ''
    d = r - dr
    lab = 'DECISIVE' if d == 0 else 'THE ROUND BEFORE' if d == -1 else 'THE ROUND AFTER' if d == 1 \
        else f'{-d} ROUNDS EARLIER' if d < 0 else f'{d} ROUNDS LATER'
    calls = [e for e in events if e['kind'] == 'call_start']
    results = [e for e in events if e['kind'] == 'call_result']
    ci = spec.get('ci', 0)
    badge = ''
    if 'res' in spec and calls:
        tool = calls[ci]['tool_name']
        badge = ('<span class="gpu">GPU</span>' if tool == 'run_gpu' else '') + f'<span class="tn">{esc(tool)}</span>'
    elif calls:
        badge = '<span class="tn">call not shown</span>'
    right = badge + ('<span class="tag">decisive</span>' if d == 0 else '')
    body += (f'<div class="rh"><span class="pt">ROUND {r} &middot; {lab}</span><span class="pr"></span>'
             f'<span class="right">{right}<span class="rn">r{r}</span></span></div>')
    n_agent = 0
    for para in spec.get('agent', []):
        for ln in wrap(para):
            check(corpus, rid, r, ln)
            body += row('agent' if n_agent == 0 else '', f'<span class="t think">{esc(ln)}</span>')
            n_agent += 1
    assert n_agent <= 8, f'{rid} r{r}: {n_agent} agent lines'
    if 'res' in spec and calls:
        c, rs = calls[ci], results[ci]
        cmd = c.get('command') or json.dumps(c.get('args'))
        if c.get('detail_kind') != 'command':
            cmd = f'{c["tool_name"]} {cmd}'   # a path or a query, not a shell line: name the tool
        lines = spec.get('cmd') or [elide(cmd)]
        key = spec.get('key')
        for i, ln in enumerate(lines):
            check(corpus, rid, r, ln, CMD_COLS)
            if ln == E:
                inner = f'<span class="t el">{E}</span>'
            else:
                inner = f'<span class="p">{"$" if i == 0 else " "} </span><span class="t cmd">{hl(ln, key)}</span>'
            body += row('call' if i == 0 else '', f'<div class="call">{inner}</div>')
        for i, ln in enumerate(spec.get('res', [])):
            bad, key = ln.startswith('!'), ln.startswith('*')
            ln = ln[1:] if bad or key else ln
            check(corpus, rid, r, ln)
            cls = 'el' if ln == E else 'err' if bad else 'key' if key else 'out'
            body += row('result' if i == 0 else '', f'<span class="t {cls}">{hl(ln, spec.get("key"))}</span>')
        meta = fmt_meta(rs)
        if meta:
            body += f'<div class="meta">{esc(meta)}</div>'
    return f'<div class="blk{" key" if d == 0 else ""}">{body}</div>'


def render(v):
    rid, dr = v['run_id'], v['decisive_round']
    run, corpus, events = load(rid)
    blocks = ''.join(block(rid, corpus.get(s['r'], ''), events.get(s['r'], []), s, dr) for s in P[rid])
    title = f'{rid} &middot; decisive round {dr} of {run["rounds"]}'
    has_err = any(ln.startswith('!') for s in P[rid] for ln in s.get('res', []))
    legend = (('<span>agent = the agent\'s words</span>' if any(s.get('agent') for s in P[rid]) else '')
              + '<span>$ = the tool call</span><span>result = stdout, stderr</span>'
              + ('<span><span class="err">error</span> = a failed line</span>' if has_err else '')
              + ('<span>rc = exit code</span>' if 'class="meta">rc ' in blocks else '')
              + '<span><span class="sw"></span> decisive round</span>')
    return f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="wrap">
<div class="term"><div class="term-bar"><span class="dot" style="background:#DF7065;"></span><span class="dot" style="background:#EEC252;"></span><span class="dot" style="background:#6BB770;"></span><span class="title">{title}</span></div>
<div class="term-body">{blocks}</div></div>
<div class="legend">{legend}</div>
</div></body></html>'''


if __name__ == '__main__':
    want = {int(a) for a in sys.argv[1:]} or {v['n'] for v in VIG}
    for v in VIG:
        if v['n'] in want:
            out = OUT / f'app_H1_zoom_{v["n"]}.html'
            out.write_text(render(v))
            print('wrote', out)
