"""Resolve one sbatch sweep's runs to the exact bundles a grader should read.

A sweep is a ``batch_id`` (``slurm-<jobid>``) shared by every ``reprocli_repro``
process the sbatch launched; each run leaves its bundle at
``<runs-dir>/<arxiv_id>/<budget>h/<run_id>/``. Naming a paper is therefore not
enough to name a run: a paper attempted more than once has several bundles, and
"the sweep's attempt" is only identifiable through the ``run_id`` its row carries.

This module reads the sweep's rows from the run-viewer Supabase and resolves each
``run_id`` to the bundle it actually wrote, so a grader points at one attempt and
its verdict patches the matching ``repro_runs`` row. Read-only; needs
``SUPABASE_URL`` + ``SUPABASE_SERVICE_KEY``.

    PYTHONPATH=src python -m reprocli_repro.batch_runs \
      --batch slurm-2687371 --runs-dir /work/nvme/bfvr/msalunkhe/reprocli/agent_runs
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from reprocli_repro import postgrest

HTTP_TIMEOUT = 20.0
SELECT = (
    "run_id,arxiv_id,status,model,budget,started_at,updated_at,"
    "batch_id,batch_label,audit_score,audit_verdict"
)


@dataclass
class Run:
    """One reproduction run of the sweep, and the bundle it wrote (once resolved)."""

    run_id: str
    arxiv_id: str
    status: str
    budget: float | None
    audit_score: int | None
    bundle: Path | None = None


def _service_key() -> str | None:
    return os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")


def fetch_runs(base_url: str, key: str, batch_id: str) -> list[dict[str, Any]]:
    """Every ``repro_runs`` row of one batch, oldest first."""
    query = urllib.parse.urlencode(
        {"batch_id": f"eq.{batch_id}", "select": SELECT, "order": "started_at.asc"}
    )
    code, text = postgrest.request(
        f"{base_url.rstrip('/')}/rest/v1/repro_runs?{query}",
        service_key=key,
        method="GET",
        timeout=HTTP_TIMEOUT,
        max_attempts=4,
    )
    if not code or code >= 300:
        raise SystemExit(f"batch_runs: repro_runs query failed (HTTP {code}): {text[:300]}")
    rows = json.loads(text)
    if not isinstance(rows, list):
        raise SystemExit(f"batch_runs: unexpected response for {batch_id}: {text[:200]}")
    return rows


def select_runs(
    rows: list[dict[str, Any]],
    *,
    include_running: bool = False,
    skip_audited: bool = False,
) -> list[Run]:
    """One :class:`Run` per paper: the sweep's newest attempt, filtered.

    Running rows are dropped by default (their bundle is still being written, and
    grading a half-finished run scores the harness, not the model). ``skip_audited``
    drops papers that already carry a verdict, so a re-run only grades what is
    missing instead of paying for the whole sweep again.
    """
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        arxiv_id, run_id = row.get("arxiv_id"), row.get("run_id")
        if not arxiv_id or not run_id:
            continue
        if not include_running and row.get("status") == "running":
            continue
        if skip_audited and row.get("audit_score") is not None:
            continue
        previous = latest.get(arxiv_id)
        if previous is None or _started(row) >= _started(previous):
            latest[arxiv_id] = row
    return [
        Run(
            run_id=str(row["run_id"]),
            arxiv_id=str(row["arxiv_id"]),
            status=str(row.get("status") or "?"),
            budget=row.get("budget"),
            audit_score=row.get("audit_score"),
        )
        for row in sorted(latest.values(), key=lambda r: str(r.get("arxiv_id")))
    ]


def _started(row: dict[str, Any]) -> str:
    return str(row.get("started_at") or row.get("updated_at") or "")


def bundle_for(runs_dir: Path, arxiv_id: str, run_id: str) -> Path | None:
    """The bundle directory this run wrote: ``<runs-dir>/<arxiv_id>/**/<run_id>``."""
    paper_dir = Path(runs_dir) / arxiv_id
    if not paper_dir.is_dir():
        return None
    for candidate in sorted(paper_dir.rglob(run_id)):
        if candidate.is_dir():
            return candidate
    return None


def newest_bundle(runs_dir: Path, arxiv_id: str) -> Path | None:
    """The most recent bundle for a paper, for grading outside a sweep.

    Used when the caller names papers rather than a batch: with no ``run_id`` to
    match, the newest bundle that actually holds a run record (``report.json`` or
    ``stats.json``) is the only defensible choice.
    """
    paper_dir = Path(runs_dir) / arxiv_id
    if not paper_dir.is_dir():
        return None
    marked = [
        path.parent
        for path in paper_dir.rglob("*")
        if path.name in ("report.json", "stats.json") and path.is_file()
    ]
    if not marked:
        return None
    return max(marked, key=lambda path: path.stat().st_mtime)


def resolve_bundles(runs: list[Run], runs_dir: Path) -> tuple[list[Run], list[Run]]:
    """Split ``runs`` into (resolved, missing) by whether their bundle is on disk."""
    resolved, missing = [], []
    for run in runs:
        run.bundle = bundle_for(runs_dir, run.arxiv_id, run.run_id)
        (resolved if run.bundle else missing).append(run)
    return resolved, missing


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="reprocli_repro.batch_runs", description=__doc__)
    parser.add_argument("--batch", required=True, help="batch_id to resolve, e.g. slurm-2687371.")
    parser.add_argument("--runs-dir", type=Path, required=True,
                        help="Root of the agent run bundles (<runs-dir>/<arxiv_id>/<budget>h/<run_id>).")
    parser.add_argument("--supabase-url", default=os.environ.get("SUPABASE_URL"),
                        help="Supabase project URL (default: $SUPABASE_URL).")
    parser.add_argument("--include-running", action="store_true",
                        help="Also grade runs still in progress (their bundles are incomplete).")
    parser.add_argument("--skip-audited", action="store_true",
                        help="Skip papers whose repro_runs row already has an audit_score.")
    parser.add_argument("--limit", type=int, help="Grade at most this many papers (smoke tests).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base, key = (args.supabase_url or "").rstrip("/"), _service_key()
    if not base or not key:
        print("batch_runs: set SUPABASE_URL (or --supabase-url) and SUPABASE_SERVICE_KEY",
              file=sys.stderr)
        return 2

    runs = select_runs(
        fetch_runs(base, key, args.batch),
        include_running=args.include_running,
        skip_audited=args.skip_audited,
    )
    if args.limit is not None:
        runs = runs[: max(0, args.limit)]
    resolved, missing = resolve_bundles(runs, args.runs_dir)
    for run in missing:
        print(f"  {run.arxiv_id}: no bundle for run {run.run_id} under {args.runs_dir} -- skipped",
              file=sys.stderr)
    if not resolved:
        print(f"batch_runs: no gradeable bundles for {args.batch}", file=sys.stderr)
        return 1

    for run in resolved:
        print(f"{run.arxiv_id}\t{run.run_id}\t{run.bundle}")
    print(
        f"batch_runs: {len(resolved)} bundle(s) bound for {args.batch}"
        + (f", {len(missing)} missing" if missing else ""),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
