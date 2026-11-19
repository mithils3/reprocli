import json,sys,math,random,statistics as st
import numpy as np
M=sys.argv[1]; B=json.load(open(f'{M}/band.json'))
CON={}
for l in open(f'{M}/papers.jsonl'):
    x=json.loads(l); CON[x['id']]=x['contribution']
for r in B: r['contribution']=CON.get(r['id'],[])
LO={2024:5,2025:5,2026:4}
li=lambda r: r['R'].index(LO[r['year']])
def pos(r,k): return [x for i,x in enumerate(r[k]) if i!=li(r)]
def fit(X,y,lam=1.0):
    X=np.c_[np.ones(len(X)),X]; w=np.zeros(X.shape[1])
    for _ in range(50):
        p=1/(1+np.exp(-X@w)); g=X.T@(y-p)-lam*np.r_[0,w[1:]]; H=-(X.T*(p*(1-p)))@X-lam*np.diag(np.r_[0,np.ones(len(w)-1)])
        w=w-np.linalg.solve(H,g)
    return w
def run(name,rows,F,ours,base_filter):
    X=np.array([[f(r) for f in F.values()] for r in rows],float); y=np.array([r['acc'] for r in rows],float)
    w=fit(X,y); ref=np.array([[f(r) for f in F.values()] for r in rows if base_filter(r)],float)
    o=np.array([ours[k] if ours[k] is not None else ref[:,i].mean() for i,k in enumerate(F)],float)
    def offset(w): return float(np.r_[1,o]@w - np.mean(np.c_[np.ones(len(ref)),ref]@w))
    boots=[]; rng=random.Random(22528)
    for _ in range(300):
        idx=[rng.randrange(len(rows)) for _ in rows]; boots.append(offset(fit(X[idx],y[idx])))
    boots.sort()
    print(f'== {name}: n={len(rows)}, accepted {int(y.sum())}')
    for k,c in zip(F,w[1:]): print(f'   {k:<48} coef {c:+.2f}   ours={ours[k]}')
    print(f'   our log-odds offset vs the average {"3-review " if True else ""}paper in the reference group: {offset(w):+.2f}  [95% bootstrap {boots[7]:+.2f}, {boots[292]:+.2f}]')
    return offset(w),boots[7],boots[292]
E=[r for r in B if r['year']<2026]
F1={'4 reviews':lambda r: len(r['R'])==4,'5+ reviews':lambda r: len(r['R'])>=5,'year 2025':lambda r: r['year']==2025,
    'author reply has a table':lambda r: r['table'],'general response':lambda r: r['general'],'author words >= 4,000':lambda r: r['words']>=4000,
    'numbers per 1,000 words > 46':lambda r: r['nums']>46,'low reviewer silent, a positive posted':lambda r: (not r['rev_replied'][li(r)]) and any(pos(r,'rev_replied')),
    'no positive reviewer posted':lambda r: not any(pos(r,'rev_replied')),'positives mean confidence <= 3':lambda r: st.mean(pos(r,'C'))<=3,
    'area datasets and benchmarks':lambda r: r['area']=='datasets and benchmarks','low review < 300 words':lambda r: r['wc'][li(r)]<300 if len(r['wc'])==len(r['R']) else 0}
ours1={'4 reviews':0,'5+ reviews':0,'year 2025':None,'author reply has a table':1,'general response':1,'author words >= 4,000':0,'numbers per 1,000 words > 46':1,
       'low reviewer silent, a positive posted':1,'no positive reviewer posted':0,'positives mean confidence <= 3':1,'area datasets and benchmarks':1,'low review < 300 words':0}
a=run('2024+25 band, rebuttal and engagement factors',E,F1,ours1,lambda r: len(r['R'])==3)
N=[r for r in B if r['year']==2026 and len(r['wc'])==len(r['R'])]
F2={'4 reviews':lambda r: len(r['R'])==4,'5+ reviews':lambda r: len(r['R'])>=5,'positives mean confidence <= 3':lambda r: st.mean(pos(r,'C'))<=3,
    'area datasets and benchmarks':lambda r: r['area']=='datasets and benchmarks','low review < 300 words':lambda r: r['wc'][li(r)]<300,
    'low reviewer contribution <= 1':lambda r: (r['contribution'][li(r)]<=1) if len(r['contribution'])==len(r['R']) else 0,
    'mean contribution >= 2.5':lambda r: st.mean(r['contribution'])>=2.5 if r['contribution'] else 0}
ours2={'4 reviews':0,'5+ reviews':0,'positives mean confidence <= 3':1,'area datasets and benchmarks':1,'low review < 300 words':0,'low reviewer contribution <= 1':1,'mean contribution >= 2.5':0}
b=run('2026 band, review factors',N,F2,ours2,lambda r: len(r['R'])==3)
sig=lambda z:1/(1+math.exp(-z)); lg=lambda p: math.log(p/(1-p))
print('\nApplied to the 2027 base rate for 3,3,2 (from an3: 69/65/58/52% at 32/30/27/25% acceptance):')
for rate,base in ((32,.69),(30,.65),(27,.58),(25,.52)):
    for lab,off in (('rebuttal model only',a[0]),('both models added',a[0]+b[0])):
        print(f'   {rate}% accepted: base {100*base:.0f}% -> {lab}: {100*sig(lg(base)+off):.0f}%')
