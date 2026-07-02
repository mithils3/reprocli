"""SLURM substrate — a held GPU allocation the agent runs successive steps into.

The agent's GPU access is **one allocation held for the episode**, not a fresh
``salloc`` per command. The first ``run_gpu`` call acquires it and every later call
runs into the same node, so the agent stops re-queueing between install → verify →
run:

    # acquire once (returns the instant the alloc is granted, then stays up):
    salloc --no-shell -A <account> -p <partition> --nodes=1 --gpus=<k> --time=<min>
    # run each step into the held jobid (no new queue wait), inside the sandbox image:
    srun --jobid=<jobid> --ntasks=1 apptainer exec --nv ... <sif> bash -lc 'cd <ws> && <cmd>'
    # release when the agent is done (or at teardown):
    scancel <jobid>

``<account>/<partition>`` come from the cluster profile (``cluster.py``);
``<k>``/``<min>`` come from the model's ``run_gpu`` arguments on the call that
*starts* the session. ``--time`` is the hold's hard lifetime (SLURM kills it at the
wall limit) and the budget pre-authorization. Queue wait is naturally excluded from
billing: ``acquire_session`` blocks during the wait and the meter only starts the
clock once the allocation is granted (see ``gpu_session``).

The ``srun`` payload (the Apptainer wrap + ``cd`` + ``<cmd>``) is built by
``env.exec_argv(..., on_gpu=True, sandbox=...)`` — ``on_gpu`` adds ``--nv`` so the GPU
step sees the device + CUDA driver; the CUDA toolkit itself comes from the image, not a
host ``module load``. ``build_acquire``/``build_srun`` are pure (the tests assert the
exact argv); the ``*_session`` helpers execute them. ``salloc --no-shell`` is the one
cluster-specific seam — some sites need a held ``salloc ... sleep`` or
``SallocDefaultCommand`` instead.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from typing import TYPE_CHECKING, IO

from reprocli_repro import env
from reprocli_repro.cluster import Cluster

if TYPE_CHECKING:
    from reprocli_repro.sandbox import Sandbox

# salloc prints "... allocation <jobid>" (Pending then Granted share the number).
_JOBID_RE = re.compile(r"allocation (\d+)")
# srun into a dead/expired allocation fails with one of these — the held session is
# gone (hit --time or was cancelled), so the caller should drop it and re-acquire.
# The first three are the scancel/revoke path; the last three are the --time-expiry
# path (a held job drains COMPLETING -> EXPIRED, each with its own srun wording), which
# is the common one for short held sessions and must drop the session just the same.
_LOST_MARKERS = (
    "invalid job id",
    "unable to confirm allocation",
    "job allocation has been revoked",
    "already completing or completed",  # "Unable to create step ... Job/step already completing or completed"
    "has expired",                      # "Slurm job N has expired"
    "expired or invalid job",           # "Check SLURM_JOB_ID environment variable. Expired or invalid job N"
)


class SlurmConfigError(Exception):
    """The requested GPU allocation can't be built from the cluster profile.

    Raised by the pure argv builders when the operator-set substrate is unusable
    (no account/partition, or a gpu count outside the node). A domain error, not a
    ``SystemExit`` — the caller (``gpu_session.ensure_session``) turns it into a
    clean acquire failure instead of crashing the loop from inside library code.
    """


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


def _require_target(cluster: Cluster, gpus: int, partition: str | None) -> None:
    """Validate the operator-set substrate before building any allocation argv."""
    if not cluster.account or not partition:
        raise SlurmConfigError(
            f"cluster {cluster.name!r} has no account/partition for a GPU allocation "
            "(pass --account/--partition or pick a cluster profile that sets them)."
        )
    if gpus < 1 or gpus > cluster.gpus_per_node:
        raise SlurmConfigError(
            f"run_gpu gpus={gpus} out of range for {cluster.name!r} "
            f"(1..{cluster.gpus_per_node} per node)."
        )


def build_acquire(
    cluster: Cluster, *, gpus: int, minutes: int, partition: str | None = None
) -> list[str]:
    """Argv that holds one allocation (``salloc --no-shell``) and returns once granted.

    ``partition`` overrides the profile's default pool for this allocation (the agent
    picks it from ``list_partitions``); ``None`` falls back to ``cluster.partition``.
    """
    part = partition or cluster.partition
    _require_target(cluster, gpus, part)
    return [
        "salloc",
        "--no-shell",
        "-A", cluster.account,
        "-p", part,
        "--nodes=1",
        f"--gpus={int(gpus)}",
        f"--time={int(minutes)}",
    ]


def build_srun(
    cluster: Cluster,
    workspace: Path | str,
    cmd: str,
    *,
    jobid: str,
    sandbox: "Sandbox | None" = None,
) -> list[str]:
    """Argv that runs ``cmd`` into the already-held allocation ``jobid``.

    ``sandbox`` (always active for agent steps) wraps the payload in the episode's
    Apptainer container, so the untrusted GPU step runs inside the read-only image and
    is write-confined to the episode's dirs on the compute node. ``srun`` itself — the
    trusted launcher — stays outside the wrap.
    """
    # --unbuffered: forward step output as it arrives instead of line-buffering it in
    # slurmstepd, so the streamed evidence log (run_in_session's log_path) holds
    # everything the step printed even when SLURM kills it at the --time wall.
    return [
        "srun",
        f"--jobid={jobid}",
        "--ntasks=1",
        "--unbuffered",
        *env.exec_argv(workspace, cmd, on_gpu=True, sandbox=sandbox),
    ]


def acquire_session(
    cluster: Cluster,
    *,
    gpus: int,
    minutes: int,
    timeout: float | None = None,
    partition: str | None = None,
) -> SessionHandle:
    """Hold a GPU allocation; block through the queue wait, return once it is granted."""
    argv = build_acquire(cluster, gpus=gpus, minutes=minutes, partition=partition)
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
    sandbox: "Sandbox | None" = None,
    log_path: Path | str | None = None,
) -> StepResult:
    """Run one command into the held allocation and time it (queue wait already paid).

    Output is *streamed*, not just captured: each chunk is teed to ``log_path`` (the
    episode's ``evidence/gpu_step_<n>.log``) as it arrives, so when the step dies —
    our timeout, the --time wall, scancel — everything printed up to the kill is on
    disk and in the returned (partial) ``StepResult`` instead of dying in a pipe
    buffer with the process.
    """
    argv = build_srun(cluster, workspace, cmd, jobid=jobid, sandbox=sandbox)
    start = time.monotonic()
    try:
        # Own process group: a timeout kill must take out srun's whole tree, or an
        # orphan keeps the pipes open and the pumps block long past the kill.
        proc = subprocess.Popen(
            argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True
        )
    except OSError as exc:
        return StepResult(
            ok=False, returncode=127, stdout="", stderr=f"{type(exc).__name__}: {exc}",
            elapsed_s=time.monotonic() - start, command=argv,
        )
    log = open(log_path, "ab", buffering=0) if log_path else None
    try:
        out_buf: list[bytes] = []
        err_buf: list[bytes] = []
        pumps = [
            threading.Thread(target=_pump, args=(proc.stdout, out_buf, log), daemon=True),
            threading.Thread(target=_pump, args=(proc.stderr, err_buf, log), daemon=True),
        ]
        for t in pumps:
            t.start()
        timed_out = False
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_tree(proc)
            proc.wait()
        for t in pumps:
            t.join(timeout=10)
    finally:
        if log is not None:
            log.close()
    stdout = b"".join(out_buf).decode("utf-8", errors="replace")
    stderr = b"".join(err_buf).decode("utf-8", errors="replace")
    if timed_out:
        stderr += "\n[step exceeded timeout]"
    return StepResult(
        ok=proc.returncode == 0 and not timed_out,
        returncode=124 if timed_out else proc.returncode,
        stdout=stdout,
        stderr=stderr,
        elapsed_s=time.monotonic() - start,
        command=argv,
    )


def _kill_tree(proc: subprocess.Popen) -> None:
    """Kill the step's whole process group (falling back to just the leader)."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (OSError, ProcessLookupError):
        proc.kill()


def _pump(pipe: IO[bytes] | None, buf: list[bytes], log: IO[bytes] | None) -> None:
    """Drain one pipe: collect chunks in memory and tee them to the evidence log.

    The log write happens per-chunk (unbuffered handle), so the on-disk file is
    current the moment the process is killed; both streams share one log in arrival
    order — the interleaving a terminal would have shown.
    """
    if pipe is None:
        return
    try:
        for chunk in iter(lambda: pipe.read1(65536), b""):
            buf.append(chunk)
            if log is not None:
                try:
                    log.write(chunk)
                except OSError:
                    log = None  # keep collecting for the result even if the disk sink dies
    except (OSError, ValueError):
        pass
    finally:
        try:
            pipe.close()
        except OSError:
            pass


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
