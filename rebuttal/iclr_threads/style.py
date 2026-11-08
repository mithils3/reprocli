"""Surface style of author replies: raised vs unchanged threads.

usage: style.py <corpus_dir> <style_stats.md> <style_rows.jsonl>
Author text = the AUTHORS posts under the review (general responses excluded).
Share rows: % of threads with the marker, Wilson 95%. Rate rows: median per 1,000 author words,
with a bootstrap 95% interval on the raised-minus-unchanged difference of medians (seed 22528).
"""
import glob, json, math, random, re, statistics, sys
from pathlib import Path

corpus, out_md, out_rows = sys.argv[1:4]

MARKERS = {
    "thanks": r"\bthank(s| you)\b|\bgrateful\b|\bappreciate",
    "apology": r"\b(sorry|apologi[sz]e|apologies)\b",
    "we_agree": r"\bwe (fully |completely |totally )?agree\b",
    "you_are_right": r"\byou are (absolutely |completely )?(right|correct)\b|\bgood (point|catch)\b|\bvalid (point|concern)\b",
    "respectfully": r"\brespectfully\b",
    "disagree": r"\b(disagree|we do not think|we don't think|we believe this is a misunderstanding|misunderst)",
    "hedge": r"\b(may|might|could|possibly|perhaps|likely|we believe|we think|to some extent|arguably)\b",
    "booster": r"\b(clearly|obviously|significantly|substantially|strongly|definitely|undoubtedly|indeed)\b",
    "we": r"\bwe\b|\bour\b|\bus\b",
    "you": r"\byou\b|\byour\b|\bthe reviewer\b",
    "location_ref": r"\b(line|lines|L\d+|section|sec\.|appendix|app\.|table|figure|fig\.|eq\.|equation)\s*[A-Z]?\d",
    "revised_pdf": r"\b(revised (paper|manuscript|version|pdf|draft)|updated (paper|manuscript|version|pdf|draft)|in the revision)\b",
    "color_mark": r"\b(in|highlighted in|marked in) (blue|red|green|orange|purple|magenta)\b",
    "promise_future": r"\b(will (add|include|clarify|revise|update|discuss)|in the (final|camera[- ]ready) version|in future work)\b",
    "score_ask": r"\b(raise|increase|reconsider|re-?evaluat\w*|update) (your |the )?(score|rating|assessment)\b",
    "nudge": r"\b(gentle reminder|kind reminder|kindly remind|discussion (period|phase) (ends|is ending|deadline)|haven't heard|look forward to your (response|feedback|reply))\b",
}
STRUCT = {
    "md_heading": r"(?m)^\s{0,3}(#{1,4} |\*\*[^*\n]{2,80}\*\*\s*$)",
    "bold": r"\*\*[^*\n]+\*\*",
    "bullet": r"(?m)^\s*([-*•]|\d+[.)])\s+",
    "table": r"(?m)^\s*\|.*\|\s*$",
    "blockquote": r"(?m)^\s*>",
    "latex": r"\$[^$\n]+\$",
    "link": r"https?://",
    "number": r"\b\d+(\.\d+)?%?",
    "point_label": r"\b(W|Q|C)\d\b|\bWeakness \d|\bQuestion \d|\bConcern \d",
}


def author_text(path):
    t = Path(path).read_text()
    head = t.split("\n", 3)
    group = re.search(r"GROUP: (\w+)", t).group(1)
    disc = t.split("=== DISCUSSION UNDER THIS REVIEW (time order) ===", 1)[-1]
    posts = re.split(r"(?m)^--- (\S+) ---$", disc)
    auth = [posts[i + 1].strip() for i in range(1, len(posts) - 1, 2) if posts[i] == "AUTHORS"]
    return group, auth


def sentences(text):
    plain = re.sub(r"(?m)^\s*\|.*$", "", text)
    plain = re.sub(r"\$[^$]+\$", "X", plain)
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(])", plain) if len(s.split()) >= 3]


rows = []
for f in sorted(glob.glob(f"{corpus}/*.txt")):
    group, auth = author_text(f)
    if not auth:
        continue
    text = "\n\n".join(auth)
    words = len(text.split())
    if words < 30:
        continue
    sents = sentences(text)
    first = auth[0]
    r = {"file": Path(f).name, "group": group, "posts": len(auth), "words": words,
         "first_post_words": len(first.split()),
         "sent_len_median": statistics.median([len(s.split()) for s in sents]) if sents else 0,
         "first_sentence": sents[0][:300] if sents else ""}
    for k, pat in {**MARKERS, **STRUCT}.items():
        n = len(re.findall(pat, text, flags=re.I if k in MARKERS else 0))
        r[k] = n
        r[k + "_per_k"] = 1000 * n / words
    r["thanks_in_first_40w"] = bool(re.search(MARKERS["thanks"], " ".join(first.split()[:40]), re.I))
    r["agree_in_first_40w"] = bool(re.search(MARKERS["we_agree"] + "|" + MARKERS["you_are_right"], " ".join(first.split()[:40]), re.I))
    r["last_post_score_ask"] = bool(re.search(MARKERS["score_ask"], auth[-1], re.I))
    rows.append(r)

with open(out_rows, "w") as fh:
    for r in rows:
        fh.write(json.dumps(r) + "\n")


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(100 * (c - h)), round(100 * (c + h))


G = {g: [r for r in rows if r["group"] == g] for g in ("raised", "unchanged")}
rng = random.Random(22528)


def boot_diff(a, b, n=2000):
    ds = sorted(statistics.median(rng.choices(a, k=len(a))) - statistics.median(rng.choices(b, k=len(b))) for _ in range(n))
    return ds[int(0.025 * n)], ds[int(0.975 * n)]


L = ["# Surface style of author replies: raised vs unchanged", "",
     f"Threads with author text under the review: raised n={len(G['raised'])}, unchanged n={len(G['unchanged'])}. "
     "Share rows: % of threads with at least one match [Wilson 95%]. Rate rows: median matches per 1,000 author words, "
     "with a bootstrap 95% interval on the difference of medians. Patterns are in style.py.", "",
     "## Share of threads with the marker", "", "| marker | raised | unchanged | diff (pts) |", "|---|---|---|---|"]
for k in list(MARKERS) + list(STRUCT) + ["thanks_in_first_40w", "agree_in_first_40w", "last_post_score_ask"]:
    c = {}
    for g, xs in G.items():
        hit = sum(1 for r in xs if r[k]); lo, hi = wilson(hit, len(xs)); c[g] = (round(100 * hit / len(xs)), lo, hi)
    a, b = c["raised"], c["unchanged"]
    L.append(f"| {k} | {a[0]}% [{a[1]}, {a[2]}] | {b[0]}% [{b[1]}, {b[2]}] | {a[0] - b[0]:+d} |")
L += ["", "## Medians", "", "| quantity | raised | unchanged | diff of medians [95%] |", "|---|---|---|---|"]
for k in ["words", "posts", "first_post_words", "sent_len_median"] + [m + "_per_k" for m in list(MARKERS) + list(STRUCT)]:
    a = [r[k] for r in G["raised"]]; b = [r[k] for r in G["unchanged"]]
    lo, hi = boot_diff(a, b)
    L.append(f"| {k} | {statistics.median(a):.1f} | {statistics.median(b):.1f} | {statistics.median(a) - statistics.median(b):+.1f} [{lo:+.1f}, {hi:+.1f}] |")
Path(out_md).write_text("\n".join(L) + "\n")
print("\n".join(L))
