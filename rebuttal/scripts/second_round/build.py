import re, json, os, glob, random
from collections import defaultdict, Counter
import pyarrow as pa
import pyarrow.parquet as pq

BASE = '/tmp/claude-1000/-home-mithil-PyCharmProjects-reprocli/ee88b5cc-f222-456d-9de1-997a82c38396/scratchpad'
RAW = f'{BASE}/timing25/raw/data'
OUT = f'{BASE}/round2'
VENUE = 'ICLR.cc/2025/Conference'
HOUR = 3.6e6

RAISE = re.compile(r'(rais|increas|bump|upgrad|updat|improv|chang)\w*.{0,60}(score|rating|recommendation|evaluation)'
                   r'|(score|rating).{0,40}(to|→|->)\s*(an?\s*)?(6|8|10)\b', re.I)
KEEP = re.compile(r'(keep|maintain|retain|remain|stay|stand by|not chang|unchanged|will not (raise|increase)'
                  r'|cannot (raise|increase)).{0,60}(score|rating|recommendation|evaluation|assessment)', re.I)
LOWER = re.compile(r'(lower|decreas|reduc|downgrad)\w*.{0,60}(score|rating)', re.I)
RATING = re.compile(r'(?im)^\s*rating\s*:\s*(\d+)')
SENT = re.compile(r'(?<=[.!?])\s+|\n+')
BANNED = re.compile(
    r"(rais|increas|bump|upgrad|updat|improv|chang|keep|maintain|retain|remain|lower|decreas|reconsider|revis|adjust|reflect)\w*"
    r"[^.!?\n]{0,80}\b(scor\w*|ratings?|recommendation|evaluation|assessment)\b"
    r"|\b(your|my|final|current|initial|original|overall)\s+(scor\w*|ratings?|recommendation|assessment|evaluation)\b"
    r"|\b(scores?|ratings?)\s+(of|to|from|at)\s+\d"
    r"|\b(accept|reject)(ance|ion|ed)?\b|borderline|\bpositive (side|direction)\b", re.I)


def join(notes):
    return '\n\n'.join(n['text'] for n in notes)


def clean(text):
    parts = [p.strip() for p in SENT.split(text) if p and p.strip()]
    return ' '.join(p for p in parts if not BANNED.search(p))


def scrub(text, fid):
    return text.replace(fid, "[id]")


def feat_r1(x):
    return cut(scrub(clean(x["r1"]), x["forum"]), 2500)


def feat_a2(x):
    return cut(scrub(clean(x["a2"]), x["forum"]), 9000)


def cut(text, n):
    return text if len(text) <= n else text[:n].rstrip() + ' [cut]'


# ---- load ICLR 2025 rows only (venue filter pushed down to parquet)
files = sorted(glob.glob(f'{RAW}/*.parquet'))
tab = pa.concat_tables([pq.read_table(f, columns=['venue', 'forum_id', 'note_id', 'note_type', 'note_created',
                                                  'note_replyto', 'note_signatures', 'note_text'],
                                      filters=[('venue', '==', VENUE)]) for f in files])
rows = tab.to_pylist()
print('ICLR 2025 note rows:', len(rows))
forums = defaultdict(list)
for r in rows:
    sig = (r['note_signatures'] or [''])[0]
    forums[r['forum_id']].append(dict(id=r['note_id'], typ=r['note_type'], rep=r['note_replyto'],
                                      t=int(r['note_created']), role=sig.split('/')[-1],
                                      text=r['note_text'] or ''))
del rows, tab
print('forums:', len(forums))

