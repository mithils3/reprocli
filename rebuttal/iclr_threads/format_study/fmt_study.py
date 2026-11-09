import json, re, sys, statistics as st, collections, random, math

R = '/home/mithil/PyCharmProjects/reprocli/rebuttal/'
rows = [json.loads(l) for l in open(R + 'iclr_threads/format_sample.jsonl')]
notes = {}
for i in range(1, 7):
    for l in open(R + f'iclr_threads/format_notes_{i}.jsonl'):
        d = json.loads(l); notes[d['thread_id']] = d


def split_post(t):
    m = re.match(r'title:\s*(.*?)\ncomment:\s*(.*)', t, re.S)
    return (m.group(1), m.group(2)) if m else ('', re.sub(r'^\s*comment:\s*', '', t))


NUMLAB = r'(?:W|Q|A|R|C|Weak(?:ness)?(?:es)?|Questions?|Concerns?|Comments?|Answer|Response|Point|Issue)\s*[-_.#]?\s*\d+'
ANSLAB = re.compile(r'^\s*(?:>\s*)?(?:\*\*|__)?\s*\[?\(?(?:A\d*|R\d*|Ans|Answer|Response|Reply|Authors?)\b[^\n]{0,30}?[:.\]]', re.I)
PART = re.compile(r'\(\s*\d\s*/\s*\d\s*\)|\[\s*\d\s*/\s*\d\s*\]|\bpart\s*(?:\d|i{1,3}\b|iv\b|one|two)|\bcont(?:inued|inue|\'d|d)?\b\.?\)?$|\(cont|\bcontinued\b|\b\d\s*/\s*\d\b', re.I)

FORMS = {
    'md_heading': re.compile(r'^\s*#{1,4}\s+\S'),
    'blockquote': re.compile(r'^\s*>\s*\S'),
    'bold_numbered_label': re.compile(r'^\s*[-*]?\s*(?:\*\*|__|\*\*\*)\s*[\[(]?\s*' + NUMLAB, re.I),
    'plain_numbered_label': re.compile(r'^\s*[\[(]?' + NUMLAB + r'\s*[\]).:]', re.I),
    'bold_topic_leadin': re.compile(r'^\s*[-*]?\s*\d*\.?\s*\*\*(?!\s*[\[(]?\s*' + NUMLAB + r')[^*\n]{4,160}\*\*'),
}
NUMANY = re.compile(r'(?:^|[\s*>#\[(])' + NUMLAB + r'\b', re.I)


def head_kind(line):
    for k, rx in FORMS.items():
        if rx.search(line):
            if k == 'bold_topic_leadin' and ANSLAB.search(line):
                return None
            return k
    return None


def is_point_start(line):
    if ANSLAB.search(line) and not re.search(r'\b(?:W|Q|Weak|Question|Concern|Comment)', line[:40]):
        return None
    k = head_kind(line)
    if k == 'blockquote':
        prev = None
    return k


def table_count(t):
    return len(re.findall(r'^\s*\|?\s*:?-{3,}:?\s*\|', t, re.M))


PTR = {
    'revised_or_updated_doc': re.compile(r'\b(?:revised|updated|new|rebuttal)\s+(?:version|manuscript|paper|pdf|draft|submission|revision)\b', re.I),
    'colour_mark': re.compile(r'\b(?:in|with|using)\s+(?:the\s+)?(?:blue|red|green|orange|purple|magenta|violet)\b|\b(?:highlighted|marked|colou?red)\b', re.I),
    'line_numbers': re.compile(r'\b(?:lines?|L)\s?\.?\s?\d{2,4}\b|\bl\.\s?\d{2,4}'),
    'appendix': re.compile(r'\bAppendi(?:x|ces)\s+[A-Z]', re.I),
    'section': re.compile(r'\b(?:Section|Sec\.)\s*[A-Z]?\d', re.I),
    'table_or_figure': re.compile(r'\b(?:Table|Tab\.|Figure|Fig\.)\s*[A-Z]?\d', re.I),
    'page': re.compile(r'\b(?:page|p\.)\s*\d+', re.I),
}
THANKS = re.compile(r'\b(?:thank|grateful|gratitude|appreciate)', re.I)
INVITE = re.compile(r'let us know|further (?:questions|concerns|comments|discussion|feedback|clarification)|happy to|glad to|feel free|do not hesitate|don\'t hesitate|any (?:other|more|remaining|additional) (?:questions|concerns)|look forward', re.I)
SCORE = re.compile(r'\b(?:re-?evaluat|reconsider|raise|increase|improve|update)\w*\s+(?:your|the)?\s*(?:score|rating|assessment|evaluation)', re.I)
HOPE = re.compile(r'\bwe hope\b|\bhope (?:that|this|these|our)', re.I)


def sents(t):
    t = re.sub(r'\s+', ' ', t).strip()
    return [s for s in re.split(r'(?<=[.!?])\s+(?=[A-Z*>#\[(])', t) if s]


def strip_md(t):
    return re.sub(r'[*_#>`]', '', t).strip()


