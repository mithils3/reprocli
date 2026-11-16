"""Reproduction rates by target-audit group (E7 v3 checks), submission (A) and revision (B)."""
import csv, math, re, pathlib
from collections import Counter
from scipy.stats import fisher_exact

ROOT = pathlib.Path('/home/mithil/PyCharmProjects/reprocli')
OUT = pathlib.Path('/tmp/claude-1000/-home-mithil-PyCharmProjects-reprocli/ee88b5cc-f222-456d-9de1-997a82c38396/scratchpad/followup_1116/ev_targets')
TIER = {'Easy': 'run', 'Medium': 'retrain', 'Hard': 'reimplement'}
TIERS = ['run', 'retrain', 'reimplement']
MODELS = ['dsv4', 'minimax', 'muse', 'qwen3']
Z = 1.959964

# Revision changes from rebuttal/post/general.md (grade changes table) and STATUS.md line 14.
REMOVE_B = [('dsv4', 'run', '2505.23747'), ('minimax', 'run', '2505.23747'),
            ('muse', 'retrain', '2508.21046'), ('minimax', 'reimplement', '2505.12677')]
ADD_B = [('muse', 'run', '2503.23035')]

# 1. papers
papers = {}
for r in csv.DictReader(open(ROOT / 'rebuttal/results/e7/comparison.csv')):
    papers[r['custom_id']] = dict(tier=TIER[r['tier']],
                                  all4=all(r[f'v3_{c}_yes'] == 'True' for c in 'abcd'))
ids = set(papers)
# 16 papers with a setting or label off: rows of the full sheet in e7_merged.md
off = set()
for line in open(ROOT / 'rebuttal/mithil/e7_merged.md'):
    p = [x.strip() for x in line.split('|')]
    if len(p) > 6 and p[1].isdigit() and p[5].startswith('setting or label'):
        off.add(p[2])

# 2. graded runs (submission)
rep_A = set()
rows = list(csv.DictReader(open(ROOT / 'rebuttal/results/e6/table.csv')))
mismatch = 0
for r in rows:
    key = (r['model'], r['arxiv_id'])
    if r['arxiv_id'] not in ids:
        mismatch += 1
        continue
    if papers[r['arxiv_id']]['tier'] != r['tier']:
        mismatch += 1
    if r['index_verdict'] == 'reproduced':
        rep_A.add(key)
rep_B = set(rep_A)
for m, t, i in REMOVE_B:
    assert (m, i) in rep_B and papers[i]['tier'] == t, (m, t, i)
    rep_B.discard((m, i))
for m, t, i in ADD_B:
    assert papers[i]['tier'] == t
    rep_B.add((m, i))


def wilson(k, n):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return (c - h, c + h)


def pct(k, n):
    return f'{k} of {n} = {100 * k / n:.1f}%' if n else '0 of 0'


def stats(group, rep):
    out = {}
    cells = len(group) * 4
    k_all = sum(1 for (m, i) in rep if i in group)
    out['cells'] = (k_all, cells)
    out['tier_model'] = {}
    out['best'] = {}
    for t in TIERS:
        ps = [i for i in group if papers[i]['tier'] == t]
        n = len(ps)
        per = {m: sum(1 for i in ps if (m, i) in rep) for m in MODELS}
        out['tier_model'][t] = (n, per)
        top = max(per.values())
        out['best'][t] = (n, [m for m in MODELS if per[m] == top], top)
    out['any'] = (sum(1 for i in group if any((m, i) in rep for m in MODELS)), len(group))
    return out


def fmt_group(name, s):
    lines = [f'{name}: cells {pct(*s["cells"])}; at least one agent reproduces {pct(*s["any"])}']
    for t in TIERS:
        n, top_models, top = s['best'][t]
        lines.append(f'  {t}: best {", ".join(top_models)} {pct(top, n)}')
    return lines


G_all = ids
G55 = {i for i in ids if papers[i]['all4']}
G45 = ids - G55
G84 = ids - off
assert len(G55) == 55, len(G55)
assert len(off) == 16 and off <= ids, (len(off), off - ids)
assert off <= G45, 'setting-or-label papers should all be among the 45 failing'

report = []
report.append(f'checks: all-four {len(G55)} (expect 55); setting-or-label {len(off)} (expect 16); '
              f'table rows mapped to 100 papers {len(rows) - mismatch} of {len(rows)} (tier mismatches folded in: {mismatch})')
ok_A = len(rep_A) == 73
ok_B = len(rep_B) == 70
report.append(f'reproduced cells: (A) {len(rep_A)} (expect 73, {"OK" if ok_A else "MISMATCH"}); '
              f'(B) {len(rep_B)} (expect 70, {"OK" if ok_B else "MISMATCH"})')

tables = {}
for ver, rep in (('A', rep_A), ('B', rep_B)):
    S = {'all100': stats(G_all, rep), 'pass55': stats(G55, rep),
         'other45': stats(G45, rep), 'minus16': stats(G84, rep)}
    tables[ver] = S
    report.append(f'\n## {ver}')
    for name, g in (('All 100', 'all100'), ('55 pass all four', 'pass55'),
                    ('45 other', 'other45'), ('84 (100 minus 16 off)', 'minus16')):
        report.extend(fmt_group(name, S[g]))
    for g, name in (('pass55', '55'), ('other45', '45')):
        report.append(f'  per tier, model ({name}):')
        for t in TIERS:
            n, per = S[g]['tier_model'][t]
            report.append(f'    {t} n={n}: ' + '; '.join(f'{m} {pct(per[m], n)}' for m in MODELS))
    # Fisher and Wilson
    a_k, a_n = S['pass55']['cells']
    b_k, b_n = S['other45']['cells']
    odds, p = fisher_exact([[a_k, a_n - a_k], [b_k, b_n - b_k]], alternative='two-sided')
    report.append(f'  Fisher two-sided: 55 {pct(a_k, a_n)} vs 45 {pct(b_k, b_n)}; OR {odds:.3f}, p = {p:.4g}')
    for g, name in (('pass55', '55'), ('other45', '45')):
        for t in TIERS:
            n, models, top = S[g]['best'][t]
            lo, hi = wilson(top, n)
            report.append(f'  Wilson {name} {t} best {"/".join(models)}: {top}/{n} = {100*top/n:.1f}% [{100*lo:.1f}, {100*hi:.1f}]')

text = '\n'.join(report)
print(text)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'ev_targets_raw.txt').write_text(text + '\n')
