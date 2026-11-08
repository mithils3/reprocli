"""Outcome-blind copies of the threads for author-side coding.

usage: build_blind.py <corpus_dir> <blind_dir> <key.json> <shard_dir>
Each blind file keeps the review, the authors' general responses and the authors' posts under the
review, and drops the header (group, ratings), the forum link and every reviewer follow-up. Author
sentences that mention a score change are redacted. Files get opaque ids; key.json maps id to source
file and group and lives outside blind_dir. Shards of 10 mix both groups (seed 22528).
"""
import glob, json, random, re, sys
from pathlib import Path

corpus, blind, key_path, shard_dir = sys.argv[1:5]
Path(blind).mkdir(parents=True, exist_ok=True)
Path(shard_dir).mkdir(parents=True, exist_ok=True)
SCORE = re.compile(r"[^.!?\n]*\b(rais|increas|updat|improv|revis|adjust|reconsider)\w*\s+(your |the |our |my )?(score|rating|assessment)[^.!?\n]*[.!?]?", re.I)
files = sorted(glob.glob(f"{corpus}/*.txt"))
rng = random.Random(22528)
ids = list(range(len(files)))
rng.shuffle(ids)
key = {}
for f, i in zip(files, ids):
    t = Path(f).read_text()
    group = re.search(r"GROUP: (\w+)", t).group(1)
    review = t.split("=== REVIEW ===", 1)[1].split("\n=== ", 1)[0].strip()
    general = ""
    if "=== AUTHORS' GENERAL RESPONSE(S) TO ALL REVIEWERS ===" in t:
        general = t.split("=== AUTHORS' GENERAL RESPONSE(S) TO ALL REVIEWERS ===", 1)[1].split("=== DISCUSSION UNDER THIS REVIEW", 1)[0].strip()
    disc = t.split("=== DISCUSSION UNDER THIS REVIEW (time order) ===", 1)[-1]
    posts = re.split(r"(?m)^--- (\S+) ---$", disc)
    auth = [posts[k + 1].strip() for k in range(1, len(posts) - 1, 2) if posts[k] == "AUTHORS"]
    if not auth:
        continue
    red = lambda s: SCORE.sub("[redacted]", s)
    review = re.split(r"(?im)^.{0,20}(post[- ]rebuttal|after (the )?(rebuttal|discussion|author response)|update[ds]? (after|following)|\[?update\b)", review)[0]
    parts = ["=== REVIEW ===", red(review).strip(), ""]
    if general:
        parts += ["=== AUTHORS' GENERAL RESPONSE TO ALL REVIEWERS ===", red(general), ""]
    parts += ["=== AUTHORS' POSTS UNDER THIS REVIEW (time order; reviewer replies removed) ==="]
    for n, a in enumerate(auth, 1):
        parts += [f"--- AUTHOR POST {n} ---", red(a), ""]
    bid = f"t{i:03d}"
    (Path(blind) / f"{bid}.txt").write_text("\n".join(parts))
    key[bid] = {"file": Path(f).name, "group": group}
Path(key_path).write_text(json.dumps(key, indent=1))
order = sorted(key)
rng.shuffle(order)
for s in range(0, len(order), 10):
    Path(shard_dir, f"blind_{s // 10:02d}.txt").write_text("\n".join(f"{Path(blind).resolve()}/{b}.txt" for b in order[s:s + 10]) + "\n")
print(len(key), "blind files;", sum(v["group"] == "raised" for v in key.values()), "raised;", (len(order) + 9) // 10, "shards")
