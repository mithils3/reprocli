"""Path-confined write tools for the reproduction agent.

The agent *reads* files through ``workspace_bash`` (``grep -n`` / ``sed -n`` /
``cat`` -- targeted, line-numbered, and far cheaper than dumping whole files into
context), so this module ships only the mutating ops: ``write_file`` and
``apply_patch``.

Adapted from ``run_dir_tools._resolve_within``: every path the agent writes must
resolve inside one of the episode's writable roots -- ``workspace`` (the editable
clone) and ``evidence``; the ``reference/`` copy is never writable. These are a
subset of the roots the Apptainer sandbox (``sandbox.py``) binds read-write — the file
tools stay tight to durable source/evidence, while bulk ``/tmp`` scratch is
shell-driven, not a file-tool path — so the tool-layer check is a strict inner
boundary nested inside the OS sandbox.

Relative paths resolve against the workspace (the same cwd ``workspace_bash`` runs
in); absolute paths must still fall within an allowed root. ``..`` segments and NUL
bytes are rejected outright, and ``resolve()`` canonicalizes symlinks before the
containment check, so traversal, symlink escapes, and writes outside the bundle are
all rejected before any I/O happens. ``apply_patch`` additionally confines every
rename/copy target, not just the diff's ``+++``/``---`` headers.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from reprocli_vllm.config.config import RUN_FILE_WRITE_MAX_CHARS, function_tool

from reprocli_repro.context import ExecutionContext
from reprocli_repro import evidence


def write_file(arguments: dict[str, Any], ctx: ExecutionContext) -> dict[str, Any]:
    resolved = _resolve(ctx, arguments.get("path"), writable=True)
    if not resolved["ok"]:
        return resolved
    target: Path = resolved["path"]
    if target.is_dir():
        return {"ok": False, "error": f"Path is a directory: {arguments.get('path')}"}
    content = arguments.get("content")
    if not isinstance(content, str):
        return {"ok": False, "error": "Missing 'content' string to write."}
    if len(content) > RUN_FILE_WRITE_MAX_CHARS:
        return {"ok": False, "error": f"Content exceeds {RUN_FILE_WRITE_MAX_CHARS} chars."}
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": True, "path": str(target), "bytes_written": len(content.encode("utf-8"))}


def apply_patch(arguments: dict[str, Any], ctx: ExecutionContext) -> dict[str, Any]:
    workspace = ctx.workspace
    if workspace is None or not Path(workspace).is_dir():
        return {"ok": False, "error": "No workspace directory for this episode."}
    diff = arguments.get("diff") or arguments.get("patch")
    if not isinstance(diff, str) or not diff.strip():
        return {"ok": False, "error": "Missing unified-diff 'diff' string to apply."}
    targets, strip = _patch_targets(diff)
    if not targets:
        return {"ok": False, "error": "Could not find any '+++'/'---' file headers in the diff."}
    for rel in targets:
        confined = _resolve(ctx, rel, writable=True)
        if not confined["ok"]:
            return {"ok": False, "error": f"Patch touches a confined path: {confined.get('error')}"}
    saved = evidence.save_patch(ctx.evidence, diff, name=Path(targets[0]).name) if ctx.evidence else None
    result = _git_apply(diff, Path(workspace), strip)
    if ctx.evidence is not None:
        evidence.log_command(
            ctx.evidence, f"git apply (-p{strip}) {', '.join(targets)}",
            returncode=result.get("returncode"), cwd=workspace,
        )
    result["patch_file"] = str(saved) if saved else None
    result["files"] = targets
    return result


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def _resolve(ctx: ExecutionContext, raw: Any, *, writable: bool) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        return {"ok": False, "error": "Missing path."}
    if "\\" in text or "\x00" in text:
        return {"ok": False, "error": f"Unsafe path: {text!r}"}
    if ".." in Path(text).parts:
        return {"ok": False, "error": f"Path contains a '..' segment: {text}"}
    roots = _roots(ctx, writable=writable)
    if not roots:
        return {"ok": False, "error": "Episode has no workspace directory set."}
    base = Path(text) if text.startswith("/") else Path(ctx.workspace or roots[0]) / text
    try:
        resolved = base.resolve()
    except OSError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    for root in roots:
        rootr = root.resolve()
        if resolved == rootr or rootr in resolved.parents:
            return {"ok": True, "path": resolved, "root": str(rootr)}
    where = "writable" if writable else "readable"
    return {"ok": False, "error": f"Path escapes the episode's {where} roots: {text}"}


def _roots(ctx: ExecutionContext, *, writable: bool) -> list[Path]:
    # ``write_file``/``apply_patch`` only ever write durable source/evidence, so they
    # stay tight to workspace + evidence (a subset of the sandbox's rw binds; bulk
    # /tmp scratch is shell-driven, not a file-tool path). ``writable=False``
    # (reference readable too) is retained for callers that only inspect paths.
    candidates = [ctx.workspace, ctx.evidence] if writable else [ctx.workspace, ctx.reference, ctx.evidence]
    return [Path(p) for p in candidates if p is not None]


# ``git diff`` rename/copy metadata can move a file to a path the ``+++``/``---``
# headers never name (a pure rename has no content hunk), so we confine these too.
_MOVE_PREFIXES = ("rename from ", "rename to ", "copy from ", "copy to ")


def _patch_targets(diff: str) -> tuple[list[str], int]:
    targets: list[str] = []
    strip = 0
    for line in diff.splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            token = line[4:].strip().split("\t")[0]
        elif any(line.startswith(p) for p in _MOVE_PREFIXES):
            token = line.split(" ", 2)[2].strip()
        else:
            continue
        if token in ("/dev/null", ""):
            continue
        if token[:2] in ("a/", "b/"):
            strip = 1
            token = token[2:]
        if token not in targets:
            targets.append(token)
    return targets, strip


def _git_apply(diff: str, workspace: Path, strip: int) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["git", "apply", f"-p{strip}", "-"],
            input=diff if diff.endswith("\n") else diff + "\n",
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stderr": proc.stderr,
    }


FILE_TOOLS = [
    function_tool(
        "write_file",
        "Write (or overwrite) a UTF-8 text file in the workspace or evidence dir. "
        "The reference copy is read-only; writes outside the bundle are rejected.",
        {
            "path": {"type": "string", "description": "File path (relative to workspace, or absolute within the bundle)."},
            "content": {"type": "string", "description": "Full file contents to write."},
        },
        ["path", "content"],
    ),
    function_tool(
        "apply_patch",
        "Apply a unified diff to file(s) in the workspace with `git apply`. The diff "
        "is saved verbatim under evidence/patches/. Every file the diff touches must "
        "stay inside the workspace.",
        {
            "diff": {"type": "string", "description": "A unified diff (git or plain). File headers must point inside the workspace."},
        },
        ["diff"],
    ),
]

FILE_TOOL_HANDLERS = {
    "write_file": write_file,
    "apply_patch": apply_patch,
}
