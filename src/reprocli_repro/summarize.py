"""summarize-compaction — the context tier that *summarizes* and keeps the loop going.

The loop keeps every tool result verbatim in context; when the conversation nears
``max_input_tokens``, a single brain call rewrites the old span into one compact
structured summary so the agent can **keep working** instead of being forced to
finalize. It replaces the old hard ``context_budget`` stop.

Design adapted from Pi's compaction (Earendil Inc., MIT — https://pi.dev, docs:
"Compaction & Branch Summarization"). We take the parts that fit a stateless,
in-memory ``list[dict]`` conversation:

* **cut-point discipline** — keep ~``keep_recent_tokens`` of the newest messages and
  snap the cut to a safe boundary; never strand a ``role:"tool"`` result from the
  assistant ``tool_calls`` that produced it (an orphan tool message is rejected by
  the chat API);
* the **structured summary format** (Goal / Constraints / Progress / Key Decisions /
  Next Steps / Critical Context), tuned so Critical Context pins our anchor metric,
  the commands that worked, and ``evidence/`` paths;
* **serialize-then-truncate** the span (tool results + call args capped) so the
  summary request itself stays small, and **cumulative file tracking** across
  repeated compactions — for our toolset that means modified files only
  (``write_file`` / ``edit_file``); there is no read tool (reads go through
  ``workspace_bash``), so Pi's read-files list does not apply.

We deliberately skip Pi's branch / ``/tree`` summarization, its persisted entry-tree
+ reload (we splice the in-memory list in place), its split-turn summarization, and
its extension hooks.

vLLM prefix-cache caveat: rewriting the head invalidates the KV cache from the
first changed message. We fire rarely — only once the conversation nears the
ceiling — and keep the post-compaction tail stable so the cache rebuilds a single
time.
"""

from __future__ import annotations

import json
from typing import Any

from reprocli_vllm.config.config import REQUEST_TIMEOUT
from reprocli_vllm.runtime.loop_guards import BUDGET_CHARS_PER_TOKEN, conversation_chars
from reprocli_vllm.vllm.client import post_chat_completion_row, response_row
from reprocli_vllm.vllm.io import response_message

# Tools whose ``path`` argument names a file the agent changed. There is no read
# tool (reads go through ``workspace_bash``), so we track modified files only.
_WRITE_TOOLS = {"write_file", "edit_file"}
_TOOL_RESULT_CAP = 2000  # Pi caps serialized tool results so the summary call stays small.
_CALL_ARG_CAP = 600      # write_file/edit_file args carry whole-file content; cap them too.
_SUMMARY_MAX_TOKENS = 1500
_SUMMARY_TEMPERATURE = 0.3

SUMMARY_SYSTEM = (
    "You compress a reproduction agent's working transcript so it can keep going "
    "with a smaller context. Output ONLY the structured summary requested — no "
    "preamble, no closing remarks. Be specific and lossless about anything needed "
    "to continue: the exact commands that worked, metric values and the anchor "
    "target/tolerance, file and evidence/ paths, and the held GPU jobid / remaining "
    "budget."
)

SUMMARY_TEMPLATE = """## Goal
[The paper's reproduction target and what the agent is trying to run]

## Constraints & Preferences
- [Budget, hardware, lockfile target, setup constraints]

## Progress
### Done
- [Completed setup/experiment steps, with the commands that worked]

### In Progress
- [The current step]

### Blocked
- [Errors hit and what was already tried]

## Key Decisions
- **[Decision]**: [why]

## Next Steps
1. [What to do next]

## Critical Context
- [Anchor metric + tolerance, metric values seen, evidence/ artifact paths, held GPU jobid / budget left]"""


def _message_chars(message: dict[str, Any]) -> int:
    chars = len(str(message.get("content") or ""))
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        chars += len(str(function.get("arguments") or ""))
    return chars


def choose_cut(messages: list[dict[str, Any]], keep_recent_tokens: int) -> int:
    """Index where the kept recent tail starts (always after the system message).

    Walks back from the newest message accumulating estimated tokens until
    ``keep_recent_tokens`` is reached, then snaps to a safe boundary: a tail may not
    begin with a ``role:"tool"`` result (it would be orphaned from its assistant
    ``tool_calls``), so we back the cut onto the assistant that owns it. A return of
    ``<= 1`` means there is nothing old enough to summarize (only the system message,
    or the whole conversation fits inside the keep window).
    """
    budget_chars = max(0, keep_recent_tokens) * BUDGET_CHARS_PER_TOKEN
    acc = 0
    cut = 1
    for index in range(len(messages) - 1, 0, -1):  # never cross index 0 (system)
        acc += _message_chars(messages[index])
        cut = index
        if acc >= budget_chars:
            break
    while cut > 1 and messages[cut].get("role") == "tool":
        cut -= 1
    return cut


