"""SLURM substrate — a held GPU allocation the agent runs successive steps into.

The agent's GPU access is **one allocation held for the episode**, not a fresh
``salloc`` per command. The first ``run_gpu`` call acquires it and every later call
runs into the same node, so the agent stops re-queueing between install → verify →
run:

    # acquire once (returns the instant the alloc is granted, then stays up):
    salloc --no-shell -A <account> -p <partition> --nodes=1 --gpus=<k> --time=<min>
    # run each step into the held jobid (no new queue wait):
    srun --jobid=<jobid> --ntasks=1 bash -lc 'cd <ws> && module load ... && <cmd>'
    # release when the agent is done (or at teardown):
    scancel <jobid>

``<account>/<partition>``/modules come from the cluster profile (``cluster.py``);
``<k>``/``<min>`` come from the model's ``run_gpu`` arguments on the call that
*starts* the session. ``--time`` is the hold's hard lifetime (SLURM kills it at the
wall limit) and the budget pre-authorization. Queue wait is naturally excluded from
billing: ``acquire_session`` blocks during the wait and the meter only starts the
clock once the allocation is granted (see ``gpu_session``).

The ``srun`` payload (the ``cd`` + on-GPU ``module load``) is built by
``env.exec_argv(..., on_gpu=True)`` — so a GPU step gets the CUDA toolkit the
CPU-side ``workspace_bash`` deliberately omits. ``build_acquire``/``build_srun`` are
pure (the tests assert the exact argv); the ``*_session`` helpers execute them.
``salloc --no-shell`` is the one cluster-specific seam — some sites need a held
``salloc ... sleep`` or ``SallocDefaultCommand`` instead.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from reprocli_repro import env
from reprocli_repro.cluster import Cluster

# salloc prints "... allocation <jobid>" (Pending then Granted share the number).
_JOBID_RE = re.compile(r"allocation (\d+)")
# srun into a dead/expired allocation fails with one of these — the held session is
# gone (hit --time or was cancelled), so the caller should drop it and re-acquire.
_LOST_MARKERS = ("invalid job id", "unable to confirm allocation", "job allocation has been revoked")


@dataclass
class StepResult:
    """Outcome of one GPU step run into the held allocation."""

    ok: bool
    returncode: int
    stdout: str
    stderr: str
    elapsed_s: float
    command: list[str]


@dataclass
class SessionHandle:
    """Outcome of acquiring a held allocation — ``jobid`` set iff ``ok``."""

    ok: bool
    jobid: str | None
    stderr: str
    command: list[str]


def _require_target(cluster: Cluster, gpus: int) -> None:
    """Validate the operator-set substrate before building any allocation argv."""
    if not cluster.account or not cluster.partition:
        raise SystemExit(
            f"cluster {cluster.name!r} has no account/partition for a GPU allocation "
            "(pass --account/--partition or pick a cluster profile that sets them)."
        )
    if gpus < 1 or gpus > cluster.gpus_per_node:
        raise SystemExit(
            f"run_gpu gpus={gpus} out of range for {cluster.name!r} "
            f"(1..{cluster.gpus_per_node} per node)."
        )


def build_acquire(cluster: Cluster, *, gpus: int, minutes: int) -> list[str]:
    """Argv that holds one allocation (``salloc --no-shell``) and returns once granted."""
    _require_target(cluster, gpus)
    return [
        "salloc",
        "--no-shell",
        "-A", cluster.account,
        "-p", cluster.partition,
        "--nodes=1",
        f"--gpus={int(gpus)}",
        f"--time={int(minutes)}",
    ]


def build_srun(cluster: Cluster, workspace: Path | str, cmd: str, *, jobid: str) -> list[str]:
    """Argv that runs ``cmd`` into the already-held allocation ``jobid``."""
    return [
        "srun",
        f"--jobid={jobid}",
        "--ntasks=1",
        *env.exec_argv(cluster, workspace, cmd, on_gpu=True),
    ]


def acquire_session(
    cluster: Cluster, *, gpus: int, minutes: int, timeout: float | None = None
) -> SessionHandle:
    """Hold a GPU allocation; block through the queue wait, return once it is granted."""
    argv = build_acquire(cluster, gpus=gpus, minutes=minutes)
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return SessionHandle(
            ok=False,
            jobid=None,
            stderr=(exc.stderr or "") + "\n[salloc timed out waiting for the allocation]",
            command=argv,
        )
    found = _JOBID_RE.findall((proc.stdout or "") + "\n" + (proc.stderr or ""))
    jobid = found[-1] if found else None
    return SessionHandle(
        ok=jobid is not None and proc.returncode == 0,
        jobid=jobid,
        stderr=proc.stderr or "",
        command=argv,
    )


def run_in_session(
    cluster: Cluster,
    workspace: Path | str,
    cmd: str,
    *,
    jobid: str,
    timeout: float | None = None,
) -> StepResult:
    """Run one command into the held allocation and time it (queue wait already paid)."""
    argv = build_srun(cluster, workspace, cmd, jobid=jobid)
    start = time.monotonic()
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return StepResult(
            ok=False,
            returncode=124,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + "\n[step exceeded timeout]",
            elapsed_s=time.monotonic() - start,
            command=argv,
        )
    return StepResult(
        ok=proc.returncode == 0,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        elapsed_s=time.monotonic() - start,
        command=argv,
    )


def release_session(jobid: str) -> None:
    """Free the held allocation (``scancel``); best-effort, never raises."""
    try:
        subprocess.run(["scancel", str(jobid)], capture_output=True, text=True, timeout=60)
    except (subprocess.SubprocessError, OSError):
        pass


def session_lost(step: StepResult) -> bool:
    """Whether a step failed because the held allocation is gone (expired/cancelled)."""
    if step.ok:
        return False
    blob = (step.stderr or "").lower()
    return any(marker in blob for marker in _LOST_MARKERS)
