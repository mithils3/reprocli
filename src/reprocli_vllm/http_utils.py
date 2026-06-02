from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from typing import Any


def build_url(base_url: str, params: dict[str, str]) -> str:
    return base_url + "?" + urllib.parse.urlencode(params)


def http_json(
    url: str,
    timeout: float,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    status, final_url, content_type, text = http_text(
        url,
        timeout,
        data=data,
        headers=headers,
        max_chars=2_000_000,
    )
    if not 200 <= status < 300:
        raise RuntimeError(f"HTTP {status} for {url}: {text[:500]}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Expected JSON from {final_url} ({content_type}), got: {text[:500]}"
        ) from exc


def safe_http_json(
    url: str,
    timeout: float,
    *,
    headers: dict[str, str] | None = None,
) -> Any:
    try:
        return http_json(url, timeout, headers=headers)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def http_text(
    url: str,
    timeout: float,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    max_chars: int = 100_000,
) -> tuple[int, str, str, str]:
    request_headers = {
        "User-Agent": "reprocli-artifact-verifier/0.1",
        "Accept": "text/html,application/json,text/plain,*/*",
    }
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, data=data, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(max(max_chars * 4, 65536))
            charset = response.headers.get_content_charset() or "utf-8"
            return (
                response.status,
                response.geturl(),
                response.headers.get("Content-Type", ""),
                raw.decode(charset, errors="replace"),
            )
    except urllib.error.HTTPError as exc:
        raw = exc.read(max(max_chars * 4, 65536))
        charset = exc.headers.get_content_charset() or "utf-8"
        return (
            exc.code,
            exc.geturl(),
            exc.headers.get("Content-Type", ""),
            raw.decode(charset, errors="replace"),
        )


def is_http_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_probably_text(content_type: str) -> bool:
    lowered = content_type.lower()
    return any(marker in lowered for marker in ("text", "html", "json", "xml", "javascript"))


def html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?is)</(p|div|li|h[1-6]|tr)>", "\n", html)
    return clean_text(html)


def clean_text(value: str) -> str:
    text = re.sub(r"(?is)<[^>]+>", " ", value)
    text = unescape(text)
    return re.sub(r"[ \t\r\f\v]+", " ", text).replace("\n ", "\n").strip()