def words(t):
    return len(re.findall(r"[A-Za-z0-9][\w'.%-]*", t))


def first_sentence(body):
    lines = [l for l in body.split('\n') if l.strip()]
    lines = [l for l in lines if not re.match(r'^\s*(?:dear\b|hi\b|hello\b)', l, re.I) or len(l) > 80]
    txt = ' '.join(lines)
    s = sents(txt)
    return s[0] if s else ''


def last_sentence(body):
    s = sents(body)
    return s[-1] if s else ''


def segment_points(body):
    lines = body.split('\n')
    segs, cur, curhead, prevbq = [], [], None, False
    for l in lines:
        k = head_kind(l)
        start = False
        if k == 'blockquote':
            start = not prevbq
            prevbq = True
        else:
            if l.strip():
                prevbq = False
            if k in ('md_heading', 'bold_numbered_label', 'plain_numbered_label', 'bold_topic_leadin'):
                if ANSLAB.search(l) and not re.search(r'\b(?:W|Q|Weak|Question|Concern|Comment)\s*\d', l[:40], re.I):
                    start = False
                else:
                    start = True
        if start:
            if curhead is not None:
                segs.append((curhead, cur))
            curhead, cur = (k, l), []
        else:
            cur.append(l)
    if curhead is not None:
        segs.append((curhead, cur))
    return segs


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def newcombe(k1, n1, k2, n2):
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1); l2, u2 = wilson(k2, n2)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return d, lo, hi


def boot_med_diff(a, b, B=2000, seed=0):
    rng = random.Random(seed)
    ds = []
    for _ in range(B):
        x = [a[rng.randrange(len(a))] for _ in a]; y = [b[rng.randrange(len(b))] for _ in b]
        ds.append(st.median(x) - st.median(y))
    ds.sort()
    return st.median(a) - st.median(b), ds[int(.025 * B)], ds[int(.975 * B) - 1]


def q(xs):
    a = st.quantiles(xs, n=4, method='inclusive')
    return a[0], st.median(xs), a[2]


T = []
allpoints = []
for z in rows:
    posts = [split_post(p['text']) for p in z['author_posts']]
    bodies = [b for _, b in posts]
    titles = [t for t, _ in posts]
    full = '\n'.join(bodies)
    d = {'id': z['thread_id'], 'forum': z['forum'], 'group': z['group']}
    d['n_posts'] = len(posts)
    d['chars'] = sum(len(b) for b in bodies)
    d['chars_per_post'] = [len(b) for b in bodies]
    d['words'] = sum(words(b) for b in bodies)
    STRICT = re.compile(r'\(\s*\d\s*/\s*[\dn]\s*\)|\[\s*\d\s*/\s*[\dn]\s*\]|\bpart\s*(?:\d|[ivx]+\b)|^\W*\(?cont(?:inued|\'d|d)?\W*$|continued (?:in|from|below)|to be continued|\(cont', re.I)
    partl = [t for t in titles if PART.search(t) and not re.search(r'continued (?:support|engagement|discussion|interest)', t, re.I)] + [l for b in bodies for l in [x for x in b.split('\n') if x.strip()][:1] + [x for x in b.split('\n') if x.strip()][-1:] if STRICT.search(l) and len(l) < 90]
    d['parts'] = bool(partl); d['part_labels'] = partl
    d['tables'] = table_count(full)
    d['has_table'] = d['tables'] > 0
    kinds = collections.Counter()
    first_kind = None
    for b in bodies:
        for l in b.split('\n'):
            k = head_kind(l)
            if k:
                kinds[k] += 1
                if first_kind is None and not (k == 'bold_topic_leadin' and len(strip_md(l)) < 4):
                    first_kind = k
    d['kinds'] = kinds; d['first_kind'] = first_kind or 'none'
    d['numbered_label'] = bool(NUMANY.search(full))
    d['blockquote'] = kinds['blockquote'] > 0
    d['md_heading'] = kinds['md_heading'] > 0
    for k, rx in PTR.items():
        d['ptr_' + k] = bool(rx.search(full))
    d['gr'] = z['general_response']
    fs = first_sentence(bodies[0]) if bodies else ''
    d['open'] = fs
    d['open_thanks'] = bool(THANKS.search(fs))
    d['open_dear'] = bool(re.match(r'^\s*(?:\*\*)?\s*dear\b', bodies[0], re.I)) if bodies else False
    d['open_label'] = bool(head_kind(bodies[0].strip().split('\n')[0])) if bodies else False
    ls = last_sentence(bodies[-1]) if bodies else ''
    d['close'] = ls
    d['close_invite'] = bool(INVITE.search(ls)); d['close_thanks'] = bool(THANKS.search(ls))
    d['close_score'] = bool(SCORE.search(bodies[-1][-600:])) if bodies else False
    d['close_hope'] = bool(HOPE.search(ls))
    d['titles'] = titles
    pts = []
    for pi, b in enumerate(bodies):
        for (k, hl), seg in segment_points(b):
            ans = [l for l in seg if not re.match(r'^\s*>', l)]
            txt = '\n'.join(ans).strip()
            w = words(txt)
            if w < 5:
                continue
            s = sents(strip_md(re.sub(ANSLAB, '', txt, count=1)))
            fsent = s[0] if s else ''
            p = {'thread': z['thread_id'], 'forum': z['forum'], 'group': z['group'], 'kind': k, 'head': hl.strip()[:160], 'words': w,
                 'thanks_first': bool(THANKS.search(fsent[:120])), 'has_num': bool(re.search(r'\d+\.\d+|\d+%|\b\d{2,}\b', txt)),
                 'has_ptr': any(PTR[x].search(txt) for x in ('appendix', 'section', 'table_or_figure', 'line_numbers', 'page')),
                 'has_table': table_count(txt) > 0, 'text': txt, 'first': fsent}
            pts.append(p)
    d['n_seg'] = len(pts)
    allpoints += pts
    T.append(d)

