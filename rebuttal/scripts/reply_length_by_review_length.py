import json, statistics, sys
from collections import defaultdict

BASE = "/home/mithil/PyCharmProjects/reprocli/rebuttal/results/style/"

def pct(xs, p):
    s = sorted(xs)
    if not s:
        return float("nan")
    k = (len(s) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)

def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r

def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx) ** 0.5
    vy = sum((b - my) ** 2 for b in ry) ** 0.5
    return cov / (vx * vy)

reviews = {}
with open(BASE + "review_comments.jsonl") as f:
    for line in f:
        r = json.loads(line)
        reviews[r["id"]] = len(r["text"].split())

replies = defaultdict(lambda: {"chars": 0, "words": 0, "posts": 0})
n_lines = 0
with open(BASE + "author_comments.jsonl") as f:
    for line in f:
        n_lines += 1
        c = json.loads(line)
        rt = c.get("replyto")
        if rt in reviews:
            d = replies[rt]
            d["chars"] += len(c["text"])
            d["words"] += len(c["text"].split())
            d["posts"] += 1

rows = []
no_reply = 0
for rid, wc in reviews.items():
    if rid not in replies:
        no_reply += 1
        continue
    d = replies[rid]
    rows.append((wc, d["chars"], d["words"], d["posts"]))

BINS = [("under 250", 0, 249), ("250-349", 250, 349), ("350-499", 350, 499),
        ("500-699", 500, 699), ("700-999", 700, 999), ("1000 or more", 1000, 10**9)]

def row_stats(name, rs):
    chars = [r[1] for r in rs]
    words = [r[2] for r in rs]
    posts = [r[3] for r in rs]
    ratio = [r[2] / r[0] for r in rs]
    return (f"| {name} | {len(rs)} | {pct(chars,.5):,.0f} | {pct(chars,.25):,.0f} | "
            f"{pct(chars,.75):,.0f} | {pct(words,.5):,.0f} | {pct(posts,.5):,.1f} | "
            f"{pct(ratio,.5):.2f} |")

print(f"Author comments read: {n_lines:,}. Reviews in set: {len(reviews):,}. "
      f"Reviews with no direct author reply (dropped): {no_reply:,}. Kept: {len(rows):,}.\n")
print("| Review words | n | Reply chars median | Q25 | Q75 | Reply words median | Posts median | Reply/review words median |")
print("|---|---|---|---|---|---|---|---|")
for name, lo, hi in BINS:
    rs = [r for r in rows if lo <= r[0] <= hi]
    if rs:
        print(row_stats(name, rs))
print(row_stats("All reviews", rows))

rho = spearman([r[0] for r in rows], [r[1] for r in rows])
print(f"\nSpearman rho, review words vs reply chars: {rho:.3f} (n={len(rows):,}).\n")

print("Lookups (reviews within 15% of target word count):\n")
print("| Target words | n | Reply chars median | Q25 | Q75 |")
print("|---|---|---|---|---|")
for t in (205, 320, 850):
    rs = [r for r in rows if abs(r[0] - t) <= 0.15 * t]
    print(f"| {t} | {len(rs)} | {pct([r[1] for r in rs],.5):,.0f} | "
          f"{pct([r[1] for r in rs],.25):,.0f} | {pct([r[1] for r in rs],.75):,.0f} |")

print("\nMethod: each review was matched to author comments whose replyto equals the review id; "
      "reply length is the summed characters and words of those comments, and posts is their count. "
      "Reviews without a direct author reply were dropped, so the set only holds threads where authors replied.")
