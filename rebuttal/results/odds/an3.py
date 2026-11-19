import json,sys,math,collections,statistics as st
M=sys.argv[1]
raw=json.load(open(f'{M}/raw/iclr2026.json'))
main=[p for p in raw if p.get('track','main')=='main']
sc=collections.Counter(p['status'] for p in main); print('2026 main statuses',dict(sc))
sub26=len(main); P=[json.loads(l) for l in open(f'{M}/papers.jsonl')]; P26=[r for r in P if r['year']==2026]
acc26=sum(r['acc'] for r in P26); print(f'2026: submissions {sub26}, decided {len(P26)}, accepted {acc26} = {100*acc26/sub26:.1f}% of submissions, {100*acc26/len(P26):.1f}% of decided')
conv={0:1,1:1,2:1,3:2,4:2,5:2,6:3,7:3,8:4,9:4,10:4}
def key(R): return round(st.mean(R),2)
lv=collections.defaultdict(lambda:[0,0])
for r in P26:
    R=[conv[x] for x in r['R']]; k=key(R); lv[k][0]+=r['acc']; lv[k][1]+=1
# 2027
d=json.load(open(f'{M}/raw/dipta007.github.io_iclr-2027-rebuttal-radar_data_papers.json'))
rows=[dict(zip(d['columns'],x)) for x in d['rows']]; rows=[x for x in rows if x['ratings']]
c27=collections.Counter(key(x['ratings']) for x in rows); N27=len(rows); SUB27=42789
print(f'2027 active with ratings {N27}')
print('\n2026 acceptance by mean on the 2027 scale (0,2->1, 4->2, 6->3, 8,10->4)  |  2027 papers now')
for k in sorted(set(lv)|set(c27),reverse=True):
    if 2.2<=k<=3.4: a,n=lv.get(k,[0,0]); print(f'  {k:4.2f}: 2026 {a:>5}/{n:<5} {100*a/max(n,1):5.1f}%   2027 {c27.get(k,0):>6}')
def logit(p): p=min(max(p,1e-4),1-1e-4); return math.log(p/(1-p))
sig=lambda z:1/(1+math.exp(-z))
base={k:(lv[k][0]+0.5)/(lv[k][1]+1) for k in lv}
def rate_for(k):  # nearest 2026 level
    kk=min(base,key=lambda b:abs(b-k)); return base[kk]
implied=sum(c27[k]*rate_for(k) for k in c27)
print(f'\nmodel A (2026 rate per mean level, applied to 2027 counts): {implied:.0f} accepts = {100*implied/SUB27:.1f}% of submissions; rate at 2.67: {100*rate_for(2.67):.1f}%')
for target in (.32,.30,.27,.25,.22,.20):
    T=target*SUB27; lo,hi=-10,10
    for _ in range(80):
        s=(lo+hi)/2; tot=sum(c27[k]*sig(logit(rate_for(k))+s) for k in c27)
        lo,hi=(s,hi) if tot<T else (lo,s)
    print(f'  if {int(target*100)}% of submissions accepted ({T:.0f}): shift {s:+.2f}, rate at 2.67 = {100*sig(logit(rate_for(2.67))+s):.1f}%, at 2.75 = {100*sig(logit(rate_for(2.75))+s):.1f}%, at 2.33 = {100*sig(logit(rate_for(2.33))+s):.1f}%')
# model B: percentile matching among papers still active
m26=sorted([st.mean(r['R']) for r in P26],reverse=True)
def pct_rows(vals,k): above=sum(1 for v in vals if v>k+1e-9); tie=sum(1 for v in vals if abs(v-k)<1e-9); return above,tie
m27=[st.mean(x['ratings']) for x in rows]; a,t=pct_rows(m27,8/3)
print(f'\nmodel B: 2027 2.67 band spans ranks {a+1}..{a+t} of {N27} active = top {100*a/N27:.1f}% to {100*(a+t)/N27:.1f}%')
for frac_decided in (1.0,0.9,0.85):
    D=N27*frac_decided  # later withdrawals assumed to come from below the band
    lo_,hi_=a/D,(a+t)/D
    order=sorted(P26,key=lambda r:-st.mean(r['R'])); n=len(order)
    seg=order[int(lo_*n):int(hi_*n)]; acc=sum(r['acc'] for r in seg)
    print(f'  if {int(frac_decided*100)}% of active papers reach a decision: 2.67 band = top {100*lo_:.1f}% to {100*hi_:.1f}% of decided; 2026 papers at that rank: {acc}/{len(seg)} = {100*acc/len(seg):.1f}% accepted')
