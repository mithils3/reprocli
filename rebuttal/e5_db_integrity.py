#!/usr/bin/env python3
"""E5 second check: do the on-disk evidence logs match the event stream the harness sent to the database?

The harness posts every tool call and its result to `repro_events` while a run is going; the row time
(`created_at`) is set by the database server. The sandbox has no database key, so the agent cannot write
there. For each run this compares, in both directions:
  A. every database bash / run_gpu call  -> an entry in evidence/commands.log with the same command and rc;
  B. every agent entry in commands.log   -> a database call with the same command and rc;
  C. run_gpu rows in trajectory.jsonl    -> the database result's cost and remaining budget;
  D. the time in each commands.log header against the server time of the matching database result.

Usage: e5_db_integrity.py --per-run PER_RUN.csv --events DIR --disk DIR --out DIR      (stdlib only)
"""
import argparse
import collections
import csv
import datetime as dt
import gzip
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e5_log_integrity import CMD_HDR, classify_entry, norm, parse_commands_log, rc_norm  # noqa: E402

TOOLS = ("workspace_bash", "run_gpu")


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def db_calls(path):
    """Pair each call_start with its call_result: the result row is the one at seq + 1."""
    rows = [json.loads(l) for l in gzip.open(path, "rt")]
    rows.sort(key=lambda r: (r["seq"], r["id"]))
    by_seq = {r["seq"]: r for r in rows}
    out = []
    for r in rows:
        if r["kind"] == "call_start":
            nxt = by_seq.get(r["seq"] + 1)
            out.append({"tool": r["tool_name"], "cmd": r["command"], "detail": r["detail_kind"], "seq": r["seq"],
                        "res": nxt if nxt and nxt["kind"] == "call_result" else None})
    return rows, out


def header_times(text):
    t = []
    for ln in text.split("\n"):
        m = CMD_HDR.match(ln)
        if m:
            t.append(ts(m.group(1)))
    return t


def check_run(pub, run_dir, events_dir, disk_dir):
    rid = os.path.basename(run_dir)
    rows, calls = db_calls(os.path.join(events_dir, rid + ".jsonl.gz"))
    ev = os.path.join(disk_dir, run_dir.lstrip("/"), "evidence")
    text = open(os.path.join(ev, "commands.log"), errors="replace").read()
    entries = parse_commands_log(text)
    times = header_times(text)
    flags = []
    disk = collections.defaultdict(list)          # (tool, command) -> entries still unmatched
    for e, t in zip(entries, times):
        kind, cmd, _ = classify_entry(e)
        e.update(kind=kind, key=norm(cmd), t=t, used=False)
        if kind in TOOLS:
            disk[(kind, e["key"])].append(e)
    st = collections.Counter()
    lags = []
    todo = [c for c in calls if c["tool"] in TOOLS and c["detail"] == "command" and c["cmd"] is not None]
    st["db_calls"] = len(todo)
    left = []
    for c in todo:                                 # pass 1: same command and same rc
        if c["res"] is None:
            st["db_result_row_missing"] += 1
        res = c["res"] or {}
        same = [e for e in disk.get((c["tool"], norm(c["cmd"])), [])
                if not e["used"] and rc_norm(e["rc"]) == rc_norm(res.get("rc"))]
        if not same:
            left.append(c)
            continue
        e = min(same, key=lambda e: abs(e["t"] - ts(res["created_at"])) if res.get("created_at") else 0)
        e["used"] = True
        st["matched"] += 1
        if res.get("created_at"):
            lags.append(ts(res["created_at"]) - e["t"])
    for c in left:                                 # pass 2: what is left over
        res = c["res"] or {}
        cands = [e for e in disk.get((c["tool"], norm(c["cmd"])), []) if not e["used"]]
        if c["res"] is None and cands:             # the result row never reached the database
            cands[0]["used"] = True
            st["matched_command_only"] += 1
        elif cands:
            cands[0]["used"] = True
            st["rc_differs"] += 1
            flags.append([pub, "rc_differs", c["seq"], str(res.get("rc")), cands[0]["rc"], norm(c["cmd"])[:200]])
        else:
            # a call the tool refused, or one that returned without an rc, is never written to commands.log
            why = "db_only_no_rc" if res.get("rc") is None else "db_only"
            st[why] += 1
            flags.append([pub, why, c["seq"], str(res.get("rc")) + " ok=" + str(res.get("ok")) + " " + str(res.get("error"))[:60],
                          "", norm(c["cmd"])[:200]])
    for e in entries:
        if e["kind"] in TOOLS:
            st["disk_entries"] += 1
            if not e["used"]:
                # the harness retries a timed-out bash call once: both attempts are in commands.log (the first
                # with rc=?), the database holds the call once
                twin = any(o["used"] for o in disk[(e["kind"], e["key"])])
                why = "disk_retry_attempt" if e["rc"] == "?" and twin else "disk_only"
                st[why] += 1
                flags.append([pub, why, e["line"], "", e["rc"], e["key"][:200]])
    # C: run_gpu cost and remaining budget, trajectory.jsonl against the database result
    traj, releases = collections.defaultdict(list), []
    for ln in open(os.path.join(ev, "trajectory.jsonl"), errors="replace"):
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if r.get("type") == "run_gpu" and r.get("command") is not None:
            traj[norm(r["command"])].append(r)
        elif r.get("type") == "gpu_release":      # an agent call that only gives the GPU back: empty command
            releases.append(r)
    for c in calls:
        res = c["res"] or {}
        if c["tool"] != "run_gpu" or c["cmd"] is None or res.get("cost_h100") is None:
            continue
        st["gpu_db"] += 1
        if not norm(c["cmd"]):
            hit = [r for r in releases if not r.get("_used") and r.get("final_charge_h100_hours") is not None
                   and abs(r["final_charge_h100_hours"] - res["cost_h100"]) < 1.5e-4]
            if hit:
                hit[0]["_used"] = True
                st["gpu_release_match"] += 1
                continue
        rows_t = traj.get(norm(c["cmd"]), [])
        hit = [r for r in rows_t if not r.get("_used") and r.get("cost_h100_hours") is not None
               and abs(r["cost_h100_hours"] - res["cost_h100"]) < 1.5e-4
               and (res.get("remaining_h100") is None or r.get("remaining_h100_hours") is None
                    or abs(r["remaining_h100_hours"] - res["remaining_h100"]) < 1.5e-4)]
        if hit:
            hit[0]["_used"] = True
            st["gpu_match"] += 1
        else:
            st["gpu_differs" if rows_t else "gpu_db_only"] += 1
            flags.append([pub, "gpu_differs" if rows_t else "gpu_db_only", c["seq"], str(res.get("cost_h100")),
                          str([r.get("cost_h100_hours") for r in rows_t][:4]), norm(c["cmd"])[:200]])
    seqs = [r["seq"] for r in rows]
    st["seq_missing"] = (max(seqs) - min(seqs) + 1 - len(set(seqs))) if seqs else 0
    return st, lags, flags


