import json,sys,collections
import pyarrow.dataset as ds
M=sys.argv[1]
ACC={'Poster','Spotlight','Oral'}
eng={}
d=ds.dataset('/home/mithil/.cache/openreview_raw/default/train',format='parquet')
for y in (2024,2025):
    t=d.to_table(filter=ds.field('venue')==f'ICLR.cc/{y}/Conference',columns=['forum_id','note_type','note_signatures','note_text','note_replyto','note_id'])
    for r in t.to_pylist():
        e=eng.setdefault(r['forum_id'],{'rev_commenters':set(),'author_comments':0,'author_chars':0,'reviewer_comments':0,'meta':None,'rev_text':{}})
        s=(r['note_signatures'] or [''])[0].rsplit('/',1)[-1]
        if r['note_type']=='official_comment':
            if s.startswith('Reviewer_'): e['rev_commenters'].add(s[9:]); e['reviewer_comments']+=1; e['rev_text'].setdefault(s[9:],[]).append(r['note_text'][:1500])
            elif s=='Authors': e['author_comments']+=1; e['author_chars']+=len(r['note_text'] or '')
        elif r['note_type']=='meta_review': e['meta']=r['note_text']
out=open(f'{M}/papers.jsonl','w'); n=0
for y in (2024,2025,2026):
    for p in json.load(open(f'{M}/raw/iclr{y}.json')):
        if p.get('track','main')!='main' or p['status'] not in ACC|{'Reject'}: continue
        try: R=[int(x) for x in p['rating'].split(';')]; Cf=[int(x) for x in p['confidence'].split(';')]
        except Exception: continue
        revs=p.get('reviewers','').split(';')
        sub={k:[int(x) for x in p.get(k,'').split(';') if x.strip().lstrip('-').isdigit()] for k in ('soundness','presentation','contribution')}
        e=eng.get(p['id'])
        row=dict(year=y,id=p['id'],status=p['status'],acc=p['status'] in ACC,area=p.get('primary_area',''),R=R,C=Cf,revs=revs,**sub,
                 wc=[int(x) for x in p.get('wc_review','').split(';') if x.isdigit()])
        if e and y<2026:
            row.update(rev_replied=[r in e['rev_commenters'] for r in revs],author_comments=e['author_comments'],author_chars=e['author_chars'],
                       reviewer_comments=e['reviewer_comments'],meta=e['meta'],rev_text={r:e['rev_text'].get(r,[]) for r in revs})
        out.write(json.dumps(row)+'\n'); n+=1
print('rows',n)
