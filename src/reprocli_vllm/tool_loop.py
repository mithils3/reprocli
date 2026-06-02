from __future__ import annotations

import argparse
import sys

from .batch_io import (
    append_assistant_tool_call,
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
from .openai_client import run_requests
from .papers import Paper
from .web_tools import execute_tool_call


def run_tool_loop(
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
        write_batch_requests(
            request_path,
            args.model,
            active_ids,
            conversations,
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
