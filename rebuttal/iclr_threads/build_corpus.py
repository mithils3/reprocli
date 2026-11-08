"""Build a corpus of ICLR 2025 review threads where the reviewer changed (or kept) their score.

Scores before/after rebuttal: Paper Copilot iclr-insights (iclr2025_threshold6_11677_reviewers.json).
Thread text: HF dataset Jasonpicky/openreview_raw (OpenReview notes), parquet downloaded with
`hf download Jasonpicky/openreview_raw --repo-type dataset --revision refs/convert/parquet` (argv[3]).
Selection (seed 22528): 250 "raised" threads where the rating crossed from <=5 to >=6, one reviewer
per forum, plus 50 "unchanged" controls with rating <=5 that stayed put although the reviewer replied.
"""
import json, random, sys
from pathlib import Path

OUT = Path(sys.argv[1])
PC = Path(sys.argv[2])
PARQ = Path(sys.argv[3])
SEED, N_RAISED = 22528, 250
N_CTRL = int(sys.argv[4]) if len(sys.argv) > 4 else 50


FORUMS = {}


def load_parquet(d):
    import pyarrow.dataset as ds
    t = ds.dataset(str(d), format="parquet").to_table(
        filter=ds.field("venue") == "ICLR.cc/2025/Conference",
        columns=["forum_id", "note_id", "note_type", "note_created", "note_replyto", "note_signatures", "note_text"])
    for r in t.to_pylist():
        FORUMS.setdefault(r["forum_id"], []).append(r)


def fetch_forum(fid):
    return FORUMS.get(fid)


def sig(r):
    s = r["note_signatures"][0] if r["note_signatures"] else ""
    return s.rsplit("/", 1)[-1]


def thread_text(paper, rows, reviewer, pre, post, group):
    review = next((r for r in rows if r["note_type"] == "official_review" and sig(r) == f"Reviewer_{reviewer}"), None)
    if review is None:
        return None
    kids = {}
    for r in rows:
        kids.setdefault(r["note_replyto"], []).append(r)
    sub, stack = [], [review["note_id"]]
    while stack:
        nid = stack.pop()
        for k in kids.get(nid, []):
            sub.append(k); stack.append(k["note_id"])
    general = [r for r in rows if r["note_replyto"] == paper["id"] and r["note_type"] == "official_comment"
               and sig(r) == "Authors"]
    reviewer_replied = any(sig(r) == f"Reviewer_{reviewer}" for r in sub)
    sub.sort(key=lambda r: r["note_created"] or 0)
    general.sort(key=lambda r: r["note_created"] or 0)
    parts = [f"PAPER: {paper['title']}", f"GROUP: {group}  REVIEWER: {reviewer}  RATING BEFORE: {pre}  AFTER: {post}",
             f"FORUM: https://openreview.net/forum?id={paper['id']}", "", "=== REVIEW ===", review["note_text"].strip(), ""]
    if general:
        parts += ["=== AUTHORS' GENERAL RESPONSE(S) TO ALL REVIEWERS ==="]
        parts += [g["note_text"].strip()[:6000] + "\n" for g in general[:2]]
    parts += ["=== DISCUSSION UNDER THIS REVIEW (time order) ==="]
    for r in sub:
        who = "AUTHORS" if sig(r) == "Authors" else sig(r).upper()
        parts += [f"--- {who} ---", r["note_text"].strip(), ""]
    text = "\n".join(parts)
    return text[:40000], reviewer_replied, len(sub)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    load_parquet(PARQ)
    print(f"forums loaded {len(FORUMS)}", flush=True)
    data = json.load(open(PC))
    raised, ctrl = [], []
    for p in data:
        for rv, s in (p.get("review") or {}).items():
            try:
                pre, post = (int(float(x)) for x in s["rating"].split(";"))
            except Exception:
                continue
            if pre <= 5 and post >= 6:
                raised.append((p, rv, pre, post))
            elif pre <= 5 and post == pre:
                ctrl.append((p, rv, pre, post))
    rng = random.Random(SEED)
    rng.shuffle(raised); rng.shuffle(ctrl)
    ctrl = ctrl[:max(400, N_CTRL * 8)]
    print(f"candidates raised={len(raised)} unchanged={len(ctrl)}", flush=True)
    manifest, seen = [], set()

    def take(pool, n, group, need_reply):
        cand = [c for c in pool if c[0]["id"] not in seen][: int(n * (4 if need_reply else 1.6))]
        fetched = [fetch_forum(c[0]["id"]) for c in cand]
        got = 0
        for (p, rv, pre, post), rows in zip(cand, fetched):
            if got >= n:
                break
            if p["id"] in seen or not rows:
                continue
            res = thread_text(p, rows, rv, pre, post, group)
            if not res:
                continue
            text, replied, n_sub = res
            if n_sub == 0 or (need_reply and not replied):
                continue
            seen.add(p["id"])
            name = f"{group}-{got:03d}-{p['id']}-{rv}.txt"
            (OUT / name).write_text(text)
            manifest.append({"file": name, "group": group, "forum": p["id"], "reviewer": rv, "pre": pre,
                             "post": post, "chars": len(text), "title": p["title"]})
            got += 1
        print(f"{group}: kept {got} of {len(cand)} fetched", flush=True)
        return got

    take(raised, N_RAISED, "raised", need_reply=False)
    take(ctrl, N_CTRL, "unchanged", need_reply=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print("done", len(manifest), flush=True)


if __name__ == "__main__":
    main()