def _cap(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f" …[+{len(text) - limit} chars]"


def _render_call(call: dict[str, Any]) -> str:
    function = call.get("function") or {}
    name = str(function.get("name") or "?")
    arguments = _cap(str(function.get("arguments") or ""), _CALL_ARG_CAP)
    return f"{name}({arguments})"


def serialize_span(messages: list[dict[str, Any]]) -> str:
    """Render a span to plain text (Pi's ``serializeConversation``), capping bulk.

    Tool results and tool-call arguments are truncated so the summary request stays
    small; the durable copy of anything truncated lives in ``evidence/``.
    """
    lines: list[str] = []
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if role == "user":
            lines.append(f"[User]: {content or ''}")
        elif role == "assistant":
            if message.get("reasoning"):
                lines.append(f"[Assistant thinking]: {message['reasoning']}")
            if content:
                lines.append(f"[Assistant]: {content}")
            calls = message.get("tool_calls") or []
            if calls:
                lines.append("[Assistant tool calls]: " + "; ".join(_render_call(c) for c in calls))
        elif role == "tool":
            lines.append(f"[Tool result]: {_cap(str(content or ''), _TOOL_RESULT_CAP)}")
    return "\n".join(lines)


def accumulate_files(messages: list[dict[str, Any]], previous: list[str]) -> list[str]:
    """Cumulative list of files the agent modified, merging ``previous`` with this span."""
    modified = list(previous)
    for message in messages:
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            if str(function.get("name") or "") not in _WRITE_TOOLS:
                continue
            path = _arg_path(function.get("arguments"))
            if path and path not in modified:
                modified.append(path)
    return modified


def _arg_path(arguments: Any) -> str | None:
    if isinstance(arguments, dict):
        value = arguments.get("path")
        return str(value) if value else None
    try:
        parsed = json.loads(arguments)
    except (TypeError, json.JSONDecodeError):
        return None
    value = parsed.get("path") if isinstance(parsed, dict) else None
    return str(value) if value else None


def _summary_prompt(transcript: str, previous_summary: str | None) -> str:
    parts: list[str] = []
    if previous_summary:
        parts.append("Earlier summary of the run so far (fold it in, drop no facts):\n" + previous_summary)
    parts.append("Transcript of the turns to compress (oldest first):\n" + transcript)
    parts.append("Write the summary now, using exactly this structure:\n" + SUMMARY_TEMPLATE)
    return "\n\n".join(parts)


_PLAN_MARKS = {"pending": "[ ]", "in_progress": "[~]", "completed": "[x]"}


def _render_plan(plan: list[dict[str, str]] | None) -> str:
    if not plan:
        return ""
    return "\n".join(f"{_PLAN_MARKS.get(i.get('status', ''), '[ ]')} {i.get('step', '')}" for i in plan)


def _summary_block(summary_text: str, modified: list[str], plan: list[dict[str, str]] | None = None) -> str:
    block = (
        "[Context compacted — earlier turns were summarized to free context. The "
        "evidence on disk under evidence/ is the source of truth; continue from here.]"
        "\n\n" + summary_text.strip()
    )
    plan_text = _render_plan(plan)
    if plan_text:
        block += "\n\n<plan>\n" + plan_text + "\n</plan>"
    if modified:
        block += "\n\n<modified-files>\n" + "\n".join(modified) + "\n</modified-files>"
    return block


def _request_summary(
    server_url: str, model: str, args: Any, custom_id: str, user_prompt: str
) -> str:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SUMMARY_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": _SUMMARY_TEMPERATURE,
        "top_p": args.top_p,
        "max_tokens": min(args.max_tokens, _SUMMARY_MAX_TOKENS),
        "truncate_prompt_tokens": args.max_input_tokens,
    }
    request = {"custom_id": custom_id, "method": "POST", "url": "/v1/chat/completions", "body": body}
    body_out = post_chat_completion_row(server_url.rstrip("/"), request, REQUEST_TIMEOUT)
    message = response_message(response_row(custom_id, body_out))
    return str(message.get("content") or "")


def summarize_compact(
    messages: list[dict[str, Any]],
    *,
    server_url: str,
    model: str,
    args: Any,
    custom_id: str,
    keep_recent_tokens: int,
    previous_summary: str | None = None,
    previous_modified: list[str] | None = None,
    plan: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Summarize the old span into one message and splice it in; keep the recent tail.

    Mutates ``messages`` in place to ``[system, task, summary, *tail]`` on success
    and returns a stats dict. On any failure (nothing old enough, summary call
    errored, empty summary) it leaves ``messages`` untouched and returns
    ``compacted=False`` with a ``reason`` — the caller keeps going and retries next
    round, falling back to the hard context guard only if it ever crosses the real
    ceiling.

    The task prompt at ``messages[1]`` is pinned verbatim and never summarized, so the
    definition-of-done (anchor metric, tolerance, MRE target, step-by-step task) can
    never evaporate into a lossy summary and leave the agent finalizing prematurely.
    """
    cut = choose_cut(messages, keep_recent_tokens)
    # Span starts at index 2: messages[0] is the system message and messages[1] is the
    # pinned task prompt, both kept verbatim. A cut of <= 2 means there is nothing old
    # enough behind the pinned head to summarize.
    if cut <= 2:
        return {"compacted": False, "reason": "nothing-old-enough"}
    span = messages[2:cut]
    tail = messages[cut:]
    chars_before = conversation_chars(messages)
    modified = accumulate_files(span, previous_modified or [])
    prompt = _summary_prompt(serialize_span(span), previous_summary)
    try:
        summary_text = _request_summary(server_url, model, args, custom_id, prompt)
    except Exception as exc:  # transient endpoint error: no-op, the caller retries
        return {"compacted": False, "reason": f"summary-error: {type(exc).__name__}"}
    if not summary_text.strip():
        return {"compacted": False, "reason": "empty-summary"}
    summary_message = {"role": "user", "content": _summary_block(summary_text, modified, plan)}
    messages[:] = [messages[0], messages[1], summary_message, *tail]
    return {
        "compacted": True,
        "summary": summary_text.strip(),
        "modified_files": modified,
        "summarized_messages": len(span),
        "chars_before": chars_before,
        "chars_after": conversation_chars(messages),
    }
