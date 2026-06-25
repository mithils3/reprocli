"""Tool-enforced execution environment for the reproduction agent.

The agent issues plain shell commands; the **tools** (never the model) decide where
each one runs. ``exec_argv`` is the single seam both sides use: the orchestrator tools
(``workspace_bash``, the venv build) pass it straight to ``subprocess.run``; the GPU
substrate (``slurm.py``) splices it in after ``srun``.

Every step body is just ``cd <ws> && <cmd>`` — the agent's cwd pinned to the episode's
workspace. There is no host ``module load`` and no CPU/GPU split in the body any more:
the CUDA toolkit, Python, and a prebuilt GPU ``torch`` come from the **Apptainer image**
the step runs inside (``sandbox.py``), not from the bare host. ``on_gpu`` no longer
changes the body; it only tells the sandbox to add ``--nv`` so a GPU step sees the
device, while a CPU-setup step on the login node does not.

The sandbox is **mandatory** for every agent step (``sandbox`` is passed on each call);
the pure builders keep it optional so argv-shape tests can assert the bare body without
the container wrap.
"""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reprocli_repro.sandbox import Sandbox


def env_inner(workspace, command: str) -> str:
    """The ``bash -lc`` body for one step: ``cd <ws> && <cmd>``.

    The container (``sandbox.py``) supplies the toolchain, so the body carries no
    ``module load`` — loading host modules would either be a no-op or, inside the
    ``--cleanenv`` container where ``module`` does not exist, fail and short-circuit the
    real command. The cwd is pinned to the workspace (the same root the file tools and
    the rw bind confine to).
    """
    return f"cd {shlex.quote(str(workspace))} && {command}"


def exec_argv(
    workspace,
    command: str,
    *,
    on_gpu: bool = False,
    sandbox: "Sandbox | None" = None,
) -> list[str]:
    """Argv that runs ``command`` in the episode's environment.

    Pass directly to ``subprocess.run`` for orchestrator-side tools, or splice in after
    ``srun ...`` for a GPU step. When ``sandbox`` is supplied (every agent step — the
    sandbox is mandatory) the ``bash -lc`` body is wrapped in the episode's Apptainer
    container, so the step runs inside the read-only image and can only *write* the
    episode's own dirs. ``on_gpu`` adds ``--nv`` for GPU steps.
    """
    body = env_inner(workspace, command)
    if sandbox is not None:
        return sandbox.wrap_argv(body, nv=on_gpu)
    return ["bash", "-lc", body]
