import json, re, csv, collections, statistics as st, random
exec(open('fmt_study.py').read().split('\nrows = ')[0])
exec('\n'.join(l for l in open('fmt_study.py').read().split('\n') if False))
src = open('fmt_study.py').read()
exec(src[src.index('NUMLAB ='):src.index('def head_kind')])
exec(src[src.index('def wilson'):src.index('def q(xs)')])
exec(src[src.index('QLAB ='):src.index('def norm')])
S = '/home/mithil/PyCharmProjects/reprocli/rebuttal/results/style/'
titles = {}
with open(S + 'iclr_author_responses.csv') as f:
    for r in csv.DictReader(f): titles[r['id']] = r['comment_title'] or ''
C = []
for l in open(S + 'author_comments.jsonl'):
    d = json.loads(l); t = d['text'] or ''; ti = titles.get(d['id'], '')
    lines = t.split('\n')
    C.append({'y': d['year'], 'f': d['forum'], 'rt': d['replyto'], 'gr': d['replyto'] == d['forum'], 'n': len(t),
              'tab': bool(re.search(r'^\s*\|?\s*:?-{3,}:?\s*\|', t, re.M)),
              'part': bool(re.search(r'\(\s*\d\s*/\s*[\dn]\s*\)|\[\s*\d\s*/\s*[\dn]\s*\]|\bpart\s*(?:\d|[ivx]+\b)|\(cont|\bcontinued\)?\s*$', ti, re.I)) or bool(re.search(r'^\W*(?:\(\s*\d\s*/\s*\d\s*\)|\(?cont(?:inued|\'d|d)?\W*$)', t[:40], re.I)),
              'numq': any(QLAB.match(x) for x in lines), 'bq': any(re.match(r'^\s*>\s*\S', x) for x in lines), 'mdh': any(re.match(r'^\s*#{1,4}\s+\S', x) for x in lines),
              'bold': any(re.match(r'^\s*[-*]?\s*\*\*[^*\n]{3,160}\*\*', x) for x in lines),
              'dear': bool(re.match(r'^\s*(?:\*\*)?\s*dear\b', t, re.I)), 'cap': len(t) > 4800,
              'match': bool(re.search(r'we thank|thank the reviewer', t, re.I)),
              'blue': bool(re.search(r'\b(?:in|with) (?:blue|red|green|orange|purple)\b|highlighted', t, re.I)),
              'rev': bool(re.search(r'\b(?:revised|updated)\s+(?:version|manuscript|paper|pdf|draft|submission)', t, re.I)),
              'line': bool(re.search(r'\b(?:[Ll]ines?|L)\s?\d{2,4}\b', t)),
              'w': len(re.findall(r"[A-Za-z0-9][\w'.%-]*", t))})
def qq(xs):
    a = st.quantiles(xs, n=4, method='inclusive'); return f'{a[0]:,.0f} / {st.median(xs):,.0f} / {a[2]:,.0f}'
def boot(a, b, B=400):
    rng = random.Random(1); ds = []
    for _ in range(B):
        ds.append(st.median(rng.choices(a, k=len(a))) - st.median(rng.choices(b, k=len(b))))
    ds.sort(); return st.median(a) - st.median(b), ds[int(.025*B)], ds[int(.975*B)-1]
for sub, filt in [('all', lambda c: True), ('matched (text has "we thank" or "thank the reviewer")', lambda c: c['match'])]:
    print('==', sub)
    for kind, kf in [('reviewer replies', lambda c: not c['gr']), ('general responses', lambda c: c['gr'])]:
        g = {y: [c for c in C if c['y'] == y and filt(c) and kf(c)] for y in (2025, 2026)}
        print(' ', kind, {y: len(v) for y, v in g.items()})
        for y in g: print('   ', y, 'chars', qq([c['n'] for c in g[y]]), 'words', qq([c['w'] for c in g[y]]))
        d, lo, hi = boot([c['n'] for c in g[2026]], [c['n'] for c in g[2025]]); print('    2026-2025 median chars', f'{d:+.0f} [{lo:+.0f}, {hi:+.0f}]')
        for k in ['tab', 'part', 'numq', 'bq', 'mdh', 'bold', 'dear', 'cap', 'blue', 'rev', 'line']:
            a = sum(c[k] for c in g[2026]); b = sum(c[k] for c in g[2025]); n1, n2 = len(g[2026]), len(g[2025])
            dd, l, h = newcombe(a, n1, b, n2)
            print(f'    {k}: 2025 {100*b/n2:.1f}%  2026 {100*a/n1:.1f}%  diff {100*dd:+.1f} [{100*l:+.1f}, {100*h:+.1f}]')
    # per-thread totals
    for y in (2025, 2026):
        th = collections.defaultdict(int)
        for c in C:
            if c['y'] == y and filt(c) and not c['gr']: th[(c['f'], c['rt'])] += c['n']
        print('  thread totals', y, len(th), qq(list(th.values())))
