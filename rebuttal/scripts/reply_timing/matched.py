import json, sys, pathlib, datetime as dt, collections as C
FD = pathlib.Path(sys.argv[1]); UTC = dt.timezone.utc
kind = lambda n: ((n.get("invitations") or [""])[0].split("/-/") + [""])[1]
role = lambda n: (n.get("signatures") or [""])[0].split("/")[-1]
END = dt.datetime(2025, 11, 29, 0, 0, tzinfo=UTC).timestamp()*1000  # end of 11-28 UTC
rows = []; lastrev = 0; firstrep_day = C.Counter(); revc = C.Counter()
for p in sorted(FD.glob("*.json")):
    notes = json.loads(p.read_text()); byid = {n["id"]: n for n in notes}
    def under(n, root):
        seen = set(); cur = n
        while cur is not None and cur["id"] not in seen:
            seen.add(cur["id"])
            if cur.get("replyto") == root: return True
            cur = byid.get(cur.get("replyto"))
        return False
    for n in notes:
        if kind(n) == "Official_Comment" and role(n).startswith("Reviewer"): lastrev = max(lastrev, n["cdate"])
    for R in [n for n in notes if kind(n) == "Official_Review"]:
        th = sorted([n for n in notes if n["id"] != R["id"] and under(n, R["id"])], key=lambda n: n["cdate"])
        au = [n for n in th if role(n) == "Authors"]
        if not au: continue
        a0 = au[0]["cdate"]; rv = [n["cdate"] for n in th if role(n) == role(R) and n["cdate"] > a0]
        rows.append(((END-a0)/8.64e7, (rv[0]-a0)/3.6e6 if rv else None, (END-rv[0])/8.64e7 if rv else None))
print("last reviewer comment", dt.datetime.fromtimestamp(lastrev/1000, UTC))
def cond(lo, hi, silent_h):
    g = [r for r in rows if lo <= r[0] < hi]; rep = [r for r in g if r[1] is not None]
    early = [r for r in rep if r[1] <= silent_h]; late = [r for r in rep if r[1] > silent_h]
    lag = sorted(r[1] for r in rep); q = lambda p: round(lag[int((len(lag)-1)*p)])
    print(f"authors answered {lo}-{hi} days before end: n={len(g)} replied={len(rep)} ({100*len(rep)/len(g):.0f}%) lag q25/med/q75 {q(.25)}/{q(.5)}/{q(.75)} h; replied within {silent_h} h: {len(early)}; still-silent threads {len(g)-len(early)}, of which reply later {len(late)} ({100*len(late)/(len(g)-len(early)):.0f}%)")
    d = C.Counter(int(r[2]) for r in late); print("   later replies by whole days before end:", sorted(d.items(), reverse=True))
cond(6.5, 8.0, 84)   # Reviewers 1 and 2: posted about 7.3 days before the end, silent for 84 h
cond(6.5, 8.0, 0)
cond(4.0, 5.5, 0)    # Reviewer 3: posted about 4.7 days before the end
cond(4.0, 5.5, 20)
rep = [r for r in rows if r[1] is not None]
print("first replies in final 5 days", sum(r[2] < 5 for r in rep), len(rep), "final 3 days", sum(r[2] < 3 for r in rep), "final 24h", sum(r[2] < 1 for r in rep))
