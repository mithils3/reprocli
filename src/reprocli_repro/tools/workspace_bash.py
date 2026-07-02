"""Workspace-scoped shell for the reproduction agent.

The agent does its CPU-side work here: ``git clone`` the released code, inspect and
edit files, build the venv, install pure-Python deps. This runs on the
orchestrator/login node, which has **no GPU** — the metered ``run_gpu`` tool is where
the GPU and the experiment run live. The shell's cwd is pinned to ``ctx.workspace``
(the same root the file tools confine to) and every command is appended to
``evidence/commands.log`` so the auditor can re-trace exactly what ran. Commands run
through the env seam (``env.exec_argv`` with ``on_gpu=False``): a plain
``cd <ws> && <cmd>`` body wrapped in the episode's Apptainer container
(``ctx.sandbox``) — without ``--nv``, since the login node has no GPU to pass through.
The container supplies git/Python/CUDA, so there is no host ``module load``.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from reprocli_vllm.config.config import RUN_FILE_DEFAULT_CHARS, function_tool

from reprocli_repro import env
from reprocli_repro.context import ExecutionContext
from reprocli_repro import evidence
from reprocli_repro.tools import output as output_mod
from reprocli_repro.tools.run_gpu_notes import bounded

# Setup steps (clone, dependency installs) routinely run for minutes, so the
# default is far longer than the auditor's 60s; metered GPU steps get their own
# per-step timeout in Phase 4's run_gpu tool.
WORKSPACE_BASH_TIMEOUT = 900
WORKSPACE_BASH_MAX_TIMEOUT = 3600


def workspace_bash(arguments: dict[str, Any], ctx: ExecutionContext) -> dict[str, Any]:
    workspace = ctx.workspace
    if workspace is None or not Path(workspace).is_dir():
        return {"ok": False, "error": "No workspace directory for this episode."}
    command = str(arguments.get("command") or "").strip()
    if not command:
        return {"ok": False, "error": "Missing bash command."}
    timeout = bounded(arguments.get("timeout"), WORKSPACE_BASH_TIMEOUT, WORKSPACE_BASH_MAX_TIMEOUT)
    start = time.time()
    # Binary capture, decoded by hand: text mode's universal newlines turn every \r
    # of a progress-bar redraw into its own line, which defeats the spam stripper.
    try:
        proc = subprocess.run(
            env.exec_argv(workspace, command, sandbox=ctx.sandbox),
            cwd=str(workspace),
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        _log(ctx, command, None, workspace, time.time() - start)
        out, _ = output_mod.shape(_decode(exc.stdout), RUN_FILE_DEFAULT_CHARS)
        err, _ = output_mod.shape(_decode(exc.stderr), RUN_FILE_DEFAULT_CHARS)
        return {
            "ok": False,
            "command": command,
            "error": f"bash timed out after {timeout}s",
            "stdout": out,
            "stderr": err,
        }
    except OSError as exc:
        return {"ok": False, "command": command, "error": f"{type(exc).__name__}: {exc}"}
    duration = time.time() - start
    _log(ctx, command, proc.returncode, workspace, duration)
    stdout, t_out = output_mod.shape(_decode(proc.stdout), RUN_FILE_DEFAULT_CHARS)
    stderr, t_err = output_mod.shape(_decode(proc.stderr), RUN_FILE_DEFAULT_CHARS)
    return {
        "ok": proc.returncode == 0,
        "command": command,
        "returncode": proc.returncode,
        "duration_s": round(duration, 1),
        "stdout": stdout,
        "stderr": stderr,
        "truncated": t_out or t_err,
    }


def _decode(blob: bytes | str | None) -> str:
    if blob is None:
        return ""
    if isinstance(blob, str):
        return blob
    return blob.decode("utf-8", errors="replace")


def _log(ctx: ExecutionContext, command: str, rc: int | None, cwd: Path, duration: float) -> None:
    if ctx.evidence is not None:
        evidence.log_command(ctx.evidence, command, returncode=rc, cwd=cwd, duration_s=duration)


WORKSPACE_BASH_TOOL = function_tool(
    "workspace_bash",
    "Run a bash command with the per-paper workspace as the working directory. Use "
    "it to clone the released code, build the venv, install dependencies, and run "
    "the experiment. Every command is recorded to evidence/commands.log. Returns "
    "stdout, stderr, exit code, and wallclock duration.",
    {
        "command": {"type": "string", "description": "Bash command to run inside the workspace."},
        "timeout": {
            "type": "integer",
            "default": WORKSPACE_BASH_TIMEOUT,
            "minimum": 1,
            "maximum": WORKSPACE_BASH_MAX_TIMEOUT,
            "description": "Seconds before the command is killed.",
        },
    },
    ["command"],
)

WORKSPACE_BASH_HANDLERS = {"workspace_bash": workspace_bash}
