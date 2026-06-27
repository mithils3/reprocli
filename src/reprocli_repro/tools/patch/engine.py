"""Fuzzy, line-number-free patch application.

A faithful Python port of OpenAI Codex's ``apply_patch`` engine
(``codex-rs/apply-patch/src/{seek_sequence,lib}.rs``): hunks carry **no line
numbers** and are located by context with progressively looser matching
(exact -> trailing-whitespace -> all-whitespace -> unicode-folded), applied
forward with a monotonic cursor and committed in reverse order so earlier
edits don't shift the offsets of later ones.

This replaces the old ``git apply -p{n}`` path, which demanded both exact
context *and* the exact ``-p`` strip level -- the latter is what made
workspace-prefixed diff headers (e.g. ``repro/workspace/x/y.py``) fail with
"No such file or directory" even though the file was right there.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class PatchError(ValueError):
    """A model-friendly patch parse/apply failure (message is shown to the agent)."""


@dataclass
class UpdateChunk:
    """One context-anchored edit within a file (a unified ``@@`` hunk or a V4A chunk)."""

    change_context: str | None = None
    old_lines: list[str] = field(default_factory=list)
    new_lines: list[str] = field(default_factory=list)
    is_end_of_file: bool = False


@dataclass
class FileOp:
    """A single add / update / delete against one path (update may also rename)."""

    kind: str  # "add" | "update" | "delete"
    path: str
    move_to: str | None = None
    add_lines: list[str] = field(default_factory=list)
    chunks: list[UpdateChunk] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Unicode folding for the most permissive match pass (mirrors seek_sequence.rs)
# --------------------------------------------------------------------------- #
_FOLD: dict[int, str] = {}
for _c in (0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212):
    _FOLD[_c] = "-"
for _c in (0x2018, 0x2019, 0x201A, 0x201B):
    _FOLD[_c] = "'"
for _c in (0x201C, 0x201D, 0x201E, 0x201F):
    _FOLD[_c] = '"'
for _c in (0x00A0, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007,
           0x2008, 0x2009, 0x200A, 0x202F, 0x205F, 0x3000):
    _FOLD[_c] = " "


def _normalise(s: str) -> str:
    return s.strip().translate(_FOLD)


def seek_sequence(
    lines: list[str], pattern: list[str], start: int, eof: bool
) -> int | None:
    """Find ``pattern`` within ``lines`` at or after ``start``; return its start index.

    Four passes of decreasing strictness, first match wins. When ``eof`` is set the
    search is anchored at the end of the file first (for hunks that match a file's
    tail). Port of ``seek_sequence.rs``.
    """
    if not pattern:
        return start
    if len(pattern) > len(lines):
        return None
    plen = len(pattern)
    last = len(lines) - plen
    search_start = last if (eof and len(lines) >= plen) else start

    def _scan(key) -> int | None:
        for i in range(search_start, last + 1):
            if all(key(lines[i + j]) == key(pattern[j]) for j in range(plen)):
                return i
        return None

    for key in (lambda x: x, str.rstrip, str.strip, _normalise):
        hit = _scan(key)
        if hit is not None:
            return hit
    return None


def _miss(lines: list[str], pattern: list[str], path: str, start: int) -> str:
    """A recovery-oriented match-failure message (lazy import breaks the cycle)."""
    from reprocli_repro.tools.patch.diagnose import describe_miss

    return describe_miss(lines, pattern, path, start, seek=seek_sequence)


def compute_replacements(
    original_lines: list[str], path: str, chunks: list[UpdateChunk]
) -> list[tuple[int, int, list[str]]]:
    """Resolve each chunk to a ``(start, old_len, new_lines)`` replacement.

    The cursor advances monotonically so chunks are matched in order; a trailing
    empty ``old_lines`` element (the file's final newline) is retried-without on
    miss. Port of ``compute_replacements`` in ``lib.rs``.
    """
    replacements: list[tuple[int, int, list[str]]] = []
    line_index = 0
    for chunk in chunks:
        if chunk.change_context is not None:
            idx = seek_sequence(original_lines, [chunk.change_context], line_index, False)
            if idx is None:
                raise PatchError(_miss(original_lines, [chunk.change_context], path, line_index))
            line_index = idx + 1

        if not chunk.old_lines:
            insertion_idx = (
                len(original_lines) - 1
                if original_lines and original_lines[-1] == ""
                else len(original_lines)
            )
            replacements.append((insertion_idx, 0, list(chunk.new_lines)))
            continue

        pattern = chunk.old_lines
        new_slice = chunk.new_lines
        found = seek_sequence(original_lines, pattern, line_index, chunk.is_end_of_file)
        if found is None and pattern and pattern[-1] == "":
            pattern = pattern[:-1]
            if new_slice and new_slice[-1] == "":
                new_slice = new_slice[:-1]
            found = seek_sequence(original_lines, pattern, line_index, chunk.is_end_of_file)
        if found is None:
            raise PatchError(_miss(original_lines, chunk.old_lines, path, line_index))
        replacements.append((found, len(pattern), list(new_slice)))
        line_index = found + len(pattern)

    replacements.sort(key=lambda r: r[0])
    return replacements


def apply_replacements(
    lines: list[str], replacements: list[tuple[int, int, list[str]]]
) -> list[str]:
    """Apply replacements in descending index order so earlier edits don't shift later."""
    out = list(lines)
    for start_idx, old_len, new_segment in reversed(replacements):
        for _ in range(old_len):
            if start_idx < len(out):
                del out[start_idx]
        for offset, new_line in enumerate(new_segment):
            out.insert(start_idx + offset, new_line)
    return out


def derive_new_contents(original: str, path: str, chunks: list[UpdateChunk]) -> str:
    """Return the new file text after applying ``chunks`` to ``original``.

    Patch context lines never carry a ``\\r``, so a uniformly-CRLF file is
    normalised to ``\\n`` for matching and restored to ``\\r\\n`` on the way out;
    without this the ``split('\\n')`` round-trip left a stray ``\\r`` on every
    untouched line and dropped it from edited ones, silently mangling endings.
    """
    crlf = "\r\n" in original and "\n" not in original.replace("\r\n", "")
    work = original.replace("\r\n", "\n") if crlf else original
    lines = work.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    replacements = compute_replacements(lines, path, chunks)
    new_lines = apply_replacements(lines, replacements)
    if not (new_lines and new_lines[-1] == ""):
        new_lines.append("")
    result = "\n".join(new_lines)
    return result.replace("\n", "\r\n") if crlf else result
