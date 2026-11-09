import json, re, sys, statistics as st, collections

R = '/home/mithil/PyCharmProjects/reprocli/rebuttal/'
OUT = R + 'results/style/first_reply_length.md'
rows = [json.loads(l) for l in open(R + 'iclr_threads/format_sample.jsonl')]

# copied from iclr_threads/format_study/fmt_study.py (that file runs on import, so it is not imported)
def split_post(t):
    m = re.match(r'title:\s*(.*?)\ncomment:\s*(.*)', t, re.S)
    return (m.group(1), m.group(2)) if m else ('', re.sub(r'^\s*comment:\s*', '', t))

ANSLAB = re.compile(r'^\s*(?:>\s*)?(?:\*\*|__)?\s*\[?\(?(?:A\d*|R\d*|Ans|Answer|Response|Reply|Authors?)\b[^\n]{0,30}?[:.\]]', re.I)
PART = re.compile(r'\(\s*\d\s*/\s*\d\s*\)|\[\s*\d\s*/\s*\d\s*\]|\bpart\s*(?:\d|i{1,3}\b|iv\b|one|two)|\bcont(?:inued|inue|\'d|d)?\b\.?\)?$|\(cont|\bcontinued\b|\b\d\s*/\s*\d\b', re.I)
# part-marker forms used by the rule below (stricter than PART: no bare "2/3")
MARK = re.compile(r'\(\s*\d+\s*/\s*[\dN]+\s*\)|\[\s*\d+\s*/\s*\d+\s*\]|\bpart\s*\d+\b|\bcontinued\b|\(cont', re.I)
FIRSTN = re.compile(r'\(\s*1\s*/\s*(\d+)\s*\)|\[\s*1\s*/\s*(\d+)\s*\]', re.I)
FIRST1 = re.compile(r'\bpart\s*1\b', re.I)
TABLE_SEP = re.compile(r'^\s*\|?\s*:?-{3,}:?\s*\|', re.M)
QLAB = re.compile(r'^\s*(?P<pre>(?:>\s*)?(?:#{1,4}\s*)?(?:[-*]\s+)?(?:\d+\.\s+)?(?:\*\*\*|\*\*|__|\*|\$\\textbf\{)?\s*[\[(]?\s*)(?P<lab>W(?:eak(?:ness(?:es)?)?)?|Q(?:uestions?)?|C(?:omments?|oncerns?)?|Points?|Issues?)\s*[-_.#]?\s*(?P<num>\d+)', re.I)


def words(t):
    return len(re.findall(r"[A-Za-z0-9][\w'.%-]*", t))


def table_count(t):
    return len(TABLE_SEP.findall(t))


def norm(lab, num):
    l = lab[0].upper()
    if lab.lower().startswith('p') or lab.lower().startswith('i'):
        l = 'P'
    return l + num


def qsegments(body):
    segs, cur, curid = [], [], None
    seen = set()
    for l in body.split('\n'):
        m = QLAB.match(l)
        if m and len(l) < 2000:
            pid = norm(m.group('lab'), m.group('num'))
            if pid not in seen:
                if curid: segs.append((curid, curhead, cur))
                curid, curhead, cur = pid, l.strip(), []
                seen.add(pid)
                cur.append(l[m.end():])
                continue
        cur.append(l)
    if curid: segs.append((curid, curhead, cur))
    return segs


# first-reply rule
def marker_text(title, body):
    head = body.strip()[:80]
    return title + ' ' + head


def first_reply_idx(posts):
    """posts: list of (title, body). Returns indices of the first reply."""
    t0, b0 = posts[0]
    m = FIRSTN.search(t0) or FIRSTN.search(b0.strip()[:80])
    if m:
        n = int(m.group(1) or m.group(2))
        return list(range(0, min(n, len(posts))))
    if FIRST1.search(marker_text(t0, b0)):
        idx = [0]
        for i in range(1, len(posts)):
            if MARK.search(marker_text(*posts[i])):
                idx.append(i)
            else:
                break
        return idx
    idx = [0]
    for i in range(1, len(posts)):
        if MARK.search(marker_text(*posts[i])):
            idx.append(i)
        else:
            break
    return idx


# reviewer points: items under Weaknesses / Questions in review_text
KEY = re.compile(r'^\s*[#*_ ]*(summary|strengths?|weaknesses|questions|soundness|presentation|contribution|rating|confidence|reference|minor|typo|missing|key|related|clarity|significance|quality|recommendations?|task|structured)\b[^\n]{0,40}?:', re.I)
SEC = re.compile(r'^\s*[#*_ ]*(weaknesses|questions)\b[^\n]{0,40}?:', re.I)
ITEM = re.compile(r'^\s*(?:\d+[.)]|[-*•]|\(\d+\))\s+\S')


