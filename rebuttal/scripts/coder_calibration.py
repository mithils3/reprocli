#!/usr/bin/env python3
"""Run the unchanged blind failure-mode coder on open-agent runs that carry paper labels.

Frame: the 372 graded open-agent runs of the paper, with the primary mode of record in
~/sweeps/paper-table-2026-09-05/resolved_modes.json, joined to the run directory on Delta by
(sweep job id, arXiv id) as listed in tools/anon_viewer/export.py SWEEPS. Failing = mode other than
reproduced-clean. Draw rule (seed 20261109, random.Random): every run labelled "Never launched an
experiment" (procrastination/wall-kill), plus 3 per other failing mode drawn uniformly, plus the
remaining draws of 40 uniform from the other failing runs not yet drawn.

    python3 rebuttal/scripts/coder_calibration.py [--dry-run] [--frame frame.json]
"""
import argparse, csv, json, os, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import frontier_failure_modes as F

OUT = F.OUT_DIR / "coder_calibration.csv"
SEED, N_STRAT, PER_MODE = 20261109, 40, 3
NL = "procrastination/wall-kill"


def draw(frame):
    rng = random.Random(SEED)
    fails = sorted((x for x in frame if x["mode"] != "reproduced-clean"), key=lambda x: x["id"])
    forced = [x for x in fails if x["mode"] == NL]
    rest = [x for x in fails if x["mode"] != NL]
    picked = []
    for m in sorted({x["mode"] for x in rest}):
        pool = [x for x in rest if x["mode"] == m]
        if len(pool) >= 5:
            picked += rng.sample(pool, PER_MODE)
    left = [x for x in rest if x not in picked]
    picked += rng.sample(left, N_STRAT - len(picked))
    return forced + picked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--frame", required=True)
    a = ap.parse_args()
    os.nice(19)
    sample = draw(json.load(open(a.frame)))
    rows = [{"run_id": x["id"], "arm": x["model"] + "-" + x["tier"], "paper": x["arxiv"],
             "run_dir": x["run_dir"], "paper_mode": x["mode"]} for x in sample]
    est = len(rows) * 0.15
    print(f"{len(rows)} runs, estimated ${est:.2f}; Anthropic ledger ${F.spent():.2f}", file=sys.stderr)
    if est > 10:
        sys.exit("estimate over $10; stopping")
    done = {}
    if OUT.is_file():
        done = {r["run_id"]: r for r in csv.DictReader(OUT.open())}
    for r in rows:
        F.digest(r)  # read-only transcript fetch over delta, cached
    if a.dry_run:
        return
    import anthropic
    from concurrent.futures import ThreadPoolExecutor
    client = anthropic.Anthropic()
    todo = [r for r in rows if r["run_id"] not in done]
    n0 = sum(1 for _ in F.LEDGER.open())
    with ThreadPoolExecutor(4) as ex:
        futs = [ex.submit(F.code_one, client, r) for r in todo]
        for f in futs:
            try:
                res = f.result()
            except Exception as e:
                print("skipped:", e, file=sys.stderr); continue
            r, o = res["r"], res["obj"]
            done[r["run_id"]] = {"run_id": r["run_id"], "arm": r["arm"], "paper": r["paper"], "paper_mode": r["paper_mode"],
                                 **o["modes"], "primary": o["primary"], "evidence": o["evidence"], "coder_model": F.MODEL}
    cols = ["run_id", "arm", "paper", "paper_mode"] + F.SLUGS + ["primary", "evidence", "coder_model"]
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, cols); w.writeheader()
        for k in sorted(done): w.writerow({c: done[k].get(c, "") for c in cols})
    lines = F.LEDGER.read_text().splitlines()
    for i in range(n0, len(lines)):
        d = json.loads(lines[i])
        if d.get("item") == "frontier-failure-modes":
            d["item"] = "coder-calibration"
            d["note"] = d["note"].replace("failure-mode coding", "calibration coding of open-agent run")
            lines[i] = json.dumps(d, sort_keys=True)
    F.LEDGER.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
