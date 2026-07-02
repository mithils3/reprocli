"""Direct URL fetch + tool-argument parsing shared across agent toolsets.

``fetch_url_tool`` is the urllib + HTML->text fetch used by the reproduction
agent (``reprocli_repro.tools.fetch``); ``parse_tool_arguments`` normalizes the
JSON ``arguments`` payload of a model tool call for every dispatcher.
"""

from __future__ import annotations

import json
from typing import Any

from reprocli_vllm.config.config import TOOL_MAX_CHARS, TOOL_TIMEOUT

from .http_utils import html_to_text, http_text, is_http_url, is_probably_text


def fetch_url_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    url = str(arguments.get("url", "")).strip()
    max_chars = min(int(arguments.get("max_chars") or TOOL_MAX_CHARS), TOOL_MAX_CHARS)
    if not is_http_url(url):
        return {"ok": False, "error": f"Only http(s) URLs are supported: {url}"}
    status, final_url, content_type, text = http_text(url, TOOL_TIMEOUT, max_chars=max_chars)
    body = text if is_probably_text(content_type) else ""
    if "html" in content_type.lower():
        body = html_to_text(body)
    return {
        "ok": 200 <= status < 400,
        "url": url,
        "status": status,
        "final_url": final_url,
        "content_type": content_type,
        "text": body[:max_chars],
    }


def parse_tool_arguments(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value in {None, ""}:
        return {}
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    raise ValueError(f"Tool arguments must be a JSON object, got {value!r}")
