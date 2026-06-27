"""Apply a V4A or unified-diff patch to confined workspace files.

The agent reads files at the short in-container paths the sandbox remaps the
episode onto (``/repro/workspace/...``) and routinely bakes those -- or a bare
``repro/workspace/...`` / ``a/`` / ``b/`` prefix -- into patch headers. The old
``git apply -p{n}`` path could not recover from that (the strip level had to be
exactly right), so a perfectly good edit failed with "No such file or directory".

Here we instead generate prefix-stripped *candidates* for every header path and
keep the one that actually resolves (and, for edits, exists) inside the
workspace, then apply the hunks with the forgiving context matcher in
:mod:`engine`. Confinement is delegated to the ``confine`` callback so all
security checks stay in one place (``tools/files.py``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from reprocli_repro.tools.patch.engine import PatchError, derive_new_contents
from reprocli_repro.tools.patch.parse import parse_patch, peek_paths

__all__ = ["apply_patch_text", "peek_paths"]

Confine = Callable[[str], dict]

_PREFIXES = ("/repro/workspace/", "repro/workspace/", "/repro/", "workspace/", "./")


def _canonical(raw: str) -> str:
    """Strip the prefixes the agent tends to bake in, yielding a workspace-relative path."""
    p = raw.strip().strip('"').strip("'")
    for ab in ("a/", "b/"):
        if p.startswith(ab):
            p = p[len(ab):]
            break
    changed = True
    while changed:
        changed = False
        for pref in _PREFIXES:
            if p.startswith(pref):
                p = p[len(pref):]
                changed = True
    return p


def _candidates(raw: str) -> list[str]:
    p = raw.strip().strip('"').strip("'")
    out: list[str] = []
    for cand in (_canonical(p), p[2:] if p[:2] in ("a/", "b/") else p, p):
        if cand and cand not in out:
            out.append(cand)
    return out


def _resolve_op_path(raw: str, must_exist: bool, *, confine: Confine) -> dict:
    confine_errors: list[str] = []
    first_ok: dict | None = None
    for cand in _candidates(raw):
        r = confine(cand)
        if not r.get("ok"):
            confine_errors.append(str(r.get("error")))
            continue
        if first_ok is None:
            first_ok = r
        if not must_exist or Path(r["path"]).exists():
            return r
    if first_ok is not None:
        if must_exist:
            return {"ok": False, "error": f"Patch target does not exist in workspace: {raw}"}
        return first_ok
    return {"ok": False, "error": f"Patch touches a confined path: {confine_errors[0] if confine_errors else raw}"}


def apply_patch_text(text: str, *, confine: Confine) -> dict[str, Any]:
    """Parse and atomically apply ``text`` (V4A or unified diff). No writes happen
    unless every hunk resolves, so a mid-patch failure leaves the tree untouched."""
    try:
        ops = parse_patch(text)
    except PatchError as exc:
        return {"ok": False, "error": str(exc)}

    plan: dict[Path, tuple[str, str | None]] = {}  # path -> ("write", content) | ("delete", None)
    cache: dict[Path, str] = {}
    for op in ops:
        if op.kind == "add":
            r = _resolve_op_path(op.path, False, confine=confine)
            if not r["ok"]:
                return r
            target = Path(r["path"])
            content = "".join(line + "\n" for line in op.add_lines)
            plan[target] = ("write", content)
            cache[target] = content
        elif op.kind == "delete":
            r = _resolve_op_path(op.path, True, confine=confine)
            if not r["ok"]:
                return r
            plan[Path(r["path"])] = ("delete", None)
        else:  # update
            r = _resolve_op_path(op.path, True, confine=confine)
            if not r["ok"]:
                return r
            target = Path(r["path"])
            original = cache.get(target)
            if original is None:
                try:
                    # newline="" keeps \r\n intact so derive_new_contents can detect
                    # and restore the file's line endings (read_text would collapse them).
                    with open(target, encoding="utf-8", newline="") as fh:
                        original = fh.read()
                except OSError as exc:
                    return {"ok": False, "error": f"Failed to read {op.path}: {type(exc).__name__}: {exc}"}
            try:
                new_content = derive_new_contents(original, op.path, op.chunks)
            except PatchError as exc:
                return {"ok": False, "error": str(exc)}
            if op.move_to:
                rr = _resolve_op_path(op.move_to, False, confine=confine)
                if not rr["ok"]:
                    return rr
                plan[target] = ("delete", None)
                dest = Path(rr["path"])
                plan[dest] = ("write", new_content)
                cache[dest] = new_content
            else:
                plan[target] = ("write", new_content)
                cache[target] = new_content

    return _commit(plan)


def _commit(plan: dict[Path, tuple[str, str | None]]) -> dict[str, Any]:
    added, modified, deleted = [], [], []
    for path, (action, _) in plan.items():
        if action == "delete":
            if path.exists():
                deleted.append(path)
        else:
            (modified if path.exists() else added).append(path)
    try:
        for path, (action, content) in plan.items():
            if action == "write":
                path.parent.mkdir(parents=True, exist_ok=True)
                # newline="" so a restored \r\n is written through untranslated.
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(content or "")
            elif path.exists() or path.is_symlink():
                path.unlink()
    except OSError as exc:
        return {"ok": False, "error": f"Write failed: {type(exc).__name__}: {exc}"}

    summary = ["Success. Updated the following files:"]
    summary += [f"A {p}" for p in added] + [f"M {p}" for p in modified] + [f"D {p}" for p in deleted]
    return {
        "ok": True,
        "files": [str(p) for p in (*added, *modified, *deleted)],
        "summary": "\n".join(summary),
    }
