import json,sys,math,collections,statistics as st
M=sys.argv[1]; P=[json.loads(l) for l in open(f'{M}/papers.jsonl')]
def wil(k,n,z=1.96):
    if n==0: return (0,0)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return (100*(c-h),100*(c+h))
def show(lab,rows):
    k=sum(r['acc'] for r in rows); n=len(rows); lo,hi=wil(k,n)
    print(f"  {lab:<58} {k:>5}/{n:<5} {100*k/max(n,1):5.1f}% [{lo:4.1f}, {hi:4.1f}]")
LO={2024:5,2025:5,2026:4}
def band(r):  # all reviewers at weak accept except exactly one at weak reject
    lo=LO[r['year']]; R=r['R']; return R.count(lo)==1 and R.count(6)==len(R)-1 and len(R)>=3
for y in (2024,2025,2026):
    Y=[r for r in P if r['year']==y]; B=[r for r in Y if band(r)]
    print(f"== {y}: all decided {len(Y)}, accepted {sum(r['acc'] for r in Y)} ({100*sum(r['acc'] for r in Y)/len(Y):.1f}% of decided)")
    show('band: all weak accept but one weak reject',B)
    show('  3 reviews (like 6,6,5 / 6,6,4)',[r for r in B if len(r['R'])==3])
    show('  4 reviews',[r for r in B if len(r['R'])==4])
    show('  5+ reviews',[r for r in B if len(r['R'])>=5])
    for lab,f in [('mean > band (strictly above, e.g. any 8)',lambda r: st.mean(r['R'])>st.mean([6,6,LO[y]])+1e-9 ),]:
        pass
    m=st.mean([6,6,LO[y]])
    above=[r for r in Y if st.mean(r['R'])>m+1e-9]; at=[r for r in Y if abs(st.mean(r['R'])-m)<1e-9]
    show(f'mean strictly above {m:.2f}',above); show(f'mean exactly {m:.2f} (any pattern)',at)
    at3=[r for r in at if len(r['R'])==3]
    for pat in sorted(set(tuple(sorted(r['R'],reverse=True)) for r in at3)): show(f'    pattern {pat}',[r for r in at3 if tuple(sorted(r['R'],reverse=True))==pat])