json.dump({'threads': [{k: v for k, v in d.items() if k not in ('kinds',)} | {'kinds': dict(d['kinds'])} for d in T], 'points': allpoints},
          open(sys.argv[1], 'w'))


QLAB = re.compile(r'^\s*(?P<pre>(?:>\s*)?(?:#{1,4}\s*)?(?:[-*]\s+)?(?:\d+\.\s+)?(?:\*\*\*|\*\*|__|\*|\$\\textbf\{)?\s*[\[(]?\s*)(?P<lab>W(?:eak(?:ness(?:es)?)?)?|Q(?:uestions?)?|C(?:omments?|oncerns?)?|Points?|Issues?)\s*[-_.#]?\s*(?P<num>\d+)', re.I)


def norm(lab, num):
    l = lab[0].upper()
    if lab.lower().startswith('p') or lab.lower().startswith('i'):
        l = 'P'
    return l + num


def marker(pre):
    if '>' in pre: return 'blockquote'
    if '#' in pre: return 'md_heading'
    if '**' in pre or '__' in pre or 'textbf' in pre: return 'bold'
    if '*' in pre: return 'italic'
    return 'plain'


def qsegments(body):
    segs, cur, curid = [], [], None
    seen = set()
    for l in body.split('\n'):
        m = QLAB.match(l)
        if m and len(l) < 2000:
            pid = norm(m.group('lab'), m.group('num'))
            if pid not in seen:
                if curid: segs.append((curid, curmark, curhead, cur))
                curid, curmark, curhead, cur = pid, marker(m.group('pre')), l.strip(), []
                seen.add(pid)
                rest = l[m.end():]
                cur.append(rest)
                continue
        cur.append(l)
    if curid: segs.append((curid, curmark, curhead, cur))
    return segs


Q = []
for z, d in zip(rows, T):
    posts = [split_post(p['text'])[1] for p in z['author_posts']]
    tsegs = []
    seen_ids = set()
    for b in posts:
        for pid, mk, hl, seg in qsegments(b):
            if pid in seen_ids:
                continue
            seen_ids.add(pid)
            ans = [l for l in seg if not re.match(r'^\s*>', l)]
            txt = '\n'.join(ans).strip()
            txt_body = re.sub(r'^[^\n]{0,400}?(?:\*\*|\n)', '', txt, count=1) if txt.startswith(('*', ':', '.')) else txt
            s = sents(strip_md(ANSLAB.sub('', txt, count=1)))
            tsegs.append({'thread': z['thread_id'], 'forum': z['forum'], 'group': z['group'], 'id': pid, 'mark': mk, 'head': hl[:200],
                          'words': words(txt), 'text': txt,
                          'thanks_any': bool(THANKS.search(' '.join(s[:2])[:250])),
                          'has_num': bool(re.search(r'\d+\.\d+|\d+%|\b\d{2,}\b', txt)),
                          'has_ptr': any(PTR[x].search(txt) for x in ('appendix', 'section', 'table_or_figure', 'line_numbers', 'page')),
                          'has_rev': bool(PTR['revised_or_updated_doc'].search(txt) or re.search(r'\bwe (?:have )?(?:added|revised|updated|included|clarified|rewritten|rephrased|corrected|fixed|moved)\b', txt, re.I)),
                          'has_table': table_count(txt) > 0, 'quoted': any(re.match(r'^\s*>', l) for l in seg)})
    d['qsegs'] = len(tsegs)
    d['q_first_mark'] = tsegs[0]['mark'] if tsegs else None
    d['q_marks'] = sorted({s['mark'] for s in tsegs})
    d['q_ids'] = sorted({s['id'][0] for s in tsegs})
    if tsegs:
        aw = sum(words('\n'.join(l for l in b.split('\n') if not re.match(r'^\s*>', l))) for b in posts)
        d['words_per_q'] = aw / len(tsegs)
    Q += tsegs
json.dump({'threads': [{k: v for k, v in d.items() if k not in ('kinds',)} | {'kinds': dict(d['kinds'])} for d in T], 'points': allpoints, 'q': Q},
          open(sys.argv[1], 'w'))
