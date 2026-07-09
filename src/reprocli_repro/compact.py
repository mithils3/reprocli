"""Context compaction by tool-stdout elision — the tier that keeps the loop going.

When the conversation nears ``max_input_tokens`` we recover space by replacing the
*contents* of old, bulky tool results with a short ``[elided N chars — on disk at
…]`` placeholder. Every assistant turn (reasoning + ``tool_calls``), every small
tool result, and the pinned head (system + task prompt) are kept **verbatim**.

Why elision rather than a brain-call summary (the prior tier): the bulk of a full
context is tool stdout — pip/download logs, GPU eval logs, file dumps — not the
agent's reasoning. Eliding only that stdout leaves the agent's own words intact, so
its stated intent (what it just learned, what it planned to do next) survives the
compaction boundary instead of being flattened into a lossy third-person summary.
The full output is never lost: it lives in the durable evidence store
(``trajectory.jsonl`` + ``agent.full.log``), which the placeholder points at, so an
elided number can be re-read instead of re-computed.

Cut discipline (kept from the prior tier): keep ~``keep_recent_tokens`` of the
newest messages verbatim so fresh results the agent is actively using are never
elided, never elide behind the pinned system + task head, and — since we only
shrink ``role:"tool"`` contents in place and never drop or reorder messages — no
tool result is ever stranded from the assistant ``tool_calls`` that produced it.

vLLM prefix-cache caveat: shrinking an old message invalidates the KV cache from
that message on. We fire rarely (only near the ceiling) and never touch the recent
tail, so the cache rebuilds a single time.
"""

from __future__ import annotations

from typing import Any

from reprocli_vllm.runtime.loop_guards import BUDGET_CHARS_PER_TOKEN, conversation_chars

# Tool results shorter than this stay verbatim — short confirmations ("ok", a path,
# a small count) cost little and reading them is cheaper than a disk round-trip.
ELIDE_MIN_CHARS = 1000
_ELIDED_PREFIX = "[elided "


def _message_chars(message: dict[str, Any]) -> int:
    chars = len(str(message.get("content") or ""))
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        chars += len(str(function.get("arguments") or ""))
    return chars


def choose_cut(messages: list[dict[str, Any]], keep_recent_tokens: int) -> int:
    """Index where the kept recent tail starts (always after the system message).

    Walks back from the newest message accumulating estimated tokens until
    ``keep_recent_tokens`` is reached. A return of ``<= 1`` means there is nothing
    old enough to compact (only the system message, or the whole conversation fits
    inside the keep window). No boundary snap is needed here — we shrink tool
    contents in place rather than slicing, so the tail can begin anywhere.
    """
    budget_chars = max(0, keep_recent_tokens) * BUDGET_CHARS_PER_TOKEN
    acc = 0
    cut = 1
    for index in range(len(messages) - 1, 0, -1):  # never cross index 0 (system)
        acc += _message_chars(messages[index])
        cut = index
        if acc >= budget_chars:
            break
    return cut


def _placeholder(n_chars: int, pointer: str) -> str:
    return f"{_ELIDED_PREFIX}{n_chars} chars — on disk at {pointer}]"


def elide_compact(
    messages: list[dict[str, Any]],
    *,
    keep_recent_tokens: int,
    full_log_path: str | None = None,
) -> dict[str, Any]:
    """Elide bulky old tool results in place; keep everything else verbatim.

    Mutates ``messages``: for each ``role:"tool"`` result in the old span (index 2
    up to the recent-tail cut) whose content exceeds ``ELIDE_MIN_CHARS``, the
    content is replaced with a pointer to the durable on-disk copy. The pinned head
    (``messages[0]`` system, ``messages[1]`` task prompt) and the recent tail are
    never touched. Returns a stats dict; ``compacted`` is False (with a ``reason``)
    when there was nothing old and bulky enough to free, leaving ``messages``
    unchanged so the caller can fall back to the hard-ceiling backstop.
    """
    cut = choose_cut(messages, keep_recent_tokens)
    # Span starts at index 2: messages[0] is system, messages[1] is the pinned task
    # prompt. A cut of <= 2 means there is nothing old enough behind the pinned head.
    if cut <= 2:
        return {"compacted": False, "reason": "nothing-old-enough"}
    pointer = full_log_path or "evidence/"
    chars_before = conversation_chars(messages)
    elided = 0
    freed = 0
    for index in range(2, cut):
        message = messages[index]
        if message.get("role") != "tool":
            continue
        content = str(message.get("content") or "")
        if len(content) <= ELIDE_MIN_CHARS or content.startswith(_ELIDED_PREFIX):
            continue
        message["content"] = _placeholder(len(content), pointer)
        elided += 1
        freed += len(content)
    if elided == 0:
        return {"compacted": False, "reason": "no-bulk-tool-output"}
    return {
        "compacted": True,
        "elided_messages": elided,
        "freed_chars": freed,
        "chars_before": chars_before,
        "chars_after": conversation_chars(messages),
    }
