"""Blind packets for the reply-ranking workflow: review + first-round author reply, outcome and source hidden.
usage: build.py <corpus_dir> <repo_rebuttal_dir> <out_dir>
First round = author posts before the first reviewer post. Ratings and sub-scores are stripped from every review,
score-change sentences are redacted, ids are opaque, key.json stays outside packets/."""
import glob, json, random, re, sys
from pathlib import Path
corpus, reb, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
pk = out/'packets'
SCORE = re.compile(r"[^.!?\n]*\b(rais|increas|updat|improv|revis|adjust|reconsider)\w*\s+(your |the |our |my )?(score|rating|assessment)[^.!?\n]*[.!?]?", re.I)
META = re.compile(r"(?im)^(soundness|presentation|contribution|rating|confidence|flag_for_ethics_review|code_of_conduct|details_of_ethics_concerns)\s*:.*$\n?")
red = lambda s: SCORE.sub("[redacted]", s)
def fmt(review, general, posts):
    p = ["=== REVIEW ===", review.strip(), ""]
    if general: p += ["=== AUTHORS' GENERAL RESPONSE TO ALL REVIEWERS (context) ===", general.strip(), ""]
    p += ["=== AUTHORS' FIRST REPLY UNDER THIS REVIEW ==="]
    for n, a in enumerate(posts, 1): p += [f"--- AUTHOR POST {n} ---", a.strip(), ""]
    return "\n".join(p)
rows = []
for f in sorted(glob.glob(f"{corpus}/*.txt")):
    t = Path(f).read_text(); group = re.search(r"GROUP: (\w+)", t).group(1)
    review = t.split("=== REVIEW ===", 1)[1].split("\n=== ", 1)[0]
    review = re.split(r"(?im)^.{0,20}(post[- ]rebuttal|after (the )?(rebuttal|discussion|author response)|update[ds]? (after|following)|\[?update\b)", review)[0]
    review = red(META.sub("", review))
    general = ""
    if "=== AUTHORS' GENERAL RESPONSE(S) TO ALL REVIEWERS ===" in t:
        general = red(t.split("=== AUTHORS' GENERAL RESPONSE(S) TO ALL REVIEWERS ===", 1)[1].split("=== DISCUSSION UNDER THIS REVIEW", 1)[0])[:6000]
    disc = t.split("=== DISCUSSION UNDER THIS REVIEW (time order) ===", 1)[-1]
    parts = re.split(r"(?m)^--- (\S+) ---$", disc)
    first = []
    for k in range(1, len(parts) - 1, 2):
        if parts[k] != "AUTHORS": break
        first.append(red(parts[k + 1]))
    n = sum(len(a) for a in first)
    if not first or n < 1500 or n > 22000: continue
    rows.append((Path(f).name, group, fmt(review, general, first), n))
rng = random.Random(22528)
by = {g: [r for r in rows if r[1] == g] for g in ("raised", "unchanged")}
print({g: len(v) for g, v in by.items()})
for g in by: rng.shuffle(by[g])
NSH, PER = 30, 4
ours_review = (out/'ours_review.txt').read_text()
gen = (reb/'post/general.md').read_text()
ours = fmt(ours_review, gen, [f"title: Response to Reviewer YGTR ({i}/2)\ncomment: " + (reb/f'post/YGTR_{i}.md').read_text() for i in (1, 2)])
ids = [f"r{n:04d}" for n in rng.sample(range(1000, 9999), NSH * (2 * PER + 1) + 3)]
key, shards = {}, []
for s in range(NSH):
    items = [(r, r[1]) for r in by['raised'][s*PER:(s+1)*PER]] + [(r, r[1]) for r in by['unchanged'][s*PER:(s+1)*PER]] + [(("OURS", "ours", ours, 0), "ours")]
    rng.shuffle(items); paths = []
    for r, g in items:
        i = ids.pop(); (pk/f"{i}.txt").write_text(r[2]); key[i] = {"file": r[0], "group": g, "shard": s}; paths.append(str((pk/f"{i}.txt").resolve()))
    shards.append(paths)
h2h = []
for j in range(3):
    i = ids.pop(); (pk/f"{i}.txt").write_text(ours); key[i] = {"file": "OURS", "group": "ours", "shard": f"h2h{j}"}; h2h.append(i)
(out/'key.json').write_text(json.dumps(key, indent=1))
(out/'args.json').write_text(json.dumps({"shards": shards, "ours": {str(v["shard"]): k for k, v in key.items() if v["group"] == "ours"}, "pk": str(pk.resolve()), "out": str((out/'out').resolve())}))
sz = [sum(len(Path(p).read_text()) for p in sh) for sh in shards]
print("shards", NSH, "threads", sum(len(s) for s in shards), "chars per shard min/median/max", min(sz), sorted(sz)[NSH//2], max(sz), "ours chars", len(ours))
