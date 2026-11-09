#!/usr/bin/env python3
"""Code failure modes for failing frontier-arm runs with the paper's nine-mode taxonomy.

The paper's labels came from a language model reading each run's transcript against the
Appendix G definitions (Sonnet dissection fan-out, skill analyze-sweep). The original prompt
was not saved, so this script rebuilds it from the Appendix G definitions and uses the pinned
auditor model (claude-sonnet-5). Deviation from the paper's pass, on purpose: the coder never
sees the verdict, score, flags or arm, and each run is its own call, so no shard can mix or
split arms. The coder returns strict JSON booleans, one per mode, and one primary mode.

Rows: verdict not_reproduced, partial or unverifiable in rebuttal/results/databook/frontier_cells.csv.
Transcripts are read over `delta` (read only) and cut to a digest. Reruns code only run_ids
missing from failure_modes.csv. Local work runs at nice 19; the only remote step is reading files.

    python3 rebuttal/scripts/frontier_failure_modes.py [--dry-run] [--limit N] [--report-only]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CELLS = ROOT / "rebuttal/results/databook/frontier_cells.csv"
OUT_DIR = ROOT / "rebuttal/results/frontier"
CSV_OUT = OUT_DIR / "failure_modes.csv"
MD_OUT = OUT_DIR / "failure_modes.md"
LEDGER = ROOT / "rebuttal/results/spend/spend.jsonl"
CACHE = Path.home() / ".cache/frontier_failure_modes"
MODEL = "claude-sonnet-5"
FAIL = {"not_reproduced", "partial", "unverifiable"}
PLANNED = 58
MAX_USD, ANTHROPIC_CAP = 15.0, 200.0
# $/M tokens, fitted to the ledger's frontier-grade rows: input plus cache write, cached read, output.
P_IN, P_CACHED, P_OUT = 3.75, 0.30, 15.0

# slug, plain-language name used in the paper, open-agent cell count of 400 (Table failure-modes-by-agent)
MODES = [
    ("reproduced-clean", "Reproduced", 72),
    ("near-miss-partial", "Ran, outside tolerance", 76),
    ("reimplement-without-validating", "Reimplemented but did not check the result", 63),
    ("environment-fights", "Build and dependency failures", 24),
    ("artifact-provenance-mismatch", "Wrong artifact measured", 38),
    ("scope-substitution", "Wrong experiment", 46),
    ("stale-artifact-reliance", "Echoed a shipped number", 9),
    ("procrastination/wall-kill", "Never launched an experiment", 13),
    ("killed-before-the-number", "Failed before any number was produced", 31),
]
SLUGS = [m[0] for m in MODES]
OPEN_NO_LABEL = 28

DEFS = """\
reproduced-clean: The agent runs the pinned experiment, using the released artifacts the tier provides, and the number it computed lands inside the pinned bar. Evidence: a number the run computed, traced to a command that ran the experiment.
near-miss-partial: The agent runs the right pipeline and measures a number that misses the bar. Evidence: a completed run of the pinned quantity with clean provenance and a measured value on the wrong side of the bar.
reimplement-without-validating: The agent writes its own version of the method, or part of it, and never checks any stage against a reference it did not produce. Evidence: a component written from scratch in the run's own code, and a reference number the paper supplies (most often its baseline in the same table as the target) that the transcript never compares against.
environment-fights: Most of the run goes to build and dependency failures in the released stack, and the experiment never produces a valid number. Evidence: repeated install, compile and binary-compatibility failures against the authors' pinned versions.
artifact-provenance-mismatch: The agent measures a different checkpoint, dataset, split or scale from the one the dataset row names. Evidence: a downloaded artifact whose model card, README or example disagrees with the task, and a measurement taken on it.
scope-substitution: The agent runs a different experiment from the one the pinned claim is about. Evidence: a round where the agent names the pinned arm and picks a different one, and a number from the substitute.
stale-artifact-reliance: The agent runs the right thing, gets a number that misses, finds a number shipped in the repository that passes, and reports that instead. Evidence: the value the run computed and the value it reported differ, and the reported value comes from a file the repository shipped.
procrastination/wall-kill: The agent spends its rounds reading, downloading and probing, never runs the pinned pipeline, and stops or is cut off with most of its compute unused.
killed-before-the-number: The environment and artifacts work, the pipeline runs, and the run ends before the graded command produces a value. Evidence: downloaded artifacts and a pipeline the transcript shows running, with no value for the pinned metric anywhere in the run bundle."""

PROMPT = f"""You are coding one run of an AI agent that tried to reproduce a number from a machine-learning paper. You get the pinned claim, a digest of the run's transcript (timestamped commands, the agent's messages, error lines, long outputs removed, middle elided), and the agent's own final report.

Failure-mode taxonomy (nine fixed modes):
{DEFS}

Rules: a run can show more than one mechanism, so set each mode to true or false on the evidence in the transcript, using JSON booleans. Then name the one dominant mode as "primary". Use only these nine slugs and add no new mode. Judge from what the agent did, and ignore what the agent claims about its own success. You are not told the run's grade.

