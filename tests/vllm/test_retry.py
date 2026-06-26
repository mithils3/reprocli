"""Unit tests for the transient-network retry wrapper (no real sockets)."""

from __future__ import annotations

import socket
import urllib.error

import pytest

from reprocli_vllm.vllm.retry import with_retries

# zero delays so the suite never actually sleeps
NODELAY = {"base_delay": 0.0, "max_delay": 0.0}


def _dns_error() -> urllib.error.URLError:
    # exactly what the login node raises: URLError wrapping gaierror -3
    return urllib.error.URLError(socket.gaierror(-3, "Temporary failure in name resolution"))


def test_retries_transient_dns_then_succeeds() -> None:
    calls = {"n": 0}

    def thunk() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise _dns_error()
        return "ok"

    assert with_retries(thunk, max_attempts=5, **NODELAY) == "ok"
    assert calls["n"] == 3


def test_exhausts_attempts_and_reraises() -> None:
    calls = {"n": 0}

    def thunk() -> str:
        calls["n"] += 1
        raise _dns_error()

    with pytest.raises(urllib.error.URLError):
        with_retries(thunk, max_attempts=4, **NODELAY)
    assert calls["n"] == 4  # tried exactly max_attempts, no more


def test_non_retryable_http_status_raises_immediately() -> None:
    calls = {"n": 0}

    def thunk() -> str:
        calls["n"] += 1
        raise urllib.error.HTTPError("u", 400, "Bad Request", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        with_retries(thunk, max_attempts=5, **NODELAY)
    assert calls["n"] == 1  # 400 is a caller error -- never retried


def test_retryable_http_status_is_retried() -> None:
    calls = {"n": 0}

    def thunk() -> str:
        calls["n"] += 1
        if calls["n"] < 2:
            raise urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)
        return "ok"

    assert with_retries(thunk, max_attempts=5, **NODELAY) == "ok"
    assert calls["n"] == 2


def test_non_network_error_not_retried() -> None:
    calls = {"n": 0}

    def thunk() -> str:
        calls["n"] += 1
        raise ValueError("bad json")

    with pytest.raises(ValueError):
        with_retries(thunk, max_attempts=5, **NODELAY)
    assert calls["n"] == 1
