"""Tool-enforced execution environment for the reproduction agent.

The agent issues plain shell commands; the **tools** (never the model) decide
where each one runs. There are two kinds of step and they wrap differently:

* **CPU setup** (``workspace_bash``: clone, edits, file reads, the venv build,
  pure-Python installs) runs on the orchestrator/login node, which has no GPU. It
  is wrapped as just ``bash -lc 'cd <ws> && <cmd>'`` — deliberately a *clean*
  shell. We do NOT ``module load`` the CUDA stack here: a spack CUDA module
  prepends an ``LD_LIBRARY_PATH`` that shadows the system ``git``'s
  ``libcurl``/``libnghttp2`` (an ``undefined symbol`` crash on ``git clone``), and
  CPU setup needs no CUDA libraries anyway.

* **GPU steps** (``run_gpu``, spliced after ``srun`` by ``slurm.py``) DO need the
  CUDA toolkit — to build any custom CUDA extensions and to run the experiment —
  so those take the ``on_gpu=True`` wrap: ``cd <ws> && module load <modules> &&
  <cmd>``. The NVIDIA driver is always present on a GPU node, so a CUDA-enabled
  torch wheel runs there regardless; the ``module load`` is for the build toolkit.

``exec_argv`` is the single seam both sides use, with ``on_gpu`` selecting the
wrap: the orchestrator tools pass it straight to ``subprocess.run``; the GPU
substrate splices it in after ``srun``.

Apptainer (running a step inside an NGC ``.sif``) is now **opt-in and off by
default** — the agent instead installs a CUDA-enabled torch into the per-paper
venv from the right PyTorch index. Set ``apptainer_image`` on the cluster profile
(or ``--apptainer-image`` / ``$REPRO_APPTAINER_SIF``) to re-enable it for a site
that needs the container path. When set, the step runs via ``apptainer exec --nv
--cleanenv`` (``--cleanenv`` stops the login shell's ``LD_LIBRARY_PATH``/
``PYTHONPATH`` leaking in and shadowing the image's own libs/packages); ``--nv``
passes the GPU through and we bind the scratch root and host ``uv`` binary in.
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


def env_inner(
    cluster: "Cluster | None", workspace: Path | str, command: str, *, on_gpu: bool = False
) -> str:
    """The ``bash -lc`` body for one step.

    Opt-in apptainer path (``apptainer_image`` set): ``apptainer exec --nv ... <sif>
    bash -c 'cd <ws> && <cmd>'`` (CUDA torch comes from the image; modules skipped).
    Otherwise the bare-host path: always ``cd <ws>``, plus ``module load <modules>``
    only when ``on_gpu`` — GPU steps need the CUDA toolkit, while the CPU-setup shell
    stays clean so it doesn't break ``git``. Single-quoting the inner body on the
    apptainer path defers expansion to the in-container shell.
    """
    cd = f"cd {shlex.quote(str(workspace))}"
    if cluster is not None and cluster.apptainer_image:
        inner = f"{cd} && {command}"
        return f"{_apptainer_prefix(cluster, workspace)} bash -c {shlex.quote(inner)}"
    parts = [cd]
    if on_gpu and cluster is not None and cluster.modules:
        parts.append("module load " + " ".join(cluster.modules))
    parts.append(command)
    return " && ".join(parts)


def exec_argv(
    cluster: "Cluster | None", workspace: Path | str, command: str, *, on_gpu: bool = False
) -> list[str]:
    """Argv that runs ``command`` in the episode's environment.

    ``on_gpu`` selects the GPU-step wrap (CUDA ``module load``); the default
    CPU-setup wrap is a clean shell. Pass directly to ``subprocess.run`` for
    orchestrator-side tools, or splice in after ``srun ...`` for a GPU step.
    """
    return ["bash", "-lc", env_inner(cluster, workspace, command, on_gpu=on_gpu)]
