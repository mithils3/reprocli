from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reprocli_vllm.config.config import TOOL_MAX_CHARS, TOOL_RESULT_MAX_CHARS, TOOL_TIMEOUT
from reprocli_vllm.papers.papers import Paper
from .github_mcp import (
    github_file_contents_tool,
    github_repo_tool,
    github_repository_tree_tool,
    github_search_code_tool,
    github_search_repositories_tool,
)
from .huggingface_mcp import huggingface_repo_tool, huggingface_search_tool
from .huggingface_tree import huggingface_repository_tree_tool
from .http_utils import html_to_text, http_text, is_http_url, is_probably_text
from .paper_bundle import paper_bundle_file_contents_tool
from .result_limits import is_transient_error, truncate_tool_result
from .run_dir_tools import AUDIT_TOOL_HANDLERS


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


TOOL_HANDLERS = {
    "github_search_repositories": github_search_repositories_tool,
    "github_search_code": github_search_code_tool,
    "github_repo": github_repo_tool,
    "github_file_contents": github_file_contents_tool,
    "github_repository_tree": github_repository_tree_tool,
    "huggingface_search": huggingface_search_tool,
    "huggingface_repo": huggingface_repo_tool,
    "huggingface_repository_tree": huggingface_repository_tree_tool,
    "fetch_url": fetch_url_tool,
}


def execute_tool_call(call: dict[str, Any], paper: Paper | None = None) -> dict[str, Any]:
    result = run_tool_call(call, paper)
    if is_transient_error(result):
        result = run_tool_call(call, paper)
        result["retried"] = True
    return truncate_tool_result(result, TOOL_RESULT_MAX_CHARS)


def run_tool_call(call: dict[str, Any], paper: Paper | None) -> dict[str, Any]:
    function = call.get("function") or {}
    name = function.get("name", "")
    try:
        arguments = parse_tool_arguments(function.get("arguments", {}))
        audit_handler = AUDIT_TOOL_HANDLERS.get(name)
        if audit_handler is not None:
            run_dir = str(getattr(paper, "run_dir", "") or "") if paper else ""
            if not run_dir:
                return {
                    "ok": False,
                    "tool": name,
                    "error": "No agent run directory is bound for this paper (set --runs-dir).",
                }
            return audit_handler(arguments, Path(run_dir))
        if name == "paper_bundle_file_contents":
            if paper is None:
                return {
                    "ok": False,
                    "tool": name,
                    "error": "paper_bundle_file_contents requires current Paper context",
                }
            return paper_bundle_file_contents_tool(arguments, paper)
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            available = ", ".join(
                (*TOOL_HANDLERS, "paper_bundle_file_contents", *AUDIT_TOOL_HANDLERS)
            )
            return {
                "ok": False,
                "error": f"Unknown tool: {name}. Available tools: {available}",
            }
        return handler(arguments)
    except Exception as exc:
        return {"ok": False, "tool": name, "error": f"{type(exc).__name__}: {exc}"}


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
