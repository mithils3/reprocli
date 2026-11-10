#!/usr/bin/env python3
"""Continue Codex runs that the old 48-hour wall stopped. Runs on DeltaAI login node."""
import getpass
import glob
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/Chicago")
except ImportError:  # DeltaAI python3 predates zoneinfo; Chicago is CST (UTC-6) in November
    TZ = timezone(timedelta(hours=-6), "CST")
STOP = datetime(2026, 11, 15, 17, 0, tzinfo=TZ)
ROOT = "/work/nvme/bfvr/msalunkhe/reprocli/agent_runs"
CODEX = "/work/nvme/bfvr/msalunkhe/rebuttal/codex"
LAUNCHER = f"{CODEX}/rerun_one.sh"
GRADING = "/work/nvme/bfvr/msalunkhe/rebuttal/grading"
EXCLUDE = {"codex-gpt-6-astra-20261107T010540Z-a54ff7", "codex-gpt-6-astra-20261107T140243Z-9f613b"}


def stamp():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S %Z")


def read(path):
    with open(path, errors="replace") as f:
        return f.read()


def candidate(d):
    """Return (run_id, paper, model, budget, nudge_arg) if run dir d should be continued, else None."""
    run_id = os.path.basename(d)
    if os.path.exists(f"{d}/VOID") or not os.path.exists(f"{d}/report.json"):
        return None
    if run_id in EXCLUDE and os.environ.get("AUTOCONT_NO_EXCLUDE") != "1":
        return None
    text = read(f"{d}/agent.full.log")
    reasons = re.findall(r"DONE exit_reason=(\w+)", text)
    if not reasons or reasons[-1] != "wall_clock":
        return None
    if time.time() - os.path.getmtime(f"{d}/report.json") <= 90:
        return None
    meta = json.load(open(f"{d}/codex_run.json"))
    if len(meta.get("continuations") or []) >= 2:
        return None
    nudge = ""
    if meta.get("variant") == "nudge":
        left = int(meta.get("max_nudges", 0)) - len(re.findall(r"NUDGE \d+/", text))
        if left > 0:
            nudge = f" --nudges {left}"
    budget = float(meta["budget_h100_hours"])
    budget = str(int(budget)) if budget.is_integer() else str(budget)
    return run_id, d.split("/")[-3], meta["model"], budget, nudge


def nproc():
    out = subprocess.run(["ps", "-u", getpass.getuser(), "-o", "pid="], stdout=subprocess.PIPE,
                         universal_newlines=True).stdout
    return len([line for line in out.splitlines() if line.strip()])


def launch(run_id, paper, model, budget, nudge):
    name = "rb-cont-" + run_id[-6:]
    if subprocess.run(["tmux", "has-session", "-t", name], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
        print(f"{stamp()} skip {run_id}: tmux session {name} exists", flush=True)
        return False
    log = f"{CODEX}/continue-{run_id}.log"
    cmd = f"bash {LAUNCHER} {paper} {budget} {model} --continue-run-id {run_id}{nudge} > {log} 2>&1"
    subprocess.run(["tmux", "new", "-d", "-s", name, cmd], check=True)
    print(f"{stamp()} launch {run_id} session={name} cmd={cmd}", flush=True)
    return True


def supersede(run_id):
    src = f"{GRADING}/grades.jsonl"
    if not os.path.exists(src):
        return
    lines = open(src).read().splitlines(keepends=True)
    hit = [line for line in lines if run_id in line]
    if not hit:
        return
    with open(f"{GRADING}/grades_superseded.jsonl", "a") as f:
        f.writelines(hit)
    tmp = src + ".tmp"
    with open(tmp, "w") as f:
        f.writelines(line for line in lines if run_id not in line)
    os.replace(tmp, src)


def cycle(dry):
    dirs = sorted(d for d in glob.glob(f"{ROOT}/*/*/codex-gpt-6*") if os.path.isdir(d))
    picked = []
    for d in dirs:
        try:
            c = candidate(d)
        except Exception as e:
            print(f"{stamp()} error {d}: {e}", flush=True)
            continue
        if c:
            picked.append(c)
    if dry:
        for c in picked:
            print(f"{stamp()} would continue {c[0]} budget={c[3]} nudge='{c[4].strip()}'", flush=True)
        print(f"{stamp()} scanned={len(dirs)} would_continue={len(picked)} {' '.join(c[0] for c in picked)}", flush=True)
        return
    if picked and nproc() > 700:
        print(f"{stamp()} skip launching: more than 700 processes on node", flush=True)
        picked = []
    launched = []
    for c in picked:
        if launch(*c):
            supersede(c[0])
            launched.append(c[0])
    print(f"{stamp()} scanned={len(dirs)} continued={len(launched)} {' '.join(launched)}", flush=True)


def main():
    dry = "--dry-run" in sys.argv
    once = dry or "--once" in sys.argv
    while True:
        if datetime.now(TZ) >= STOP:
            print(f"{stamp()} past 2026-11-15 17:00 America/Chicago, stopping", flush=True)
            return
        cycle(dry)
        if once:
            return
        time.sleep(300)


if __name__ == "__main__":
    main()
