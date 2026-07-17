"""Per-agent CPU and build-parallelism caps for CPU-step Apptainer sandboxing.

Slurm job 2666353: the sweep brain (vLLM) shares one --mem cgroup with six parallel
reproduction agents' CPU shell steps on the same node. One agent ran
``uv pip install flash-attn --no-build-isolation``; ninja defaulted -j to nproc, the
parallel nvcc jobs blew the 120G cgroup cap, and the kernel OOM-killed the vLLM
engine.

Apptainer's native ``--cpus``/``--memory`` cgroup flags are unusable on DeltaAI: there
is no cgroup delegation, so they fail with "while applying cgroups config ...
memory.max: no such file or directory". The portable fix is two-part instead:

1. ``taskset`` sched-affinity pinning. Affinity survives into the container and
   ``nproc`` honors it, so every build tool's default ``-j`` follows without the
   container runtime needing cgroup permissions at all.
2. Explicit build-parallelism env vars for tools that read ``MAX_JOBS`` etc. directly
   instead of asking ``nproc``.

Caps apply ONLY to CPU steps (``workspace_bash``, ``nv=False``), which run on the
shared brain node. GPU steps (``nv=True``) run on dedicated JIT-allocated nodes where
capping would hurt legitimate work, so they are never touched here.
"""

from __future__ import annotations

import os
import shutil


def taskset_argv(cpus: int) -> list[str]:
    """``["taskset", "-c", "<core ids>"]`` pinning the step to *cpus* cores, or ``[]``.

    Returns ``[]`` when there is nothing to do: no ``taskset`` binary, a non-positive
    cap, or the process's current allowed set is already at or below *cpus* cores (no
    shrinking needed).

    Core selection rotates ``sorted(os.sched_getaffinity(0))`` by
    ``(os.getpid() * cpus) % len(allowed)`` and takes the first *cpus* entries. Each
    paper's episode runs in its own orchestrator process, so a pid-derived offset
    spreads concurrent agents across the job's cores without any coordination between
    them; overlap between two agents' picks is harmless (the OS scheduler balances
    runnable threads across the machine regardless), the only thing that matters is
    that ``nproc`` inside the taskset slice reports *cpus*.
    """
    if cpus <= 0 or not shutil.which("taskset"):
        return []
    try:
        allowed = sorted(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return []  # non-Linux, or affinity unsupported here
    if len(allowed) <= cpus:
        return []
    offset = (os.getpid() * cpus) % len(allowed)
    rotated = allowed[offset:] + allowed[:offset]
    cores = ",".join(str(c) for c in rotated[:cpus])
    return ["taskset", "-c", cores]


def build_env_args(cpus: int) -> list[str]:
    """Apptainer ``--env`` args capping build fan-out for tools that ignore affinity.

    Compile RAM scales with job count, not core count, so these are set independent of
    whether :func:`taskset_argv` fired. ``MAX_JOBS`` is what flash-attn/torch extension
    builds honor directly; ``NVCC_THREADS``, ``CMAKE_BUILD_PARALLEL_LEVEL``, and
    ``MAKEFLAGS`` cover cmake/make/nvcc invocations that read their job count from the
    environment instead of calling ``nproc``.
    """
    return [
        "--env", f"MAX_JOBS={cpus}",
        "--env", "NVCC_THREADS=2",
        "--env", f"CMAKE_BUILD_PARALLEL_LEVEL={cpus}",
        "--env", f"MAKEFLAGS=-j{cpus}",
    ]
