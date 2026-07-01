"""Shape raw step output into what the model should actually read.

Training/eval commands drown their one result line in progress-bar spam: tqdm
redraws a single line hundreds of times with ``\r``, and a 40k-char head cut then
spends the whole budget on bar frames while dropping the final metrics printed at
the end. Both fixes are lossless for the information the agent needs:

* :func:`strip_progress` keeps only the final frame of every ``\r``-rewritten
  line — exactly what a terminal would have displayed;
* :func:`clip` elides the *middle* when output still exceeds the budget, keeping
  the head (the command's banner/config echo) and the tail (where the result
  line and the traceback live).

``shape`` composes the two and is the single seam ``workspace_bash`` and
``run_gpu`` shape their stdout/stderr through. Callers must capture output in
*binary* and decode it themselves: ``subprocess`` text mode translates lone
``\r`` to ``\n`` (universal newlines), which turns each redraw into its own line
and makes the spam indistinguishable from real output.
"""

from __future__ import annotations

# Split a clipped result ~1:3 head:tail — the tail is where results/tracebacks are.
_HEAD_FRACTION = 0.25


def strip_progress(text: str) -> str:
    """Collapse ``\r``-rewritten progress lines to the final frame a terminal shows."""
    if "\r" not in text:
        return text
    # Normalise Windows line ends first so the \r of a \r\n doesn't eat the line.
    text = text.replace("\r\n", "\n")
    return "\n".join(
        line.rsplit("\r", 1)[-1] if "\r" in line else line
        for line in text.split("\n")
    )


def clip(text: str, limit: int, *, note: str = "") -> tuple[str, bool]:
    """Fit ``text`` into ``limit`` chars by eliding the middle; ``(shaped, clipped)``.

    ``note`` names where the full output lives (e.g. the evidence log path) so the
    agent fetches it instead of re-running the command.
    """
    if len(text) <= limit:
        return text, False
    head = max(1, int(limit * _HEAD_FRACTION))
    tail = max(1, limit - head)
    marker = f"\n... [{len(text) - head - tail} chars elided{note}] ...\n"
    return text[:head] + marker + text[-tail:], True


def tail(text: str, limit: int) -> str:
    """The last ``limit`` chars, progress spam stripped (for kill/expiry paths)."""
    shaped = strip_progress(text)
    return shaped[-limit:]


def shape(text: str | None, limit: int, *, note: str = "") -> tuple[str, bool]:
    """Strip progress spam, then middle-elide to ``limit``; ``(shaped, clipped)``."""
    return clip(strip_progress(text or ""), limit, note=note)
