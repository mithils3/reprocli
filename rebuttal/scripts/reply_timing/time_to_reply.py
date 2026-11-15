import json, sys, pathlib, datetime as dt, collections as C
FD = pathlib.Path(sys.argv[1]); UTC = dt.timezone.utc
kind = lambda n: ((n.get("invitations") or [""])[0].split("/-/") + [""])[1]
role = lambda n: (n.get("signatures") or [""])[0].split("/")[-1]
FREEZE = dt.datetime(2025, 11, 28, 10, 57, tzinfo=UTC).timestamp()*1000
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
        if not au or au[0] >= FREEZE: continue
        rv = sorted(n["cdate"] for n in th if role(n) == role(R) and n["cdate"] > au[0])
        obs.append(((rv[0]-au[0])/3.6e6, 1, au[0]) if rv else ((FREEZE-au[0])/3.6e6, 0, au[0]))
print("threads with a response before the stop:", len(obs), "replied", sum(o[1] for o in obs))
def km(ob, ts):
    ev = sorted(ob); n = len(ev); s = 1.0; out = {}; i = 0; ts = list(ts); atrisk = n
    for t in ts:
        while i < n and ev[i][0] <= t:
            if ev[i][1]: s *= 1 - 1/atrisk
            atrisk -= 1; i += 1
        out[t] = (1-s, atrisk)
    return out
r = km(obs, (12, 24, 48, 72, 96, 120, 144, 168, 192, 240))
for t, (p, ar) in r.items(): print(f"reply within {t:>3} h ({t/24:.1f} d): {100*p:.0f}%   (threads still observed: {ar})")
# hazard by weekday: replies per 100 silent thread-days
exp = C.Counter(); evs = C.Counter()
for lag, e, a0 in obs:
    t = a0; end = a0 + lag*3.6e6
    while t < end:
        d = dt.datetime.fromtimestamp(t/1000, UTC); nxt = (d.replace(hour=0, minute=0, second=0, microsecond=0) + dt.timedelta(days=1)).timestamp()*1000
        exp[d.strftime("%a")] += (min(nxt, end)-t)/8.64e7; t = nxt
    if e: evs[dt.datetime.fromtimestamp(end/1000, UTC).strftime("%a")] += 1
print("replies per 100 silent thread-days, by weekday (UTC):", {k: round(100*evs[k]/exp[k], 1) for k in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")})
# by calendar date
exp = C.Counter(); evs = C.Counter()
for lag, e, a0 in obs:
    t = a0; end = a0 + lag*3.6e6
    while t < end:
        d = dt.datetime.fromtimestamp(t/1000, UTC); nxt = (d.replace(hour=0, minute=0, second=0, microsecond=0) + dt.timedelta(days=1)).timestamp()*1000
        exp[d.date()] += (min(nxt, end)-t)/8.64e7; t = nxt
    if e: evs[dt.datetime.fromtimestamp(end/1000, UTC).date()] += 1
print("by date:", {str(k)[5:]: round(100*evs[k]/exp[k], 1) for k in sorted(exp) if exp[k] > 20})
