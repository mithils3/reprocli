import json,sys,math,collections,statistics as st
M=sys.argv[1]; P=[json.loads(l) for l in open(f'{M}/papers.jsonl')]
conv={0:1,1:1,2:1,3:2,4:2,5:2,6:3,7:3,8:4,9:4,10:4}
logit=lambda p: math.log(p/(1-p)); sig=lambda z:1/(1+math.exp(-z))
def wil(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return (100*(c-h),100*(c+h))
pat=collections.defaultdict(lambda:[0,0])
for r in P:
    if r['year']!=2026: continue
    R=tuple(sorted((conv[x] for x in r['R']),reverse=True))
    if abs(st.mean(R)-8/3)<1e-9: pat[R][0]+=r['acc']; pat[R][1]+=1
d=json.load(open(f'{M}/raw/dipta007.github.io_iclr-2027-rebuttal-radar_data_papers.json'))
rows=[dict(zip(d['columns'],x)) for x in d['rows']]
c27=collections.Counter(tuple(sorted(x['ratings'],reverse=True)) for x in rows if x['ratings'] and abs(st.mean(x['ratings'])-8/3)<1e-9)
print('patterns at mean 2.67 (2027 scale): 2026 accepted | 2027 papers now')
for R in sorted(set(pat)|set(c27),key=lambda R:-(c27.get(R,0))):
    a,n=pat.get(R,[0,0]); lo,hi=wil(a,n) if n else (0,0)
    print(f'  {str(R):<22} 2026 {a:>4}/{n:<4} {100*a/max(n,1):5.1f}% [{lo:4.1f},{hi:4.1f}]   2027 {c27.get(R,0)}')
lvl=sum(v[0] for v in pat.values())/sum(v[1] for v in pat.values()); p332=pat[(3,3,2)][0]/pat[(3,3,2)][1]
print(f'3,3,2 vs whole 2.67 level in 2026: logit {logit(p332)-logit(lvl):+.2f}')
# engagement, 2024/25 band, 3-review only
LO={2024:5,2025:5}
B=[r for r in P if r['year']<2026 and 'rev_replied' in r and len(r['R'])==3 and r['R'].count(LO[r['year']])==1 and r['R'].count(6)==2]
def show(lab,rows):
    k=sum(r['acc'] for r in rows); n=len(rows); lo,hi=wil(k,n); print(f'  {lab:<60} {k:>3}/{n:<3} {100*k/n:5.1f}% [{lo:4.1f},{hi:4.1f}]')
print(f'\n2024+2025 papers ending 6,6,5 with 3 reviews (n={len(B)})')
li=lambda r: r['R'].index(5)
for lab,f in [('low reviewer silent, at least one positive reviewer posted',lambda r: not r['rev_replied'][li(r)] and any(x for i,x in enumerate(r['rev_replied']) if i!=li(r))),
              ('low reviewer silent, no positive reviewer posted',lambda r: not r['rev_replied'][li(r)] and not any(x for i,x in enumerate(r['rev_replied']) if i!=li(r))),
              ('low reviewer posted, at least one positive posted',lambda r: r['rev_replied'][li(r)] and any(x for i,x in enumerate(r['rev_replied']) if i!=li(r))),
              ('low reviewer posted, no positive posted',lambda r: r['rev_replied'][li(r)] and not any(x for i,x in enumerate(r['rev_replied']) if i!=li(r))),
              ('exactly one of the two positive reviewers posted, low silent',lambda r: not r['rev_replied'][li(r)] and sum(x for i,x in enumerate(r['rev_replied']) if i!=li(r))==1)]:
    show(lab,[r for r in B if f(r)])
# same for whole 2024/25 band any size
B2=[r for r in P if r['year']<2026 and 'rev_replied' in r and len(r['R'])>=3 and r['R'].count(5)==1 and r['R'].count(6)==len(r['R'])-1]
print(f'\nsame, any number of reviews (n={len(B2)})')
for lab,f in [('low silent, some positive posted',lambda r: not r['rev_replied'][r['R'].index(5)] and any(x for i,x in enumerate(r['rev_replied']) if i!=r['R'].index(5))),
              ('low posted',lambda r: r['rev_replied'][r['R'].index(5)]),
              ('nobody posted',lambda r: not any(r['rev_replied']))]:
    show(lab,[r for r in B2 if f(r)])
