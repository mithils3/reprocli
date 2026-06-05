from __future__ import annotations

import argparse
import csv
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


def build_batch_request(
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
    if args.chat_template_kwargs:
        body["chat_template_kwargs"] = args.chat_template_kwargs
    if include_tools:
        body["tools"] = WEB_TOOLS
        body["tool_choice"] = tool_choice
    elif not args.disable_structured_final_output:
        # vLLM >= 0.12.0 removed the request-level `guided_json` /
        # `guided_decoding_backend` fields. The OpenAI-standard
        # `response_format` json_schema is the supported, version-stable way to
        # constrain the final answer; pick the decoding backend at server
        # startup via `--structured-outputs-config.backend`.
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


def round_request_path(path: Path, round_index: int) -> Path:
    if round_index == 0:
        return path
    return path.with_name(f"{path.stem}_round{round_index}{path.suffix}")


def round_output_path(path: Path, round_index: int) -> Path:
    return path.with_name(f"{path.stem}_round{round_index}{path.suffix}")


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


def write_extracted_rows(
    path: Path,
    custom_ids: list[str],
    rows: dict[str, dict[str, Any]],
    output_format: str,
) -> None:
    extracted = [extracted_response(custom_id, rows[custom_id]) for custom_id in custom_ids]
    path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "csv":
        write_extracted_csv(path, extracted)
        return
    with path.open("w", encoding="utf-8") as handle:
        for row in extracted:
            json.dump(row, handle, ensure_ascii=False)
            handle.write("\n")


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


def write_extracted_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key)) for key in fieldnames})


def csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


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
