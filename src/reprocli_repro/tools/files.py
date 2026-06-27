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

The agent works against the short in-container paths the sandbox remaps the episode
dirs onto (``/repro/workspace`` etc.); since these tools do real *host* I/O,
``_to_host`` first translates a leading ``/repro`` back to the host run dir. Relative
paths then resolve against the workspace (the same cwd ``workspace_bash`` runs in), and
host-absolute paths must still fall within an allowed root. ``..`` segments and NUL
bytes are rejected outright, and ``resolve()`` canonicalizes symlinks before the
containment check, so traversal, symlink escapes, and writes outside the bundle are
all rejected before any I/O happens.

``apply_patch`` delegates parsing/application to :mod:`reprocli_repro.tools.patch`
(a port of Codex's context-matching engine) and hands it ``_resolve`` as the
confinement callback, so every file the patch touches -- including rename targets --
passes the same boundary check before any write.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reprocli_vllm.config.config import RUN_FILE_WRITE_MAX_CHARS, function_tool

from reprocli_repro.context import ExecutionContext
from reprocli_repro import evidence
from reprocli_repro.sandbox import CONTAINER_RUN
from reprocli_repro.tools.patch import apply_patch_text, peek_paths


def write_file(arguments: dict[str, Any], ctx: ExecutionContext) -> dict[str, Any]:
    raw_path = _first(arguments, "path", "file_path", "filename", "file")
    resolved = _resolve(ctx, raw_path, writable=True)
    if not resolved["ok"]:
        return resolved
    target: Path = resolved["path"]
    if target.is_dir():
        return {"ok": False, "error": f"Path is a directory: {raw_path}"}
    content = _first(arguments, "content", "text", "contents", "data")
    if not isinstance(content, str):
        return {"ok": False, "error": "Missing 'content' string to write."}
    if len(content) > RUN_FILE_WRITE_MAX_CHARS:
        return {
            "ok": False,
            "error": (
                f"Content is {len(content)} chars, over the {RUN_FILE_WRITE_MAX_CHARS} limit. "
                "Write the file in pieces (apply_patch to append) or generate it with a "
                "workspace_bash heredoc instead."
            ),
        }
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
    diff = _first(arguments, "diff", "patch", "patch_text", "input", "content")
    if not isinstance(diff, str) or not diff.strip():
        return {"ok": False, "error": "Missing patch 'diff' string to apply."}
    diff = _unescape_patch(diff)

    peeked = peek_paths(diff)
    name = Path(peeked[0]).name if peeked else "patch.diff"
    saved = evidence.save_patch(ctx.evidence, diff, name=name) if ctx.evidence else None

    result = apply_patch_text(diff, confine=lambda p: _resolve(ctx, p, writable=True))
    if ctx.evidence is not None:
        evidence.log_command(
            ctx.evidence,
            f"apply_patch {', '.join(result.get('files') or peeked)}",
            returncode=0 if result.get("ok") else 1,
            cwd=workspace,
        )
    result["patch_file"] = str(saved) if saved else None
    return result


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def _first(arguments: dict[str, Any], *keys: str) -> Any:
    """First present, non-empty value among ``keys`` -- absorbs models that name
    the argument ``file_path``/``text``/``patch`` instead of the schema's name."""
    for key in keys:
        val = arguments.get(key)
        if val not in (None, ""):
            return val
    return None


def _unescape_patch(text: str) -> str:
    """Recover a patch that arrived JSON-escaped: one physical line whose newlines
    are literal ``\\n``. Only fires when there are no real newlines, so a genuine
    multi-line patch is never touched."""
    if "\n" not in text and "\\n" in text:
        return text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
    return text


def _to_host(ctx: ExecutionContext, text: str) -> str:
    """Map an in-container ``/repro/...`` path back to the host run dir for host-side I/O.

    The agent works against the short, remapped container paths (``sandbox.py``), but these
    tools do real host I/O, so ``/repro/workspace/x`` → ``<run_dir>/workspace/x`` (and the
    run dir is the host workspace's parent — see ``inputs.RunPaths``). Host-absolute and
    relative paths are returned unchanged; the containment check below still bounds them.
    """
    if ctx.workspace is None:
        return text
    if text == CONTAINER_RUN or text.startswith(CONTAINER_RUN + "/"):
        run_dir = Path(ctx.workspace).parent
        rel = text[len(CONTAINER_RUN):].lstrip("/")
        return str(run_dir / rel) if rel else str(run_dir)
    return text


def _resolve(ctx: ExecutionContext, raw: Any, *, writable: bool) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        return {"ok": False, "error": "Missing path."}
    if "\\" in text or "\x00" in text:
        return {"ok": False, "error": f"Unsafe path: {text!r}"}
    text = _to_host(ctx, text)
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
        "Edit file(s) in the workspace by applying a patch. Hunks are located by "
        "matching their context (not line numbers) and tolerate minor whitespace "
        "drift, so you do not need exact line numbers. Two formats are accepted:\n"
        "(1) V4A (preferred):\n"
        "*** Begin Patch\n"
        "*** Update File: path/to/file.py\n"
        "@@ optional_anchor_line\n"
        " unchanged context line\n"
        "-removed line\n"
        "+added line\n"
        "*** End Patch\n"
        "(use '*** Add File: p' then '+'-prefixed lines to create, '*** Delete File: p' "
        "to delete, '*** Move to: p' right after an Update header to rename);\n"
        "(2) a standard unified diff (--- / +++ / @@).\n"
        "Paths are relative to the workspace root (e.g. 'pkg/mod.py'); a leading "
        "'/repro/workspace/', 'a/' or 'b/' is tolerated. Every file touched must stay "
        "inside the workspace. The patch is saved verbatim under evidence/patches/.\n"
        "If a hunk fails to match, the error quotes the file's actual text near the "
        "closest line -- copy that text into your context lines instead of resending "
        "the same patch.",
        {
            "diff": {"type": "string", "description": "The patch text: a V4A '*** Begin Patch' block or a unified diff."},
        },
        ["diff"],
    ),
]

FILE_TOOL_HANDLERS = {
    "write_file": write_file,
    "apply_patch": apply_patch,
}
