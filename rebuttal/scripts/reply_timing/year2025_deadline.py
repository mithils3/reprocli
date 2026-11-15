import json, sys, pathlib, datetime as dt, collections as C
FD = pathlib.Path(sys.argv[1]); UTC = dt.timezone.utc
kind = lambda n: ((n.get("invitations") or [""])[0].split("/-/") + [""])[1]
role = lambda n: (n.get("signatures") or [""])[0].split("/")[-1]
D1 = dt.datetime(2024, 11, 27, 12, 0, tzinfo=UTC).timestamp()*1000   # 11-26 23:59 AoE, candidate first deadline
D1b = dt.datetime(2024, 11, 28, 12, 0, tzinfo=UTC).timestamp()*1000  # 11-27 23:59 AoE
obs = []
for p in sorted(FD.glob("*.json")):
    notes = json.loads(p.read_text()); byid = {n["id"]: n for n in notes}
    def under(n, root):
        seen = set(); cur = n
        while cur is not None and cur["id"] not in seen:
            seen.add(cur["id"])
            if cur.get("replyto") == root: return True
            cur = byid.get(cur.get("replyto"))
        return False
    for R in [n for n in notes if kind(n) == "Official_Review"]:
        th = [n for n in notes if n["id"] != R["id"] and under(n, R["id"])]
        au = sorted(n["cdate"] for n in th if role(n) == "Authors")
        if not au: continue
        rv = sorted(n["cdate"] for n in th if role(n) == role(R) and n["cdate"] > au[0])
        obs.append((au[0], rv[0] if rv else None))
rep = [o for o in obs if o[1]]
# hourly profile around the candidate deadlines
hh = C.Counter()
for a, r in rep:
    d = dt.datetime.fromtimestamp(r/1000, UTC)
    if dt.date(2024, 11, 26) <= d.date() <= dt.date(2024, 11, 28): hh[(d.strftime("%m-%d"), d.hour//6*6)] += 1
print("first replies per 6 h block (UTC):", sorted(hh.items()))
for name, D in (("D1 = 11-27 12:00 UTC", D1), ("D1b = 11-28 12:00 UTC", D1b)):
    print("\n", name)
    print("  first replies: before D-72h", sum(r < D-72*3.6e6 for a, r in rep), "| last 72h before D", sum(D-72*3.6e6 <= r < D for a, r in rep), "(last 24h", sum(D-24*3.6e6 <= r < D for a, r in rep), ") | after D", sum(r >= D for a, r in rep), "| total", len(rep))
    for lo, hi, sil in ((6.5, 8.0, 0), (6.5, 8.0, 84), (4.0, 5.5, 0), (4.0, 5.5, 20)):
        g = [(a, r) for a, r in obs if lo <= (D-a)/8.64e7 < hi]
        early = [1 for a, r in g if r and (r-a)/3.6e6 <= sil]
        still = [(a, r) for a, r in g if not (r and (r-a)/3.6e6 <= sil)]
        byD = [1 for a, r in still if r and r < D]; ever = [1 for a, r in still if r]
        days = C.Counter(int((D-r)/8.64e7) for a, r in still if r and r < D)
        print(f"  answered {lo}-{hi} d before D, silent at {sil} h: n={len(still)} (of {len(g)}); replied before D {len(byD)} ({100*len(byD)/len(still):.0f}%); replied ever {len(ever)} ({100*len(ever)/len(still):.0f}%); by whole days before D {sorted(days.items(), reverse=True)}")
