"""OpenAI flex-tier policy for chat-completions requests.

``REPROCLI_SERVICE_TIER=flex`` puts ``service_tier: flex`` on every body. Flex is the
half-price tier that waits for spare capacity, so it answers 429 or 408 when the queue
is full and a long generation can outlast the read timeout. A flex request is retried
with backoff for a fixed budget. When the budget runs out, the same request is resent
at standard price with ``service_tier`` removed, and a ``flex-fallback`` line is
written to stderr. OpenAI does not bill a flex request that came back 429.
"""

from __future__ import annotations

import os
import socket
import sys
import time
import urllib.error
from typing import Any, Callable

from reprocli_vllm.vllm.retry import annotate_http_error

ENV_SERVICE_TIER = "REPROCLI_SERVICE_TIER"
FLEX = "flex"
FLEX_MIN_READ_TIMEOUT = 900.0
FLEX_RETRY_BUDGET = 600.0
FLEX_BACKOFF_START = 15.0
FLEX_BACKOFF_CAP = 120.0
FLEX_RETRY_CODES = frozenset({408, 429})


def service_tier() -> str | None:
    """The ``service_tier`` every body carries, or None when the env var is unset."""
    value = (os.environ.get(ENV_SERVICE_TIER) or "").strip()
    return value or None


def apply_service_tier(body: dict[str, Any]) -> None:
    """Attach the env-configured ``service_tier`` in-place; a body's own value wins."""
    tier = service_tier()
    if tier is not None:
        body.setdefault("service_tier", tier)


def is_flex(body: dict[str, Any]) -> bool:
    return body.get("service_tier") == FLEX


def read_timeout(timeout: float, body: dict[str, Any]) -> float:
    """The socket timeout for one POST: at least 900 s on the flex tier."""
    return max(timeout, FLEX_MIN_READ_TIMEOUT) if is_flex(body) else timeout


def without_service_tier(body: dict[str, Any]) -> dict[str, Any]:
    standard = dict(body)
    standard.pop("service_tier", None)
    return standard


def is_flex_retryable(exc: BaseException) -> bool:
    """A 429 or 408, or a read timeout. Other failures are not flex capacity signals."""
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in FLEX_RETRY_CODES
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return True
    return isinstance(exc, urllib.error.URLError) and isinstance(
        exc.reason, (socket.timeout, TimeoutError)
    )


def post_flex(
    send_flex: Callable[[dict[str, Any]], Any],
    send_standard: Callable[[dict[str, Any]], Any],
    body: dict[str, Any],
    *,
    what: str,
    budget: float = FLEX_RETRY_BUDGET,
) -> Any:
    """Send ``body`` on flex, retrying capacity errors for ``budget`` seconds.

    The budget starts at the first failure, so a single 900 s read timeout still
    leaves the full retry window. After the budget, the request is resent once through
    ``send_standard`` with ``service_tier`` removed.
    """
    delay = FLEX_BACKOFF_START
    first_failure: float | None = None
    while True:
        try:
            return send_flex(body)
        except Exception as exc:  # noqa: BLE001 -- re-raised below unless a flex signal
            if isinstance(exc, urllib.error.HTTPError):
                annotate_http_error(exc)
            if not is_flex_retryable(exc):
                raise
            now = time.monotonic()
            if first_failure is None:
                first_failure = now
            elapsed = now - first_failure
            if elapsed >= budget:
                break
            wait = min(delay, budget - elapsed)
            print(
                f"[flex] {what}: {type(exc).__name__}: {exc} -- "
                f"retrying in {wait:.1f}s ({elapsed:.0f}/{budget:.0f}s of flex budget used)",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(wait)
            delay = min(FLEX_BACKOFF_CAP, delay * 2)
    print(
        f"flex-fallback {what}: no flex capacity within {budget:.0f}s; "
        "resending at standard price without service_tier",
        file=sys.stderr,
        flush=True,
    )
    return send_standard(without_service_tier(body))
