"""Explain a failed hunk match so the agent can fix it, not just retry.

``seek_sequence`` returning ``None`` used to surface as a bare "Failed to find
expected lines", which sends the model into re-emitting the *same* patch. Given
the file and the hunk that missed, :func:`describe_miss` pinpoints the most
likely cause -- lines an earlier hunk already consumed, context that drifted in
indentation, or simply the wrong file -- and quotes the real text near the
closest match so the next attempt edits against what is actually there.

Only ever runs on the failure path (once per rejected patch), so the difflib
ranking cost is irrelevant; a large-file guard keeps the worst case bounded.
"""

from __future__ import annotations

from typing import Callable

_PAD = 3            # file lines quoted on each side of the closest match
_MAX_SCAN = 20_000  # skip fuzzy ranking on very large files (cost guard)


def _render(lines: list[str], lo: int, hi: int) -> str:
    return "\n".join(f"{i + 1:>6}\t{lines[i]}" for i in range(lo, hi))


def _anchor(pattern: list[str]) -> tuple[str, int] | None:
    """The most distinctive (longest non-blank) pattern line and its index.

    Anchoring the window on this line means leading-line drift can't hide an
    otherwise-good match.
    """
    best, bi, blen = None, -1, 0
    for i, ln in enumerate(pattern):
        s = ln.strip()
        if len(s) > blen:
            best, bi, blen = s, i, len(s)
    return (best, bi) if best else None


def _ratio(window: list[str], pattern: list[str]) -> float:
    import difflib

    a = "\n".join(x.strip() for x in window)
    b = "\n".join(x.strip() for x in pattern)
    return difflib.SequenceMatcher(None, a, b).ratio()


def _closest(lines: list[str], pattern: list[str]) -> tuple[int, float] | None:
    """``(start, ratio)`` of the file window most similar to ``pattern`` (or ``None``)."""
    anc = _anchor(pattern)
    plen = len(pattern)
    if anc is None or plen > len(lines) or len(lines) > _MAX_SCAN:
        return None
    text, off = anc
    cands = [i for i, ln in enumerate(lines) if ln.strip() == text]
    if not cands:  # anchor never appears verbatim -- fall back to nearest single line
        import difflib

        stripped = [ln.strip() for ln in lines]
        cands = [stripped.index(m) for m in difflib.get_close_matches(text, stripped, n=3, cutoff=0.6)]
    best: tuple[int, float] | None = None
    for i in cands:
        start = max(0, min(i - off, len(lines) - plen))
        r = _ratio(lines[start:start + plen], pattern)
        if best is None or r > best[1]:
            best = (start, r)
    return best


def _why(window: list[str], pattern: list[str]) -> str:
    if [x.strip() for x in window] == [x.strip() for x in pattern]:
        return "only the indentation/whitespace differs -- copy the leading spaces exactly."
    return "the file text has changed since you last read it."


def describe_miss(
    lines: list[str],
    pattern: list[str],
    path: str,
    start: int,
    *,
    seek: Callable[[list[str], list[str], int, bool], int | None],
) -> str:
    """Build a recovery-oriented error for a hunk ``seek`` could not place.

    ``seek`` is the engine's ``seek_sequence`` (injected to avoid an import
    cycle); ``start`` is the monotonic cursor the real search began from.
    """
    quoted = "\n".join(pattern) if pattern else "(empty)"
    head = f"Could not find these lines in {path}:\n{quoted}"

    earlier = seek(lines, pattern, 0, False)
    if earlier is not None and earlier < start:
        lo, hi = max(0, earlier - _PAD), min(len(lines), earlier + len(pattern) + _PAD)
        return (
            f"{head}\n\nThey DO appear near line {earlier + 1}, but an earlier hunk in "
            f"this patch already advanced past line {start + 1}. List hunks top-to-bottom "
            f"in file order, or add unique surrounding context. The file there reads:\n"
            f"{_render(lines, lo, hi)}"
        )

    near = _closest(lines, pattern)
    if near and near[1] >= 0.4:
        idx, ratio = near
        lo, hi = max(0, idx - _PAD), min(len(lines), idx + len(pattern) + _PAD)
        return (
            f"{head}\n\nClosest match: lines {idx + 1}-{idx + len(pattern)} "
            f"({int(ratio * 100)}% similar) -- {_why(lines[idx:idx + len(pattern)], pattern)} "
            f"The file there reads:\n{_render(lines, lo, hi)}"
        )

    return (
        f"{head}\n\nNothing similar is present -- the path may be wrong or the file "
        f"already changed. Re-read it (e.g. `sed -n '1,40p' {path}` or `cat -n`) and copy "
        f"the current lines verbatim into your context."
    )
