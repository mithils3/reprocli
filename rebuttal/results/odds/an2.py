import json,sys,math,statistics as st
M=sys.argv[1]; P=[json.loads(l) for l in open(f'{M}/papers.jsonl')]
def wil(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return (100*(c-h),100*(c+h))
def show(lab,rows):
    k=sum(r['acc'] for r in rows); n=len(rows)
    if n==0: print(f"    {lab:<62} none"); return
    lo,hi=wil(k,n); print(f"    {lab:<62} {k:>4}/{n:<4} {100*k/n:5.1f}% [{lo:4.1f}, {hi:4.1f}]")
LO={2024:5,2025:5,2026:4}
def band(r): lo=LO[r['year']]; R=r['R']; return R.count(lo)==1 and R.count(6)==len(R)-1 and len(R)>=3
def li(r): return r['R'].index(LO[r['year']])
def split(lab,rows,f):
    print('  '+lab)
    vals=sorted(set(f(r) for r in rows),key=str)
    for v in vals: show(str(v),[r for r in rows if f(r)==v])
for name,B in [('2026, all-but-one weak accept (n reviews >= 3)',[r for r in P if r['year']==2026 and band(r)]),
               ('2024+2025, same band',[r for r in P if r['year']<2026 and band(r)])]:
    print('=====',name,len(B))
    split('reviews',B,lambda r: min(len(r['R']),5))
    split('low reviewer confidence',B,lambda r: r['C'][li(r)])
    split('low reviewer confidence vs highest positive confidence',B,lambda r: 'low more sure' if r['C'][li(r)]>max(c for i,c in enumerate(r['C']) if i!=li(r)) else ('equal' if r['C'][li(r)]==max(c for i,c in enumerate(r['C']) if i!=li(r)) else 'low less sure'))
    split('primary area is datasets and benchmarks',B,lambda r: r['area']=='datasets and benchmarks')
    split('low reviewer contribution score',B,lambda r: r['contribution'][li(r)] if len(r['contribution'])==len(r['R']) else None)
    split('min soundness across reviewers',B,lambda r: min(r['soundness']) if r['soundness'] else None)
    split('mean presentation >= 3',B,lambda r: (st.mean(r['presentation'])>=3) if r['presentation'] else None)
    split('mean contribution (rounded 0.5)',B,lambda r: round(2*st.mean(r['contribution']))/2 if r['contribution'] else None)
    E=[r for r in B if 'rev_replied' in r]
    if E:
        split('low reviewer posted a comment in the discussion',E,lambda r: r['rev_replied'][li(r)])
        split('positive reviewers who posted (share)',E,lambda r: ('none' if not any(x for i,x in enumerate(r['rev_replied']) if i!=li(r)) else ('all' if all(x for i,x in enumerate(r['rev_replied']) if i!=li(r)) else 'some')))
        split('no reviewer posted at all',E,lambda r: not any(r['rev_replied']))
        split('author comments (bucket)',E,lambda r: '0' if r['author_comments']==0 else ('1-5' if r['author_comments']<=5 else ('6-15' if r['author_comments']<=15 else '16+')))
