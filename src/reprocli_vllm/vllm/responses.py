"""Chat-completions to OpenAI Responses adapter for api.openai.com.

The harness builds chat-completions bodies and reads chat-completions rows. GPT
reasoning models refuse function tools together with ``reasoning_effort`` on
/v1/chat/completions, so OpenAI calls go to /v1/responses instead. This module
translates the request out and the response back, so both loops still see
chat-shaped messages.

Reasoning carry-over: a stateless call (``store: false``) returns reasoning items
with ``encrypted_content``. They ride on the assistant message under REASONING_KEY,
and the next request re-emits them before that turn's function_call items, as the
API requires when no server-side state is kept.
"""

from __future__ import annotations

from typing import Any

REASONING_KEY = "_openai_reasoning_items"
PRIVATE_PREFIX = "_openai_"
RESPONSES_PATH = "/v1/responses"


def strip_openai_private(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Copies of ``messages`` without the private ``_openai_*`` keys, for other providers."""
    return [
        {key: value for key, value in message.items() if not key.startswith(PRIVATE_PREFIX)}
        for message in messages
    ]


def _text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return str(content)


def _tool(tool: dict[str, Any]) -> dict[str, Any]:
    fn = tool.get("function", tool)
    return {
        "type": "function",
        "name": fn["name"],
        "description": fn.get("description", ""),
        "parameters": fn.get("parameters", {"type": "object", "properties": {}}),
        "strict": bool(fn.get("strict", False)),
    }


def _tool_choice(choice: Any) -> Any:
    if isinstance(choice, str):
        return choice
    if isinstance(choice, dict):
        name = (choice.get("function") or {}).get("name")
        if name:
            return {"type": "function", "name": name}
    return "auto"


def _text_format(response_format: dict[str, Any]) -> dict[str, Any]:
    kind = response_format.get("type")
    if kind == "json_schema":
        schema = response_format.get("json_schema") or {}
        return {
            "type": "json_schema",
            "name": schema.get("name", "output"),
            "schema": schema.get("schema", {}),
            "strict": bool(schema.get("strict", False)),
        }
    return {"type": kind or "text"}


def request_to_responses(body: dict[str, Any]) -> dict[str, Any]:
    """Translate a chat-completions body into a /v1/responses body."""
    out: dict[str, Any] = {
        "model": body["model"],
        "input": [],
        "store": False,
        "include": ["reasoning.encrypted_content"],
    }
    instructions: list[str] = []
    for message in body.get("messages") or []:
        role = message.get("role")
        if role in ("system", "developer"):
            instructions.append(_text(message.get("content")))
        elif role == "user":
            out["input"].append({"role": "user", "content": message.get("content") or ""})
        elif role == "assistant":
            out["input"].extend(message.get(REASONING_KEY) or [])
            text = _text(message.get("content"))
            if text:
                out["input"].append({"role": "assistant", "content": text})
            for call in message.get("tool_calls") or []:
                fn = call.get("function") or {}
                out["input"].append({
                    "type": "function_call",
                    "call_id": call.get("id", ""),
                    "name": fn.get("name", ""),
                    "arguments": fn.get("arguments") or "{}",
                })
        elif role == "tool":
            out["input"].append({
                "type": "function_call_output",
                "call_id": message.get("tool_call_id", ""),
                "output": _text(message.get("content")),
            })
    if instructions:
        out["instructions"] = "\n\n".join(text for text in instructions if text)
    if body.get("tools"):
        out["tools"] = [_tool(tool) for tool in body["tools"]]
    if "tool_choice" in body:
        out["tool_choice"] = _tool_choice(body["tool_choice"])
    limit = body.get("max_completion_tokens", body.get("max_tokens"))
    if limit is not None:
        out["max_output_tokens"] = limit
    if body.get("reasoning_effort"):
        out["reasoning"] = {"effort": body["reasoning_effort"]}
    if body.get("service_tier"):
        out["service_tier"] = body["service_tier"]
    for key in ("temperature", "top_p"):
        if key in body:
            out[key] = body[key]
    if body.get("response_format"):
        out["text"] = {"format": _text_format(body["response_format"])}
    return out


def response_to_chat(response: dict[str, Any]) -> dict[str, Any]:
    """Translate a /v1/responses object into a chat-completions-shaped response."""
    texts: list[str] = []
    calls: list[dict[str, Any]] = []
    reasoning: list[dict[str, Any]] = []
    for item in response.get("output") or []:
        kind = item.get("type")
        if kind == "message":
            for part in item.get("content") or []:
                if part.get("type") == "output_text":
                    texts.append(part.get("text", ""))
        elif kind == "function_call":
            calls.append({
                "id": item.get("call_id") or item.get("id", ""),
                "type": "function",
                "function": {
                    "name": item.get("name", ""),
                    "arguments": item.get("arguments") or "{}",
                },
            })
        elif kind == "reasoning":
            reasoning.append(item)
    message: dict[str, Any] = {"role": "assistant", "content": "".join(texts) if texts else None}
    if calls:
        message["tool_calls"] = calls
    if reasoning:
        message[REASONING_KEY] = reasoning
    incomplete = (response.get("incomplete_details") or {}).get("reason")
    if calls:
        finish = "tool_calls"
    elif incomplete == "max_output_tokens":
        finish = "length"
    else:
        finish = "stop"
    usage = response.get("usage") or {}
    prompt = int(usage.get("input_tokens") or 0)
    completion = int(usage.get("output_tokens") or 0)
    return {
        "id": response.get("id"),
        "object": "chat.completion",
        "model": response.get("model"),
        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": int(usage.get("total_tokens") or prompt + completion),
            "prompt_tokens_details": {
                "cached_tokens": int((usage.get("input_tokens_details") or {}).get("cached_tokens") or 0),
            },
            "completion_tokens_details": {
                "reasoning_tokens": int((usage.get("output_tokens_details") or {}).get("reasoning_tokens") or 0),
            },
        },
        "service_tier": response.get("service_tier"),
    }
