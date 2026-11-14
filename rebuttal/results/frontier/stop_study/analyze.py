import json,csv,glob,collections,math,sys
S=sys.argv[1]
def wil(k,n,z=1.959964):
    if n==0: return 'n/a'
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return f"{k}/{n} = {100*p:.0f}% [{100*(c-h):.0f}%, {100*(c+h):.0f}%]"
key={r['rid']:r for r in csv.DictReader(open(S+'/key.csv'))}
codes={}
for f in sorted(glob.glob(S+'/codes/*.jsonl')):
    for l in open(f):
        l=l.strip()
        if l:
            d=json.loads(l); codes[d['rid']]=d
print('coded',len(codes),'of',len(key),'missing',sorted(set(key)-set(codes))[:12])
rows=[dict(key[r],**codes[r]) for r in codes if r in key]
for r in rows: r['rep']=int(r['score'] or 0)>=8; r['share']=float(r['spent'] or 0)/float(r['budget'] or 1)
out=[]
def tab(name,sel):
    out.append(f'\n## {name}')
    for g in ('frontier','open'):
        xs=[r for r in rows if r['group']==g and sel(r)]
        c=collections.Counter(r['stop_reason'] for r in xs)
        out.append(f'{g}: n={len(xs)}; '+'; '.join(f'{k} {wil(v,len(xs))}' for k,v in c.most_common()))
        for b in ('admits_not_reproduced','reduced_scale','estimates_full_cost','mentions_unused_budget','lists_next_steps','trained_model'):
            out.append(f'   {b}: {wil(sum(bool(r.get(b)) for r in xs),len(xs))}')
tab('all runs',lambda r:True)
tab('runs not reproduced',lambda r:not r['rep'])
tab('not reproduced, Retrain and Reimplement',lambda r:not r['rep'] and r['tier']!='run')
tab('not reproduced and under 10% of grant spent',lambda r:not r['rep'] and r['share']<0.10)
out.append('\n## quotes, frontier runs not reproduced')
for r in sorted(rows,key=lambda r:r['stop_reason']):
    if r['group']=='frontier' and not r['rep']: out.append(f"- {r['rid']} {r['run']} [{r['stop_reason']}; {100*r['share']:.1f}% of grant]: {r.get('quote','')[:200]}")
open(S+'/summary.md','w').write('\n'.join(out)+'\n'); print('\n'.join(out[:60]))
