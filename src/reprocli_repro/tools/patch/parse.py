"""Parse the two accepted patch formats into the shared :class:`FileOp` model.

* **V4A** -- Codex's ``*** Begin Patch`` / ``*** Update File:`` envelope with
  context-anchored ``@@`` hunks and no line numbers
  (``codex-rs/prompts/templates/apply_patch_tool_instructions.md``).
* **Unified diff** -- ordinary ``--- / +++ / @@ -a,b +c,d @@`` output. We keep
  the body lines but **drop the line numbers**, so it is applied with the same
  forgiving context matcher as V4A rather than a strict ``git apply``.
"""

from __future__ import annotations

from reprocli_repro.tools.patch.engine import FileOp, PatchError, UpdateChunk

_BEGIN = "*** Begin Patch"
_END = "*** End Patch"


def detect_format(text: str) -> str | None:
    if _BEGIN in text:
        return "v4a"
    for line in text.splitlines():
        if line.startswith(("--- ", "+++ ", "@@ ", "diff --git ")) or line == "@@":
            return "unified"
    return None


def parse_patch(text: str) -> list[FileOp]:
    fmt = detect_format(text)
    if fmt == "v4a":
        return _parse_v4a(text)
    if fmt == "unified":
        return _parse_unified(text)
    raise PatchError(
        "Unrecognized patch format. Provide a '*** Begin Patch' V4A patch or a unified diff."
    )


def peek_paths(text: str) -> list[str]:
    """Best-effort target paths for evidence naming; never raises."""
    try:
        return [op.path for op in parse_patch(text)]
    except Exception:
        return []


# --------------------------------------------------------------------------- #
# V4A
# --------------------------------------------------------------------------- #
def _parse_v4a(text: str) -> list[FileOp]:
    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == _BEGIN)
    except StopIteration:
        raise PatchError("The first line of the patch must be '*** Begin Patch'") from None
    ops: list[FileOp] = []
    cur: FileOp | None = None
    chunk: UpdateChunk | None = None

    for ln in lines[start + 1:]:
        if ln.strip() == _END:
            break
        if ln.startswith("*** Add File: "):
            cur = FileOp(kind="add", path=ln[len("*** Add File: "):].strip())
            ops.append(cur)
            chunk = None
        elif ln.startswith("*** Delete File: "):
            cur = FileOp(kind="delete", path=ln[len("*** Delete File: "):].strip())
            ops.append(cur)
            chunk = None
        elif ln.startswith("*** Update File: "):
            cur = FileOp(kind="update", path=ln[len("*** Update File: "):].strip())
            ops.append(cur)
            chunk = None
        elif ln.startswith("*** Move to: "):
            if cur is None or cur.kind != "update":
                raise PatchError("'*** Move to:' must follow an '*** Update File:' header")
            cur.move_to = ln[len("*** Move to: "):].strip()
        elif ln == "*** End of File":
            if chunk is not None:
                chunk.is_end_of_file = True
        elif cur is None:
            raise PatchError(f"Patch body before any file header: {ln!r}")
        elif cur.kind == "add":
            if not ln.startswith("+"):
                raise PatchError(f"Add File hunk lines must start with '+': {ln!r}")
            cur.add_lines.append(ln[1:])
        elif cur.kind == "update":
            if ln == "@@" or ln.startswith("@@ "):
                chunk = UpdateChunk(change_context=ln[3:] if ln.startswith("@@ ") else None)
                cur.chunks.append(chunk)
            else:
                if chunk is None:
                    chunk = UpdateChunk()
                    cur.chunks.append(chunk)
                _append_body(chunk, ln)
        else:  # delete file: stray body lines are ignored
            continue
    if not ops:
        raise PatchError("Patch contained no file operations.")
    return ops


def _append_body(chunk: UpdateChunk, ln: str) -> None:
    if ln.startswith("+"):
        chunk.new_lines.append(ln[1:])
    elif ln.startswith("-"):
        chunk.old_lines.append(ln[1:])
    elif ln.startswith(" "):
        chunk.old_lines.append(ln[1:])
        chunk.new_lines.append(ln[1:])
    elif ln == "":
        chunk.old_lines.append("")
        chunk.new_lines.append("")
    else:
        raise PatchError(
            f"Unexpected line in update hunk: {ln!r}. Every line must start with "
            "' ' (context), '+' (added), or '-' (removed)."
        )


# --------------------------------------------------------------------------- #
# Unified diff
# --------------------------------------------------------------------------- #
def _hdr_path(token: str) -> str:
    return token.strip().split("\t")[0].strip().strip('"')


def _parse_unified(text: str) -> list[FileOp]:
    lines = text.split("\n")
    ops: list[FileOp] = []
    cur: FileOp | None = None
    chunk: UpdateChunk | None = None
    pending_old: str | None = None
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("--- "):
            pending_old = _hdr_path(ln[4:])
            chunk = cur = None
        elif ln.startswith("+++ "):
            new_path = _hdr_path(ln[4:])
            cur = _open_file_op(pending_old, new_path)
            ops.append(cur)
            chunk = None
            pending_old = None
        elif ln.startswith("@@"):
            if cur is not None and cur.kind == "update":
                chunk = UpdateChunk()
                cur.chunks.append(chunk)
        elif cur is None:
            pass  # preamble / diff --git / index / mode lines
        elif ln.startswith("\\"):
            pass  # "\ No newline at end of file"
        elif cur.kind == "add":
            if ln.startswith("+"):
                cur.add_lines.append(ln[1:])
        elif cur.kind == "delete":
            pass
        elif chunk is not None and ln[:1] in ("+", "-", " "):
            _append_body(chunk, ln)
        elif chunk is not None and ln == "":
            _append_body(chunk, ln)
        i += 1
    if not ops:
        raise PatchError("Patch contained no unified-diff file headers.")
    return ops


def _open_file_op(old_path: str | None, new_path: str) -> FileOp:
    if old_path == "/dev/null":
        return FileOp(kind="add", path=new_path)
    if new_path == "/dev/null":
        return FileOp(kind="delete", path=old_path or new_path)
    return FileOp(kind="update", path=new_path)
