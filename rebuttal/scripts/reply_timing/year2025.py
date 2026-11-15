import json, sys, pathlib, datetime as dt, collections as C
FD = pathlib.Path(sys.argv[1]); UTC = dt.timezone.utc
kind = lambda n: ((n.get("invitations") or [""])[0].split("/-/") + [""])[1]
role = lambda n: (n.get("signatures") or [""])[0].split("/")[-1]
def val(c, k):
    v = (c or {}).get(k); return v.get("value") if isinstance(v, dict) else v
obs = []; last = 0; nrev = 0; auth_by = C.Counter(); rev_by = C.Counter(); firstrep_by = C.Counter(); ratings = C.Counter(); papers = []
for p in sorted(FD.glob("*.json")):
    notes = json.loads(p.read_text()); byid = {n["id"]: n for n in notes}
    def under(n, root):
        seen = set(); cur = n
        while cur is not None and cur["id"] not in seen:
            seen.add(cur["id"])
            if cur.get("replyto") == root: return True
            cur = byid.get(cur.get("replyto"))
        return False
    pr = []
    for n in notes:
        if kind(n) == "Official_Comment":
            d = dt.datetime.fromtimestamp(n["cdate"]/1000, UTC).date()
            if role(n).startswith("Reviewer"): rev_by[d] += 1; last = max(last, n["cdate"])
            elif role(n) == "Authors": auth_by[d] += 1
    for R in [n for n in notes if kind(n) == "Official_Review"]:
        nrev += 1
        th = [n for n in notes if n["id"] != R["id"] and under(n, R["id"])]
        au = sorted(n["cdate"] for n in th if role(n) == "Authors")
        if not au: continue
        rv = sorted(n["cdate"] for n in th if role(n) == role(R) and n["cdate"] > au[0])
        rt = str(val(R.get("content"), "rating") or "")[:2].strip(": ")
        obs.append(dict(a0=au[0], rep=rv[0] if rv else None, rating=rt)); pr.append(bool(rv))
        if rv: firstrep_by[dt.datetime.fromtimestamp(rv[0]/1000, UTC).date()] += 1
    if pr: papers.append(pr)
N = len(obs); rep = [o for o in obs if o["rep"]]
print("reviews", nrev, "threads with author response", N, "reviewer replied", len(rep), f"{100*len(rep)/N:.1f}%")
print("last reviewer comment", dt.datetime.fromtimestamp(last/1000, UTC))
print("papers", len(papers), ">=1 reply", sum(any(p) for p in papers), "all", sum(all(p) for p in papers))
print("\ndate: reviewer comments / first replies / author comments")
for d in sorted(set(rev_by) | set(auth_by)): print(d, d.strftime("%a"), rev_by[d], firstrep_by[d], auth_by[d])
lag = sorted((o["rep"]-o["a0"])/3.6e6 for o in rep); q = lambda p: round(lag[int((len(lag)-1)*p)], 1)
print("\nlag h p10/q25/med/q75/p90", q(.1), q(.25), q(.5), q(.75), q(.9))
for h in (12, 24, 48, 72, 96, 120, 168, 240): print(f"within {h} h: {sum(x<=h for x in lag)}/{N} = {100*sum(x<=h for x in lag)/N:.0f}%")
print("\nby rating:")
for k in sorted({o["rating"] for o in obs}):
    g = [o for o in obs if o["rating"] == k]; print(repr(k), len(g), sum(1 for o in g if o["rep"]), f"{100*sum(1 for o in g if o['rep'])/len(g):.0f}%")
# hazard by date and weekday
exp = C.Counter(); evs = C.Counter(); expw = C.Counter(); evw = C.Counter()
for o in obs:
    t = o["a0"]; end = o["rep"] or last
    while t < end:
        d = dt.datetime.fromtimestamp(t/1000, UTC); nxt = (d.replace(hour=0, minute=0, second=0, microsecond=0) + dt.timedelta(days=1)).timestamp()*1000
        w = (min(nxt, end)-t)/8.64e7; exp[d.date()] += w; expw[d.strftime("%a")] += w; t = nxt
    if o["rep"]:
        d = dt.datetime.fromtimestamp(o["rep"]/1000, UTC); evs[d.date()] += 1; evw[d.strftime("%a")] += 1
print("\nfirst replies per 100 silent thread-days by date:", {str(k)[5:]: round(100*evs[k]/exp[k], 1) for k in sorted(exp) if exp[k] > 20})
print("by weekday:", {k: round(100*evw[k]/expw[k], 1) for k in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")})
# by author-post date
print("\nby date the authors first answered: threads, replied, median lag h, share of replies within 48h")
by = C.defaultdict(list)
for o in obs: by[dt.datetime.fromtimestamp(o["a0"]/1000, UTC).date()].append(o)
import statistics as st
for d in sorted(by):
    g = by[d]; r = [(o["rep"]-o["a0"])/3.6e6 for o in g if o["rep"]]
    if len(g) >= 15: print(d, d.strftime("%a"), len(g), len(r), f"{100*len(r)/len(g):.0f}%", round(st.median(r), 0) if r else None, f"{sum(x<=48 for x in r)}/{len(g)}")
hr = C.Counter(dt.datetime.fromtimestamp(o["rep"]/1000, UTC).hour for o in rep if dt.datetime.fromtimestamp(o["rep"]/1000, UTC).date() in (dt.date(2024,11,26), dt.date(2024,11,27), dt.date(2024,12,2), dt.date(2024,12,3)))
print("\n(sanity) sample file keys:", sorted(notes[0].keys()))
