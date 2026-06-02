from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .config import WEB_SYSTEM_MESSAGE, WEB_TOOLS


def initial_messages(prompt: str, *, include_web_system: bool) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if include_web_system:
        messages.append({"role": "system", "content": WEB_SYSTEM_MESSAGE})
    messages.append({"role": "user", "content": prompt})
    return messages


def write_batch_requests(
    output_path: Path,
    model: str,
    custom_ids: list[str],
    conversations: dict[str, list[dict[str, Any]]],
    args: argparse.Namespace,
    *,
    include_tools: bool,
    tool_choice: str = "auto",
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for custom_id in custom_ids:
            body: dict[str, Any] = {
                "model": model,
                "messages": conversations[custom_id],
                "temperature": args.temperature,
                "top_p": args.top_p,
                "max_tokens": args.max_tokens,
            }
            if include_tools:
                body["tools"] = WEB_TOOLS
                body["tool_choice"] = tool_choice
            request = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": body,
            }
            json.dump(request, handle, ensure_ascii=False)
            handle.write("\n")


def round_request_path(path: Path, round_index: int) -> Path:
    if round_index == 0:
        return path
    return path.with_name(f"{path.stem}_round{round_index}{path.suffix}")


def round_output_path(path: Path, round_index: int) -> Path:
    return path.with_name(f"{path.stem}_round{round_index}{path.suffix}")


def read_batch_output(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_final_rows(
    path: Path,
    custom_ids: list[str],
    rows: dict[str, dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for custom_id in custom_ids:
            json.dump(rows[custom_id], handle, ensure_ascii=False)
            handle.write("\n")


def response_message(row: dict[str, Any]) -> dict[str, Any]:
    choices = row.get("response", {}).get("body", {}).get("choices") or []
    if not choices:
        return {}
    return choices[0].get("message") or {}


def normalize_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for index, call in enumerate(tool_calls):
        item = dict(call)
        item.setdefault("id", f"call_{index}")
        item.setdefault("function", {})
        normalized.append(item)
    return normalized


def append_assistant_tool_call(
    messages: list[dict[str, Any]],
    message: dict[str, Any],
    tool_calls: list[dict[str, Any]],
) -> None:
    assistant_message: dict[str, Any] = {
        "role": "assistant",
        "tool_calls": tool_calls,
    }
    if message.get("content"):
        assistant_message["content"] = message["content"]
    if message.get("reasoning"):
        assistant_message["reasoning"] = message["reasoning"]
    messages.append(assistant_message)


def tool_result_message(call: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    function = call.get("function") or {}
    return {
        "role": "tool",
        "tool_call_id": call.get("id", ""),
        "name": function.get("name", "unknown_tool"),
        "content": json.dumps(result, ensure_ascii=False),
    }
