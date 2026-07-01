"""Push Stage-7 auditor verdicts into the agent-logs Supabase (opt-in, standalone).

The auditor (``reprocli_vllm --mode audit``) writes graded verdict rows to a JSONL
(``--extracted-output``), keyed by ``paper_id``, and deliberately never touches
Supabase -- the classifier/auditor core stays storage-free. This step closes that
gap: it reads that JSONL and PATCHes the ``audit_*`` columns onto the matching
``repro_runs`` row, so the run viewer can show the score/verdict and drive its
"reproduced" status from the grader instead of a hand-applied tag.

Mapping a per-paper verdict to a ``run_id``: the repro sink drops ``stats.json``
(carrying ``run_id``) into each bundle root, so ``<runs-dir>/<paper_id>/stats.json``
names the run that produced the graded bundle. When that file is absent (the run
predates the sink, or stats upload was off) we fall back to the most recently
updated ``repro_runs`` row for the arxiv id.

Config mirrors ``supabase_sink``: ``SUPABASE_URL`` (or ``--supabase-url``) +
``SUPABASE_SERVICE_KEY`` (the service key bypasses RLS to write). Best-effort and
idempotent -- re-running overwrites the same row with the same verdict.

    python -m reprocli_repro.audit_upload \
      --verdicts audit_2505.18513_extracted.jsonl \
      --runs-dir /work/nvme/bfvr/msalunkhe/reprocli/agent_runs
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

try:  # already importable transitively (datasets/hf_hub); urllib is the fallback
    import requests
except ImportError:  # pragma: no cover
    requests = None

HTTP_TIMEOUT = 15.0


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _service_key() -> str | None:
    return os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")


def _request(method: str, url: str, key: str, body: Any = None) -> tuple[int, str]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if method == "PATCH":
        headers["Prefer"] = "return=minimal"
    if requests is not None:
        r = requests.request(method, url, headers=headers, data=data, timeout=HTTP_TIMEOUT)
        return r.status_code, r.text
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:  # 4xx/5xx carry a useful body
        return e.code, e.read().decode()
    except OSError as e:  # DNS/connection — treat as a soft failure
        return 0, str(e)


def run_id_from_stats(runs_dir: Path, paper_id: str) -> str | None:
    """The sink drops stats.json (carrying run_id) into each run's bundle root, at
    <runs-dir>/<arxiv_id>/<budget>h/<run_id>/stats.json. Grade the newest (the run
    the auditor just walked); '**' also matches a flat <arxiv_id>/stats.json."""
    paper_dir = Path(runs_dir) / paper_id
    try:
        found = sorted(paper_dir.glob("**/stats.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return None
    for stats in found:
        try:
            rid = json.loads(stats.read_text()).get("run_id")
        except (OSError, ValueError):
            continue
        if rid:
            return rid
    return None


def run_id_from_db(base: str, key: str, arxiv_id: str) -> str | None:
    """Fallback: the most recently updated repro_runs row for this paper."""
    q = urllib.parse.urlencode(
        {"arxiv_id": f"eq.{arxiv_id}", "select": "run_id", "order": "updated_at.desc", "limit": "1"}
    )
    code, text = _request("GET", f"{base}/rest/v1/repro_runs?{q}", key)
    if not code or code >= 300:
        return None
    try:
        rows = json.loads(text)
    except ValueError:
        return None
    return rows[0]["run_id"] if rows else None


def audit_fields(row: dict[str, Any], model: str | None) -> dict[str, Any]:
    """The audit_* column payload derived from one finalized verdict row."""
    fields = {
        "audit_score": row.get("score"),
        "audit_reported_score": row.get("reported_score"),
        "audit_verdict": row.get("verdict"),
        "audit_reproduced": row.get("reproduced"),
        "audit_has_high_cheat_flag": row.get("has_high_cheat_flag"),
        "audit_flags": row.get("cheat_flags") or [],
        "audit_rationale": row.get("rationale"),
        "audited_at": _now_iso(),
    }
    if model:
        fields["audit_model"] = model
    return fields


def paper_of(row: dict[str, Any]) -> str | None:
    """The extracted audit rows are keyed by custom_id (io.py always sets it);
    paper_id only appears when the model emits it in schema-valid JSON. Mirror
    load_mre_records' key resolution so a graded row is never dropped."""
    pid = row.get("custom_id") or row.get("paper_id") or row.get("arxiv_id")
    return str(pid) if pid else None


def load_verdicts(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if paper_of(obj):
            out.append(obj)
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="reprocli_repro.audit_upload", description=__doc__)
    p.add_argument("--verdicts", type=Path, required=True,
                   help="Auditor --extracted-output JSONL (one finalized row per paper_id).")
    p.add_argument("--runs-dir", type=Path, required=True,
                   help="Root of the agent run bundles; <runs-dir>/<arxiv_id>/stats.json names the run_id.")
    p.add_argument("--supabase-url", default=os.environ.get("SUPABASE_URL"),
                   help="Supabase project URL (default: $SUPABASE_URL).")
    p.add_argument("--audit-model", help="Grader model id to record on the row (audit_model).")
    p.add_argument("--dry-run", action="store_true", help="Resolve run_ids and print, but don't PATCH.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base = (args.supabase_url or "").rstrip("/")
    key = _service_key()
    if not base or not key:
        print("audit_upload: set SUPABASE_URL (or --supabase-url) and SUPABASE_SERVICE_KEY",
              file=sys.stderr)
        return 2

    verdicts = load_verdicts(args.verdicts)
    if not verdicts:
        print(f"audit_upload: no verdict rows in {args.verdicts}", file=sys.stderr)
        return 1

    patched = skipped = failed = 0
    for row in verdicts:
        pid = paper_of(row)
        # A degraded audit row (unparseable model output) carries no score/verdict —
        # nothing to grade with, so flag it rather than silently patching nulls.
        if row.get("score") is None and not row.get("verdict"):
            print(f"  {pid}: audit produced no verdict (degraded output) -- skipped", file=sys.stderr)
            skipped += 1
            continue
        run_id = run_id_from_stats(args.runs_dir, pid)
        if not run_id and not args.dry_run:
            run_id = run_id_from_db(base, key, pid)
        if not run_id:
            print(f"  {pid}: no run_id (no stats.json, no repro_runs row) -- skipped", file=sys.stderr)
            skipped += 1
            continue
        fields = audit_fields(row, args.audit_model)
        tag = f"score={fields['audit_score']} verdict={fields['audit_verdict']}"
        if args.dry_run:
            print(f"  {pid} -> {run_id}: {tag} (dry-run)")
            continue
        q = urllib.parse.urlencode({"run_id": f"eq.{run_id}"})
        code, text = _request("PATCH", f"{base}/rest/v1/repro_runs?{q}", key, fields)
        if code and code < 300:
            print(f"  {pid} -> {run_id}: {tag}")
            patched += 1
        else:
            print(f"  {pid} -> {run_id}: PATCH failed HTTP {code} {text[:160]}", file=sys.stderr)
            failed += 1

    print(f"audit_upload: {patched} patched, {skipped} skipped, {failed} failed "
          f"({len(verdicts)} verdicts)", file=sys.stderr)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
