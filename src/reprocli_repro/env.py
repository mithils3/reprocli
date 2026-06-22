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
exactly the same environment as CPU-side setup. When the cluster profile sets
``apptainer_image`` (DeltaAI's default — a shared NGC PyTorch ARM ``.sif``), the
wrap instead runs the step *inside* that image via ``apptainer exec --nv`` so a
GH200-correct CUDA PyTorch is already present (the bare aarch64 host only resolves
CPU torch wheels). ``--nv`` passes the GPU through; we bind the scratch root
(workspace/venv/reference) and the host ``uv`` binary into the container. We run
with ``--cleanenv`` (the login shell's ``LD_LIBRARY_PATH``/``PYTHONPATH`` otherwise
leak in and shadow the image's own libs/packages); ``--containall``/``--no-home``
stay off so $HOME (HF caches) and binds keep working for trusted M1–M3 papers.
"""

from __future__ import annotations

import shlex
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reprocli_repro.cluster import Cluster


def _apptainer_prefix(cluster: "Cluster", workspace: Path | str) -> str:
    """``apptainer exec --nv --cleanenv ...`` prefix that runs a step in the NGC image.

    ``--cleanenv`` is mandatory for correctness, not just hygiene: the orchestrator's
    login shell exports ``LD_LIBRARY_PATH`` (spack/CUDA modules) and ``PYTHONPATH``,
    and apptainer would otherwise leak them into the container — the host libs then
    shadow the image's own (e.g. the container ``git``/``libcurl`` loading an older
    host ``libnghttp2`` → ``undefined symbol`` crash) and host ``PYTHONPATH`` could
    drag a CPU ``torch`` onto ``sys.path``. ``--cleanenv`` gives the container its
    own environment; ``$HOME`` is still mounted (no ``--no-home``) so ``~/.cache``
    (HF) works, and ``uv`` is bound onto the container's default PATH.

    Binds the scratch root (workspace/venv/reference visible) and the host ``uv``
    binary (NGC images ship ``pip`` but not ``uv``, and the prompt uses ``uv pip``).
    """
    root = cluster.scratch_root or str(Path(workspace).parent)
    binds = ["--bind", shlex.quote(str(root))]
    uv = shutil.which("uv")
    if uv:
        binds += ["--bind", f"{shlex.quote(uv)}:/usr/local/bin/uv"]
    return "apptainer exec --nv --cleanenv " + " ".join(binds) + " " + shlex.quote(str(cluster.apptainer_image))


def env_inner(cluster: "Cluster | None", workspace: Path | str, command: str) -> str:
    """The ``bash -lc`` body for one step — run inside the NGC image if configured.

    With ``apptainer_image`` set: ``apptainer exec --nv ... <sif> bash -c 'cd <ws>
    && <cmd>'`` (CUDA PyTorch comes from the image). Otherwise the bare-host path:
    ``cd <ws> && module load <modules> && <cmd>``. Single-quoting the inner body
    defers shell expansion to the in-container shell, so substitutions in <cmd>
    still run there.
    """
    cd = f"cd {shlex.quote(str(workspace))}"
    if cluster is not None and cluster.apptainer_image:
        inner = f"{cd} && {command}"
        return f"{_apptainer_prefix(cluster, workspace)} bash -c {shlex.quote(inner)}"
    parts = [cd]
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