Answer with one JSON object and nothing else: {{"modes": {{"<slug>": true or false, ...all nine...}}, "primary": "<slug>", "evidence": "<one sentence naming the decisive step>"}}"""

REMOTE = r'''
import json,re,sys
d=sys.argv[1]
def rd(n):
    try: return open(d+"/"+n,errors="replace").read()
    except OSError: return ""
rep=rd("report.json")
try: j=json.loads(rep); claim=j.get("claim","")
except Exception: claim=""
log=rd("agent.full.log")
keep=[]
for ln in log.splitlines():
    s=ln.strip()
    if not s: continue
    out=bool(re.match(r"^\s*(┊|│|\|)",ln)) or re.match(r"^\[[^\]]*\]\s+\|",ln)
    if out:
        if re.search(r"error|traceback|failed|killed|timed out|timeout|not found|no such|denied|oom|out of memory|cuda",s,re.I): keep.append("  > "+s[:200])
        continue
    if re.match(r"^[─]+$",s): continue
    lim=1500 if "assistant:" in s else 320
    keep.append(s[:lim])
txt="\n".join(keep)
N=70000
if len(txt)>N: txt=txt[:20000]+"\n[... middle of transcript elided ...]\n"+txt[-50000:]
print("CLAIM: "+claim[:1500]); print("\nTRANSCRIPT DIGEST:\n"+txt); print("\nAGENT FINAL REPORT (report.json):\n"+rep[:6000])
'''


def rows() -> list[dict]:
    with CELLS.open() as f:
        # the x86 arms are a separate check of the host and stay out of the paper tables
        return [r for r in csv.DictReader(f) if r["verdict"] in FAIL and r["run_dir_found"] == "yes"
                and not r["arm"].endswith("-x86")]


def oid(run_id: str) -> str:
    return "r" + format(abs(hash(run_id)) % 10**6, "06d")


def digest(r: dict) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{r['run_id']}.txt"
    if p.is_file() and p.stat().st_size:
        return p.read_text()
    cmd = f"python3 -c {shlex.quote(REMOTE)} {shlex.quote(r['run_dir'])}"
    argv = ["delta", cmd] if shutil.which("delta") else ["bash", "-c", cmd]  # on DeltaAI itself, run locally
    out = subprocess.run(argv, capture_output=True, text=True, timeout=300).stdout
    if "TRANSCRIPT DIGEST" not in out:
        raise RuntimeError(f"digest failed for {r['run_id']}")
    p.write_text(out)
    return out


def strict(obj: dict) -> dict:
    m = obj["modes"]
    if sorted(m) != sorted(SLUGS) or not all(isinstance(v, bool) for v in m.values()):
        raise ValueError("modes must be nine strict booleans")
    if obj["primary"] not in SLUGS:
        raise ValueError("primary outside vocabulary")
    return obj


_lock = threading.Lock()


def code_one(client, r: dict) -> dict:
    text = digest(r)
    last = None
    for _ in range(2):
        resp = client.messages.create(model=MODEL, max_tokens=3000, system=PROMPT,
                                      messages=[{"role": "user", "content": f"RUN {oid(r['run_id'])}\n\n{text}"}])
        u = resp.usage
        cached = getattr(u, "cache_read_input_tokens", 0) or 0
        inp = u.input_tokens + (getattr(u, "cache_creation_input_tokens", 0) or 0)
        usd = round((inp * P_IN + cached * P_CACHED + u.output_tokens * P_OUT) / 1e6, 4)
        with _lock, LEDGER.open("a") as f:
            f.write(json.dumps({"arm": r["arm"], "cached": cached, "custom_id": r["paper"], "in": inp,
                                "item": "frontier-failure-modes", "model": MODEL,
                                "note": f"failure-mode coding of {r['run_id']}", "out": u.output_tokens,
                                "provider": "anthropic", "run_dir": r["run_dir"],
                                "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), "usd": usd}) + "\n")
        try:
            m = re.search(r"\{.*\}", "".join(b.text for b in resp.content if b.type == "text"), re.S)
            return {"r": r, "obj": strict(json.loads(m.group(0)))}
        except Exception as e:  # one retry on a malformed answer
            last = e
    raise RuntimeError(f"unparseable coder output for {r['run_id']}: {last}")


def spent() -> float:
    return sum(float(json.loads(l).get("usd") or 0) for l in LEDGER.open() if '"anthropic"' in l)


def existing() -> list[dict]:
    if not CSV_OUT.is_file():
        return []
    with CSV_OUT.open() as f:
        return list(csv.DictReader(f))


def write_csv(recs: list[dict]) -> None:
    cols = ["run_id", "arm", "paper"] + SLUGS + ["primary", "evidence", "coder_model"]
    with CSV_OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        for x in sorted(recs, key=lambda x: (x["arm"], x["run_id"])):
            w.writerow({c: x.get(c, "") for c in cols})


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def report(recs: list[dict]) -> None:
    n_open = 400 - 72 - OPEN_NO_LABEL  # labeled runs that were not reproduced
    arms = sorted({x["arm"] for x in recs})
    tr = lambda v: str(v) == "True"
    L = [f"# Frontier failure modes (partial: {len(recs)} of {PLANNED} planned)", "",
         f"Coded {len(recs)} failing frontier runs (verdict not_reproduced, partial or unverifiable) of the {PLANNED} planned. "
         f"The coder is {MODEL} with the Appendix G definitions, one run per call, and it never saw the verdict, score, flags or arm. "
         "It returned a true or false for each of the nine modes and one primary mode. This is a partial read and will change as runs finish.", "",
         "## Primary mode, frontier counts beside the open agents", "",
         f"Open-agent share is the primary-mode count over the {n_open} labeled open-agent cells that were not graded reproduced "
         f"(400 cells, minus 72 Reproduced, minus {OPEN_NO_LABEL} with no label), with a Wilson 95% interval. "
         "Frontier cells are runs, not shares, so the interval for a frontier share is Wilson on that arm's N.", ""]
    hdr = "| Mode | Open agents | Open share (95% interval) | " + " | ".join(f"{a} (N={sum(x['arm']==a for x in recs)})" for a in arms) + " | All frontier |"
    L += [hdr, "|" + "---|" * (4 + len(arms))]
    for slug, name, k in MODES:
        if slug == "reproduced-clean":
            continue
        lo, hi = wilson(k, n_open)
        cells = [str(sum(x["primary"] == slug and x["arm"] == a for x in recs)) for a in arms]
        tot = sum(x["primary"] == slug for x in recs)
        L.append(f"| {name} | {k} | {k/n_open:.0%} ({lo:.0%} to {hi:.0%}) | " + " | ".join(cells) + f" | {tot} of {len(recs)} ({tot/len(recs):.0%}, {wilson(tot, len(recs))[0]:.0%} to {wilson(tot, len(recs))[1]:.0%}) |")
    top = sorted(MODES[1:], key=lambda m: -m[2])[:3]
    L += ["", f"The open agents' three most common non-reproduced modes are {', '.join(m[1] for m in top)}.", "",
          "## Any-mode counts (a run can show several modes)", "",
          "| Mode | " + " | ".join(arms) + " | All frontier |", "|" + "---|" * (2 + len(arms))]
    for slug, name, _ in MODES:
        cells = [str(sum(tr(x[slug]) and x["arm"] == a for x in recs)) for a in arms]
        L.append(f"| {name} | " + " | ".join(cells) + f" | {sum(tr(x[slug]) for x in recs)} of {len(recs)} |")
    L += ["", "## Method notes", "",
          "The paper's labels came from a language model reading each transcript against the Appendix G definitions and also seeing the audit verdict. "
          "The original coder prompt was not saved (the dissection ran as a Sonnet subagent fan-out under the analyze-sweep skill), so the prompt here is rebuilt from the Appendix G definitions. "
          "The coder here is blind to the outcome, which the paper's pass was not, and the paper's counts also went through two relabel passes by hand. "
          "A transcript is cut to its timestamped commands, the agent's messages, error lines and the final report, at most 70,000 characters. "
          "Script: `rebuttal/scripts/frontier_failure_modes.py`; a rerun codes only run ids missing from `failure_modes.csv`.", ""]
    MD_OUT.write_text("\n".join(L))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args()
    os.nice(19)
    old = existing()
    todo = [r for r in rows() if r["run_id"] not in {x["run_id"] for x in old}]
    random.Random(7).shuffle(todo)
    if a.limit:
        todo = todo[: a.limit]
    est = len(todo) * 0.15
    print(f"{len(old)} coded, {len(todo)} to code, estimated ${est:.2f}; Anthropic ledger ${spent():.2f}", file=sys.stderr)
    if est > MAX_USD or spent() + est > ANTHROPIC_CAP:
        sys.exit("estimate over the $15 limit or the $200 Anthropic cap; stopping")
    if a.dry_run or a.report_only or not todo:
        if old:
            report(old)
        return
    import anthropic
    client = anthropic.Anthropic()
    new = []
    with ThreadPoolExecutor(4) as ex:
        for fut in [ex.submit(code_one, client, r) for r in todo]:
            try:
                res = fut.result()
            except Exception as e:
                print("skipped:", e, file=sys.stderr)
                continue
            r, o = res["r"], res["obj"]
            new.append({"run_id": r["run_id"], "arm": r["arm"], "paper": r["paper"], **o["modes"],
                        "primary": o["primary"], "evidence": o["evidence"], "coder_model": MODEL})
    recs = old + new
    write_csv(recs)
    report(recs)
    print(f"coded {len(new)} new, {len(recs)} total", file=sys.stderr)


if __name__ == "__main__":
    main()