def review_points(text):
    lines = text.split('\n')
    inside, sec = False, []
    for l in lines:
        if SEC.match(l):
            inside = True
            sec.append(l[l.find(':') + 1:])
            continue
        if KEY.match(l):
            inside = False
            continue
        if inside:
            sec.append(l)
    items = [l for l in sec if ITEM.match(l)]
    if items:
        return len(items), 'items'
    paras = [p for p in '\n'.join(sec).split('\n\n') if p.strip()]
    return len(paras), 'paragraph fallback'


def q(xs):
    a = st.quantiles(xs, n=4, method='inclusive')
    return a[0], st.median(xs), a[2]


def qs(xs, fmt='{:.0f}'):
    if not xs:
        return 'n=0'
    a, m, b = q(xs)
    return f'{fmt.format(a)} / {fmt.format(m)} / {fmt.format(b)} (n={len(xs)})'


REF = re.compile(r'\b(?:Appendix|Table|Tab\.|Figure|Fig\.|Section|Sec\.|Eq\.|Equation|Theorem|Lemma|Assumption|Weakness|Question|Reviewer|Q|W|A|Point|Page|p\.)\s*[A-Z]?\d+(?:\.\d+)*', re.I)


def nums(t):
    return re.findall(r'\d+(?:\.\d+)?%?', REF.sub(' ', t))


def has_result(t):
    return table_count(t) > 0 or len(nums(t)) >= 3


# ---- compute ----
threads = []
for z in rows:
    posts = [split_post(p['text']) for p in z['author_posts']]
    idx = first_reply_idx(posts)
    fr_bodies = [posts[i][1] for i in idx]
    fr_text = '\n'.join(fr_bodies)
    segs = []
    seen = set()
    for b in fr_bodies:
        for pid, hl, seg in qsegments(b):
            if pid in seen:
                continue
            seen.add(pid)
            ans = [l for l in seg if not re.match(r'^\s*>', l)]
            txt = '\n'.join(ans).strip()
            segs.append({'id': pid, 'head': hl[:200], 'text': txt, 'words': words(txt),
                         'result': has_result(txt), 'table': table_count(txt) > 0})
    pts, how = review_points(z['review_text'])
    trows = 0
    for b in fr_bodies:
        for l in b.split('\n'):
            if l.strip().startswith('|') and not TABLE_SEP.match(l):
                trows += 1
    threads.append({
        'id': z['thread_id'], 'group': z['group'], 'z': z,
        'n_posts': len(idx), 'chars': sum(len(b) for b in fr_bodies),
        'words': sum(words(b) for b in fr_bodies), 'segs': segs,
        'points': pts, 'pts_how': how,
        'has_table': table_count(fr_text) > 0, 'table_rows': trows,
    })

raised = [t for t in threads if t['group'] == 'raised']
other = [t for t in threads if t['group'] != 'raised']


def ans_ratio(t):
    return t['words'] / len(t['segs']) if t['segs'] else None


def block(label, ts):
    chars = [t['chars'] for t in ts]
    words_ = [t['words'] for t in ts]
    posts_ = [t['n_posts'] for t in ts]
    nlab = [len(t['segs']) for t in ts]
    wpa = [ans_ratio(t) for t in ts if t['segs']]
    return (f'| {label} | {qs(chars)} | {qs(words_)} | {qs(posts_)} | {qs(nlab)} | {qs(wpa, "{:.0f}")} |')


lines = []
lines.append('## Method')
lines.append('- Data: format_sample.jsonl, 240 threads (group values: raised, unchanged). Raised n=%d, unchanged n=%d.' % (len(raised), len(other)))
lines.append('- First reply: post 1, plus following posts when post 1 title or first 80 chars has (1/N) or "Part 1" (then the next N-1 posts), otherwise the following posts whose title or first 80 chars has (k/N), "Part k", or "continued", stopping at the first post without one.')
lines.append('- Labelled answers: QLAB label lines (W/Q/C/Point/Issue + number), first occurrence per id, from fmt_study.py; blockquote lines excluded; words per answer = answer words; per-thread ratio = first-reply words / labels, 0-label threads excluded.')
lines.append('- Reviewer points: items (numbered/bulleted) under the "weaknesses:" and "questions:" keys of review_text; if none, paragraphs in those sections.')
lines.append('- Quartiles: statistics.quantiles, method inclusive. Table rows = pipe lines minus separator lines. Numbers = numeric tokens after removing reference labels (Table 2, Q1, Section 3). Result answer = markdown table or 3+ numbers.')
lines.append('')
lines.append('## Item 2: first reply, quartiles Q1 / median / Q3')
lines.append('| Group | Chars | Words | Posts | Labelled answers | Words per labelled answer |')
lines.append('|---|---|---|---|---|---|')
lines.append(block('All', threads))
lines.append(block('raised', raised))
lines.append(block('other (unchanged)', other))
lines.append('')

