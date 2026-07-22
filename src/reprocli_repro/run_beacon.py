"""Per-run telemetry sidecar: a metrics beacon inside each held GPU allocation.

``gpu_session.ensure_session`` calls ``start`` the moment an allocation is
granted; ``release``/``drop_lost`` call ``stop``. The beacon is one detached
``srun --overlap`` step into the held jobid running
``python -m reprocli_repro.metrics_beacon --role run``, so the run's JIT GPU
node shows up in the viewer's host panel while the agent works. Same opt-in as
``supabase_sink`` (SUPABASE_URL + SUPABASE_SERVICE_KEY, checked directly so
this stays import-light) and the same discipline: every entry point swallows
everything — telemetry may never break a run or a test.

The live ``srun`` client Popens live in a module registry keyed by jobid
(rather than on ``GpuSession``) so ``context.py`` stays plumbing-free. ``stop``
only terminates the *local* srun client — the ``scancel`` on release kills the
remote step itself; we just must not leave the client lingering.
"""

from __future__ import annotations

import os
import subprocess
import sys

_BEACONS: dict[str, subprocess.Popen] = {}


def _enabled() -> bool:
    """Same two env vars as ``SinkConfig.from_env``, checked without the import."""
    return bool(os.environ.get("SUPABASE_URL")) and bool(
        os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))


def start(ctx, jobid: str) -> None:
    """Spawn the detached beacon into the held allocation; silent no-op on any failure.

    ``srun --jobid`` targets the allocation explicitly, so the orchestrator's
    SLURM_* env scrub doesn't matter; the venv is on shared FS, so
    ``sys.executable`` resolves on the worker node too.
    """
    try:
        if not _enabled() or jobid in _BEACONS:
            return
        from reprocli_repro.supabase_sink import run_id_of
        run_id = run_id_of(ctx)
        if not run_id:
            return
        argv = [
            "srun", f"--jobid={jobid}", "--overlap", "--ntasks=1", "--nodes=1",
            "--output=/dev/null", "--error=/dev/null",
            sys.executable, "-m", "reprocli_repro.metrics_beacon",
            "--role", "run", "--run-id", run_id, "--interval", "20",
        ]
        _BEACONS[jobid] = subprocess.Popen(
            argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except Exception:  # noqa: BLE001 — telemetry may never break a run
        pass


def stop(jobid: str | None) -> None:
    """Terminate the local srun client (scancel kills the step itself); never raises."""
    try:
        proc = _BEACONS.pop(jobid, None) if jobid else None
        if proc is not None:
            proc.terminate()
    except Exception:  # noqa: BLE001 — telemetry may never break a run
        pass