def main():
    ap = argparse.ArgumentParser()
    for a in ("--per-run", "--events", "--disk", "--out"):
        ap.add_argument(a, required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    tot, all_lags, all_flags, per = collections.Counter(), [], [], []
    for r in csv.DictReader(open(a.per_run)):
        st, lags, flags = check_run(r["run_id"], r["run_dir"], a.events, a.disk)
        tot.update(st)
        all_lags += lags
        all_flags += flags
        per.append({"run_id": r["run_id"], **{k: st.get(k, 0) for k in (
            "db_calls", "matched", "matched_command_only", "db_result_row_missing", "rc_differs", "db_only", "db_only_no_rc", "disk_entries", "disk_retry_attempt", "disk_only",
            "gpu_db", "gpu_match", "gpu_release_match", "gpu_differs", "gpu_db_only", "seq_missing")},
            "lag_median_s": round(statistics.median(lags), 2) if lags else "",
            "lag_max_abs_s": round(max(map(abs, lags)), 2) if lags else ""})
    with open(os.path.join(a.out, "db_per_run.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(per[0]))
        w.writeheader()
        w.writerows(per)
    with open(os.path.join(a.out, "db_flags.tsv"), "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["run_id", "flag", "seq_or_line", "db_value", "disk_value", "command"])
        w.writerows(all_flags)
    q = sorted(all_lags)
    pick = lambda p: round(q[min(len(q) - 1, int(p * len(q)))], 2)  # noqa: E731
    summ = {"runs": len(per), **dict(tot),
            "runs_all_db_calls_matched": sum(1 for p in per if p["db_calls"] == p["matched"] + p["matched_command_only"]),
            "runs_with_rc_differs": sum(1 for p in per if p["rc_differs"]),
            "runs_with_disk_only": sum(1 for p in per if p["disk_only"]),
            "lag_s": {"n": len(q), "p01": pick(0.01), "median": pick(0.5), "p99": pick(0.99), "min": q[0], "max": q[-1],
                      "within_10s": sum(1 for x in q if abs(x) <= 10), "within_60s": sum(1 for x in q if abs(x) <= 60),
                      "over_300s": sum(1 for x in q if abs(x) > 300)}}
    json.dump(summ, open(os.path.join(a.out, "db_summary.json"), "w"), indent=1)
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
