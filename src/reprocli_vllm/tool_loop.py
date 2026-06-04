from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Any

from .batch_io import (
    append_assistant_tool_call,
    append_jsonl_row,
    build_batch_request,
    initial_messages,
    normalize_tool_calls,
    response_message,
    round_output_path,
    round_request_path,
    tool_result_message,
    write_extracted_rows,
    write_final_rows,
)
from .config import FINAL_NO_TOOLS_MESSAGE, REQUEST_TIMEOUT
from .openai_client import post_chat_completion_row, response_row
from .papers import Paper
from .tools.web_tools import execute_tool_call


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
    original_ids = [paper.arxiv_id for paper in papers]
    final_rows: dict[str, dict] = {}
    hit_tool_round_limit: set[str] = set()
    request_paths_seen: set[int] = set()
    output_paths_seen: set[int] = set()
    tool_call_counts = {custom_id: Counter() for custom_id in original_ids}
    tool_rounds_used = {custom_id: 0 for custom_id in original_ids}
    workers = max(1, min(args.request_workers, len(original_ids)))
    base_url = server_url.rstrip("/")
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
            request = build_batch_request(
                args.model,
                custom_id,
                messages,
                args,
                include_tools=include_tools,
                tool_choice="auto",
            )
            if args.save_round_jsonl:
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
                        hit_tool_round_limit,
                        output_paths_seen,
                        tool_call_counts,
                        args,
                    )
                    continue
                state = tool_futures.pop(future)
                future.result()
                next_round = int(state["round_index"]) + 1
                force_final = bool(state.get("force_final"))
                submit_request(
                    str(state["custom_id"]),
                    next_round,
                    include_tools=not force_final and next_round < args.tool_rounds,
                )

    missing = [custom_id for custom_id in original_ids if custom_id not in final_rows]
    if missing:
        raise SystemExit(f"Missing final responses for: {', '.join(missing)}")
    write_final_rows(args.output, original_ids, final_rows)
    write_extracted_rows(
        args.extracted_output,
        original_ids,
        final_rows,
        args.extracted_format,
    )


def handle_request_done(
    future: Future,
    request_futures: dict[Future, dict[str, Any]],
    tool_futures: dict[Future, dict[str, Any]],
    tools: ThreadPoolExecutor,
    conversations: dict[str, list[dict]],
    final_rows: dict[str, dict],
    tool_rounds_used: dict[str, int],
    hit_tool_round_limit: set[str],
    output_paths_seen: set[int],
    tool_call_counts: dict[str, Counter],
    args: argparse.Namespace,
) -> None:
    state = request_futures.pop(future)
    custom_id = str(state["custom_id"])
    round_index = int(state["round_index"])
    row = response_row(custom_id, future.result())
    if args.save_round_jsonl:
        write_round_row(
            round_output_path(args.output, round_index),
            row,
            round_index,
            output_paths_seen,
        )
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
            tool_future = tools.submit(noop)
            tool_futures[tool_future] = {**state, "force_final": True}
            return
        record_tool_calls(custom_id, tool_calls, tool_call_counts)
        if round_index + 1 >= args.tool_rounds:
            hit_tool_round_limit.add(custom_id)
        tool_future = tools.submit(
            append_tool_results,
            conversations[custom_id],
            message,
            tool_calls,
        )
        tool_futures[tool_future] = state
        return
    row["tool_loop"] = {
        "tool_rounds_used": tool_rounds_used[custom_id],
        "max_tool_rounds": args.tool_rounds,
        "hit_tool_round_limit": custom_id in hit_tool_round_limit,
    }
    final_rows[custom_id] = row


def repeated_tool_call(
    custom_id: str,
    tool_calls: list[dict],
    tool_call_counts: dict[str, Counter],
    max_repeats: int,
) -> str | None:
    counts = tool_call_counts[custom_id]
    seen_in_response: Counter = Counter()
    for call in tool_calls:
        signature = tool_call_signature(call)
        if counts[signature] + seen_in_response[signature] >= max_repeats:
            return f"{signature[0]}({signature[1]})"
        seen_in_response[signature] += 1
    return None


def record_tool_calls(
    custom_id: str,
    tool_calls: list[dict],
    tool_call_counts: dict[str, Counter],
) -> None:
    for call in tool_calls:
        tool_call_counts[custom_id][tool_call_signature(call)] += 1


def tool_call_signature(call: dict) -> tuple[str, str]:
    function = call.get("function") or {}
    name = str(function.get("name") or "unknown_tool")
    arguments = function.get("arguments") or ""
    try:
        parsed = json.loads(arguments)
    except (TypeError, json.JSONDecodeError):
        return name, str(arguments)
    return name, json.dumps(parsed, ensure_ascii=False, sort_keys=True)


def noop() -> None:
    return None


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
) -> None:
    append_assistant_tool_call(messages, message, tool_calls)
    for call in tool_calls:
        result = execute_tool_call(call)
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
