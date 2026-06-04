from __future__ import annotations

import json
from typing import Any


def mcp_tool_result(tool_name: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": not bool(result.get("isError")),
        "tool": tool_name,
        "result": compact_mcp_result(result),
    }


def compact_mcp_result(result: dict[str, Any]) -> dict[str, Any]:
    text = mcp_text(result)
    parsed = parse_json_text(text)
    compact: dict[str, Any] = {"text": text}
    if parsed is not None:
        compact["json"] = parsed
    return compact


def mcp_text(result: dict[str, Any]) -> str:
    pieces = []
    for item in result.get("content") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text":
            pieces.append(str(item.get("text") or ""))
        resource = item.get("resource")
        if isinstance(resource, dict) and resource.get("text"):
            pieces.append(str(resource.get("text")))
    return "\n".join(piece for piece in pieces if piece).strip()


def parse_json_text(text: str) -> Any | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
