from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any

from reprocli_vllm.vllm.endpoint import (
    auth_headers,
    chat_template_kwargs,
    openrouter_provider_routing,
    reasoning_effort,
    resolve_api_key,
)
from reprocli_vllm.vllm.retry import with_retries

# Universally-supported degrade for a json_schema response_format the routed
# provider can't honor.
JSON_OBJECT_RESPONSE_FORMAT = {"type": "json_object"}


def apply_provider_routing(body: dict[str, Any]) -> None:
    """Pin the OpenRouter upstream provider in-place when one is configured.

    Single chokepoint for every chat-completion path (repro loop, classifier/auditor
    tool loop, context compaction), so the pin applies uniformly. No-op when unset,
    and never clobbers a ``provider`` block a caller already placed on the body.
    """
    provider = openrouter_provider_routing()
    if provider is not None:
        body.setdefault("provider", provider)


def apply_chat_template_kwargs(body: dict[str, Any]) -> None:
    """Attach env-configured ``chat_template_kwargs`` in-place, if any.

    Same chokepoint and same never-clobber contract as ``apply_provider_routing``:
    a body that already carries the field wins, so a caller can still override
    per request. No-op when the env var is unset (every non-DeepSeek sweep).
    """
    kwargs = chat_template_kwargs()
    if kwargs is not None:
        body.setdefault("chat_template_kwargs", kwargs)


def apply_reasoning_effort(body: dict[str, Any]) -> None:
    """Attach the env-configured ``reasoning_effort`` in-place, if any.

    Same chokepoint and same never-clobber contract as the two above, so one env var
    sets the depth for the repro loop, the auditor tool loop, and compaction alike.
    No-op when unset (every local-vLLM sweep).
    """
    effort = reasoning_effort()
    if effort is not None:
        body.setdefault("reasoning_effort", effort)


def prepare_structured_output(body: dict[str, Any]) -> None:
    """Make a ``json_schema`` response_format actually enforceable on OpenRouter.

    OpenRouter only *enforces* structured outputs on upstreams that advertise the
    ``structured_outputs`` capability; others silently ignore ``response_format``
    or reject it with a 400 ("This response_format type is unavailable now" --
    e.g. DeepSeek/MiniMax first-party). Marking the schema ``strict`` and setting
    ``provider.require_parameters`` tells OpenRouter to route ONLY to a provider
    that can honor the schema (see the OpenRouter structured-outputs + provider-
    routing docs). If none is reachable it 404s, which the request path degrades
    to ``json_object`` rather than failing the run.

    Gated on an API key being configured: a self-hosted vLLM needs no key and
    enforces ``json_schema`` natively, so we leave its body untouched (and never
    hand it a ``provider`` block it doesn't understand).
    """
    if resolve_api_key() is None:
        return
    response_format = body.get("response_format")
    if not isinstance(response_format, dict) or response_format.get("type") != "json_schema":
        return
    response_format = dict(response_format)
    schema = response_format.get("json_schema")
    if isinstance(schema, dict):
        # Copy so we never mutate the shared module-level schema constant.
        response_format["json_schema"] = {"strict": True, **schema}
    body["response_format"] = response_format
    provider = dict(body.get("provider") or {})
    provider.setdefault("require_parameters", True)
    body["provider"] = provider


def post_chat_completion_row(
    base_url: str,
    row: dict[str, Any],
    timeout: float,
    *,
    stream: bool = False,
) -> Any:
    apply_provider_routing(row["body"])
    apply_chat_template_kwargs(row["body"])
    apply_reasoning_effort(row["body"])
    prepare_structured_output(row["body"])
    if stream:
        return stream_chat_completion(base_url, row, timeout)
    return post_vllm_chat_completion(base_url, row["body"], timeout)


def response_row(custom_id: str, body: Any) -> dict[str, Any]:
    return {
        "custom_id": custom_id,
        "response": {
            "status_code": 200,
            "body": body,
        },
    }


def post_vllm_chat_completion(base_url: str, body: dict[str, Any], timeout: float) -> Any:
    try:
        return _post_body(base_url, body, timeout)
    except urllib.error.HTTPError as exc:
        downgraded = downgrade_response_format_on_reject(body, exc)
        if downgraded is None:
            raise
        print(
            f"[response_format] no reachable provider enforces json_schema "
            f"(HTTP {exc.code}); retrying once with json_object",
            file=sys.stderr,
            flush=True,
        )
        return _post_body(base_url, downgraded, timeout)


