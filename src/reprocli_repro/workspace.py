"""Per-paper workspace setup for one reproduction episode.

Integrates the run-directory layout resolved in ``inputs.resolve_run_paths`` (the
shared "directory maker": ``<runs-dir>/<arxiv_id>/<budget>h/<run_id>/`` with a
fresh time+random ``run_id`` so re-runs of the same paper never collide) and
materializes everything the agent needs *before* the loop starts:

  - the directory layout (``workspace/`` rw, ``reference/`` ro, ``evidence/``),
  - an **empty per-paper** ``uv`` venv at ``workspace/.venv`` -- the
    reproducibility-isolation boundary; never the repo's shared ``.venv``,
  - the read-only ``reference/`` copy (paper LaTeX + every supplement file),
  - the durable ``evidence/`` sinks.

It deliberately does **not** clone the paper's code or install its dependencies:
that is the agent's job through ``workspace_bash`` (clone) into this venv. The
Apptainer/module substrate (``--apptainer-image`` / ``--modules``) is a deferred
seam consumed by Phase 3/7's ``srun`` path; the local executor builds a plain
venv and ignores it.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from reprocli_repro import evidence as evidence_mod
from reprocli_repro import reference as reference_mod
from reprocli_repro.evidence import EvidencePaths
from reprocli_repro.inputs import RunPaths, resolve_run_paths


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
    system_site_packages: bool = False,
    python: str | None = None,
    uv_bin: str = "uv",
) -> dict:
    """Create an empty per-paper ``uv`` venv at ``workspace/.venv`` (empty on purpose)."""
    venv_path = Path(workspace) / ".venv"
    cmd = [uv_bin, "venv", str(venv_path)]
    if system_site_packages:
        cmd.append("--system-site-packages")
    if python:
        cmd += ["--python", python]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
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
    make_venv: bool = True,
    materialize_ref: bool = True,
    system_site_packages: bool = False,
    venv_python: str | None = None,
    overwrite_reference: bool = False,
    reference_row: dict | None = None,
) -> WorkspaceResult:
    """Lay down one episode's bundle: dirs, evidence sinks, reference, venv."""
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
