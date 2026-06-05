from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .config import WEB_SYSTEM_MESSAGE, WEB_TOOLS
from .output_schema import FINAL_RESPONSE_FORMAT, normalize_score_and_tier


def initial_messages(prompt: str) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": WEB_SYSTEM_MESSAGE},
        {"role": "user", "content": prompt},
    ]


def build_chat_completion_request(
    model: str,
    custom_id: str,
    messages: list[dict[str, Any]],
    args: argparse.Namespace,
    *,
    include_tools: bool,
    tool_choice: str = "auto",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "max_tokens": args.max_tokens,
        "truncate_prompt_tokens": args.max_input_tokens,
    }
    if args.top_k is not None:
        body["top_k"] = args.top_k
    if include_tools:
        body["tools"] = WEB_TOOLS
        body["tool_choice"] = tool_choice
    else:
        body["response_format"] = FINAL_RESPONSE_FORMAT
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": body,
    }


def append_jsonl_row(path: Path, row: dict[str, Any], *, truncate: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if truncate else "a"
    with path.open(mode, encoding="utf-8") as handle:
        json.dump(row, handle, ensure_ascii=False)
        handle.write("\n")


def truncate_output_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def extracted_response(custom_id: str, row: dict[str, Any]) -> dict[str, Any]:
    message = response_message(row)
    content = message.get("content") or ""
    result: dict[str, Any] = {"custom_id": custom_id}
    parsed = parse_json_content(content)
    if parsed is None:
        result["extracted_json"] = None
        result["raw_content"] = content
        return result
    if isinstance(parsed, dict):
        result.update(normalize_score_and_tier(parsed))
        return result
    result["extracted_json"] = parsed
    return result


def parse_json_content(content: str) -> Any | None:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(content[start : end + 1])
    except json.JSONDecodeError:
        return None


def response_message(row: dict[str, Any]) -> dict[str, Any]:
    choices = row.get("response", {}).get("body", {}).get("choices") or []
    if not choices:
        return {}
    return choices[0].get("message") or {}


def normalize_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for index, call in enumerate(tool_calls):
        item = dict(call)
        if not item.get("id"):
            item["id"] = f"call_{index}"
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
