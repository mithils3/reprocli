import json, sys, pathlib, datetime as dt, statistics as st, re, collections as C
FD = pathlib.Path(sys.argv[1]); UTC = dt.timezone.utc
kind = lambda n: ((n.get("invitations") or [""])[0].split("/-/") + [""])[1]
role = lambda n: (n.get("signatures") or [""])[0].split("/")[-1]
day = lambda ms: dt.datetime.fromtimestamp(ms/1000, UTC).date()
def val(c, k):
    v = c.get(k); return v.get("value") if isinstance(v, dict) else v
def text(n):
    return " ".join(str(val(n.get("content", {}), k) or "") for k in ("title", "comment"))
def wil(k, n, z=1.96):
    if not n: return "n/a"
    p = k/n; d = 1+z*z/n; c = (p+z*z/(2*n))/d; h = z*((p*(1-p)/n+z*z/(4*n*n))**.5)/d
    return f"{k}/{n} = {100*p:.0f}% [{100*(c-h):.0f}%, {100*(c+h):.0f}%]"
med = lambda v: round(st.median(v), 1) if v else None
rows = []; allnotes = C.Counter(); papers = []
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
        if kind(n) == "Official_Comment": allnotes[(day(n["cdate"]), "rev" if role(n).startswith("Reviewer") else "auth" if role(n) == "Authors" else "ac")] += 1
    withdrawn = any(kind(n) == "Withdrawal" for n in notes)
    prow = []
    for R in [n for n in notes if kind(n) == "Official_Review"]:
        th = sorted([n for n in notes if n["id"] != R["id"] and under(n, R["id"])], key=lambda n: n["cdate"])
        au = [n for n in th if role(n) == "Authors"]
        if not au: continue
        a0 = au[0]; me = role(R)
        rv = [n for n in th if role(n) == me and n["cdate"] > a0["cdate"]]
        r = dict(forum=p.stem, rating=val(R["content"], "rating"), conf=val(R["content"], "confidence"), a0=a0["cdate"], rep=rv[0]["cdate"] if rv else None,
                 nrev=len(rv), edited=R.get("mdate", 0) > a0["cdate"], mdate=R.get("mdate"), withdrawn=withdrawn,
                 txt=text(rv[0]) if rv else "", au_before=len([n for n in au if not rv or n["cdate"] < rv[0]["cdate"]]),
                 au_after=len([n for n in au if rv and n["cdate"] > rv[0]["cdate"]]),
                 a_parts=len([n for n in au if n["cdate"] - a0["cdate"] < 3.6e6]))
        rows.append(r); prow.append(r)
    if prow: papers.append(prow)
N = len(rows); rep = [r for r in rows if r["rep"]]
print("threads", N, "replied", wil(len(rep), N))
END = dt.date(2025, 11, 28)
print("\n== activity by date (official comments): reviewers / authors / AC")
for d in sorted({k[0] for k in allnotes}):
    if d >= dt.date(2025, 11, 10): print(d, d.strftime("%a"), allnotes[(d, "rev")], allnotes[(d, "auth")], allnotes[(d, "ac")])
print("\n== review mdate by date (edits)"); mc = C.Counter(day(r["mdate"]) for r in rows)
for d in sorted(mc): print(d, mc[d])
print("\n== by rating: reply rate, median lag h, share edited after response")
for k in sorted({r["rating"] for r in rows}, key=lambda x: (x is None, x)):
    g = [r for r in rows if r["rating"] == k]; gr = [r for r in g if r["rep"]]
    print(k, wil(len(gr), len(g)), "lag", med([(r["rep"]-r["a0"])/3.6e6 for r in gr]), "edited", wil(sum(r["edited"] for r in g), len(g)))
print("\n== by day the authors first answered (days before 11-28): reply rate, median lag h, median reply day-before-end")
bk = C.defaultdict(list)
for r in rows: bk[(END - day(r["a0"])).days].append(r)
for k in sorted(bk, reverse=True):
    g = bk[k]; gr = [r for r in g if r["rep"]]
    print(k, wil(len(gr), len(g)), "lag", med([(r["rep"]-r["a0"])/3.6e6 for r in gr]), "replyday", med([(END-day(r["rep"])).days for r in gr]))
