import json,sys,re,math,collections,statistics as st
import pyarrow.dataset as ds
M=sys.argv[1]; P=[json.loads(l) for l in open(f'{M}/papers.jsonl')]
def wil(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return (100*(c-h),100*(c+h))
def show(lab,rows):
    if not rows: print(f'    {lab:<56} none'); return
    k=sum(r['acc'] for r in rows); n=len(rows); lo,hi=wil(k,n); print(f'    {lab:<56} {k:>4}/{n:<4} {100*k/n:5.1f}% [{lo:4.1f},{hi:4.1f}]')
LO={2024:5,2025:5,2026:4}
band=lambda r: len(r['R'])>=3 and r['R'].count(LO[r['year']])==1 and r['R'].count(6)==len(r['R'])-1
B=[r for r in P if band(r)]; ids={r['id'] for r in B if r['year']<2026}
# author text features for 2024/25 band
d=ds.dataset('/home/mithil/.cache/openreview_raw/default/train',format='parquet')
T=collections.defaultdict(list)
for y in (2024,2025):
    t=d.to_table(filter=(ds.field('venue')==f'ICLR.cc/{y}/Conference')&(ds.field('note_type')=='official_comment'),columns=['forum_id','note_signatures','note_text','note_replyto'])
    for x in t.to_pylist():
        if x['forum_id'] in ids and (x['note_signatures'] or [''])[0].endswith('/Authors'): T[x['forum_id']].append(x)
def feats(texts,forum):
    txt='\n'.join(x['note_text'] or '' for x in texts); w=len(txt.split())
    return dict(words=w, table=bool(re.search(r'^\s*\|?\s*:?-{3,}:?\s*\|',txt,re.M)),
                nums=1000*len(re.findall(r'\b\d+(\.\d+)?%?',txt))/max(w,1),
                general=any(x['note_replyto']==forum for x in texts),
                pointers=len(re.findall(r'\b(Appendix|Section|Table|Figure|revised)\b',txt)),
                newexp=bool(re.search(r'(new|additional|extra) (experiment|result|ablation|baseline)|we (ran|conducted|added|include[d]?) (new |additional )?(experiment|ablation|comparison)',txt,re.I)))
for r in B:
    if r['year']<2026: r.update(feats(T.get(r['id'],[]),r['id']))
li=lambda r: r['R'].index(LO[r['year']])
E=[r for r in B if r['year']<2026]; E3=[r for r in E if len(r['R'])==3]
for name,S in (('2024+25 all-but-one weak accept, any size',E),('2024+25 exactly 6,6,5',E3)):
    print(f'== {name} (n={len(S)})')
    q=sorted(r['words'] for r in S); qs=[q[int(len(q)*f)] for f in (.25,.5,.75)]
    print(f'  author words quartiles {qs}')
    show('author words < 1,500',[r for r in S if r['words']<1500]); show('author words 1,500-4,000',[r for r in S if 1500<=r['words']<4000]); show('author words >= 4,000',[r for r in S if r['words']>=4000])
    show('has a markdown table',[r for r in S if r['table']]); show('no table',[r for r in S if not r['table']])
    show('has a general response to all reviewers',[r for r in S if r['general']]); show('no general response',[r for r in S if not r['general']])
    show('reports new experiments (phrase match)',[r for r in S if r['newexp']]); show('no such phrase',[r for r in S if not r['newexp']])
    mn=st.median(r['nums'] for r in S); show(f'numbers per 1,000 words above median {mn:.0f}',[r for r in S if r['nums']>mn]); show('at or below median',[r for r in S if r['nums']<=mn])
for name,S in (('2026 all-but-one weak accept',[r for r in B if r['year']==2026]),('2026 exactly 6,6,4',[r for r in B if r['year']==2026 and len(r['R'])==3]),('2024+25 any size',E)):
    S=[r for r in S if len(r['wc'])==len(r['R'])]
    print(f'== {name}: low reviewer review length (n={len(S)})')
    q=sorted(r['wc'][li(r)] for r in S); print(f'  quartiles {[q[int(len(q)*f)] for f in (.25,.5,.75)]}')
    show('low review < 300 words',[r for r in S if r['wc'][li(r)]<300]); show('300-500',[r for r in S if 300<=r['wc'][li(r)]<500]); show('>= 500',[r for r in S if r['wc'][li(r)]>=500])
    show('low review shorter than every positive review',[r for r in S if r['wc'][li(r)]<min(w for i,w in enumerate(r['wc']) if i!=li(r))])
    show('mean confidence of positives <= 3 (2026 1-5 scale)',[r for r in S if st.mean(c for i,c in enumerate(r['C']) if i!=li(r))<=3])
    show('mean confidence of positives > 3',[r for r in S if st.mean(c for i,c in enumerate(r['C']) if i!=li(r))>3])
json.dump([{k:r[k] for k in ('year','id','acc','R','C','wc','area','words','table','general','newexp','nums','rev_replied','author_comments') if k in r} for r in B],open(f'{M}/band.json','w'))
