import sys, re, json, glob, os, collections
import pyarrow.parquet as pq, pyarrow.compute as pc

RAW, OUT, TARGET = sys.argv[1], sys.argv[2], int(sys.argv[3])
VENUE = 'ICLR.cc/2025/Conference'
KEYS = {'summary', 'strengths', 'weaknesses', 'questions', 'rating', 'confidence', 'soundness',
        'presentation', 'contribution', 'flag_for_ethics_review', 'code_of_conduct',
        'details_of_ethics_concerns', 'limitations', 'title', 'comment', 'withdrawal_confirmation'}
SUFFIX = {'official_review': 'Official_Review', 'official_comment': 'Official_Comment',
          'comment': 'Public_Comment', 'meta_review': 'Meta_Review', 'decision': 'Decision',
          'review': 'Review'}
KEY_RE = re.compile(r'(?m)^(' + '|'.join(sorted(KEYS, key=len, reverse=True)) + r'):[ ]?')

def parse_content(text):
    hits = list(KEY_RE.finditer(text))
    out = {}
    if not hits:
        return {'comment': {'value': text.strip()}}
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        out[m.group(1)] = {'value': text[m.end():end].rstrip('\n')}
    return out

rows = []
for f in sorted(glob.glob(os.path.join(RAW, 'data', '*.parquet'))):
    t = pq.read_table(f, columns=['venue', 'forum_id', 'note_id', 'note_type', 'note_created',
                                  'note_replyto', 'note_signatures', 'note_readers', 'note_text'])
    t = t.filter(pc.equal(t.column('venue'), VENUE))
    if t.num_rows:
        rows.extend(t.to_pylist())
print('ICLR 2025 rows', len(rows), flush=True)

forums = collections.defaultdict(list)
for r in rows:
    forums[r['forum_id']].append(r)
eligible = sorted(fid for fid, ns in forums.items() if any(n['note_type'] == 'official_review' for n in ns))
print('forums', len(forums), 'with official_review', len(eligible), flush=True)
step = len(eligible) / TARGET
chosen = [eligible[int(i * step)] for i in range(TARGET)]

os.makedirs(OUT, exist_ok=True)
for fid in chosen:
    ns = forums[fid]
    subnum = None
    for n in ns:
        m = re.search(r'Submission(\d+)/', ' '.join(n['note_signatures'] or []))
        if m:
            subnum = m.group(1); break
    base = f'{VENUE}/Submission{subnum}' if subnum else f'{VENUE}/Forum_{fid}'
    out = []
    for n in sorted(ns, key=lambda x: x['note_created'] or 0):
        suffix = SUFFIX.get(n['note_type'], n['note_type'])
        out.append({
            'id': n['note_id'], 'forum': fid, 'replyto': n['note_replyto'],
            'cdate': int(n['note_created']),
            'signatures': list(n['note_signatures'] or []),
            'invitations': [f'{base}/-/{suffix}'],
            'content': parse_content(n['note_text'] or ''),
            'writers': [VENUE], 'readers': list(n['note_readers'] or []),
        })
    with open(os.path.join(OUT, f'{fid}.json'), 'w') as fh:
        json.dump(out, fh)
print('wrote', len(chosen), 'to', OUT, flush=True)