pts_all = [t['points'] for t in threads]
lines.append('## Item 3: reviewer points vs first reply (threads with points in bin)')
lines.append(f'Points counted by: {collections.Counter(t["pts_how"] for t in threads)}; points Q1/median/Q3 = {qs(pts_all)}')
lines.append('| Points bin | Chars Q1 / med / Q3 | Words Q1 / med / Q3 |')
lines.append('|---|---|---|')
for lab, lo, hi in [('1-3', 1, 3), ('4-5', 4, 5), ('6-8', 6, 8), ('9+', 9, 10**6)]:
    sub = [t for t in threads if lo <= t['points'] <= hi]
    lines.append(f'| {lab} | {qs([t["chars"] for t in sub])} | {qs([t["words"] for t in sub])} |')
lines.append('')

lines.append('## Item 4: markdown table in first reply')
n_tab = sum(t['has_table'] for t in threads)
tab_rows = [t['table_rows'] for t in threads if t['has_table']]
lines.append(f'- Share with a table: {n_tab}/{len(threads)} = {100*n_tab/len(threads):.1f}%')
lines.append(f'- Table rows among those with a table: median {st.median(tab_rows):.0f} (Q1/Q3 {q(tab_rows)[0]:.0f}/{q(tab_rows)[2]:.0f}, n={len(tab_rows)})')
lines.append('')

lines.append('## Item 5: posts in first reply')
c = collections.Counter(min(t['n_posts'], 3) for t in threads)
for k, lab in [(1, 'one post'), (2, 'two posts'), (3, 'three or more')]:
    lines.append(f'- {lab}: {c[k]}/{len(threads)} = {100*c[k]/len(threads):.1f}%')
lines.append('')

lines.append('## Item 6: words per labelled answer, result vs rest')
allsegs = [s for t in threads for s in t['segs']]
res = [s['words'] for s in allsegs if s['result']]
rest = [s['words'] for s in allsegs if not s['result']]
lines.append(f'- Labelled answers total: {len(allsegs)}')
lines.append('| Answer type | Words Q1 / med / Q3 |')
lines.append('|---|---|')
lines.append(f'| reports a result (table or 3+ numbers) | {qs(res)} |')
lines.append(f'| rest | {qs(rest)} |')
lines.append('')

# model answers: raised group, one per thread, 90-180 words, result-bearing, first sentence with a number first
RESULT_WORDS = re.compile(r'\b(experiment|ablation|analysis|we ran|we ran|we conducted|we added|additional|new (?:result|experiment|analysis)|we evaluated|we measured|we report|results? (?:show|indicate))', re.I)
cands = []
for t in raised:
    for s in t['segs']:
        if not (90 <= s['words'] <= 180) or not s['result'] or '\u2014' in s['text']:
            continue
        if re.search(r'\[\d+\]|^\s*-{3,}\s*$', s['text'], re.M):
            continue
        body = s['text'].split('\n', 1)[1] if '\n' in s['text'] else s['text']
        bflat = re.sub(r'[*_#>|`]', '', body).strip()
        if not (RESULT_WORDS.search(bflat) and (table_count(bflat) > 0 or any(('.' in n or '%' in n) for n in nums(bflat)))):
            continue
        first = re.split(r'(?<=[.!?])\s', bflat, maxsplit=1)[0]
        cands.append((0 if re.search(r'\d', first) else 1, t, s))
cands.sort(key=lambda x: (x[0], x[1]['id']))
picked, used = [], set()
for _, t, s in cands:
    if t['id'] in used:
        continue
    used.add(t['id'])
    picked.append((t, s))
    if len(picked) == 5:
        break

lines.append('## Model answers (group raised, 90-180 words, result with numbers)')
lines.append(f'Candidates: {len(cands)} answers across {len({t["id"] for _, t, _ in cands})} threads; first five in sort order (first sentence with a number first, then thread id).')
for i, (t, s) in enumerate(picked, 1):
    lines.append('')
    lines.append(f'### {i}. thread_id {t["id"]}, {s["words"]} words, answers {s["head"]!r}')
    lines.append('')
    lines.append('> ' + s['text'].replace('\n', '\n> '))

open(OUT, 'w').write('\n'.join(lines) + '\n')
print('wrote', OUT, 'candidates', len(cands), 'picked', len(picked))
