from __future__ import annotations

import argparse
import sys
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Any

from .batch_io import (
    append_assistant_tool_call,
    append_jsonl_row,
    build_batch_request,
    initial_messages,
    normalize_tool_calls,
    read_batch_output,
    response_message,
    round_output_path,
    round_request_path,
    tool_result_message,
    write_batch_requests,
    write_final_rows,
)
from .config import FINAL_NO_TOOLS_MESSAGE
from .openai_client import post_chat_completion_row, response_row, run_requests
from .papers import Paper
from .web_tools import execute_tool_call


def run_tool_loop(
    args: argparse.Namespace,
    papers: list[Paper],
    prompts: list[str],
) -> None:
    if args.batch_backend == "server":
        run_server_tool_loop(args, papers, prompts)
        return
    run_round_tool_loop(args, papers, prompts)


def run_round_tool_loop(
    args: argparse.Namespace,
    papers: list[Paper],
    prompts: list[str],
) -> None:
    conversations = {
        paper.arxiv_id: initial_messages(prompt, include_web_system=True)
        for paper, prompt in zip(papers, prompts, strict=True)
    }
    original_ids = [paper.arxiv_id for paper in papers]
    active_ids = original_ids[:]
    final_rows: dict[str, dict] = {}

    for round_index in range(args.tool_rounds + 1):
        include_tools = round_index < args.tool_rounds
        request_path = round_request_path(args.requests_output, round_index)
        output_path = round_output_path(args.output, round_index)
        print(
            f"Round {round_index + 1}: running {len(active_ids)} request(s) "
            f"({'tools enabled' if include_tools else 'final no-tools pass'})",
            file=sys.stderr,
        )
        round_conversations = conversations
        if not include_tools:
            round_conversations = final_pass_conversations(conversations, active_ids)
        write_batch_requests(
            request_path,
            args.model,
            active_ids,
            round_conversations,
            args,
            include_tools=include_tools,
            tool_choice=args.first_tool_choice if round_index == 0 else "auto",
        )
        run_requests(args, request_path, output_path)

        next_active: list[str] = []
        for row in read_batch_output(output_path):
            custom_id = str(row.get("custom_id", ""))
            message = response_message(row)
            tool_calls = normalize_tool_calls(message.get("tool_calls") or [])
            if include_tools and tool_calls:
                append_tool_results(conversations[custom_id], message, tool_calls, args)
                next_active.append(custom_id)
                continue
            final_rows[custom_id] = row

        if not next_active:
            break
        active_ids = next_active
    else:
        raise SystemExit(
            f"Tool loop did not finish after {args.tool_rounds} tool round(s)."
        )

    missing = [custom_id for custom_id in original_ids if custom_id not in final_rows]
    if missing:
        raise SystemExit(f"Missing final responses for: {', '.join(missing)}")
    write_final_rows(args.output, original_ids, final_rows)


def run_server_tool_loop(
    args: argparse.Namespace,
    papers: list[Paper],
    prompts: list[str],
) -> None:
    conversations = {
        paper.arxiv_id: initial_messages(prompt, include_web_system=True)
        for paper, prompt in zip(papers, prompts, strict=True)
    }
    original_ids = [paper.arxiv_id for paper in papers]
    final_rows: dict[str, dict] = {}
    request_paths_seen: set[int] = set()
    output_paths_seen: set[int] = set()
    workers = max(1, min(args.request_workers, len(original_ids)))
    base_url = args.vllm_server_url.rstrip("/")
    print(
        f"Running async tool loop for {len(original_ids)} request(s) "
        f"with {workers} worker(s)",
        file=sys.stderr,
    )

    with ThreadPoolExecutor(max_workers=workers) as requests, ThreadPoolExecutor(
        max_workers=workers
    ) as tools:
        request_futures: dict[Future, dict[str, Any]] = {}
        tool_futures: dict[Future, dict[str, Any]] = {}

        def submit_request(custom_id: str, round_index: int, include_tools: bool) -> None:
            messages = conversation_for_round(conversations[custom_id], include_tools)
            tool_choice = args.first_tool_choice if round_index == 0 else "auto"
            request = build_batch_request(
                args.model,
                custom_id,
                messages,
                args,
                include_tools=include_tools,
                tool_choice=tool_choice,
            )
            write_round_row(
                round_request_path(args.requests_output, round_index),
                request,
                round_index,
                request_paths_seen,
            )
            stream = args.stream_first_response and round_index == 0 and custom_id == original_ids[0]
            future = requests.submit(
                post_chat_completion_row,
                base_url,
                request,
                args.request_timeout,
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
                        output_paths_seen,
                        args,
                    )
                    continue
                state = tool_futures.pop(future)
                future.result()
                next_round = int(state["round_index"]) + 1
                submit_request(
                    str(state["custom_id"]),
                    next_round,
                    include_tools=next_round < args.tool_rounds,
                )

    missing = [custom_id for custom_id in original_ids if custom_id not in final_rows]
    if missing:
        raise SystemExit(f"Missing final responses for: {', '.join(missing)}")
    write_final_rows(args.output, original_ids, final_rows)


def handle_request_done(
    future: Future,
    request_futures: dict[Future, dict[str, Any]],
    tool_futures: dict[Future, dict[str, Any]],
    tools: ThreadPoolExecutor,
    conversations: dict[str, list[dict]],
    final_rows: dict[str, dict],
    output_paths_seen: set[int],
    args: argparse.Namespace,
) -> None:
    state = request_futures.pop(future)
    custom_id = str(state["custom_id"])
    round_index = int(state["round_index"])
    row = response_row(custom_id, future.result())
    write_round_row(
        round_output_path(args.output, round_index),
        row,
        round_index,
        output_paths_seen,
    )
    message = response_message(row)
    tool_calls = normalize_tool_calls(message.get("tool_calls") or [])
    if state["include_tools"] and tool_calls:
        tool_future = tools.submit(
            append_tool_results,
            conversations[custom_id],
            message,
            tool_calls,
            args,
        )
        tool_futures[tool_future] = state
        return
    final_rows[custom_id] = row


def conversation_for_round(messages: list[dict], include_tools: bool) -> list[dict]:
    if include_tools:
        return messages
    return [*messages, {"role": "user", "content": FINAL_NO_TOOLS_MESSAGE}]


def write_round_row(
    path,
    row: dict[str, Any],
    round_index: int,
    seen_rounds: set[int],
) -> None:
    truncate = round_index not in seen_rounds
    append_jsonl_row(path, row, truncate=truncate)
    seen_rounds.add(round_index)


def append_tool_results(
    messages: list[dict],
    message: dict,
    tool_calls: list[dict],
    args: argparse.Namespace,
) -> None:
    append_assistant_tool_call(messages, message, tool_calls)
    for call in tool_calls:
        result = execute_tool_call(call, args)
        messages.append(tool_result_message(call, result))


def final_pass_conversations(
    conversations: dict[str, list[dict]],
    active_ids: list[str],
) -> dict[str, list[dict]]:
    return {
        custom_id: [
            *conversations[custom_id],
            {"role": "user", "content": FINAL_NO_TOOLS_MESSAGE},
        ]
        for custom_id in active_ids
    }
