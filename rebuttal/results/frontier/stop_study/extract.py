import gzip,json,glob,csv,random,os,sys
R='/home/mithil/PyCharmProjects/reprocli/'; O=sys.argv[1]
cells=[x for x in csv.DictReader(open(R+'rebuttal/results/databook/frontier_cells.csv')) if 'x86' not in x['arm'] and 'nudge' not in x['arm']]
papers=sorted({x['paper'] for x in cells})
fr=json.load(open(R+'tools/anon_viewer/public/data/frontier.json'))['runs']
items=[]
for f in sorted(glob.glob(R+'tools/anon_viewer/public/data/frontier/*.json.gz')):
    b=os.path.basename(f)[:-8]
    if 'x86' in b or 'loop' in b and 'sol-loop' in b and False: continue
    items.append(('frontier',f))
for p in papers:
    for a in ('dsv4','muse'):
        g=glob.glob(R+f'tools/anon_viewer/public/data/runs/{a}-*-{p}.json.gz')
        if g: items.append(('open',g[0]))
rows=[]
for grp,f in items:
    d=json.load(gzip.open(f)); run=d['run']; ev=d['events']
    if grp=='frontier' and ('x86' in run['id'] or 'nudge' in run.get('sweep','')+run['id'] or 'prompt' in run['id']): continue
    msgs=[e for e in ev if e['kind'] in('round_open','final') and (e.get('content') or '').strip()]
    calls=[e for e in ev if e['kind']=='call_start']
    gpu=[(e.get('command') or str(e.get('args') or ''))[:170] for e in calls if 'run_gpu' in (e.get('command') or '') or e.get('tool_name')=='run_gpu']
    rows.append(dict(grp=grp,run=run['id'],paper=run['arxiv_id'],tier=run['tier'],budget=run.get('budget_h100'),spent=run.get('spent_h100'),exit=run.get('exit_label'),score=(run.get('audit') or {}).get('score'),rounds=run.get('rounds'),n_calls=len(calls),n_gpu=len(gpu),msgs=msgs,gpu=gpu,last_calls=[(e.get('command') or str(e.get('args') or ''))[:200] for e in calls[-6:]]))
random.Random(22528).shuffle(rows)
key=csv.writer(open(O+'/key.csv','w')); key.writerow(['rid','group','run','paper','tier','budget','spent','exit','score','n_gpu'])
N=10; sh={}
for i,r in enumerate(rows):
    rid=f'r{i+1:03d}'; key.writerow([rid,r['grp'],r['run'],r['paper'],r['tier'],r['budget'],r['spent'],r['exit'],r['score'],r['n_gpu']])
    t=[f'=== RUN {rid} ===',f"tier: {r['tier']}; GPU grant: {r['budget']} H100-hours; spent: {r['spent']}; how the run ended (harness label): {r['exit']}; assistant turns: {r['rounds']}; tool calls: {r['n_calls']}; GPU commands: {r['n_gpu']}"]
    t.append('--- GPU commands (first 12 and last 4, truncated) ---'); g=r['gpu']; t+= [' * '+c.replace('\n',' ') for c in (g if len(g)<=16 else g[:12]+['...']+g[-4:])]
    t.append('--- last 6 tool commands ---'); t+=[' * '+c.replace('\n',' ') for c in r['last_calls']]
    t.append('--- last assistant messages, oldest first (truncated) ---')
    for m in r['msgs'][-5:-1]: t.append('[message] '+m['content'][:1500])
    if r['msgs']: t.append('[FINAL message] '+r['msgs'][-1]['content'][:3500])
    sh.setdefault(i//N,[]).append('\n'.join(t))
for k,v in sh.items(): open(O+f'/shards/shard_{k:02d}.txt','w').write('\n\n'.join(v)+'\n')
import collections; print(len(rows),collections.Counter(r['grp'] for r in rows),len(sh),'shards'); print([os.path.getsize(O+f'/shards/shard_{k:02d}.txt') for k in sh])
