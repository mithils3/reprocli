#!/usr/bin/env python3
"""Publish a dissected sweep to the run-viewer's Analysis tab (Supabase).

Reads the two curated artifacts the analyze-sweep skill produces — `runs.json`
(repro_runs rows) and `analyses.json` (one per-run dissection object per paper) —
then upserts one `repro_sweeps` header row + one `repro_analyses` row per paper,
and (optionally) uploads the source PDF to the public `repro-analyses` Storage
bucket. Writes need the service key (bypasses RLS); the viewer reads anon.

    source <(grep -E 'SUPABASE_SERVICE_KEY' ~/.bashrc)
    python3 .claude/skills/analyze-sweep/upload.py \
        --slug hard-2672018 --title "Qwen3.6-27B Hard-Tier Dissection" \
        --subtitle "sweep 2672018 · post-freeze" --tier Hard --frozen \
        --runs DIR/runs.json --analyses DIR/analyses.json --pdf REPORT.pdf

One-time: the tables + bucket must exist (tools/run_viewer/setup_db.py). Re-runs
are idempotent (upsert on slug / run_id, PDF upsert overwrites).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from driver import _fnum, aggregates  # noqa: E402  (sibling module, same skill dir)

BASE = "https://rjnkpoxwdslkgxjliakq.supabase.co"
REST = f"{BASE}/rest/v1"
BUCKET = "repro-analyses"


def _key() -> str:
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not key:
        sys.exit("SUPABASE_SERVICE_KEY not set. Run: source <(grep -E 'SUPABASE_SERVICE_KEY' ~/.bashrc)")
    return key


def _req(method: str, url: str, *, headers: dict, data: bytes | None = None) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _post_rows(path: str, rows: list[dict], on_conflict: str, dry: bool) -> None:
    """PostgREST bulk upsert. Pads rows to the key union (PostgREST needs uniform keys)."""
    if not rows:
        return
    keys: set[str] = set()
    for r in rows:
        keys |= set(r)
    padded = [{k: r.get(k) for k in keys} for r in rows]
    if dry:
        print(f"  [dry-run] would upsert {len(padded)} row(s) into {path}")
        return
    key = _key()
    body = json.dumps(padded).encode()
    headers = {
        "apikey": key, "Authorization": f"Bearer {key}",
        "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    code, resp = _req("POST", f"{REST}/{path}?on_conflict={on_conflict}", headers=headers, data=body)
    if code >= 300:
        sys.exit(f"✗ upsert {path} failed (HTTP {code}): {resp.decode()[:600]}")
    print(f"✓ upserted {len(padded)} row(s) into {path}")


def upload_pdf(pdf: Path, slug: str, dry: bool) -> str | None:
    obj = f"{slug}.pdf"
    public_url = f"{BASE}/storage/v1/object/public/{BUCKET}/{obj}"
    if dry:
        print(f"  [dry-run] would upload {pdf} -> {public_url}")
        return public_url
    key = _key()
    headers = {
        "apikey": key, "Authorization": f"Bearer {key}",
        "Content-Type": "application/pdf", "x-upsert": "true", "cache-control": "3600",
    }
    code, resp = _req("POST", f"{BASE}/storage/v1/object/{BUCKET}/{obj}",
                      headers=headers, data=pdf.read_bytes())
    if code >= 300:
        print(f"✗ PDF upload failed (HTTP {code}): {resp.decode()[:400]}", file=sys.stderr)
        return None
    print(f"✓ uploaded PDF -> {public_url}")
    return public_url


def build_aggregates(analyses: list[dict], runs_by_id: dict[str, dict]) -> dict:
    """driver.aggregates over the dissected runs, plus failure-mode + self-claim rollups."""
    analyzed_runs = [runs_by_id[a["run_id"]] for a in analyses if a.get("run_id") in runs_by_id]
    agg = aggregates(analyzed_runs) if analyzed_runs else {"mean_audit_score": None}
    honest = sum(1 for a in analyses if (a.get("agent_final_selfclaim") or {}).get("honest_about_failure"))
    agg["n_papers"] = len(analyses)
    agg["failure_modes"] = dict(Counter(a.get("failure_mode") for a in analyses).most_common())
    agg["self_claim"] = {
        "honest_about_failure": honest,
        "not_honest": len(analyses) - honest,
        "audited_reproduced": agg.get("n_reproduced", 0),
    }
    return agg


def build_analysis_rows(analyses: list[dict], runs_by_id: dict[str, dict], slug: str) -> list[dict]:
    rows = []
    for a in analyses:
        rid = a.get("run_id")
        if not rid:
            continue
        run = runs_by_id.get(rid, {})
        au = a.get("audit_summary") or {}
        verdict = run.get("audit_verdict") or au.get("verdict")
        score = run.get("audit_score")
        if score is None:
            score = au.get("score")
        reproduced = run.get("audit_reproduced")
        if reproduced is None and verdict:
            reproduced = verdict == "reproduced"
        rows.append({
            "run_id": rid, "sweep_slug": slug, "arxiv_id": a.get("arxiv_id") or run.get("arxiv_id"),
            "failure_mode": a.get("failure_mode"), "audit_score": score, "audit_verdict": verdict,
            "reproduced": reproduced, "target_claim": a.get("target_claim"),
            "paper_gist": a.get("paper_gist"), "data": a,
        })
    return rows


def _mode(runs: list[dict], field: str):
    vals = [r.get(field) for r in runs if r.get(field)]
    return Counter(vals).most_common(1)[0][0] if vals else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", required=True, help="stable sweep id, e.g. hard-2672018")
    ap.add_argument("--title", required=True, help="report title, e.g. 'Qwen3.6-27B Hard-Tier Dissection'")
    ap.add_argument("--subtitle", default=None, help="e.g. 'sweep 2672018 · post-freeze'")
    ap.add_argument("--runs", required=True, type=Path, help="path to runs.json")
    ap.add_argument("--analyses", required=True, type=Path, help="path to analyses.json (list of dissections)")
    ap.add_argument("--tier", default=None, help="Easy | Medium | Hard | mixed")
    ap.add_argument("--frozen", action="store_true", help="mark as post-freeze (a paper result)")
    ap.add_argument("--batch-id", default=None, help="slurm-XXXX (else the modal batch_id in runs.json)")
    ap.add_argument("--model", default=None, help="model id (else the modal model in runs.json)")
    ap.add_argument("--pdf", default=None, type=Path, help="source PDF to store + link")
    ap.add_argument("--report-md", default=None, type=Path, help="optional narrative markdown to attach")
    ap.add_argument("--dry-run", action="store_true", help="print what would be uploaded, POST nothing")
    args = ap.parse_args()

    runs = json.loads(args.runs.read_text())
    analyses = json.loads(args.analyses.read_text())
    runs_by_id = {r["run_id"]: r for r in runs}
    print(f"{len(analyses)} dissections, {len(runs)} run rows -> sweep '{args.slug}'")

    pdf_url = upload_pdf(args.pdf, args.slug, args.dry_run) if args.pdf else None
    agg = build_aggregates(analyses, runs_by_id)

    sweep = {
        "slug": args.slug, "title": args.title, "subtitle": args.subtitle,
        "batch_id": args.batch_id or _mode(runs, "batch_id"),
        "model": args.model or _mode(runs, "model"),
        "tier": args.tier, "frozen": args.frozen, "run_count": len(analyses),
        "mean_audit_score": agg.get("mean_audit_score"), "aggregates": agg,
        "report_pdf_url": pdf_url,
        "report_md": args.report_md.read_text() if args.report_md else None,
    }
    _post_rows("repro_sweeps", [sweep], "slug", args.dry_run)
    _post_rows("repro_analyses", build_analysis_rows(analyses, runs_by_id, args.slug), "run_id", args.dry_run)

    mean = agg.get("mean_audit_score")
    print(f"done. mean score {mean}, failure modes {agg['failure_modes']}")
    if not args.dry_run:
        print(f"view: https://agent-logs.vercel.app/  (Analysis tab -> {args.title})")


if __name__ == "__main__":
    main()
