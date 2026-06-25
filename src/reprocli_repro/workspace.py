"""Per-paper workspace setup for one reproduction episode.

Integrates the run-directory layout resolved in ``inputs.resolve_run_paths`` (the
shared "directory maker": ``<runs-dir>/<arxiv_id>/<budget>h/<run_id>/`` with a
fresh time+random ``run_id`` so re-runs of the same paper never collide) and
materializes everything the agent needs *before* the loop starts:

  - the directory layout (``workspace/`` rw, ``reference/`` ro, ``evidence/``),
  - the read-only ``reference/`` copy (paper LaTeX + every supplement file),
  - the durable ``evidence/`` sinks,
  - optionally (``--build-venv``) a per-paper ``uv`` venv at ``workspace/.venv``.

It deliberately does **not** clone the paper's code or install its dependencies:
that is the agent's job. By default the agent also builds the venv as its first
setup step, inside the Apptainer container (see ``prompts/prompt_reproduce.txt``), so
it inherits the image's prebuilt CUDA ``torch``. When ``--build-venv`` is set the
optional upfront :func:`build_venv` does the same through the sandbox seam: the venv
is created **with** ``--system-site-packages`` so it sees the container's torch, which
is safe here because ``--no-home`` keeps any host ``~/.local`` user-site off
``sys.path``.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from reprocli_repro import env
from reprocli_repro import evidence as evidence_mod
from reprocli_repro import reference as reference_mod
from reprocli_repro.evidence import EvidencePaths
from reprocli_repro.inputs import RunPaths, resolve_run_paths

if TYPE_CHECKING:
    from reprocli_repro.sandbox import Sandbox


@dataclass
class WorkspaceResult:
    """What ``prepare_workspace`` laid down, for reporting and the loop."""

    run_paths: RunPaths
    evidence: EvidencePaths
    venv: dict | None = None
    reference: dict | None = None


def create_layout(run_paths: RunPaths) -> None:
    """Create the run-dir layout (run_dir, workspace, reference, evidence)."""
    for path in (run_paths.run_dir, run_paths.workspace, run_paths.reference, run_paths.evidence):
        Path(path).mkdir(parents=True, exist_ok=True)


def build_venv(
    workspace: Path,
    *,
    sandbox: "Sandbox | None" = None,
    system_site_packages: bool = True,
    python: str | None = None,
    seed: bool = True,
    uv_bin: str = "uv",
) -> dict:
    """Create a per-paper ``uv`` venv at ``workspace/.venv``, inside the container.

    Built through the env seam (``env.exec_argv``) wrapped in the episode's Apptainer
    ``sandbox``, so ``uv`` runs against the *container's* Python and the venv's base
    interpreter is ABI-compatible with the image. ``--system-site-packages`` is **on**
    so the venv inherits the image's prebuilt CUDA ``torch``; that is safe here because
    ``--no-home`` keeps the host ``~/.local`` user-site out of the sandbox, so nothing
    from the login node can leak onto ``sys.path``. The agent installs the paper's
    remaining deps into this venv.

    ``--seed`` is **on by default** so the venv ships with ``pip``/``setuptools``/
    ``wheel`` already present: agents (and build backends that shell out to pip)
    otherwise hit a venv with no ``pip`` and waste rounds bootstrapping it via
    ``ensurepip``.
    """
    venv_path = Path(workspace) / ".venv"
    # Relative `.venv`: the step lands in the workspace (the sandbox's container workdir,
    # or the host workspace when bare), so the host's long/per-run path never appears in
    # the in-container command.
    parts = [uv_bin, "venv", ".venv"]
    if system_site_packages:
        parts.append("--system-site-packages")
    if seed:
        parts.append("--seed")
    if python:
        parts += ["--python", shlex.quote(python)]
    argv = env.exec_argv(workspace, " ".join(parts), sandbox=sandbox)
    try:
        proc = subprocess.run(argv, cwd=str(workspace), capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "venv": str(venv_path), "error": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": proc.returncode == 0,
        "venv": str(venv_path),
        "returncode": proc.returncode,
        "stderr": proc.stderr,
    }


def prepare_workspace(
    run_paths: RunPaths,
    *,
    arxiv_id: str,
    bundle_dataset: str = reference_mod.DEFAULT_DATASET,
    make_venv: bool = False,
    materialize_ref: bool = True,
    sandbox: "Sandbox | None" = None,
    system_site_packages: bool = True,
    venv_python: str | None = None,
    overwrite_reference: bool = False,
    reference_row: dict | None = None,
) -> WorkspaceResult:
    """Lay down one episode's bundle: dirs, evidence sinks, reference, optional venv.

    The optional upfront venv (``make_venv``) is built inside ``sandbox`` (the episode's
    Apptainer container); otherwise the agent builds it itself as its first step.
    """
    create_layout(run_paths)
    evidence = evidence_mod.init_evidence(run_paths.evidence)
    reference = None
    if materialize_ref:
        reference = reference_mod.materialize_reference(
            arxiv_id,
            run_paths.reference,
            dataset=bundle_dataset,
            overwrite=overwrite_reference,
            row=reference_row,
        )
    venv = None
    if make_venv:
        venv = build_venv(
            run_paths.workspace,
            sandbox=sandbox,
            system_site_packages=system_site_packages,
            python=venv_python,
        )
    return WorkspaceResult(run_paths=run_paths, evidence=evidence, venv=venv, reference=reference)


def resolve_and_prepare(
    runs_dir: Path,
    arxiv_id: str,
    budget: float,
    *,
    run_id: str | None = None,
    **kwargs,
) -> WorkspaceResult:
    """Convenience: resolve the run layout (the directory maker), then prepare it."""
    run_paths = resolve_run_paths(runs_dir, arxiv_id, budget, run_id)
    return prepare_workspace(run_paths, arxiv_id=arxiv_id, **kwargs)