# ---- build threads
threads, texts = [], {}
drops = Counter(); rev_total = 0; rev_not_typed = 0; null_rating = 0; ratings = Counter()
for forum, ns in forums.items():
    kids = defaultdict(list)
    for n in ns:
        kids[n['rep']].append(n)
    revs = [n for n in ns if n['rep'] == forum and n['role'].startswith('Reviewer')]
    for R in revs:
        rev_total += 1
        if R['typ'] != 'official_review':
            rev_not_typed += 1
        seen, stack, th = {R['id']}, [R['id']], []
        while stack:
            cur = stack.pop()
            for c in kids.get(cur, []):
                if c['id'] not in seen:
                    seen.add(c['id']); th.append(c); stack.append(c['id'])
        th.sort(key=lambda n: (n['t'], n['id']))
        rr = R['role']
        au = [n for n in th if n['role'] == 'Authors']
        if not au:
            drops['no author note'] += 1; continue
        later = [n for n in th if n['role'] == rr and n['t'] > R['t']]
        if not later:
            drops['no later reviewer note'] += 1; continue
        A1 = [n for n in au if n['t'] < later[0]['t']]
        if not A1:
            drops['no A1'] += 1; continue
        a0 = au[0]
        R1 = next((n for n in th if n['role'] == rr and n['t'] > a0['t']), None)
        if R1 is None:
            drops['no R1'] += 1; continue
        nxt = next((n for n in th if n['role'] == rr and n['t'] > R1['t']), None)
        A2 = [n for n in au if n['t'] > R1['t'] and (nxt is None or n['t'] < nxt['t'])]
        if not A2:
            drops['no A2'] += 1; continue
        a2txt = join(A2)
        if len(a2txt) < 300:
            drops['A2 under 300 chars'] += 1; continue
        R2 = [n for n in th if n['role'] == rr and n['t'] > A2[0]['t']]
        r1txt, r2txt = R1['text'], join(R2)
        m = RATING.search(R['text'])
        fr = int(m.group(1)) if m else None
        if fr is None:
            null_rating += 1
        ratings[fr] += 1
        tid = f"{forum}_{rr}"
        if tid in texts:
            tid += f"_dup{sum(1 for t in threads if t["forum"] == forum)}"
        threads.append(dict(
            tid=tid, forum=forum, final_rating=fr,
            len_rev=len(R['text']), len_a1=len(join(A1)), len_r1=len(r1txt), len_a2=len(a2txt), len_r2=len(r2txt),
            hours_a1_r1=(R1['t'] - a0['t']) / HOUR,
            hours_r1_a2=(A2[0]['t'] - R1['t']) / HOUR,
            hours_a2_r2=((R2[0]['t'] - A2[0]['t']) / HOUR) if R2 else None,
            has_r2=bool(R2),
            r1_raise=bool(RAISE.search(r1txt)), r1_keep=bool(KEEP.search(r1txt)), r1_lower=bool(LOWER.search(r1txt)),
            r1_thanks_only=len(r1txt) < 300,
            r2_raise=bool(RAISE.search(r2txt)), r2_keep=bool(KEEP.search(r2txt)), r2_lower=bool(LOWER.search(r2txt)),
            r2_thanks_only=len(r2txt) < 300,
        ))
        texts[tid] = dict(forum=forum, rev=R['text'], a1=join(A1), r1=r1txt, a2=a2txt, r2=r2txt)

tids = Counter(t['tid'] for t in threads)
dups = sum(1 for v in tids.values() if v > 1)
print('official reviews (reviewer-signed, replyto=forum):', rev_total, '| not typed official_review:', rev_not_typed)
print('drops:', dict(drops), '| duplicate tids:', dups)
print('ratings parsed:', dict(sorted(ratings.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))), '| null:', null_rating)

os.makedirs(OUT, exist_ok=True)
with open(f'{OUT}/threads.jsonl', 'w') as fh:
    for t in threads:
        fh.write(json.dumps(t) + '\n')

# ---- STEP 1 counts
K = len(threads)
T = lambda k: sum(1 for t in threads if t[k])
print(f'\nSTEP 1: kept threads {K}')
print('with R2:', T('has_r2'))
print('R1 flags raise/keep/lower:', T('r1_raise'), T('r1_keep'), T('r1_lower'))
print('R2 flags raise/keep/lower:', T('r2_raise'), T('r2_keep'), T('r2_lower'))
print('cross table (R1 raise, has R2, R2 raise) -> count')
for r1 in (False, True):
    for h in (False, True):
        for r2 in ((False, True) if h else (False,)):
            n = sum(1 for t in threads if t['r1_raise'] == r1 and t['has_r2'] == h and t['r2_raise'] == r2)
            print(f'  R1raise={r1!s:5} hasR2={h!s:5} R2raise={r2!s:5} -> {n}')

# ---- STEP 2 sample
pop = sorted((t for t in threads if (not t['r1_raise']) and t['has_r2'] and t['len_r2'] >= 150), key=lambda t: t['tid'])
pos = [t for t in pop if t['r2_raise']]
neg = [t for t in pop if not t['r2_raise']]
print(f'\nSTEP 2: population {len(pop)} | R2 raise true {len(pos)} | R2 raise false {len(neg)}')
rng = random.Random(1116)
pos_s = rng.sample(pos, 160) if len(pos) >= 160 else list(pos)
neg_s = rng.sample(neg, 160) if len(neg) >= 160 else list(neg)
print('sampled raise-true', len(pos_s), '| raise-false', len(neg_s), '(taken all)' if len(pos) < 160 or len(neg) < 160 else '')
combined = pos_s + neg_s
rng.shuffle(combined)
codes = [f't{i+1:03d}' for i in range(len(combined))]
key = {c: dict(tid=t['tid'], forum=t['forum'], r2_raise=t['r2_raise'], r2_keep=t['r2_keep'], r2_lower=t['r2_lower'])
       for c, t in zip(codes, combined)}
with open(f'{OUT}/key.json', 'w') as fh:
    json.dump(key, fh, indent=1)
by_tid = {t['tid']: t for t in threads}
order = [(c, t['tid']) for c, t in zip(codes, combined)]

