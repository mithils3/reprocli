"""Workspace-scoped shell for the reproduction agent.

The agent does its real work here: ``git clone`` the released code into the
workspace, install deps into the per-paper venv, run the experiment. The shell's
cwd is pinned to ``ctx.workspace`` (the same root the file tools confine to) and
every command is appended to ``evidence/commands.log`` so the auditor can re-trace
exactly what ran. This mirrors the auditor's ``bash`` posture (cwd-scoped, no hard
jail); the security boundary for untrusted paper code is the Phase-8 Apptainer
wrap, not this tool.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from reprocli_vllm.config.config import RUN_FILE_DEFAULT_CHARS, function_tool

from reprocli_repro.context import ExecutionContext
from reprocli_repro import evidence

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
    timeout = _bounded(arguments.get("timeout"), WORKSPACE_BASH_TIMEOUT, WORKSPACE_BASH_MAX_TIMEOUT)
    start = time.time()
    try:
        proc = subprocess.run(
            ["bash", "-lc", command],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        _log(ctx, command, None, workspace, time.time() - start)
        return {"ok": False, "command": command, "error": f"bash timed out after {timeout}s"}
    except OSError as exc:
        return {"ok": False, "command": command, "error": f"{type(exc).__name__}: {exc}"}
    duration = time.time() - start
    _log(ctx, command, proc.returncode, workspace, duration)
    return {
        "ok": proc.returncode == 0,
        "command": command,
        "returncode": proc.returncode,
        "duration_s": round(duration, 1),
        "stdout": proc.stdout[:RUN_FILE_DEFAULT_CHARS],
        "stderr": proc.stderr[:RUN_FILE_DEFAULT_CHARS],
        "truncated": len(proc.stdout) > RUN_FILE_DEFAULT_CHARS or len(proc.stderr) > RUN_FILE_DEFAULT_CHARS,
    }


def _log(ctx: ExecutionContext, command: str, rc: int | None, cwd: Path, duration: float) -> None:
    if ctx.evidence is not None:
        evidence.log_command(ctx.evidence, command, returncode=rc, cwd=cwd, duration_s=duration)


def _bounded(value: Any, default: int, maximum: int) -> int:
    if value in (None, ""):
        return default
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


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
