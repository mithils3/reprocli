"""Read-only run-directory tools for the LLM reproduction auditor.

The auditor is handed ONE agent reproduction run directory -- a collection of
``*.log`` files, output artifacts, and any code the agent wrote -- and explores
it to trace how every graded number was actually produced. These tools are
scoped to that one directory:

  - ``list_run_files`` -- list files and directories in the run dir,
  - ``read_run_file``  -- read one text file (a log, an output JSON, a script),
  - ``bash``           -- run a shell command with the run dir as the cwd
                          (grep logs, inspect outputs, run ``python3 -c ...``),
  - ``python``         -- TODO(audit-python): a real Python interpreter; stubbed
                          for now (use ``bash`` with ``python3`` instead).

``run_dir_manifest`` builds the file listing injected into the audit prompt so
the auditor knows what is there before it starts opening files.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ..config import (
    BASH_TIMEOUT,
    RUN_FILE_DEFAULT_CHARS,
    RUN_FILE_MAX_CHARS,
    RUN_MANIFEST_MAX_ENTRIES,
    function_tool,
)

SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}


def list_run_files(arguments: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    base = _resolve_within(run_dir, arguments.get("path") or ".")
    if not base["ok"]:
        return base
    target: Path = base["path"]
    if not target.exists():
        return {"ok": False, "error": f"Path does not exist in run dir: {arguments.get('path')}"}
    entries = _walk(target, run_dir, recursive=bool(arguments.get("recursive")))
    return {
        "ok": True,
        "run_dir": str(run_dir),
        "path": _rel(target, run_dir),
        "count": len(entries),
        "entries": entries[:RUN_MANIFEST_MAX_ENTRIES],
        "truncated": len(entries) > RUN_MANIFEST_MAX_ENTRIES,
    }


def read_run_file(arguments: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    resolved = _resolve_within(run_dir, arguments.get("path"))
    if not resolved["ok"]:
        return resolved
    target: Path = resolved["path"]
    if not target.is_file():
        return {"ok": False, "error": f"Not a file in run dir: {arguments.get('path')}"}
    max_chars = _bounded(arguments.get("max_chars"), RUN_FILE_DEFAULT_CHARS, RUN_FILE_MAX_CHARS)
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": True,
        "path": _rel(target, run_dir),
        "size": _size(target),
        "text": text[:max_chars],
        "truncated": len(text) > max_chars,
    }


def run_bash(arguments: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    command = str(arguments.get("command") or "").strip()
    if not command:
        return {"ok": False, "error": "Missing bash command"}
    if not run_dir.exists():
        return {"ok": False, "error": f"Run dir does not exist: {run_dir}"}
    timeout = _bounded(arguments.get("timeout"), BASH_TIMEOUT, BASH_TIMEOUT)
    try:
        proc = subprocess.run(
            ["bash", "-lc", command],
            cwd=str(run_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "command": command, "error": f"bash timed out after {timeout}s"}
    except OSError as exc:
        return {"ok": False, "command": command, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": proc.returncode == 0,
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def run_python(arguments: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    # TODO(audit-python): wire a real sandboxed Python interpreter (persistent
    # namespace, numpy/torch available for re-scoring artifacts). Until then,
    # fall back to the bash tool with `python3 -c "..."` scoped to the run dir.
    return {
        "ok": False,
        "tool": "python",
        "error": (
            "python interpreter not implemented yet (TODO(audit-python)). "
            'Run `python3 -c "..."` or a script through the bash tool instead.'
        ),
    }


AUDIT_TOOL_HANDLERS = {
    "list_run_files": list_run_files,
    "read_run_file": read_run_file,
    "bash": run_bash,
    "python": run_python,
}


AUDIT_TOOLS = [
    function_tool(
        "list_run_files",
        "List files and directories in the agent's reproduction run directory. "
        "Use it to discover the *.log, output, and code files the agent produced.",
        {
            "path": {
                "type": "string",
                "description": "Subdirectory within the run dir; omit for the run-dir root.",
            },
            "recursive": {"type": "boolean", "default": False},
        },
        [],
    ),
    function_tool(
        "read_run_file",
        "Read a text file (a log, an output JSON, or a script the agent wrote) "
        "from the run directory by relative path.",
        {
            "path": {
                "type": "string",
                "description": "File path relative to the run directory.",
            },
            "max_chars": {
                "type": "integer",
                "default": RUN_FILE_DEFAULT_CHARS,
                "minimum": 1,
                "maximum": RUN_FILE_MAX_CHARS,
            },
        },
        ["path"],
    ),
    function_tool(
        "bash",
        "Run a bash command with the agent's run directory as the working "
        "directory. Use it to grep logs, inspect outputs, or run `python3 -c "
        "...`. Returns stdout, stderr, and the exit code.",
        {
            "command": {
                "type": "string",
                "description": "Bash command to run inside the run directory.",
            },
            "timeout": {
                "type": "integer",
                "default": BASH_TIMEOUT,
                "minimum": 1,
                "maximum": BASH_TIMEOUT,
            },
        },
        ["command"],
    ),
    function_tool(
        "python",
        "Run Python over the run artifacts. NOT IMPLEMENTED YET (TODO); use the "
        "bash tool with python3 for now.",
        {"code": {"type": "string", "description": "Python source to execute."}},
        ["code"],
    ),
]


def run_dir_manifest(run_dir: Path) -> str:
    """A text listing of the run directory, injected into the audit prompt."""
    if not run_dir.exists():
        return (
            f"(No run directory found at {run_dir}. No agent reproduction run is "
            "available for this paper, so the only defensible verdict is "
            "`unverifiable` with score 0.)"
        )
    files = [e for e in _walk(run_dir, run_dir, recursive=True) if e["type"] == "file"]
    if not files:
        return f"(Run directory {run_dir} is empty; verdict `unverifiable`, score 0.)"
    shown = files[:RUN_MANIFEST_MAX_ENTRIES]
    lines = [f"AGENT RUN DIRECTORY: {run_dir}", f"{len(files)} file(s):"]
    lines += [f"  {entry['path']}  ({entry['size']} bytes)" for entry in shown]
    if len(files) > len(shown):
        lines.append(f"  ... and {len(files) - len(shown)} more")
    lines.append(
        "\nUse list_run_files, read_run_file, and bash (cwd = this run directory) "
        "to open these files and trace how every reported number was produced."
    )
    return "\n".join(lines)


def _resolve_within(run_dir: Path, rel: Any) -> dict[str, Any]:
    raw = str(rel or "").strip()
    if raw in ("", "."):
        return {"ok": True, "path": run_dir}
    if raw.startswith("/") or "\\" in raw or ".." in raw.split("/"):
        return {"ok": False, "error": f"Unsafe path: {raw}"}
    target = run_dir / raw
    try:
        root = run_dir.resolve()
        resolved = target.resolve()
    except OSError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if resolved != root and root not in resolved.parents:
        return {"ok": False, "error": f"Path escapes the run directory: {raw}"}
    return {"ok": True, "path": target}


def _walk(target: Path, run_dir: Path, *, recursive: bool) -> list[dict[str, Any]]:
    try:
        children = target.rglob("*") if recursive else target.iterdir()
        items = sorted(children, key=str)
    except OSError:
        return []
    entries = []
    for child in items:
        if any(part in SKIP_DIRS for part in child.relative_to(run_dir).parts):
            continue
        is_dir = child.is_dir()
        entries.append(
            {
                "path": _rel(child, run_dir),
                "type": "dir" if is_dir else "file",
                "size": 0 if is_dir else _size(child),
            }
        )
    return entries


def _rel(path: Path, run_dir: Path) -> str:
    try:
        return str(path.relative_to(run_dir))
    except ValueError:
        return str(path)


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _bounded(value: Any, default: int, maximum: int) -> int:
    if value in (None, ""):
        return default
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default
