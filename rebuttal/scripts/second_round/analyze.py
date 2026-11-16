"""Second-round study: which features of an author's second reply go with a reviewer raising afterwards.

Input folder R holds key.json (code -> thread id and regex outcome flags), feat_out/shard_NN.jsonl
(coder labels of the reviewer's first follow-up and the author's second reply, coded without the
reviewer's later comment) and out_out/shard_NN.jsonl (coder labels of the reviewer's later comment,
coded without the author's second reply).  Usage: analyze.py R OUT.md
"""
import glob
import json
import math
import sys

R, OUT = sys.argv[1], sys.argv[2]


def load(kind):
    rows = {}
    for p in sorted(glob.glob(f"{R}/{kind}_out/shard_*.jsonl")):
        for line in open(p):
            if line.strip():
                d = json.loads(line)
                rows[d["code"]] = d
    return rows


def newcombe(k1, n1, k2, n2, z=1.96):
    def wil(k, n):
        if n == 0:
            return 0.0, 1.0
        p = k / n
        c = p + z * z / (2 * n)
        h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
        d = 1 + z * z / n
        return (c - h) / d, (c + h) / d
    p1, p2 = (k1 / n1 if n1 else 0), (k2 / n2 if n2 else 0)
    l1, u1 = wil(k1, n1)
    l2, u2 = wil(k2, n2)
    d = p1 - p2
    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)


key = json.load(open(f"{R}/key.json"))
feat, out = load("feat"), load("out")
codes = [c for c in sorted(key) if c in feat and c in out]

L = []
w = L.append
w("# Second round: what the author's second reply looks like when the reviewer then raises\n")
w(f"Threads coded: {len(codes)} of {len(key)} sampled (ICLR 2025, public mirror). Each has a review, a first author reply, "
  "a reviewer follow-up that states no raise, a second author reply, and a later reviewer comment of 150 characters or more. "
  "Half were sampled where a regex found a raise in the later comment and half where it did not.\n")

# outcome: the out coder's reading of the later comment
raised = {c: bool(out[c]["later_states_raise"]) for c in codes}
agree = sum(raised[c] == bool(key[c]["r2_raise"]) for c in codes)
n_r = sum(raised.values())
w("## Outcome\n")
w(f"The outcome is the coder's reading of the reviewer's later comment (the coder saw no author text). It marks a stated raise in "
  f"{n_r} of {len(codes)} threads, and agrees with the regex flag used for sampling in {agree} of {len(codes)} "
  f"({100 * agree / len(codes):.0f}%).\n")
st = {}
for c in codes:
    st.setdefault(out[c]["later_stance"], [0, 0])[0 if raised[c] else 1] += 1
w("| Reviewer's later stance | raised | not raised |\n|---|---|---|")
for s, (a, b) in sorted(st.items(), key=lambda x: -sum(x[1])):
    w(f"| {s} | {a} | {b} |")
w("")

R1 = [c for c in codes if raised[c]]
R0 = [c for c in codes if not raised[c]]


def table(title, tests, sub1, sub0, col="Feature of the second reply"):
    w(f"## {title}\n")
    w(f"Raised n = {len(sub1)}, not raised n = {len(sub0)}. Gap is raised minus not raised in points, with a 95% interval (Newcombe).\n")
    w(f"| {col} | raised | not raised | gap |\n|---|---|---|---|")
    res = []
    for name, fn in tests:
        k1, k0 = sum(fn(feat[c]) for c in sub1), sum(fn(feat[c]) for c in sub0)
        d, lo, hi = newcombe(k1, len(sub1), k0, len(sub0))
        res.append((d, name, k1, k0, lo, hi))
    for d, name, k1, k0, lo, hi in sorted(res, key=lambda x: -x[0]):
        mark = " *" if lo > 0 or hi < 0 else ""
        p1 = 100 * k1 / len(sub1) if sub1 else 0
        p0 = 100 * k0 / len(sub0) if sub0 else 0
        w(f"| {name} | {k1} ({p1:.0f}%) | {k0} ({p0:.0f}%) | {100 * d:+.0f} [{100 * lo:+.0f}, {100 * hi:+.0f}]{mark} |")
    w("")


BOOL = ["a2_new_result", "a2_numbers_table", "a2_concedes_with_change", "a2_concedes_no_change", "a2_disagrees",
        "a2_disagrees_with_evidence", "a2_points_to_revision", "a2_promises_later", "a2_restates_first_reply",
        "a2_clarification_only"]
tests = [(b[3:].replace("_", " "), (lambda b: lambda f: bool(f[b]))(b)) for b in BOOL]
tests += [
    ("answers every concern raised", lambda f: f["r1_n_concerns"] > 0 and f["a2_n_answered"] >= f["r1_n_concerns"]),
    ("disagrees without evidence", lambda f: bool(f["a2_disagrees"]) and not f["a2_disagrees_with_evidence"]),
    ("tone warm", lambda f: f["a2_tone"] == "warm"),
    ("tone defensive", lambda f: f["a2_tone"] == "defensive"),
]
ctx = [
    ("reviewer asked for a new experiment", lambda f: bool(f["r1_asks_new_experiment"])),
    ("reviewer stance: satisfied", lambda f: f["r1_stance"] == "satisfied"),
    ("reviewer stance: partly", lambda f: f["r1_stance"] == "partly"),
    ("reviewer stance: unconvinced", lambda f: f["r1_stance"] == "unconvinced"),
    ("reviewer stance: new concern", lambda f: f["r1_stance"] == "new_concern"),
    ("reviewer stance: question only", lambda f: f["r1_stance"] == "question_only"),
    ("three or more concerns in the follow-up", lambda f: f["r1_n_concerns"] >= 3),
]
table("Where the reviewer stood before the second reply", ctx, R1, R0, col="Reviewer's follow-up")
table("All threads", tests, R1, R0)

hard = {"partly", "unconvinced", "new_concern"}
H1 = [c for c in R1 if feat[c]["r1_stance"] in hard]
H0 = [c for c in R0 if feat[c]["r1_stance"] in hard]
table("Threads where the reviewer's follow-up was partly satisfied, unconvinced or raised a new concern", tests, H1, H0)

X1 = [c for c in R1 if feat[c]["r1_asks_new_experiment"]]
X0 = [c for c in R0 if feat[c]["r1_asks_new_experiment"]]
table("Threads where the reviewer's follow-up asked for a new experiment", tests, X1, X0)

w("## Limits\n")
w("The sample was drawn half and half on the regex flag, so the percentages describe each group and are not raise rates. "
  "Every gap is a correlation. About 14 features are tested in each table, so one gap with an interval that excludes zero "
  "(marked *) is expected by chance. The coders are Claude Haiku 5.5; the coder of the second reply never saw the reviewer's "
  "later comment, and the coder of the later comment never saw the second reply.")
open(OUT, "w").write("\n".join(L) + "\n")
print(f"wrote {OUT}: {len(codes)} threads, raised {len(R1)}, not raised {len(R0)}, hard subset {len(H1)}/{len(H0)}")
