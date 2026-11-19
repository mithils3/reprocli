import json,sys,re,math
M=sys.argv[1]; P=[json.loads(l) for l in open(f'{M}/papers.jsonl')]
B=[r for r in P if r['year']==2024 and r.get('meta') and len(r['R'])>=3 and r['R'].count(5)==1 and r['R'].count(6)==len(r['R'])-1]
A=[r for r in B if r['acc']]; R=[r for r in B if not r['acc']]
print(f'2024 meta-reviews for all-but-one weak accept papers: {len(A)} accepted, {len(R)} rejected')
pats={'rebuttal addressed / resolved concerns':r'(addressed|resolved|alleviat|clarified)[^.]{0,60}(concern|question|issue)',
 'concerns remain / not fully addressed':r'(remain|not (fully|sufficiently|adequately) (addressed|resolved)|unresolved|outstanding concern)',
 'novelty / incremental / limited contribution':r'(novelty|incremental|limited (contribution|technical|novel))',
 'experiments insufficient / more experiments needed':r'(insufficient|limited|lack)[^.]{0,40}(experiment|evaluation|baseline|empirical)',
 'reviewer did not respond or engage':r'(did not (respond|engage|reply)|unresponsive|no response|not respond|did not update)',
 'AC discounts or downweights a review':r'(discount|down-?weight|less weight|not convinc[^.]{0,30}review|review[^.]{0,40}(unfair|unjustified|superficial|low.quality))',
 'AC champions / reviewer championed':r'(champion|strong(ly)? support|enthusias)',
 'mentions benchmark or dataset':r'(benchmark|dataset)',
 'presentation / clarity / writing problems':r'(clarity|presentation|writing|hard to follow|unclear)',
 'theory / proof concerns':r'(proof|theoretical|theorem)',
 'borderline':r'borderline',
 'lukewarm / no reviewer excited':r'(lukewarm|no reviewer|none of the reviewers|not excit|enthusiasm)'}
def wil(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return (100*(c-h),100*(c+h))
print(f"  {'phrase in meta-review':<52} {'accepted':>9} {'rejected':>9}   accept rate when present")
for lab,rx in pats.items():
    a=sum(bool(re.search(rx,r['meta'],re.I)) for r in A); b=sum(bool(re.search(rx,r['meta'],re.I)) for r in R)
    n=a+b; lo,hi=wil(a,n) if n else (0,0)
    print(f"  {lab:<52} {100*a/len(A):8.0f}% {100*b/len(R):8.0f}%   {a}/{n} [{lo:.0f}, {hi:.0f}]")
import random; random.seed(22528)
for grp,name in ((R,'REJECTED'),(A,'ACCEPTED')):
    for r in random.sample(grp,3):
        m=re.sub(r'\s+',' ',r['meta']); print(f'\n--- {name} {r["R"]} area={r["area"]}\n{m[:700]}')
