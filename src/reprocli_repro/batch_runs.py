"""Bind one sbatch sweep's runs to the exact bundles an auditor should grade.

A sweep is a ``batch_id`` (``slurm-<jobid>``) shared by every ``reprocli_repro``
process the sbatch launched; each run leaves its bundle at
``<runs-dir>/<arxiv_id>/<budget>h/<run_id>/``. The auditor, though, reads ONE
directory per paper (``<runs-dir>/<paper_id>``), which for a paper attempted more
than once mixes every attempt together -- so pointing it straight at the runs dir
would grade whatever attempt happens to sort first, not this sweep's.

This module bridges the two. It reads the sweep's rows from the run-viewer
Supabase, resolves each ``run_id`` to the bundle it actually wrote, and builds a
*grade root*: a directory of symlinks ``<grade-root>/<arxiv_id> -> <that run's
bundle>`` plus the matching paper-ids file. Point the auditor at the grade root
and it grades exactly this sweep; point ``reprocli_repro.audit_upload`` at the
same root afterwards and every verdict lands on the right ``repro_runs`` row
(each bundle carries its own ``stats.json`` naming its run).

Read-only against Supabase; needs ``SUPABASE_URL`` + ``SUPABASE_SERVICE_KEY``.

    PYTHONPATH=src python -m reprocli_repro.batch_runs \
      --batch slurm-2687371 \
      --runs-dir /work/nvme/bfvr/msalunkhe/reprocli/agent_runs \
      --grade-root "$SCRATCH/grade-2687371" --ids-file "$SCRATCH/ids.txt"
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


def resolve_bundles(runs: list[Run], runs_dir: Path) -> tuple[list[Run], list[Run]]:
    """Split ``runs`` into (resolved, missing) by whether their bundle is on disk."""
    resolved, missing = [], []
    for run in runs:
        run.bundle = bundle_for(runs_dir, run.arxiv_id, run.run_id)
        (resolved if run.bundle else missing).append(run)
    return resolved, missing


def build_grade_root(runs: list[Run], grade_root: Path) -> Path:
    """Populate ``grade_root`` with one ``<arxiv_id> -> bundle`` symlink per run."""
    grade_root = Path(grade_root)
    grade_root.mkdir(parents=True, exist_ok=True)
    for run in runs:
        if run.bundle is None:
            continue
        link = grade_root / run.arxiv_id
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(run.bundle.resolve(), target_is_directory=True)
    return grade_root


def write_ids_file(path: Path, runs: list[Run]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{run.arxiv_id}\n" for run in runs), encoding="utf-8")
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="reprocli_repro.batch_runs", description=__doc__)
    parser.add_argument("--batch", required=True, help="batch_id to resolve, e.g. slurm-2687371.")
    parser.add_argument("--runs-dir", type=Path, required=True,
                        help="Root of the agent run bundles (<runs-dir>/<arxiv_id>/<budget>h/<run_id>).")
    parser.add_argument("--grade-root", type=Path,
                        help="Directory to fill with <arxiv_id> -> bundle symlinks for the auditor.")
    parser.add_argument("--ids-file", type=Path,
                        help="Write the resolved paper ids here (auditor --paper-ids-file).")
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

    if args.grade_root:
        build_grade_root(resolved, args.grade_root)
    if args.ids_file:
        write_ids_file(args.ids_file, resolved)
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
