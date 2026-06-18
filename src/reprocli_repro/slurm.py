"""SLURM substrate — the just-in-time GPU step builder/runner.

One ``run_gpu`` call becomes **one self-contained, on-demand allocation** that is
released the instant the command exits — nothing is pre-held:

    salloc -A <account> -p <partition> --nodes=1 --gpus=<k> --time=<minutes> \\
      srun --ntasks=1 bash -lc 'cd <ws> && module load ... && <cmd>'

``<account>/<partition>/<modules>`` come from the cluster profile (``cluster.py``);
``<k>``/``<minutes>`` come from the model's ``run_gpu`` arguments. ``--time`` is
the budget pre-authorization (SLURM hard-kills at the wall limit), so the meter
can refuse a step before it launches. ``--executor local`` swaps the whole
allocation for a plain subprocess so the loop runs offline.

``build_command`` is pure (the gate asserts the exact argv); ``run_step`` executes
it and times the *run* so ``budget.charge`` bills elapsed, not queue wait. The
exact ``salloc``/``srun`` nesting is the one cluster-specific seam — some sites
need ``SallocDefaultCommand`` or ``sbatch --wait`` instead.
"""

from __future__ import annotations

import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from reprocli_repro.cluster import Cluster

LOCAL = "local"
SLURM = "slurm"


@dataclass
class StepResult:
    """Outcome of one GPU step — fed to ``budget.charge`` and the trajectory."""

    ok: bool
    returncode: int
    stdout: str
    stderr: str
    elapsed_s: float
    command: list[str]
    executor: str


def _inner_script(workspace: Path | str, modules: tuple[str, ...], cmd: str) -> str:
    """The ``bash -lc`` body: cd into the workspace, load modules, run the command."""
    parts = [f"cd {shlex.quote(str(workspace))}"]
    if modules:
        parts.append("module load " + " ".join(modules))
    parts.append(cmd)
    return " && ".join(parts)


def build_command(
    cluster: Cluster,
    workspace: Path | str,
    cmd: str,
    *,
    gpus: int,
    minutes: int,
    executor: str = SLURM,
) -> list[str]:
    """Build the argv for one step. ``local`` => plain bash; ``slurm`` => JIT salloc."""
    if executor == LOCAL:
        # No SLURM, no modules (`module` may not exist off-cluster): just run it.
        return ["bash", "-lc", _inner_script(workspace, (), cmd)]
    if executor != SLURM:
        raise SystemExit(f"unknown executor {executor!r}; choose from {LOCAL}, {SLURM}")
    if not cluster.account or not cluster.partition:
        raise SystemExit(
            f"--executor slurm needs an account and partition; cluster {cluster.name!r} "
            "has none (pass --account/--partition or pick a cluster profile that sets them)."
        )
    if gpus < 1 or gpus > cluster.gpus_per_node:
        raise SystemExit(
            f"run_gpu gpus={gpus} out of range for {cluster.name!r} "
            f"(1..{cluster.gpus_per_node} per node)."
        )
    inner = _inner_script(workspace, cluster.modules, cmd)
    return [
        "salloc",
        "-A", cluster.account,
        "-p", cluster.partition,
        "--nodes=1",
        f"--gpus={int(gpus)}",
        f"--time={int(minutes)}",
        "srun", "--ntasks=1", "bash", "-lc", inner,
    ]


def run_step(
    cluster: Cluster,
    workspace: Path | str,
    cmd: str,
    *,
    gpus: int,
    minutes: int,
    executor: str = SLURM,
    timeout: float | None = None,
) -> StepResult:
    """Run one step and time the wall it actually took (for the budget meter)."""
    argv = build_command(cluster, workspace, cmd, gpus=gpus, minutes=minutes, executor=executor)
    start = time.monotonic()
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - start
        return StepResult(
            ok=False,
            returncode=124,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + "\n[step exceeded --executor timeout]",
            elapsed_s=elapsed,
            command=argv,
            executor=executor,
        )
    elapsed = time.monotonic() - start
    return StepResult(
        ok=proc.returncode == 0,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        elapsed_s=elapsed,
        command=argv,
        executor=executor,
    )
