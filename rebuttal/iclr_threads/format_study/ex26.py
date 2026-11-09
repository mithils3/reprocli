import json, re, random, collections
src = open('fmt_study.py').read()
exec(src[src.index('QLAB ='):src.index('def norm')])
S = '/home/mithil/PyCharmProjects/reprocli/rebuttal/results/style/author_comments.jsonl'
up = collections.Counter(); n = collections.Counter(); out = []
rx = re.compile(r"(?:cannot|can't|can not|unable to|not (?:be )?(?:allowed|permitted|possible) to|no longer (?:be )?(?:able|possible) to)\s+(?:\w+\s+){0,3}(?:upload|update|revise|submit)\w*\s+(?:\w+\s+){0,3}(?:pdf|manuscript|paper|revision)", re.I)
for l in open(S):
    d = json.loads(l); t = d['text'] or ''; n[d['year']] += 1
    if rx.search(t): up[d['year']] += 1
    if d['year'] != 2026 or d['replyto'] == d['forum']: continue
    lines = t.split('\n')
    for i, x in enumerate(lines):
        if QLAB.match(x) and 15 < len(x) < 160:
            body = []
            for y in lines[i+1:]:
                if QLAB.match(y): break
                body.append(y)
            b = ' '.join(z.strip() for z in body if z.strip() and not z.strip().startswith('>'))
            w = len(b.split())
            if 25 <= w <= 75 and re.search(r'\d+\.\d+|\d+%', b) and re.search(r'\b(?:Table|Appendix|Section|Figure|Fig\.|Line|L\d)', b) and '|' not in b:
                out.append((d['forum'], d['id'], x.strip(), b))
print(up, n)
random.Random(3).shuffle(out); print(len(out))
for o in out[:30]: print(o, '\n')
