import json, re, statistics as st
exec(open('fmt_study.py').read().split('\nT = []')[0].replace('sys.argv[1]', '0'))
D = json.load(open('out.json')); T = D['threads']; Q = D['q']
byid = {z['thread_id']: z for z in rows}
for t in T:
    b = split_post(byid[t['id']]['author_posts'][-1]['text'])[1]
    t['close_inv_tail'] = bool(INVITE.search(b[-400:]))
    t['gr_has'] = bool(byid[t['id']]['general_response'])
    t['numq'] = t['qsegs'] > 0
    t['near_cap'] = any(c > 4800 for c in t['chars_per_post'])
F = [('Posts labelled as parts, such as (1/3) or Part 1', 'parts'), ('Any markdown table', 'has_table'), ('A general response on the forum', 'gr_has'),
     ('Numbered point labels at line start (W1, Q2, Weakness 3)', 'numq'), ('Reviewer text quoted in a blockquote', 'blockquote'), ('Markdown headings (#, ##, ###)', 'md_heading'),
     ('Phrase naming the revised document ("in the revised manuscript")', 'ptr_revised_or_updated_doc'), ('Colour marking named (in blue, highlighted)', 'ptr_colour_mark'),
     ('Line numbers given (Line 139, L460)', 'ptr_line_numbers'), ('First sentence thanks the reviewer', 'open_thanks'), ('Last post ends with an invitation to ask more', 'close_inv_tail'),
     ('Opens with a "Dear Reviewer" line', 'open_dear'), ('A post within 200 characters of the 5,000 cap', 'near_cap')]
R_ = [t for t in T if t['group'] == 'raised']; U = [t for t in T if t['group'] == 'unchanged']
out = ['| feature | raised | unchanged | diff |', '|---|---|---|---|']
for name, k in F:
    a = sum(bool(t[k]) for t in R_); b = sum(bool(t[k]) for t in U)
    l1, u1 = wilson(a, len(R_)); l2, u2 = wilson(b, len(U)); d, lo, hi = newcombe(a, len(R_), b, len(U))
    star = ' *' if lo > 0 or hi < 0 else ''
    out.append(f'| {name} | {a}/{len(R_)} = {100*a/len(R_):.0f}% [{100*l1:.0f}, {100*u1:.0f}] | {b}/{len(U)} = {100*b/len(U):.0f}% [{100*l2:.0f}, {100*u2:.0f}] | {100*d:+.0f} [{100*lo:+.0f}, {100*hi:+.0f}]{star} |')
print('\n'.join(out)); print()
out = ['| quantity | raised | unchanged | diff of medians [95%] |', '|---|---|---|---|']
M = [('Author characters per thread', lambda t: t['chars']), ('Author posts per thread', lambda t: t['n_posts']), ('Characters per post (thread median)', lambda t: st.median(t['chars_per_post'])),
     ('Tables per thread', lambda t: t['tables']), ('Words per numbered point (threads with labels)', lambda t: t.get('words_per_q'))]
for name, f in M:
    a = [f(t) for t in R_ if f(t) is not None]; b = [f(t) for t in U if f(t) is not None]
    d, lo, hi = boot_med_diff(a, b)
    star = ' *' if lo > 0 or hi < 0 else ''
    out.append(f'| {name} | {st.median(a):,.1f} (n={len(a)}) | {st.median(b):,.1f} (n={len(b)}) | {d:+,.1f} [{lo:+,.1f}, {hi:+,.1f}]{star} |')
print('\n'.join(out))
qr = [s for s in Q if s['group'] == 'raised']; qu = [s for s in Q if s['group'] == 'unchanged']
print('\npoint level (not independent):')
for k in ['has_num', 'has_ptr', 'has_rev', 'has_table', 'thanks_any']:
    a = sum(s[k] for s in qr); b = sum(s[k] for s in qu); d, lo, hi = newcombe(a, len(qr), b, len(qu))
    print(k, a, len(qr), b, len(qu), f'{100*d:+.0f} [{100*lo:+.0f},{100*hi:+.0f}]')
