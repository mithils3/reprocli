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

Which model id to send in each request is resolved the same way: ask the server
what it serves (``GET /v1/models``) and use the single advertised model, unless an
explicit name is given via ``--served-model-name`` / ``REPROCLI_SERVED_MODEL``.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV_SERVER_URL = "REPROCLI_SERVER_URL"
ENV_ENDPOINT_FILE = "REPROCLI_ENDPOINT_FILE"
ENV_SERVED_MODEL = "REPROCLI_SERVED_MODEL"
ENV_API_KEY = "REPROCLI_API_KEY"
MODELS_FETCH_TIMEOUT = 30.0


def resolve_api_key(cli_value: str | None = None) -> str | None:
    """Bearer token for an authenticated endpoint (e.g. OpenRouter), or None.

    A local self-served vLLM needs no key, so this is empty by default and the
    request goes out unauthenticated exactly as before. We only read the explicit
    ``REPROCLI_API_KEY`` (or ``OPENROUTER_API_KEY``) — never ``OPENAI_API_KEY`` —
    so an OpenAI key sitting in the shell can't leak to a different provider's URL.
    """
    value = cli_value or os.environ.get(ENV_API_KEY) or os.environ.get("OPENROUTER_API_KEY")
    return (value or "").strip() or None


def auth_headers(cli_value: str | None = None) -> dict[str, str]:
    """``Authorization: Bearer`` header when a key is configured, else ``{}``."""
    key = resolve_api_key(cli_value)
    return {"Authorization": f"Bearer {key}"} if key else {}


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


def fetch_served_models(base_url: str, timeout: float = MODELS_FETCH_TIMEOUT) -> list[str]:
    """Return the model ids the server advertises at ``/v1/models`` (may be empty)."""
    url = f"{base_url.rstrip('/')}/v1/models"
    request = urllib.request.Request(url, headers=auth_headers(), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"could not list models at {url}: {exc}") from exc
    entries = data.get("data") if isinstance(data, dict) else None
    return [
        entry["id"]
        for entry in entries or []
        if isinstance(entry, dict) and isinstance(entry.get("id"), str) and entry["id"]
    ]


def resolve_served_model(
    base_url: str,
    cli_value: str | None = None,
    timeout: float = MODELS_FETCH_TIMEOUT,
) -> str:
    """Pick the model id to send in requests against an attached server.

    Priority for the name: ``--served-model-name`` flag > ``REPROCLI_SERVED_MODEL``
    env > the model the server advertises at ``/v1/models``. With no override we use
    the single advertised model (the common case: one model per serve job); if the
    server lists several we take the first and say so. An explicit override is used
    verbatim but checked against the advertised list so a typo fails loudly here
    rather than as a per-request 404.
    """
    available = fetch_served_models(base_url, timeout)
    override = (cli_value or os.environ.get(ENV_SERVED_MODEL) or "").strip()
    if override:
        if available and override not in available:
            raise RuntimeError(
                f"requested model {override!r} is not served by {base_url}; "
                f"available: {available}"
            )
        return override
    if not available:
        raise RuntimeError(
            f"{base_url}/v1/models advertised no models; cannot auto-select. "
            f"Pass --served-model-name to choose explicitly."
        )
    if len(available) > 1:
        print(
            f"Server advertises {len(available)} models {available}; using the "
            f"first ({available[0]!r}). Pass --served-model-name to override.",
            file=sys.stderr,
        )
    return available[0]
