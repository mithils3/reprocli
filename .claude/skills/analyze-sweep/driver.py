#!/usr/bin/env python3
"""Dump one sweep (sbatch batch) from the Supabase run viewer for offline analysis.

Read-only: hits the PostgREST API of the run-viewer project with the service key
(reads work with anon-level SELECT policies; the service key is what's in env).

Commands:
  python driver.py --list [--limit N]           # recent batches with status counts
  python driver.py --batch slurm-XXXXXXX --out DIR [--include-running] [--no-events]

Output layout under --out:
  runs.json          all repro_runs rows for the batch (finished only by default)
  tags.json          repro_tags rows for those run_ids
  aggregates.json    machine-readable rollup (means, verdict/exit counts, bands)
  SUMMARY.md         human/agent-readable table + rollup
  events/<run_id>.jsonl   full ordered transcript events, one JSON object per line
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

SUPA = "https://rjnkpoxwdslkgxjliakq.supabase.co/rest/v1"
PAGE = 1000


def _key() -> str:
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not key:
        sys.exit("SUPABASE_SERVICE_KEY not set. Run: source <(grep -E 'SUPABASE_SERVICE_KEY' ~/.bashrc)")
    return key


def _get(path: str, params: dict[str, str]) -> list[dict]:
    key = _key()
    url = f"{SUPA}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"apikey": key, "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def _get_all(path: str, params: dict[str, str]) -> list[dict]:
    """Paginate a PostgREST query (offset/limit) until a short page."""
    rows: list[dict] = []
    offset = 0
    while True:
        page = _get(path, {**params, "limit": str(PAGE), "offset": str(offset)})
        rows.extend(page)
        if len(page) < PAGE:
            return rows
        offset += PAGE


def cmd_list(limit: int) -> None:
    rows = _get("repro_runs", {
        "select": "batch_id,batch_label,status,started_at,model",
        "order": "started_at.desc", "limit": str(limit),
    })
    batches: dict[str, dict] = {}
    for r in rows:
        b = batches.setdefault(r.get("batch_id") or "(none)", {
            "label": r.get("batch_label"), "statuses": Counter(),
            "models": set(), "first_seen": r["started_at"],
        })
        b["statuses"][r["status"]] += 1
        b["models"].add(r.get("model"))
    for bid, b in batches.items():
        st = ", ".join(f"{k}={v}" for k, v in sorted(b["statuses"].items()))
        models = ", ".join(sorted(str(m) for m in b["models"]))
        print(f"{bid:>16}  {str(b['label']):24} {st:34} {models}  (from {b['first_seen']})")


def _fnum(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def aggregates(runs: list[dict]) -> dict:
    scores = [r["audit_score"] for r in runs if r.get("audit_score") is not None]
    agg: dict = {
        "n_runs": len(runs),
        "n_scored": len(scores),
        "mean_audit_score": round(sum(scores) / len(scores), 3) if scores else None,
        "score_distribution": dict(sorted(Counter(scores).items())),
        "verdicts": dict(Counter(str(r.get("audit_verdict")) for r in runs)),
        "exit_reasons": dict(Counter(str(r.get("exit_reason")) for r in runs)),
        "n_high_cheat_flag": sum(1 for r in runs if r.get("audit_has_high_cheat_flag")),
        "n_reproduced": sum(1 for r in runs if r.get("audit_reproduced")),
        "spent_h100_total": round(sum(_fnum(r.get("spent_h100")) for r in runs), 1),
        "budget_h100_total": round(sum(_fnum(r.get("budget")) for r in runs), 1),
        "by_budget_band": {},
    }
    bands: dict[float, list[dict]] = defaultdict(list)
    for r in runs:
        bands[_fnum(r.get("budget"))].append(r)
    for band in sorted(bands):
        bruns = bands[band]
        bscores = [r["audit_score"] for r in bruns if r.get("audit_score") is not None]
        agg["by_budget_band"][f"{band:g}h"] = {
            "n": len(bruns),
            "mean_audit_score": round(sum(bscores) / len(bscores), 3) if bscores else None,
            "verdicts": dict(Counter(str(r.get("audit_verdict")) for r in bruns)),
            "spent_h100": round(sum(_fnum(r.get("spent_h100")) for r in bruns), 1),
        }
    return agg


def summary_md(batch: str, runs: list[dict], agg: dict) -> str:
    lines = [
        f"# Sweep dump: {batch}",
        "",
        f"- runs: {agg['n_runs']} ({agg['n_scored']} scored), mean audit score **{agg['mean_audit_score']}**",
        f"- verdicts: {agg['verdicts']}",
        f"- exit reasons: {agg['exit_reasons']}",
        f"- high cheat flags (score capped to 0): {agg['n_high_cheat_flag']}",
        f"- compute: {agg['spent_h100_total']} spent of {agg['budget_h100_total']} budgeted H100-h",
        "",
        "| band | n | mean score | verdicts | spent H100-h |",
        "|---|---|---|---|---|",
    ]
    for band, b in agg["by_budget_band"].items():
        lines.append(f"| {band} | {b['n']} | {b['mean_audit_score']} | {b['verdicts']} | {b['spent_h100']} |")
    lines += [
        "",
        "| run_id | arxiv | score | reported | verdict | exit | rounds | spent/budget | flag |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in runs:
        lines.append(
            f"| {r['run_id']} | {r['arxiv_id']} | {r.get('audit_score')} | {r.get('audit_reported_score')} "
            f"| {r.get('audit_verdict')} | {r.get('exit_reason')} | {r.get('tool_rounds_used')} "
            f"| {_fnum(r.get('spent_h100')):.1f}/{_fnum(r.get('budget')):g} "
            f"| {'HIGH' if r.get('audit_has_high_cheat_flag') else ''} |")
    return "\n".join(lines) + "\n"


def cmd_batch(batch: str, out: Path, include_running: bool, events: bool) -> None:
    params = {"batch_id": f"eq.{batch}", "select": "*", "order": "started_at.asc"}
    if not include_running:
        params["status"] = "eq.finished"
    runs = _get_all("repro_runs", params)
    if not runs:
        sys.exit(f"no runs for batch_id={batch} (try --list)")
    out.mkdir(parents=True, exist_ok=True)
    (out / "runs.json").write_text(json.dumps(runs, indent=1))

    ids = [r["run_id"] for r in runs]
    id_list = ",".join(f'"{i}"' for i in ids)
    tags = _get_all("repro_tags", {"run_id": f"in.({id_list})", "select": "*"})
    (out / "tags.json").write_text(json.dumps(tags, indent=1))

    agg = aggregates(runs)
    (out / "aggregates.json").write_text(json.dumps(agg, indent=1))
    (out / "SUMMARY.md").write_text(summary_md(batch, runs, agg))
    print(f"{len(runs)} runs -> {out}/runs.json  (mean score {agg['mean_audit_score']})")

    if events:
        evdir = out / "events"
        evdir.mkdir(exist_ok=True)
        for i, rid in enumerate(ids, 1):
            evs = _get_all("repro_events", {"run_id": f"eq.{rid}", "select": "*", "order": "seq.asc"})
            with (evdir / f"{rid}.jsonl").open("w") as f:
                for e in evs:
                    f.write(json.dumps(e) + "\n")
            print(f"  [{i}/{len(ids)}] {rid}: {len(evs)} events")
    print("done")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="list recent batches")
    ap.add_argument("--limit", type=int, default=200, help="rows to scan for --list")
    ap.add_argument("--batch", help="batch_id to dump (e.g. slurm-2672018)")
    ap.add_argument("--out", type=Path, help="output directory for the dump")
    ap.add_argument("--include-running", action="store_true", help="also dump status=running rows")
    ap.add_argument("--no-events", dest="events", action="store_false", help="skip per-run event transcripts")
    args = ap.parse_args()
    if args.list:
        cmd_list(args.limit)
    elif args.batch and args.out:
        cmd_batch(args.batch, args.out, args.include_running, args.events)
    else:
        ap.error("use --list, or --batch ID --out DIR")


if __name__ == "__main__":
    main()
