"""microcompact — the cheapest context-management tier (no model call).

Elides the *content* of stale ``role:"tool"`` messages, replacing each with a
short ``[elided N chars]`` placeholder while keeping the most recent K tool
results verbatim. It is:

* **pure** — mutates the messages list in place and returns a stats dict, with
  no model call and no I/O;
* **idempotent** — a second pass never re-touches an already-elided message, so
  it is a no-op once every eligible tool result is already elided.

The caller (``guardrails.py``) decides *when* to compact — gated on a token
threshold, not on conversation size here — so this module always elides on
every call; it is not itself a no-op below any size threshold.

Safe because evidence is the durable store (Phase 2): anything that matters —
metric values, the command that worked, artifact paths — is written to
``evidence/``, so eliding tool stdout from the prompt loses no ground truth.

vLLM prefix-cache caveat: the loop is otherwise append-only (APC hits every
round); eliding rewrites the head and invalidates the KV cache from the first
edited message. Mitigated by compacting rarely (bulk elision) and keeping
elided messages stable thereafter — the cache rebuilds once.
"""

from __future__ import annotations

import re
from typing import Any

from reprocli_vllm.runtime.loop_guards import conversation_chars

_ELIDED_RE = re.compile(r"^\[elided \d+ chars\]$")


def is_elided(content: Any) -> bool:
    """True when ``content`` is already a microcompact placeholder."""
    return isinstance(content, str) and bool(_ELIDED_RE.match(content))


def microcompact(
    messages: list[dict[str, Any]],
    *,
    keep_recent_tool_results: int,
) -> dict[str, Any]:
    """Elide stale tool-result content in place; return a stats dict.

    The content of every ``role:"tool"`` message except the most recent
    ``keep_recent_tool_results`` is replaced by an ``[elided N chars]``
    placeholder. Already-elided messages are skipped, so repeated passes
    converge and the kept-recent window stays verbatim.
    """
    keep = max(0, keep_recent_tool_results)
    chars_before = conversation_chars(messages)
    tool_indices = [i for i, message in enumerate(messages) if message.get("role") == "tool"]
    # Slicing with ``[:-0]`` would drop everything, so special-case keep == 0.
    stale = tool_indices if keep == 0 else tool_indices[:-keep]
    elided_messages = 0
    elided_chars = 0
    for index in stale:
        message = messages[index]
        content = message.get("content")
        if is_elided(content):
            continue
        size = len(str(content or ""))
        message["content"] = f"[elided {size} chars]"
        elided_messages += 1
        elided_chars += size
    chars_after = conversation_chars(messages)
    return _stats(elided_messages > 0, elided_messages, elided_chars, keep, chars_before, chars_after)


def _stats(
    compacted: bool,
    elided_messages: int,
    elided_chars: int,
    kept_tool_results: int,
    chars_before: int,
    chars_after: int,
) -> dict[str, Any]:
    return {
        "compacted": compacted,
        "elided_messages": elided_messages,
        "elided_chars": elided_chars,
        "kept_tool_results": kept_tool_results,
        "chars_before": chars_before,
        "chars_after": chars_after,
    }
