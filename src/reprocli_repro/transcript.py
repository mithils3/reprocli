"""Conversation shaping and incremental output writing for the reproduce loop.

Split out of ``loop.py`` to keep the driver focused. These are forked analogs of
the shared final-message and output helpers, minus the auditor-specific
extracted/audit rows: repro writes the raw response JSONL (and an optional round
trace). The agent's terminal output is its ``report.json`` (Phase 5) — an account
of what it ran and measured; the *verdict* is the auditor's, not written here.
"""

from __future__ import annotations

import argparse
import threading
from typing import Any

from reprocli_vllm.runtime.trace_io import append_trace_row, assistant_message
from reprocli_vllm.vllm.io import append_jsonl_row, truncate_output_file

# Repro-specific loop text; the shared strings stay in reprocli_vllm.
CONTEXT_BUDGET_NOTE = (
    "The conversation hit its context budget, so the tool phase ended early. "
    "Finalize from the evidence already written to the run directory rather "
    "than re-running tools. "
)

# Serializes incremental output writes across the tool-pool threads.
OUTPUT_WRITE_LOCK = threading.Lock()

# Exit reasons that prepend the budget note to the final tools-off turn.
EARLY_EXIT_REASONS = ("context_budget", "budget_exhausted")


def prepare_incremental_outputs(args: argparse.Namespace) -> None:
    truncate_output_file(args.output)
    if args.save_round_jsonl:
        truncate_output_file(args.trace_output)


def append_completed_outputs(
    custom_id: str,
    row: dict[str, Any],
    messages: list[dict[str, Any]],
    args: argparse.Namespace,
) -> None:
    with OUTPUT_WRITE_LOCK:
        append_jsonl_row(args.output, row, truncate=False)
        if args.save_round_jsonl:
            append_trace_row(args.trace_output, custom_id, messages, row)


def noop() -> None:
    return None


def final_user_message(budget_note: bool, final_message: str) -> dict[str, Any]:
    content = CONTEXT_BUDGET_NOTE + final_message if budget_note else final_message
    return {"role": "user", "content": content}


def round_status_message(round_index: int, max_rounds: int) -> dict[str, Any]:
    """Ephemeral per-request line telling the model which tool round it is on.

    Built fresh for each request and never stored in the conversation, so stale
    counters don't accumulate. Surfaces the turn budget — capped independently of the
    H100-hour budget — which the model otherwise has no way to see.
    """
    used = round_index + 1
    left = max(0, max_rounds - used)
    return {"role": "user", "content": f"Tool round {used}/{max_rounds} · {left} left"}


def conversation_for_round(
    messages: list[dict],
    include_tools: bool,
    *,
    budget_note: bool = False,
    final_message: str = "",
) -> list[dict]:
    if include_tools:
        return messages
    return [*messages, final_user_message(budget_note, final_message)]


def append_final_message(
    messages: list[dict[str, Any]],
    message: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    include_tools: bool,
    *,
    budget_note: bool = False,
    final_message: str = "",
) -> None:
    if not include_tools:
        messages.append(final_user_message(budget_note, final_message))
    messages.append(assistant_message(message, tool_calls))
