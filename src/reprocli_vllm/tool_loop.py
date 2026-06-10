from __future__ import annotations

import argparse
import sys
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Any

from .vllm_io import (
    append_assistant_tool_call,
    append_jsonl_row,
    build_chat_completion_request,
    extracted_response,
    initial_messages,
    normalize_tool_calls,
    response_message,
    truncate_output_file,
    tool_result_message,
)
from .config import CONTEXT_BUDGET_NOTE, FINAL_NO_TOOLS_MESSAGE, REQUEST_TIMEOUT
from .loop_guards import context_budget_exceeded, record_tool_call, repeated_tool_call
from .papers import Paper
from .run_health import loop_telemetry
from .tools.web_tools import execute_tool_call
from .trace_io import append_trace_row, assistant_message
from .vllm_client import post_chat_completion_row, response_row


def run_tool_loop(
    args: argparse.Namespace,
    papers: list[Paper],
    prompts: list[str],
    server_url: str,
) -> None:
    conversations = {
        paper.arxiv_id: initial_messages(prompt)
        for paper, prompt in zip(papers, prompts, strict=True)
    }
    papers_by_id = {paper.arxiv_id: paper for paper in papers}
    original_ids = [paper.arxiv_id for paper in papers]
    final_rows: dict[str, dict] = {}
    exit_reasons: dict[str, str] = {}
    tool_call_counts = {custom_id: Counter() for custom_id in original_ids}
    tool_rounds_used = {custom_id: 0 for custom_id in original_ids}
    workers = max(1, min(args.request_workers, len(original_ids)))
    base_url = server_url.rstrip("/")
    print(
        f"Running async tool loop for {len(original_ids)} request(s) "
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
                budget_note=exit_reasons.get(custom_id) == "context_budget",
            )
            request = build_chat_completion_request(
                args.model,
                custom_id,
                messages,
                args,
                include_tools=include_tools,
                tool_choice="auto",
            )
            stream = args.stream_first_response and round_index == 0 and custom_id == original_ids[0]
            future = requests.submit(
                post_chat_completion_row,
                base_url,
                request,
                REQUEST_TIMEOUT,
                stream=stream,
            )
            request_futures[future] = {
                "custom_id": custom_id,
                "round_index": round_index,
                "include_tools": include_tools,
            }

        for custom_id in original_ids:
            submit_request(custom_id, 0, include_tools=True)

        while request_futures or tool_futures:
            done, _ = wait(
                set(request_futures) | set(tool_futures),
                return_when=FIRST_COMPLETED,
            )
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
                        papers_by_id,
                        args,
                    )
                    continue
                state = tool_futures.pop(future)
                future.result()
                custom_id = str(state["custom_id"])
                next_round = int(state["round_index"]) + 1
                include_tools = not state.get("force_final") and next_round < args.tool_rounds
                if include_tools and context_budget_exceeded(
                    conversations[custom_id], args.max_input_tokens
                ):
                    exit_reasons[custom_id] = "context_budget"
                    include_tools = False
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
    tool_call_counts: dict[str, Counter],
    papers_by_id: dict[str, Paper],
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
            custom_id,
            tool_calls,
            tool_call_counts,
            args.max_repeated_tool_calls,
        )
        if repeated:
            print(
                f"Stopping tool loop for {custom_id}: repeated tool call {repeated}",
                file=sys.stderr,
            )
            exit_reasons[custom_id] = "repeated_call_cutoff"
            tool_future = tools.submit(noop)
            tool_futures[tool_future] = {**state, "force_final": True}
            return
        if round_index + 1 >= args.tool_rounds:
            exit_reasons[custom_id] = "round_limit"
        tool_future = tools.submit(
            append_tool_results,
            conversations[custom_id],
            message,
            tool_calls,
            papers_by_id[custom_id],
            tool_call_counts[custom_id],
        )
        tool_futures[tool_future] = state
        return
    if state["include_tools"]:
        # The model stopped without a tool call while tools were still enabled,
        # so re-issue one tools-off pass to get schema-constrained final JSON.
        conversations[custom_id].append(assistant_message(message, tool_calls))
        tool_future = tools.submit(noop)
        tool_futures[tool_future] = {**state, "force_final": True}
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
        budget_note=exit_reason == "context_budget",
    )
    final_rows[custom_id] = row
    append_completed_outputs(custom_id, row, conversations[custom_id], args)


def prepare_incremental_outputs(args: argparse.Namespace) -> None:
    truncate_output_file(args.output)
    truncate_output_file(args.extracted_output)
    if args.save_round_jsonl:
        truncate_output_file(args.trace_output)


def append_completed_outputs(
    custom_id: str,
    row: dict[str, Any],
    messages: list[dict[str, Any]],
    args: argparse.Namespace,
) -> None:
    append_jsonl_row(args.output, row, truncate=False)
    append_jsonl_row(args.extracted_output, extracted_response(custom_id, row), truncate=False)
    if args.save_round_jsonl:
        append_trace_row(args.trace_output, custom_id, messages, row)


def noop() -> None:
    return None


def conversation_for_round(
    messages: list[dict],
    include_tools: bool,
    *,
    budget_note: bool = False,
) -> list[dict]:
    if include_tools:
        return messages
    final_message = FINAL_NO_TOOLS_MESSAGE
    if budget_note:
        final_message = CONTEXT_BUDGET_NOTE + final_message
    return [*messages, {"role": "user", "content": final_message}]


def append_tool_results(
    messages: list[dict],
    message: dict,
    tool_calls: list[dict],
    paper: Paper,
    counts: Counter,
) -> None:
    append_assistant_tool_call(messages, message, tool_calls)
    for call in tool_calls:
        result = execute_tool_call(call, paper=paper)
        record_tool_call(counts, call, result)
        messages.append(tool_result_message(call, result))


def append_final_message(
    messages: list[dict[str, Any]],
    message: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    include_tools: bool,
    *,
    budget_note: bool = False,
) -> None:
    if not include_tools:
        final_message = FINAL_NO_TOOLS_MESSAGE
        if budget_note:
            final_message = CONTEXT_BUDGET_NOTE + final_message
        messages.append({"role": "user", "content": final_message})
    messages.append(assistant_message(message, tool_calls))
