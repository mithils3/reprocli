from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def trace_output_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}_trace{output.suffix}")


def write_trace_rows(
    path: Path,
    custom_ids: list[str],
    conversations: dict[str, list[dict[str, Any]]],
    final_rows: dict[str, dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for custom_id in custom_ids:
            row = {
                "custom_id": custom_id,
                "messages": conversations[custom_id],
                "final_response": final_rows[custom_id],
                "tool_loop": final_rows[custom_id].get("tool_loop", {}),
            }
            json.dump(row, handle, ensure_ascii=False)
            handle.write("\n")


def assistant_message(message: dict[str, Any], tool_calls: list[dict[str, Any]]) -> dict[str, Any]:
    item: dict[str, Any] = {"role": "assistant"}
    if message.get("content") is not None:
        item["content"] = message["content"]
    if message.get("reasoning"):
        item["reasoning"] = message["reasoning"]
    if tool_calls:
        item["tool_calls"] = tool_calls
    return item
