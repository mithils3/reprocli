"""Durable evidence store for one reproduction episode.

The auditor (S7) trusts only what it can re-trace from disk, so every reproduction
episode writes a durable record under ``evidence/`` as it works:

  - ``commands.log``    -- one human-readable line per shell command (cmd, rc, cwd),
  - ``trajectory.jsonl``-- one JSON row per tool call / step (machine-readable),
  - ``env.lock``        -- the resolved environment (``uv pip freeze``),
  - ``patches/``        -- every diff the agent applied, saved verbatim.

These are *primitives*: ``init_evidence`` lays the files down at setup; the tools
(``workspace_bash``, ``apply_patch``) and the loop append to them as the episode
runs. Microcompact can safely elide stale tool output from the conversation
precisely because the ground truth lives here, not in the model's context.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from reprocli_vllm.vllm.io import append_jsonl_row


@dataclass
class EvidencePaths:
    """Resolved locations of the four evidence sinks for one episode."""

    root: Path
    commands_log: Path
    trajectory: Path
    env_lock: Path
    patches_dir: Path


def evidence_paths(evidence_dir: Path) -> EvidencePaths:
    root = Path(evidence_dir)
    return EvidencePaths(
        root=root,
        commands_log=root / "commands.log",
        trajectory=root / "trajectory.jsonl",
        env_lock=root / "env.lock",
        patches_dir=root / "patches",
    )


def init_evidence(evidence_dir: Path) -> EvidencePaths:
    """Create the evidence dir + ``patches/`` and touch the append-only sinks."""
    paths = evidence_paths(evidence_dir)
    paths.patches_dir.mkdir(parents=True, exist_ok=True)
    for sink in (paths.commands_log, paths.trajectory, paths.env_lock):
        if not sink.exists():
            sink.write_text("", encoding="utf-8")
    return paths


def log_command(
    evidence_dir: Path,
    command: str,
    *,
    returncode: int | None = None,
    cwd: str | Path | None = None,
    duration_s: float | None = None,
) -> None:
    """Append one line to ``commands.log`` recording a shell command's outcome."""
    paths = evidence_paths(evidence_dir)
    paths.commands_log.parent.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rc = "?" if returncode is None else str(returncode)
    parts = [stamp, f"rc={rc}"]
    if duration_s is not None:
        parts.append(f"{duration_s:.1f}s")
    if cwd is not None:
        parts.append(f"cwd={cwd}")
    header = " ".join(parts)
    with paths.commands_log.open("a", encoding="utf-8") as handle:
        handle.write(f"[{header}] {command}\n")


def append_trajectory(evidence_dir: Path, row: dict) -> None:
    """Append one structured step to ``trajectory.jsonl``."""
    append_jsonl_row(evidence_paths(evidence_dir).trajectory, row, truncate=False)


def save_patch(evidence_dir: Path, diff: str, *, name: str | None = None) -> Path:
    """Persist a diff under ``patches/`` with a zero-padded sequence prefix."""
    paths = evidence_paths(evidence_dir)
    paths.patches_dir.mkdir(parents=True, exist_ok=True)
    seq = sum(1 for _ in paths.patches_dir.glob("*.diff"))
    slug = _slug(name) if name else "patch"
    target = paths.patches_dir / f"{seq:04d}-{slug}.diff"
    target.write_text(diff if diff.endswith("\n") else diff + "\n", encoding="utf-8")
    return target


def save_plan(evidence_dir: Path, rendered: str) -> Path:
    """Snapshot the agent's current plan to ``plan.md`` (overwritten each update)."""
    paths = evidence_paths(evidence_dir)
    paths.root.mkdir(parents=True, exist_ok=True)
    target = paths.root / "plan.md"
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    target.write_text(f"# Plan (updated {stamp})\n\n{rendered}\n", encoding="utf-8")
    return target


def write_env_lock(
    evidence_dir: Path, *, venv: Path | None = None, uv_bin: str = "uv"
) -> dict:
    """Freeze the resolved environment into ``env.lock`` via ``uv pip freeze``."""
    paths = evidence_paths(evidence_dir)
    cmd = [uv_bin, "pip", "freeze"]
    if venv is not None:
        cmd += ["--python", str(Path(venv) / "bin" / "python")]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        paths.env_lock.write_text("", encoding="utf-8")
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "path": str(paths.env_lock)}
    paths.env_lock.write_text(proc.stdout, encoding="utf-8")
    return {"ok": proc.returncode == 0, "path": str(paths.env_lock), "stderr": proc.stderr}


def _slug(name: str) -> str:
    keep = "".join(c if c.isalnum() or c in "-_." else "-" for c in name.strip())
    return keep.strip("-.")[:48] or "patch"
