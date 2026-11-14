import json, sys, statistics as st, re
from collections import Counter
raw = open(sys.argv[1]).read()
d = json.loads(raw)['result']
if isinstance(d, str): d = json.loads(d)
json.dump(d, open('out/result.json', 'w'), indent=1)
key = json.load(open('key.json'))
rows = []
for j in d['judged']:
    for t in j['threads']:
        g = key.get(t['id'], {}).get('group', '?')
        rows.append(dict(t, shard=j['shard'], rank=(j['ranking'].index(t['id']) + 1 if t['id'] in j['ranking'] else None), group=g, n=len(j['threads'])))
print('shards', len(d['judged']), 'rows', len(rows), Counter(r['group'] for r in rows))
def auc(pos, neg):
    w = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg); return w / (len(pos) * len(neg))
R = [r for r in rows if r['group'] == 'raised']; U = [r for r in rows if r['group'] == 'unchanged']; O = [r for r in rows if r['group'] == 'ours']
print('\nValidity: do blind scores separate raised from unchanged? AUC (0.5 = chance)')
for k in ['overall', 'p_convinced', 'coverage', 'evidence', 'clarity', 'tone']:
    print(f'  {k:12s} AUC {auc([r[k] for r in R],[r[k] for r in U]):.3f}  mean raised {st.mean(r[k] for r in R):.2f} unchanged {st.mean(r[k] for r in U):.2f} ours {st.mean(r[k] for r in O):.2f}')
print(f"  rank (lower better) AUC {auc([-r['rank'] for r in R if r['rank']],[-r['rank'] for r in U if r['rank']]):.3f}  mean rank raised {st.mean(r['rank'] for r in R if r['rank']):.2f} unchanged {st.mean(r['rank'] for r in U if r['rank']):.2f}")
# within-shard: mean rank of the raised vs unchanged
print('\nOurs: rank within each shard of 9:', sorted(Counter(r['rank'] for r in O).items()))
print('ours mean rank', st.mean(r['rank'] for r in O), 'first in', sum(r['rank'] == 1 for r in O), 'of', len(O), '; top 2 in', sum(r['rank'] <= 2 for r in O), '; top 3 in', sum(r['rank'] <= 3 for r in O))
C = R + U
for k in ['overall', 'p_convinced', 'coverage', 'evidence', 'clarity', 'tone']:
    m = st.mean(r[k] for r in O)
    pct = sum(c[k] < m for c in C) / len(C) * 100
    pr = sum(c[k] < m for c in R) / len(R) * 100
    print(f'  {k:12s} ours mean {m:.2f} (min {min(r[k] for r in O)}, max {max(r[k] for r in O)}); above {pct:.0f}% of the 240 real replies, {pr:.0f}% of the raised ones')
print('ours n_points', Counter(r['n_points'] for r in O), 'n_direct', Counter(r['n_direct'] for r in O))
print('\nWhere ours lost: shards where ours was not first')
for r in O:
    if r['rank'] != 1: print('  shard', r['shard'], 'rank', r['rank'], 'overall', r['overall'], 'clarity', r['clarity'], 'tone', r['tone'])
print('\nWeakness sentences for ours:')
for r in O: print('  -', r['weakness'])
words = Counter()
for r in O:
    for w, pat in [('dense', r'dens|long|jargon|shorthand|hard to|heavy|overload|verify'), ('claude code', r'claude code'), ('sample', r'subset|sample|preselect|small|few papers|6 |2 papers|coverage'), ('claims/extrap', r'extrapol|limited|modest|only'), ('tone', r'tone|defensive|cold')]:
        if re.search(pat, r['weakness'], re.I): words[w] += 1
print('themes', words)
print('\nHead to head (fable, ours vs 5 top real replies):')
for h in d['h2h']:
    rk = h['ranking']; oid = h['ours_id']; rk = [x.replace('.txt', '') for x in rk]
    print(' set', h['set'], 'ours rank', rk.index(oid) + 1, 'of', len(rk), [key.get(x, {}).get('group') for x in rk])
    for x in h['replies']:
        if x['id'].replace('.txt', '') == oid:
            print('   strongest:', x['strongest_move']); print('   weakness:', x['biggest_weakness']); print('   would move:', x['would_move_reviewer']); [print('   edit:', e) for e in x['best_edits']]
    print('   transferable:'); [print('    *', m) for m in h['transferable_moves']]
print('\nPointers:', json.dumps(d['pointers'], indent=1)[:3000])
print('\nAUDIT reviewer summary:\n', d['audit_reviewer']); print('\nAUDIT AC summary:\n', d['audit_ac'])
