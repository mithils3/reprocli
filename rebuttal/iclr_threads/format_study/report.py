import json, re, collections, statistics as st, sys
sys.argv = ['x', 'out.json']
exec(open('fmt_study.py').read().split('\nT = []')[0])
D = json.load(open('out.json')); T = D['threads']; Q = D['q']
rows = {z['thread_id']: z for z in rows}
def qq(xs): a = st.quantiles(xs, n=4, method='inclusive'); return f'{a[0]:.0f} / {st.median(xs):.0f} / {a[2]:.0f}'
print('chars/thread', qq([t['chars'] for t in T])); print('words/thread', qq([t['words'] for t in T]))
print('posts/thread', qq([t['n_posts'] for t in T])); cpp = [c for t in T for c in t['chars_per_post']]; print('chars/post', qq(cpp), len(cpp))
print('first post chars', qq([t['chars_per_post'][0] for t in T]))
print('posts dist', sorted(collections.Counter(t['n_posts'] for t in T).items()))
# parts
P = [t for t in T if t['parts']]
form = collections.Counter()
for t in P:
    s = ' '.join(t['part_labels'])
    form['n/m' if re.search(r'\d\s*/\s*[\dn]', s) else 'part' if re.search(r'part', s, re.I) else 'cont']+=1
print('parts', len(P), form)
print('titled posts', sum(1 for t in T if any(x.strip() for x in t['titles'])), 'title has Response/Reviewer', sum(1 for t in T if any(re.search('respon|reviewer|rebuttal|answer', x, re.I) for x in t['titles'])))
tc = collections.Counter()
for t in T:
    for x in t['titles']:
        x2 = re.sub(r'[A-Za-z0-9]{4}$|Reviewer \w{4}', 'Reviewer X', x)
        tc[re.sub(r'\s*[\(\[].*', '', x2).strip()[:40]] += 1
print(tc.most_common(12))
# heading scheme
sch = collections.Counter()
for t in T:
    if t['qsegs']: sch['numbered:' + t['q_first_mark']] += 1
    elif t['kinds'].get('blockquote'): sch['quote, no number'] += 1
    elif t['kinds'].get('md_heading'): sch['md heading, topic'] += 1
    elif t['kinds'].get('bold_topic_leadin'): sch['bold topic'] += 1
    else: sch['none'] += 1
print('scheme', sch)
print('quote anywhere', sum(1 for t in T if t['kinds'].get('blockquote')), 'answer labels', sum(1 for t in T if any(ANSLAB.search(l) for l in '\n'.join(split_post(p['text'])[1] for p in rows[t['id']]['author_posts']).split('\n'))))
print('ids', collections.Counter(''.join(t['q_ids']) for t in T if t['qsegs']))
print('q per thread', qq([t['qsegs'] for t in T if t['qsegs']]))
print('words/seg', qq([s['words'] for s in Q]), 'words per q thread', qq([t['words_per_q'] for t in T if t['qsegs']]))
print('notes words/pt', qq([n['median_words_per_point'] for n in notes.values() if isinstance(n.get('median_words_per_point'),(int,float))]), 'notes n_points', qq([n['n_points'] for n in notes.values() if isinstance(n.get('n_points'),(int,float))]))
for k in ['thanks_any','has_num','has_ptr','has_rev','has_table','quoted']: print(k, sum(s[k] for s in Q), len(Q))
short = [s for s in Q if s['words'] < 60]; print('short<60', len(short), 'of', len(Q), 'ge150', sum(s['words']>=150 for s in Q))
# tables
tb = [t for t in T if t['has_table']]; print('tables', len(tb), 'count/thread among', qq([t['tables'] for t in tb]))
hold = collections.Counter()
for n in notes.values():
    tb_ = n.get('tables'); tb_ = tb_ if isinstance(tb_, dict) else {'holds': str(tb_), 'count': 0 if not tb_ or str(tb_).startswith(('0','none')) else 1}
    h = str(tb_.get('holds', '') or '')
    if tb_.get('count', 0):
        for k, rx in {'results/benchmark': 'result|accura|score|perform|benchmark|metric|compar|baseline|F1|AUC|loss|error', 'ablation/sweep': 'ablat|sweep|hyper|sensitiv|varying|grid', 'cost/runtime': 'time|runtime|cost|memory|flop|latency|speed|GPU', 'baseline': 'baseline|vs|against'}.items():
            if re.search(rx, h, re.I): hold[k] += 1
