from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
from html import unescape
from typing import Any

from .http_utils import (
    build_url,
    clean_text,
    html_to_text,
    http_json,
    http_text,
    is_http_url,
    is_probably_text,
    safe_http_json,
)


def execute_tool_call(call: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    function = call.get("function") or {}
    name = function.get("name", "")
    try:
        arguments = parse_tool_arguments(function.get("arguments", {}))
        if name == "web_search":
            result = web_search_tool(arguments, args)
        elif name == "fetch_url":
            result = fetch_url_tool(arguments, args)
        elif name == "github_repo":
            result = github_repo_tool(arguments, args)
        elif name == "huggingface_repo":
            result = huggingface_repo_tool(arguments, args)
        else:
            result = {"ok": False, "error": f"Unknown tool: {name}"}
    except Exception as exc:
        result = {"ok": False, "tool": name, "error": f"{type(exc).__name__}: {exc}"}
    return limit_tool_result(result, args.tool_max_chars)


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


def limit_tool_result(result: dict[str, Any], max_chars: int) -> dict[str, Any]:
    encoded = json.dumps(result, ensure_ascii=False)
    if len(encoded) <= max_chars:
        return result
    return {
        "ok": bool(result.get("ok")),
        "truncated": True,
        "max_chars": max_chars,
        "result_excerpt": encoded[:max_chars],
    }


def web_search_tool(arguments: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    query = str(arguments.get("query", "")).strip()
    max_results = int(arguments.get("max_results") or 5)
    max_results = max(1, min(max_results, 10))
    if not query:
        return {"ok": False, "error": "Missing query"}
    url = build_url("https://html.duckduckgo.com/html/", {"q": query})
    status, final_url, content_type, text = http_text(url, args.tool_timeout, max_chars=120000)
    matches = re.findall(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    results = [
        {
            "title": clean_text(title_html),
            "url": normalize_duckduckgo_url(unescape(href)),
            "snippet": "",
        }
        for href, title_html in matches[:max_results]
    ]
    return {
        "ok": bool(results),
        "provider": "duckduckgo_html",
        "query": query,
        "status": status,
        "final_url": final_url,
        "content_type": content_type,
        "results": results,
        "warning": "DuckDuckGo HTML is simple/no-key, but can be blocked or incomplete.",
    }


def fetch_url_tool(arguments: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    url = str(arguments.get("url", "")).strip()
    max_chars = int(arguments.get("max_chars") or args.tool_max_chars)
    if not is_http_url(url):
        return {"ok": False, "error": f"Only http(s) URLs are supported: {url}"}
    status, final_url, content_type, text = http_text(url, args.tool_timeout, max_chars=max_chars)
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


def github_repo_tool(arguments: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    repo = parse_github_repo(str(arguments.get("repo", "")))
    if not repo:
        return {"ok": False, "error": "Could not parse GitHub repo"}
    owner, name = repo
    headers = github_headers()
    repo_url = f"https://api.github.com/repos/{owner}/{name}"
    repo_data = http_json(repo_url, args.tool_timeout, headers=headers)
    default_branch = repo_data.get("default_branch") or "main"
    encoded_branch = urllib.parse.quote(default_branch, safe="")
    contents = safe_http_json(
        f"{repo_url}/contents?ref={encoded_branch}",
        args.tool_timeout,
        headers=headers,
    )
    releases = safe_http_json(f"{repo_url}/releases?per_page=10", args.tool_timeout, headers=headers)
    files, directories = github_root_names(contents)
    return {
        "ok": True,
        "provider": "github",
        "repo": f"{owner}/{name}",
        "html_url": repo_data.get("html_url"),
        "description": repo_data.get("description"),
        "private": repo_data.get("private"),
        "archived": repo_data.get("archived"),
        "default_branch": default_branch,
        "size_kb": repo_data.get("size"),
        "stars": repo_data.get("stargazers_count"),
        "pushed_at": repo_data.get("pushed_at"),
        "license": (repo_data.get("license") or {}).get("spdx_id"),
        "root_files": files[:80],
        "root_dirs": directories[:80],
        "releases": github_release_names(releases),
        "code_markers": find_markers(files + directories, ("train", "eval", "config", "src", "readme")),
        "checkpoint_markers": find_markers(files + directories, ("checkpoint", "ckpt", "weight", "pth")),
    }


def huggingface_repo_tool(arguments: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    parsed = parse_huggingface_repo(
        str(arguments.get("repo", "")),
        str(arguments.get("repo_type") or "auto"),
    )
    if not parsed:
        return {"ok": False, "error": "Could not parse Hugging Face repo"}
    repo_id, repo_type = parsed
    candidates = [repo_type] if repo_type != "auto" else ["model", "dataset", "space"]
    errors = []
    for candidate in candidates:
        try:
            data = http_json(huggingface_api_url(repo_id, candidate), args.tool_timeout)
        except Exception as exc:
            errors.append({"repo_type": candidate, "error": str(exc)})
            continue
        files = [
            item.get("rfilename")
            for item in data.get("siblings", [])
            if item.get("rfilename")
        ]
        return {
            "ok": True,
            "provider": "huggingface",
            "repo": repo_id,
            "repo_type": candidate,
            "private": data.get("private"),
            "gated": data.get("gated"),
            "tags": data.get("tags", [])[:40],
            "files": files[:120],
            "weight_files": [name for name in files if is_weight_file(name)][:40],
            "dataset_files": [name for name in files if is_dataset_file(name)][:40],
        }
    return {"ok": False, "provider": "huggingface", "repo": repo_id, "errors": errors}


def normalize_duckduckgo_url(href: str) -> str:
    parsed = urllib.parse.urlparse(href)
    query = urllib.parse.parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return query["uddg"][0]
    return href


def parse_github_repo(value: str) -> tuple[str, str] | None:
    value = value.strip()
    if not value:
        return None
    parts = [part for part in urllib.parse.urlparse(value).path.split("/") if part] if "github.com" in value else [part for part in value.split("/") if part]
    if len(parts) < 2:
        return None
    return parts[0], parts[1].removesuffix(".git")


def github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_root_names(contents: object) -> tuple[list[str], list[str]]:
    files, directories = [], []
    if isinstance(contents, list):
        for item in contents:
            (directories if item.get("type") == "dir" else files).append(item.get("name"))
    return files, directories


def github_release_names(releases: object) -> list[str]:
    if not isinstance(releases, list):
        return []
    return [(item.get("name") or item.get("tag_name")) for item in releases[:20]]


def parse_huggingface_repo(value: str, repo_type: str) -> tuple[str, str] | None:
    value = value.strip()
    if not value:
        return None
    parsed = urllib.parse.urlparse(value)
    if parsed.netloc.endswith("huggingface.co"):
        repo_type, repo_id = parse_hf_url_parts(parsed.path, repo_type)
    else:
        repo_id = value
    return (repo_id, repo_type) if "/" in repo_id else None


def parse_hf_url_parts(path: str, repo_type: str) -> tuple[str, str]:
    parts = [part for part in path.split("/") if part]
    if parts and parts[0] == "datasets":
        repo_type, parts = "dataset", parts[1:]
    elif parts and parts[0] == "spaces":
        repo_type, parts = "space", parts[1:]
    stop_words = {"tree", "blob", "resolve", "files", "discussions"}
    repo_parts = []
    for part in parts:
        if part in stop_words:
            break
        repo_parts.append(part)
        if len(repo_parts) == 2:
            break
    return repo_type, "/".join(repo_parts)


def huggingface_api_url(repo_id: str, repo_type: str) -> str:
    encoded = urllib.parse.quote(repo_id, safe="/")
    if repo_type == "dataset":
        return f"https://huggingface.co/api/datasets/{encoded}"
    if repo_type == "space":
        return f"https://huggingface.co/api/spaces/{encoded}"
    return f"https://huggingface.co/api/models/{encoded}"


def find_markers(names: list[str], markers: tuple[str, ...]) -> list[str]:
    return [name for name in names if any(marker in str(name).lower() for marker in markers)][:40]


def is_weight_file(name: str) -> bool:
    return name.lower().endswith((".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".gguf", ".onnx"))


def is_dataset_file(name: str) -> bool:
    return name.lower().endswith((".parquet", ".jsonl", ".json", ".csv", ".tsv", ".zip", ".tar", ".gz", ".txt"))
