"""Suffix-search + mismatch-hint helpers for ``edit_file``.

The diff-application tool this replaced failed 68% of the time in sweeps -- mostly
because the agent clones the paper's repo *into* the workspace (``workspace/<repo>/src/x.py``)
and then addresses files by the repo-relative path it sees from inside the clone
(``src/x.py``), which resolves against the workspace root and misses. Rather than
teach every caller the clone layout, :func:`locate_by_suffix` walks the workspace
tree looking for exactly one file whose path ends with the given relative path;
``edit_file`` (``tools/files.py``) falls back to it only once a direct resolve
comes up empty, and only for genuinely relative paths.

:func:`mismatch_hint` mirrors the recovery-oriented diagnostics the old patch
engine gave on a context miss (see the deleted ``tools/patch/diagnose.py``):
when ``old_string`` is not found verbatim, quote the file's actual text near the
closest match so the next attempt copies what is really on disk instead of
resending the same guess.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from reprocli_repro.context import ExecutionContext
from reprocli_repro.sandbox import CONTAINER_RUN

_SKIP_DIRS = {"venv", ".venv", "node_modules", "__pycache__"}
_MAX_SUFFIX_MATCHES = 10
_HINT_PAD = 3  # file lines quoted on each side of the closest match


def locate_by_suffix(workspace: Path, rel: Path) -> list[Path]:
    """Files under ``workspace`` whose trailing path components equal ``rel``'s.

    Skips ``.git``, any other dot-directory, and common dependency dirs so a
    vendored copy or a venv's site-packages never shadows the real source file.
    Capped at ``_MAX_SUFFIX_MATCHES`` hits -- this only runs on the failure path
    of a direct resolve, but a runaway workspace tree should still bound the cost.
    """
    parts = rel.parts
    hits: list[Path] = []
    for hit in workspace.rglob(rel.name):
        if not hit.is_file():
            continue
        ancestors = hit.relative_to(workspace).parts[:-1]
        if any(part == ".git" or part.startswith(".") or part in _SKIP_DIRS for part in ancestors):
            continue
        if hit.parts[-len(parts):] == parts:
            hits.append(hit)
            if len(hits) >= _MAX_SUFFIX_MATCHES:
                break
    return hits


def mismatch_hint(content: str, old_string: str) -> str:
    """Recovery hint for an ``old_string`` that did not match ``content`` verbatim.

    Cheapest check first: if every line matches once leading/trailing whitespace
    is stripped, the drift is almost certainly just indentation -- say so
    directly. Otherwise anchor on ``old_string``'s first non-blank line and fuzzy-
    match it against the file's lines, quoting the real text ``_HINT_PAD`` lines
    on each side of the closest hit.
    """
    old_lines = old_string.splitlines()
    file_lines = content.splitlines()
    if not old_lines or not file_lines:
        return ""
    stripped_old = "\n".join(line.strip() for line in old_lines)
    stripped_file = "\n".join(line.strip() for line in file_lines)
    if stripped_old and stripped_old in stripped_file:
        return (
            "The text matches once each line's leading/trailing whitespace is "
            "stripped -- only indentation differs. Copy old_string with the "
            "file's exact whitespace."
        )
    anchor = next((line for line in old_lines if line.strip()), None)
    if anchor is None:
        return ""
    close = difflib.get_close_matches(anchor, file_lines, n=1, cutoff=0.5)
    if not close:
        return ""
    idx = file_lines.index(close[0])
    lo, hi = max(0, idx - _HINT_PAD), min(len(file_lines), idx + _HINT_PAD + 1)
    quoted = "\n".join(f"{i + 1:>6}\t{file_lines[i]}" for i in range(lo, hi))
    return f"Closest match is near line {idx + 1} -- the file's actual text there (copy it exactly):\n{quoted}"


def resolve_by_suffix(ctx: ExecutionContext, raw_path: Any) -> dict[str, Any] | None:
    """Suffix-search fallback for a relative path that did not resolve directly.

    Absolute paths join in one case: the prompt teaches the container layout, so a
    miss often arrives as ``/repro/workspace/src/x.py`` (or the host equivalent) --
    the same repo-relative confusion with the workspace prefix stapled on. Strip
    that prefix and search the remainder; any other absolute path that is missing
    is just missing, so return ``None``. Otherwise the result is a dict describing
    the outcome: ``{"ok": True, "path": Path}`` on exactly one hit, or
    ``{"ok": False, "result": <tool error dict>, "reason": <str>}`` on zero or
    multiple hits, so the caller can log the failure before returning it.
    """
    text = str(raw_path or "").strip()
    if not text or ctx.workspace is None:
        return None
    if text.startswith("/"):
        for prefix in (CONTAINER_RUN + "/workspace", str(Path(ctx.workspace))):
            if text.startswith(prefix + "/"):
                text = text[len(prefix) + 1 :]
                break
        else:
            return None
    hits = locate_by_suffix(Path(ctx.workspace), Path(text))
    if len(hits) == 1:
        return {"ok": True, "path": hits[0]}
    if len(hits) > 1:
        shown = ", ".join(str(h) for h in hits[:5])
        return {
            "ok": False,
            "reason": "ambiguous",
            "result": {"ok": False, "error": f"Ambiguous path '{raw_path}' -- matches: {shown}."},
        }
    return {
        "ok": False,
        "reason": "not found",
        "result": {
            "ok": False,
            "error": (
                f"File not found: {raw_path}. Paths are relative to the workspace root -- "
                "the repo is likely cloned into a subdirectory; check with workspace_bash `ls`."
            ),
        },
    }