print('holds', hold, len(notes))
# pointers
for k in PTR: print('ptr', k, sum(t['ptr_' + k] for t in T))
allt = '\n'.join(split_post(p['text'])[1] for z in rows.values() for p in z['author_posts'])
ph = collections.Counter(m.group(0).lower() for m in re.finditer(r'(?:in|to|of) (?:the|our) (?:revised|updated|rebuttal|new) (?:version|manuscript|paper|pdf|draft|submission|revision)(?: of (?:the|our) (?:paper|manuscript))?', allt, re.I))
print(ph.most_common(10))
ph2 = collections.Counter(m.group(0).lower() for m in re.finditer(r'(?:highlighted|marked|colou?red|shown|written|in) (?:in )?(?:blue|red|green|orange|purple)(?: text| font| color| colour)?', allt, re.I)); print(ph2.most_common(8))
ph3 = collections.Counter(m.group(0) for m in re.finditer(r'\b(?:[Ll]ines?|L)\s?\d{2,4}(?:\s?[-–]\s?\d{2,4})?', allt)); print(sum(ph3.values()), collections.Counter(re.sub(r'\d+','N',k) for k in ph3.elements()).most_common(6))
# general response
G = [rows[t['id']]['general_response'] for t in T if rows[t['id']]['general_response']]
Gb = [split_post(g)[1] for g in G]
print('GR', len(G), qq([len(b) for b in Gb]), 'words', qq([words(b) for b in Gb]))
for k, rx in {'bullets': r'^\s*(?:[-*•]|\d+[.)])\s', 'table': r'^\s*\|?\s*:?-{3,}', 'md_heading': r'^\s*#{1,4}\s', 'bold_lead': r'^\s*(?:[-*]\s*)?\*\*', 'location': r'\b(?:Appendix|Section|Sec\.|Table|Figure|Fig\.|Line|L\d)', 'colour': r'\b(?:blue|red)\b|highlight', 'summary_word': r'summar|revision|changes|updated|revised', 'thanks': r'thank|grateful|apprec', 'strengths_recap': r'reviewers? (?:\w+ )?(?:found|noted|recogni[sz]ed|acknowledged|appreciated|highlighted|agree)'}.items():
    print('GR', k, sum(1 for b in Gb if re.search(rx, b, re.I | re.M)))
gt = collections.Counter(re.sub(r'\s+', ' ', split_post(g)[0]).strip()[:45] for g in G); print(gt.most_common(12))
# openings and closings
oc = collections.Counter()
for t in T:
    s = t['open']
    oc['thanks' if THANKS.search(s) else 'label/quote' if t['open_label'] else 'other'] += 1
print('open', oc, 'dear', sum(t['open_dear'] for t in T))
o3 = collections.Counter(' '.join(strip_md(t['open']).split()[:3]) for t in T); print(o3.most_common(10))
cl = collections.Counter()
for z in rows.values():
    b = split_post(z['author_posts'][-1]['text'])[1]; tail = b[-400:]
    cl['invite' if INVITE.search(tail) else 'thanks' if THANKS.search(tail) else 'score' if SCORE.search(tail) else 'answer'] += 1
print('close last post tail', cl)
cf = collections.Counter()
for z in rows.values():
    b = split_post(z['author_posts'][0]['text'])[1]; tail = b[-400:]
    cf['invite' if INVITE.search(tail) else 'thanks' if THANKS.search(tail) else 'score' if SCORE.search(tail) else 'answer'] += 1
print('close first post tail', cf)
c3 = collections.Counter(' '.join(strip_md(t['close']).split()[:4]) for t in T); print(c3.most_common(10))
