"""Resolve which served endpoint the runner should talk to.

This is the consumer side of the reprocli_serve seam. The agent core is
provider-agnostic: it only POSTs chat-completions to a base URL, so swapping the
model behind it is purely a URL change. A base URL can come from three places, in
priority order:

1. an explicit ``--vllm-server-url`` flag,
2. the ``REPROCLI_SERVER_URL`` environment variable,
3. an endpoint file named by ``REPROCLI_ENDPOINT_FILE`` (the JSON that
   reprocli_serve publishes; we read its ``base_url`` field).

If none is set, the resolver returns ``None`` and the runner falls back to its
embedded local server exactly as before — so default behavior is unchanged.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

ENV_SERVER_URL = "REPROCLI_SERVER_URL"
ENV_ENDPOINT_FILE = "REPROCLI_ENDPOINT_FILE"


def normalize_server_url(value: str) -> str:
    """Strip a trailing slash and a trailing ``/v1`` so callers can append paths."""
    url = value.strip().rstrip("/")
    if url.endswith("/v1"):
        url = url[:-3]
    return url


def base_url_from_endpoint_file(path: Path) -> str | None:
    """Read the ``base_url`` field from a published endpoint JSON file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    url = data.get("base_url")
    return url if isinstance(url, str) and url else None


def resolve_server_url(cli_value: str | None) -> str | None:
    """Return the normalized base URL to attach to, or None for the embedded server."""
    if cli_value:
        return normalize_server_url(cli_value)
    env_url = os.environ.get(ENV_SERVER_URL)
    if env_url:
        return normalize_server_url(env_url)
    endpoint_file = os.environ.get(ENV_ENDPOINT_FILE)
    if endpoint_file:
        url = base_url_from_endpoint_file(Path(endpoint_file))
        if url:
            return normalize_server_url(url)
    return None
