"""Tool-enforced execution environment for the reproduction agent.

The agent issues plain shell commands; the **tools** (never the model) wrap every
command so it runs in the episode's CUDA environment. This is the fix for the
wrong-env trap: a ``pip install`` must never land in the orchestrator's bare CPU
env and pull CPU wheels — it has to see CUDA. The wrapping is enforced here, not
left to the prompt, so the agent cannot accidentally escape it.

The wrap loads the cluster profile's ``modules`` (e.g. ``cuda cudnn nccl``) and
enters the workspace::

    bash -lc 'cd <ws> && module load <modules> && <cmd>'

``exec_argv`` is the single seam both sides use: the orchestrator tools
(``workspace_bash``, the venv build) pass it straight to ``subprocess.run``; the
GPU substrate (``slurm``) splices it in after ``srun``, so a GPU step runs in
exactly the same environment as CPU-side setup. (A container/Apptainer mode is a
deferred seam — see ``--apptainer-image`` — and is intentionally not wired yet.)
"""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reprocli_repro.cluster import Cluster


def env_inner(cluster: "Cluster | None", workspace: Path | str, command: str) -> str:
    """The ``bash -lc`` body: enter the workspace, load CUDA modules, run command."""
    parts = [f"cd {shlex.quote(str(workspace))}"]
    if cluster is not None and cluster.modules:
        parts.append("module load " + " ".join(cluster.modules))
    parts.append(command)
    return " && ".join(parts)


def exec_argv(cluster: "Cluster | None", workspace: Path | str, command: str) -> list[str]:
    """Argv that runs ``command`` in the episode's environment.

    Pass it directly to ``subprocess.run`` for orchestrator-side tools, or splice
    it in after ``srun ...`` for a GPU step.
    """
    return ["bash", "-lc", env_inner(cluster, workspace, command)]
