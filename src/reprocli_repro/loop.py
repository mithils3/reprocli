"""Forked tool loop for the reproduction agent.

Mirrors the *structure* of ``reprocli_vllm.runtime.tool_loop.run_tool_loop``
(two thread pools, ``wait(FIRST_COMPLETED)``, ``handle_request_done``) but swaps
the loop body:

* tool calls dispatch through a per-episode ``ExecutionContext`` via
  ``dispatch.append_tool_results`` (workspace + budget + allocation + evidence)
  instead of ``execute_tool_call(call, paper=paper)``;
* the post-round seam (the ``tool_loop.py:122`` analog) adds the compute-budget
  guardrail and the ``microcompact`` context-management tier *ahead of* the hard
  context cutoff.

Conversation shaping and output writing live in ``transcript.py``; the tool seam
lives in ``dispatch.py``. Phase 5's post-loop re-execution writes the graded
``result.json`` this loop deliberately does not.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Any

from reprocli_vllm.config.config import REQUEST_TIMEOUT
from reprocli_vllm.runtime.loop_guards import (
    BUDGET_CHARS_PER_TOKEN,
    context_budget_exceeded,
    repeated_tool_call,
)
from reprocli_vllm.runtime.run_health import loop_telemetry
from reprocli_vllm.runtime.trace_io import assistant_message
from reprocli_vllm.vllm.client import post_chat_completion_row, response_row
from reprocli_vllm.vllm.io import (
    build_chat_completion_request,
    initial_messages,
    normalize_tool_calls,
    response_message,
)

from reprocli_repro import live_log
from reprocli_repro.compaction import microcompact
from reprocli_repro.context import ExecutionContext
from reprocli_repro.dispatch import append_tool_results
from reprocli_repro.transcript import (
    append_completed_outputs,
    append_final_message,
    conversation_for_round,
    noop,
    prepare_incremental_outputs,
)

# Exit reasons that prepend the budget note to the final tools-off turn.
EARLY_EXIT_REASONS = ("context_budget", "budget_exhausted")


def run_reproduce_loop(
    args: argparse.Namespace,
    contexts: list[ExecutionContext],
    prompts: list[str],
    server_url: str,
    model_id: str | None = None,
) -> None:
    request_model = model_id or args.model
    conversations = {
        ctx.arxiv_id: initial_messages(prompt, args.system_message)
        for ctx, prompt in zip(contexts, prompts, strict=True)
    }
    contexts_by_id = {ctx.arxiv_id: ctx for ctx in contexts}
    original_ids = [ctx.arxiv_id for ctx in contexts]
    final_rows: dict[str, dict] = {}
    exit_reasons: dict[str, str] = {}
    tool_call_counts = {custom_id: Counter() for custom_id in original_ids}
    tool_rounds_used = {custom_id: 0 for custom_id in original_ids}
    workers = max(1, min(args.request_workers, len(original_ids)))
    base_url = server_url.rstrip("/")
    print(
        f"Running reproduce loop for {len(original_ids)} episode(s) "
        f"with {workers} worker(s)",
        file=sys.stderr,
    )
    prepare_incremental_outputs(args)

    with ThreadPoolExecutor(max_workers=workers) as requests, ThreadPoolExecutor(
        max_workers=workers
    ) as tools:
        request_futures: dict[Future, dict[str, Any]] = {}
        tool_futures: dict[Future, dict[str, Any]] = {}

        def submit_request(custom_id: str, round_index: int, include_tools: bool) -> None:
            messages = conversation_for_round(
                conversations[custom_id],
                include_tools,
                budget_note=exit_reasons.get(custom_id) in EARLY_EXIT_REASONS,
                final_message=args.final_no_tools_message,
            )
            request = build_chat_completion_request(
                request_model,
                custom_id,
                messages,
                args,
                include_tools=include_tools,
                tool_choice="auto",
            )
            future = requests.submit(post_chat_completion_row, base_url, request, REQUEST_TIMEOUT)
            request_futures[future] = {
                "custom_id": custom_id,
                "round_index": round_index,
                "include_tools": include_tools,
            }

        for custom_id in original_ids:
            submit_request(custom_id, 0, include_tools=args.use_tools)

        while request_futures or tool_futures:
            done, _ = wait(set(request_futures) | set(tool_futures), return_when=FIRST_COMPLETED)
            for future in done:
                if future in request_futures:
                    handle_request_done(
                        future,
                        request_futures,
                        tool_futures,
                        tools,
                        conversations,
                        final_rows,
                        tool_rounds_used,
                        exit_reasons,
                        tool_call_counts,
                        contexts_by_id,
                        args,
                    )
                    continue
                state = tool_futures.pop(future)
                future.result()
                custom_id = str(state["custom_id"])
                next_round = int(state["round_index"]) + 1
                include_tools = not state.get("force_final") and next_round < args.tool_rounds
                include_tools = apply_guardrails(
                    custom_id,
                    contexts_by_id[custom_id],
                    conversations[custom_id],
                    args,
                    exit_reasons,
                    include_tools,
                )
                submit_request(custom_id, next_round, include_tools)

    missing = [custom_id for custom_id in original_ids if custom_id not in final_rows]
    if missing:
        raise SystemExit(f"Missing final responses for: {', '.join(missing)}")


def apply_guardrails(
    custom_id: str,
    ctx: ExecutionContext,
    messages: list[dict[str, Any]],
    args: argparse.Namespace,
    exit_reasons: dict[str, str],
    include_tools: bool,
) -> bool:
    """Budget guardrail + context management, run between tool rounds.

    Returns whether the next request should still offer tools. Force-finals
    first when the compute budget is spent, then lets ``microcompact`` reclaim
    room before falling back to the hard tools-off context cutoff.
    """
    if not include_tools:
        return False
    if ctx.budget is not None and ctx.budget.exhausted():
        exit_reasons[custom_id] = "budget_exhausted"
        print(f"Stopping reproduce loop for {custom_id}: compute budget exhausted", file=sys.stderr)
        return False
    if args.microcompact:
        stats = microcompact(
            messages,
            keep_recent_tool_results=args.microcompact_keep,
            soft_limit_chars=microcompact_soft_limit(args),
        )
        if stats["compacted"]:
            print(
                f"microcompact {custom_id}: elided {stats['elided_messages']} stale tool "
                f"result(s), {stats['chars_before']}->{stats['chars_after']} chars",
                file=sys.stderr,
            )
    if context_budget_exceeded(messages, args.max_input_tokens):
        exit_reasons[custom_id] = "context_budget"
        return False
    return True


def microcompact_soft_limit(args: argparse.Namespace) -> int:
    return int(args.microcompact_threshold * args.max_input_tokens * BUDGET_CHARS_PER_TOKEN)


def handle_request_done(
    future: Future,
    request_futures: dict[Future, dict[str, Any]],
    tool_futures: dict[Future, dict[str, Any]],
    tools: ThreadPoolExecutor,
    conversations: dict[str, list[dict]],
    final_rows: dict[str, dict],
    tool_rounds_used: dict[str, int],
    exit_reasons: dict[str, str],
    tool_call_counts: dict[str, Counter],
    contexts_by_id: dict[str, ExecutionContext],
    args: argparse.Namespace,
) -> None:
    state = request_futures.pop(future)
    custom_id = str(state["custom_id"])
    round_index = int(state["round_index"])
    row = response_row(custom_id, future.result())
    message = response_message(row)
    tool_calls = normalize_tool_calls(message.get("tool_calls") or [])
    if state["include_tools"] and tool_calls:
        tool_rounds_used[custom_id] = max(tool_rounds_used[custom_id], round_index + 1)
        repeated = repeated_tool_call(
            custom_id, tool_calls, tool_call_counts, args.max_repeated_tool_calls
        )
        if repeated:
            print(
                f"Stopping reproduce loop for {custom_id}: repeated tool call {repeated}",
                file=sys.stderr,
            )
            exit_reasons[custom_id] = "repeated_call_cutoff"
            tool_futures[tools.submit(noop)] = {**state, "force_final": True}
            return
        if round_index + 1 >= args.tool_rounds:
            exit_reasons[custom_id] = "round_limit"
        tool_future = tools.submit(
            append_tool_results,
            conversations[custom_id],
            message,
            tool_calls,
            contexts_by_id[custom_id],
            tool_call_counts[custom_id],
            round_index,
        )
        tool_futures[tool_future] = state
        return
    if state["include_tools"]:
        # Model stopped without a tool call while tools were live; re-issue one
        # tools-off pass to get the schema-constrained final submission.
        conversations[custom_id].append(assistant_message(message, tool_calls))
        live_log.log_round_open(contexts_by_id[custom_id], message, round_index=round_index)
        tool_futures[tools.submit(noop)] = {**state, "force_final": True}
        return
    exit_reason = exit_reasons.get(custom_id, "natural")
    row["tool_loop"] = {
        "tool_rounds_used": tool_rounds_used[custom_id],
        "max_tool_rounds": args.tool_rounds,
        "hit_tool_round_limit": exit_reason == "round_limit",
        "exit_reason": exit_reason,
        "telemetry": loop_telemetry(conversations[custom_id], args.max_input_tokens),
    }
    append_final_message(
        conversations[custom_id],
        message,
        tool_calls,
        bool(state["include_tools"]),
        budget_note=exit_reason in EARLY_EXIT_REASONS,
        final_message=args.final_no_tools_message,
    )
    final_rows[custom_id] = row
    live_log.log_final(
        contexts_by_id[custom_id], message, round_index=round_index, exit_reason=exit_reason
    )
    append_completed_outputs(custom_id, row, conversations[custom_id], args)
