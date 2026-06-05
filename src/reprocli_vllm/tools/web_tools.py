from __future__ import annotations

import json
from typing import Any

from ..config import TOOL_MAX_CHARS, TOOL_TIMEOUT
from ..papers import Paper
from .github_mcp import (
    github_file_contents_tool,
    github_repo_tool,
    github_repository_tree_tool,
    github_search_code_tool,
    github_search_commits_tool,
    github_search_issues_tool,
    github_search_pull_requests_tool,
    github_search_repositories_tool,
    github_search_tool,
)
from .huggingface_mcp import huggingface_repo_tool, huggingface_search_tool
from .huggingface_tree import huggingface_repository_tree_tool
from .http_utils import html_to_text, http_text, is_http_url, is_probably_text
from .paper_bundle import paper_bundle_file_contents_tool


def execute_tool_call(call: dict[str, Any], paper: Paper | None = None) -> dict[str, Any]:
    function = call.get("function") or {}
    name = function.get("name", "")
    try:
        arguments = parse_tool_arguments(function.get("arguments", {}))
        if name == "github_search":
            result = github_search_tool(arguments)
        elif name == "github_search_repositories":
            result = github_search_repositories_tool(arguments)
        elif name == "github_search_code":
            result = github_search_code_tool(arguments)
        elif name == "github_search_commits":
            result = github_search_commits_tool(arguments)
        elif name == "github_search_issues":
            result = github_search_issues_tool(arguments)
        elif name == "github_search_pull_requests":
            result = github_search_pull_requests_tool(arguments)
        elif name == "github_repo":
            result = github_repo_tool(arguments)
        elif name == "github_file_contents":
            result = github_file_contents_tool(arguments)
        elif name == "github_repository_tree":
            result = github_repository_tree_tool(arguments)
        elif name == "huggingface_search":
            result = huggingface_search_tool(arguments)
        elif name == "huggingface_repo":
            result = huggingface_repo_tool(arguments)
        elif name == "huggingface_repository_tree":
            result = huggingface_repository_tree_tool(arguments)
        elif name == "fetch_url":
            result = fetch_url_tool(arguments)
        elif name == "paper_bundle_file_contents":
            if paper is None:
                result = {
                    "ok": False,
                    "tool": name,
                    "error": "paper_bundle_file_contents requires current Paper context",
                }
            else:
                result = paper_bundle_file_contents_tool(arguments, paper)
        else:
            result = {"ok": False, "error": f"Unknown tool: {name}"}
    except Exception as exc:
        result = {"ok": False, "tool": name, "error": f"{type(exc).__name__}: {exc}"}
    return result


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


def fetch_url_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    url = str(arguments.get("url", "")).strip()
    max_chars = int(arguments.get("max_chars") or TOOL_MAX_CHARS)
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