def _post_body(base_url: str, body: dict[str, Any], timeout: float) -> Any:
    data = json.dumps(body).encode("utf-8")

    def _do() -> Any:
        request = urllib.request.Request(
            f"{base_url}/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                **auth_headers(),
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    return with_retries(_do, what=f"chat.completions POST {base_url}")


def downgrade_response_format_on_reject(
    body: dict[str, Any], exc: urllib.error.HTTPError
) -> dict[str, Any] | None:
    """A copy of ``body`` with a json_schema response_format swapped for
    json_object, or ``None`` when the rejection isn't a structured-output one.

    Two ways OpenRouter refuses a ``json_schema`` request when no reachable
    upstream can enforce it:

    * a routed provider rejects it -- 400 *"This response_format type is
      unavailable now"* (DeepSeek/MiniMax first-party), or
    * ``provider.require_parameters`` (added by ``prepare_structured_output``)
      finds no capable provider -- 404 *"No endpoints found that can handle the
      requested parameters"* / *"No allowed providers are available"*.

    Either, unhandled, kills the whole run (e.g. every audit on its tools-off
    final pass). json_object is universally supported and, paired with our
    tolerant JSON parsing + schema finalize, is a safe degrade; we also drop
    ``require_parameters`` so the retry isn't gated on a capability we no longer
    request. A self-hosted vLLM speaks json_schema natively and never hits this.
    (The caller's prompts already contain the word "json", which json_object
    needs.)
    """
    rf = body.get("response_format")
    if not isinstance(rf, dict) or rf.get("type") != "json_schema":
        return None
    detail = (getattr(exc, "reprocli_body", "") or "").lower()
    provider_rejected = "response_format" in detail and any(
        token in detail for token in ("unavailable", "unsupported", "not support")
    )
    no_capable_provider = exc.code == 404 and (
        "requested parameters" in detail or "allowed providers" in detail
    )
    if not (provider_rejected or no_capable_provider):
        return None
    downgraded = dict(body)
    downgraded["response_format"] = dict(JSON_OBJECT_RESPONSE_FORMAT)
    provider = dict(downgraded.get("provider") or {})
    provider.pop("require_parameters", None)
    if provider:
        downgraded["provider"] = provider
    else:
        downgraded.pop("provider", None)
    return downgraded


def stream_chat_completion(base_url: str, row: dict[str, Any], timeout: float) -> Any:
    body = dict(row["body"])
    body["stream"] = True
    print(f"\n--- streaming {row['custom_id']} ---", file=sys.stderr, flush=True)
    try:
        return post_streaming_chat_completion(base_url, body, timeout)
    finally:
        print(f"\n--- end stream {row['custom_id']} ---", file=sys.stderr, flush=True)


def post_streaming_chat_completion(
    base_url: str,
    body: dict[str, Any],
    timeout: float,
) -> Any:
    data = json.dumps(body).encode("utf-8")

    def _do() -> Any:
        request = urllib.request.Request(
            f"{base_url}/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                **auth_headers(),
            },
            method="POST",
        )
        builder = StreamedResponseBuilder(body["model"])
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or line.startswith(":") or not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                builder.add_chunk(json.loads(payload))
        return builder.response()

    return with_retries(_do, what=f"chat.completions stream {base_url}")


class StreamedResponseBuilder:
    def __init__(self, model: str) -> None:
        self.model = model
        self.role = "assistant"
        self.content_parts: list[str] = []
        self.reasoning_parts: list[str] = []
        self.tool_calls: dict[int, dict[str, Any]] = {}
        self.finish_reason: str | None = None
        self.usage: dict[str, Any] | None = None

    def add_chunk(self, chunk: dict[str, Any]) -> None:
        # The final SSE chunk (with stream_options.include_usage) carries usage and
        # an empty choices list — capture it before the early return below.
        if chunk.get("usage"):
            self.usage = chunk["usage"]
        choices = chunk.get("choices") or []
        if not choices:
            return
        choice = choices[0]
        self.finish_reason = choice.get("finish_reason") or self.finish_reason
        delta = choice.get("delta") or {}
        self.role = delta.get("role") or self.role
        self.add_text_delta(delta)
        self.add_tool_call_deltas(delta.get("tool_calls") or [])

    def add_text_delta(self, delta: dict[str, Any]) -> None:
        content = delta.get("content")
        if content:
            self.content_parts.append(content)
            print(content, end="", file=sys.stderr, flush=True)
        reasoning = delta.get("reasoning") or delta.get("reasoning_content")
        if reasoning:
            self.reasoning_parts.append(reasoning)
            print(reasoning, end="", file=sys.stderr, flush=True)

    def add_tool_call_deltas(self, deltas: list[dict[str, Any]]) -> None:
        for delta in deltas:
            index = int(delta.get("index", len(self.tool_calls)))
            call = self.tool_calls.setdefault(
                index,
                {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
            )
            if delta.get("id"):
                call["id"] += delta["id"]
            function = delta.get("function") or {}
            if function.get("name"):
                call["function"]["name"] += function["name"]
            if function.get("arguments"):
                call["function"]["arguments"] += function["arguments"]
                print(function["arguments"], end="", file=sys.stderr, flush=True)

    def response(self) -> dict[str, Any]:
        message: dict[str, Any] = {
            "role": self.role,
            "content": "".join(self.content_parts) or None,
        }
        if self.reasoning_parts:
            message["reasoning"] = "".join(self.reasoning_parts)
        if self.tool_calls:
            message["tool_calls"] = [
                self.tool_calls[index] for index in sorted(self.tool_calls)
            ]
        out: dict[str, Any] = {
            "id": "streamed",
            "object": "chat.completion",
            "model": self.model,
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": self.finish_reason or "stop",
                }
            ],
        }
        if self.usage:
            out["usage"] = self.usage
        return out
