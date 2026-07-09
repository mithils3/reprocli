"""Forked tool loop for the reproduction agent.

A *diverged* fork of ``reprocli_vllm.runtime.tool_loop.run_tool_loop``: it began
by mirroring that loop's structure (two thread pools, ``wait(FIRST_COMPLETED)``,
``handle_request_done``) but the two have since drifted and are no longer kept in
sync — this loop swaps the body for the reproduction seams:

* tool calls dispatch through a per-episode ``ExecutionContext`` via
  ``dispatch.append_tool_results`` (workspace + budget + allocation + evidence)
  instead of ``execute_tool_call(call, paper=paper)``;
* the post-round seam (the analog of ``handle_request_done`` in ``tool_loop.py``)
  calls ``guardrails.apply_guardrails`` — the compute-budget force-final plus the
  ``elide-compact`` context tier that keeps the loop going.

Conversation shaping and output writing live in ``transcript.py``; the tool seam
lives in ``dispatch.py``; the between-round budget + context guardrails live in
``guardrails.py``; the end-of-episode seam (release GPU, emit ``report.json``, flip
the run terminal) lives in ``finalize.py``. The loop emits the agent's ``report.json``
(Phase 5) but writes **no verdict** — the auditor grades the run bundle.
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Any

from reprocli_vllm.config.config import REQUEST_TIMEOUT
from reprocli_vllm.runtime.trace_io import assistant_message
from reprocli_vllm.vllm.client import post_chat_completion_row, response_row
from reprocli_vllm.vllm.io import (
    build_chat_completion_request,
    initial_messages,
    normalize_tool_calls,
    response_message,
)

from reprocli_repro import live_log
from reprocli_repro.context import ExecutionContext
from reprocli_repro.dispatch import append_tool_results
from reprocli_repro.finalize import finalize_episode
from reprocli_repro.guardrails import apply_guardrails
from reprocli_repro.transcript import (
    EARLY_EXIT_REASONS,
    conversation_for_round,
    noop,
    prepare_incremental_outputs,
    round_status_message,
)


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
            if include_tools:
                # Ephemeral, request-only: append the turn-budget counter without
                # persisting it into the stored conversation (no stale copies pile up).
                messages = [*messages, round_status_message(round_index, args.tool_rounds)]
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


def handle_request_done(
    future: Future,
    request_futures: dict[Future, dict[str, Any]],
    tool_futures: dict[Future, dict[str, Any]],
    tools: ThreadPoolExecutor,
    conversations: dict[str, list[dict]],
    final_rows: dict[str, dict],
    tool_rounds_used: dict[str, int],
    exit_reasons: dict[str, str],
    contexts_by_id: dict[str, ExecutionContext],
    args: argparse.Namespace,
) -> None:
    state = request_futures.pop(future)
    custom_id = str(state["custom_id"])
    round_index = int(state["round_index"])
    try:
        result = future.result()
    except Exception as exc:  # noqa: BLE001 — a failed model call must not strand the run
        # The round's model call failed after the retry budget (a non-retryable 4xx, or a
        # hang that exhausted timeout+retries). Letting it propagate unwinds the whole loop
        # and leaves this run's row stuck at status="running" with no report.json. Finalize
        # just this episode as an error terminal instead: it reaches a terminal status and
        # still gets a (degraded) report for the auditor, and sibling episodes keep running.
        print(
            f"request {custom_id}: model call failed at round {round_index}: {exc}",
            file=sys.stderr,
        )
        finalize_episode(
            custom_id,
            {"custom_id": custom_id, "response": {"status_code": 0, "body": None, "error": str(exc)}},
            {},
            [],
            round_index,
            "error",
            conversations,
            final_rows,
            tool_rounds_used,
            contexts_by_id,
            args,
        )
        return
    row = response_row(custom_id, result)
    message = response_message(row)
    # Capture the model's real token usage for this response (every round, the
    # intermediate force-final pass, and the final turn each pass through here once).
    body = row.get("response", {}).get("body")
    usage = body.get("usage") if isinstance(body, dict) else None
    live_log.log_usage(contexts_by_id[custom_id], usage, round_index=round_index)
    # Stash the exact prompt-token count so the between-round context guardrails gate on
    # the server's own number instead of a chars-per-token estimate.
    if isinstance(usage, dict) and usage.get("prompt_tokens") is not None:
        contexts_by_id[custom_id].last_prompt_tokens = int(usage["prompt_tokens"])
    tool_calls = normalize_tool_calls(message.get("tool_calls") or [])
    if state["include_tools"] and tool_calls:
        tool_rounds_used[custom_id] = max(tool_rounds_used[custom_id], round_index + 1)
        if round_index + 1 >= args.tool_rounds:
            exit_reasons[custom_id] = "round_limit"
        tool_future = tools.submit(
            append_tool_results,
            conversations[custom_id],
            message,
            tool_calls,
            contexts_by_id[custom_id],
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
    finalize_episode(
        custom_id,
        row,
        message,
        tool_calls,
        round_index,
        exit_reason,
        conversations,
        final_rows,
        tool_rounds_used,
        contexts_by_id,
        args,
    )
