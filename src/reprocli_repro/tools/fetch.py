"""Read-only web fetch for the reproduction agent.

The agent has no general web-search tool (datacenter IPs get bot-challenged by the
keyless search endpoints), but it CAN fetch a public URL it already knows or can
construct: the PyTorch install docs / wheel index to work out the right
aarch64+CUDA torch build, a raw README / requirements file, a release-notes page.

This reuses the classifier's ``fetch_url`` (urllib + HTML→text) verbatim; the only
adapter is the ``(arguments, ctx)`` handler signature the repro loop dispatches
through — ``fetch_url`` itself needs no episode context.
"""

from __future__ import annotations

from typing import Any

from reprocli_vllm.config.config import TOOL_MAX_CHARS, function_tool
from reprocli_vllm.tools.web_tools import fetch_url_tool

from reprocli_repro.context import ExecutionContext


def fetch_url(arguments: dict[str, Any], ctx: ExecutionContext) -> dict[str, Any]:
    """Fetch a public http(s) URL (``ctx`` unused — fetch needs no episode state)."""
    return fetch_url_tool(arguments)


FETCH_TOOLS = [
    function_tool(
        "fetch_url",
        "Fetch a direct public http(s) URL and return its status, final URL, and "
        "text (HTML is reduced to text). There is no general web-search tool — you "
        "fetch URLs you already know or can construct (e.g. the PyTorch install page "
        "or wheel index to find the right aarch64/CUDA torch build, a raw README or "
        "requirements file, a docs/release page).",
        {
            "url": {"type": "string", "description": "HTTP or HTTPS URL."},
            "max_chars": {"type": "integer", "default": TOOL_MAX_CHARS},
        },
        ["url"],
    ),
]

FETCH_TOOL_HANDLERS = {"fetch_url": fetch_url}