# ---- STEP 3 shards
for d in ('feat', 'out'):
    os.makedirs(f'{OUT}/{d}', exist_ok=True)
    for f in glob.glob(f'{OUT}/{d}/shard_*.md'):
        os.remove(f)
blocks = []
for c, tid in order:
    x = texts[tid]
    blocks.append(f"## {c}\nREVIEWER FOLLOW-UP:\n{feat_r1(x)}\n\nAUTHOR SECOND REPLY:\n{feat_a2(x)}\n")
for i in range(0, len(blocks), 10):
    with open(f'{OUT}/feat/shard_{i//10+1:02d}.md', 'w') as fh:
        fh.write('\n'.join(blocks[i:i+10]))
rng2 = random.Random(1117)
shuf = [c for c in codes]
rng2.shuffle(shuf)
tid_of = dict((c, tid) for c, tid in order)
oblocks = {}
for c in shuf:
    x = texts[tid_of[c]]
    oblocks[c] = f"## {c}\nREVIEWER COMMENT 1:\n{scrub(x['r1'], x['forum'])}\n\nREVIEWER LATER COMMENTS:\n{scrub(cut(x['r2'], 4000), x['forum'])}\n"
for i in range(0, len(shuf), 20):
    with open(f'{OUT}/out/shard_{i//20+1:02d}.md', 'w') as fh:
        fh.write('\n'.join(oblocks[c] for c in shuf[i:i+20]))
print(f'\nwrote feat shards {len(range(0, len(blocks), 10))}, out shards {len(range(0, len(shuf), 20))}')

# ---- CHECKS
feat_files = sorted(glob.glob(f'{OUT}/feat/shard_*.md'))
out_files = sorted(glob.glob(f'{OUT}/out/shard_*.md'))
feat_text = {f: open(f).read() for f in feat_files}
out_text = {f: open(f).read() for f in out_files}
feat_all = ''.join(feat_text.values())
out_all = ''.join(out_text.values())
expected = set(codes)
res = {}

def seen_codes(all_text):
    return Counter(re.findall(r'(?m)^## (t\d{3})$', all_text))

c1f, c1o = seen_codes(feat_all), seen_codes(out_all)
res[1] = (len(feat_files) == 32 and len(out_files) == 16 and set(c1f) == expected and set(c1o) == expected
          and all(v == 1 for v in c1f.values()) and all(v == 1 for v in c1o.values()))
print('\nCHECK 1 (shard counts and each code once per set):', 'PASS' if res[1] else 'FAIL',
      len(feat_files), len(out_files), len(c1f), len(c1o))

forum_ids = [v['forum'] for v in key.values()]
banned_hit = any(BANNED.search(t) for t in feat_text.values())
forum_hit = any(fid in t for t in feat_text.values() for fid in forum_ids)
out_forum_hit = any(fid in t for t in out_text.values() for fid in forum_ids)
plural = Counter(m.lower() for m in re.findall(r'(?i)\b(?:scor|rating|recommendation)\w+', feat_all))
res[2] = (not banned_hit) and (not forum_hit)
print('CHECK 2 (no forum id and no score/rating/recommendation word in feat shards):', 'PASS' if res[2] else 'FAIL',
      '| forum id in out shards:', out_forum_hit, '| plural/variant word forms left by literal rule:', sum(plural.values()))

random.seed(0)
samp = random.Random(1118).sample(sorted(expected), 5)
ok3 = True
for c in samp:
    tid = tid_of[c]; x = texts[tid]
    idx = feat_all.index(f'## {c}\n')
    end = feat_all.find('\n## ', idx + 1)
    block = feat_all[idx: end if end != -1 else None]
    exp_a2 = f"AUTHOR SECOND REPLY:\n{feat_a2(x)}"
    exp_r1 = f"REVIEWER FOLLOW-UP:\n{feat_r1(x)}"
    a2_ok = exp_a2 in block and exp_r1 in block
    leak = 0; kept_overlap = 0
    for s in SENT.split(x['r2']):
        s = s.strip()
        if len(s) >= 80:
            if s in x['r1'] or s in x['a2']:
                kept_overlap += 1; continue
            if s in block:
                leak += 1
    ok3 = ok3 and a2_ok and leak == 0
    print(f'  check3 {c}: A2+R1 rebuilt match {a2_ok} | R2 80+ sentence leaks {leak} | R2 sentences shared with R1/A2 skipped {kept_overlap}')
res[3] = ok3
print('CHECK 3 (feat text matches parquet rebuild; no R2 leak):', 'PASS' if res[3] else 'FAIL')

res[4] = len(key) == 320
print('CHECK 4 (key.json has 320 entries):', 'PASS' if res[4] else 'FAIL', len(key))
print('\nOVERALL', 'PASS' if all(res.values()) else 'FAIL')
