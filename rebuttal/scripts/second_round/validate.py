import json, re, sys, pathlib
kind, nn = sys.argv[1], sys.argv[2]
R = pathlib.Path(__file__).parent
shard = (R / kind / f"shard_{nn}.md").read_text()
codes = re.findall(r"(?m)^## (t\d{3})$", shard)
outp = R / f"{kind}_out" / f"shard_{nn}.jsonl"
B = bool
spec = {"feat": {"r1_n_concerns": int, "r1_asks_new_experiment": B, "r1_stance": {"satisfied", "partly", "unconvinced", "new_concern", "question_only"},
                 "a2_n_answered": int, "a2_new_result": B, "a2_numbers_table": B, "a2_concedes_with_change": B, "a2_concedes_no_change": B,
                 "a2_disagrees": B, "a2_disagrees_with_evidence": B, "a2_points_to_revision": B, "a2_promises_later": B,
                 "a2_restates_first_reply": B, "a2_clarification_only": B, "a2_tone": {"warm", "neutral", "defensive"}},
        "out": {"c1_states_raise": B, "c1_states_keep": B, "later_states_raise": B, "later_states_keep": B, "later_states_lower": B,
                "later_new_score": (int, type(None)), "later_stance": {"satisfied", "partly", "unconvinced", "unclear"}}}[kind]
if not outp.exists():
    sys.exit(f"FAIL: {outp} missing")
rows = [json.loads(l) for l in outp.read_text().splitlines() if l.strip()]
errs = []
if [r.get("code") for r in rows] != codes:
    errs.append(f"codes must be exactly, in order: {codes}")
for r in rows:
    if set(r) != set(spec) | {"code"}:
        errs.append(f"{r.get('code')}: keys differ: missing {sorted(set(spec) - set(r))} extra {sorted(set(r) - set(spec) - {'code'})}")
        continue
    for k, t in spec.items():
        v = r[k]
        ok = (v in t) if isinstance(t, set) else (isinstance(v, t) and not (t is int and isinstance(v, bool)))
        if isinstance(t, tuple): ok = isinstance(v, t) and not isinstance(v, bool)
        if not ok: errs.append(f"{r['code']}: bad value for {k}: {v!r}")
print("FAIL\n" + "\n".join(errs[:12]) if errs else f"OK {kind} shard {nn}: {len(rows)} rows")