def grp(lo, hi):
    g = [r for r in rows if lo <= (END-day(r["a0"])).days <= hi]; gr = [r for r in g if r["rep"]]
    lag = sorted((r["rep"]-r["a0"])/3.6e6 for r in gr)
    q = lambda p: round(lag[int((len(lag)-1)*p)], 0) if lag else None
    return f"{wil(len(gr), len(g))} lag q25 {q(.25)} med {q(.5)} q75 {q(.75)}; within 24h {sum(x<=24 for x in lag)}, 48h {sum(x<=48 for x in lag)}, 72h {sum(x<=72 for x in lag)}, 96h {sum(x<=96 for x in lag)} of {len(g)} threads; last-3-days replies {sum((END-day(r['rep'])).days<=2 for r in gr)}/{len(gr)}"
for lo, hi in ((10, 20), (7, 9), (5, 6), (3, 4), (0, 2)): print(f"authors answered {hi}-{lo} days before end:", grp(lo, hi))
print("\n== weekday / hour (UTC) of first reviewer replies")
wd = C.Counter(dt.datetime.fromtimestamp(r["rep"]/1000, UTC).strftime("%a") for r in rep); print(dict(wd))
hr = C.Counter(dt.datetime.fromtimestamp(r["rep"]/1000, UTC).hour//4*4 for r in rep); print({f"{k:02d}-{k+4:02d}": hr[k] for k in sorted(hr)})
print("\n== papers")
np_ = len(papers); print("papers", np_, "with >=1 reviewer reply", wil(sum(any(r["rep"] for r in p) for p in papers), np_), "all reviewers replied", wil(sum(all(r["rep"] for r in p) for p in papers), np_))
dist = C.Counter((sum(1 for r in p if r["rep"]), len(p)) for p in papers); print("replied-of-reviewers:", sorted(dist.items()))
print("\n== what the first reviewer reply says (regex)")
UP = re.compile(r"(rais|increas|upgrad|bump|improv)\w*\s+(my|the)?\s*(score|rating|recommendation|evaluation)|(score|rating)\s+(to|from|up)|updat\w+\s+(my|the)\s+(score|rating)|(have|will|i'll|i)\s+(raised|increased|updated)|lean\w*\s+toward\w*\s+accept", re.I)
KEEP = re.compile(r"(maintain|keep|retain|remain|stand by|stick)\w*\s+(with\s+)?(my|the)?\s*(original|current|initial)?\s*(score|rating|assessment|evaluation|recommendation)|not\s+(change|chang|rais|increas)\w*|unchanged|still\s+(have|believe|think|find|feel)|remain\w*\s+(unconvinced|concerned)", re.I)
Q = re.compile(r"\?")
cls = C.Counter()
for r in rep:
    t = r["txt"]; u = bool(UP.search(t)); k = bool(KEEP.search(t))
    cls["raise" if u and not k else "keep" if k and not u else "both" if u and k else "question" if Q.search(t) else "other"] += 1
print(dict(cls)); print("median chars of first reply", med([len(r["txt"]) for r in rep]))
for lab, f in (("raise-ish", lambda r: UP.search(r["txt"]) and not KEEP.search(r["txt"])), ("keep-ish", lambda r: KEEP.search(r["txt"]) and not UP.search(r["txt"]))):
    g = [r for r in rep if f(r)]; print(lab, len(g), "lag med", med([(r["rep"]-r["a0"])/3.6e6 for r in g]), "replyday med", med([(END-day(r["rep"])).days for r in g]), "ratings", sorted(C.Counter(r["rating"] for r in g).items(), key=lambda x: (x[0] is None, x[0])))
print("\n== rounds")
print("authors answered the reviewer reply:", wil(sum(r["au_after"] > 0 for r in rep), len(rep)), "| reviewer wrote 2+ times:", wil(sum(r["nrev"] >= 2 for r in rep), len(rep)))
print("\n== silent edits: review edited after the response, no comment")
sil = [r for r in rows if not r["rep"]]; print(wil(sum(r["edited"] for r in sil), len(sil)), "| among repliers:", wil(sum(r["edited"] for r in rep), len(rep)))
print("\n== author follow-up before any reviewer reply (a later author note >=24h after first)")
