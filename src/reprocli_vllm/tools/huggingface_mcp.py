from __future__ import annotations

import os
import shlex
import urllib.parse
from functools import cache
from typing import Any

from ..config import TOOL_TIMEOUT
from .mcp_client import MCPError, StdioMCPClient, StreamableHTTPMCPClient
from .mcp_results import mcp_tool_result


DEFAULT_HF_MCP_URL = "https://huggingface.co/mcp"


def huggingface_search_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query", "")).strip()
    search_type = str(arguments.get("search_type") or "repositories")
    if not query:
        return {"ok": False, "error": "Missing query"}
    tool = choose_hf_tool(search_type)
    params = params_for_schema(tool, arguments, query=query)
    result = call_hf_mcp(str(tool["name"]), params)
    payload = hf_result("huggingface_search", result, params)
    payload["hint"] = (
        "If results are weak, try title, acronym, no-hyphen acronym, arXiv ID, "
        "method, dataset, model, checkpoint, Space, or benchmark queries before "
        "concluding no Hugging Face artifact exists."
    )
    return payload


def huggingface_repo_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_hf_repo(
        str(arguments.get("repo", "")),
        str(arguments.get("repo_type") or "auto"),
    )
    if not parsed:
        return {"ok": False, "error": "Could not parse Hugging Face repo"}
    repo_id, repo_type = parsed
    tool = choose_hf_tool("repo_details")
    params = params_for_schema(tool, arguments, repo_id=repo_id, repo_type=repo_type)
    result = call_hf_mcp(str(tool["name"]), params)
    return hf_result("huggingface_repo", result, params)


def choose_hf_tool(search_type: str) -> dict[str, Any]:
    tools = hf_mcp_client().list_tools()
    ranked = sorted(
        tools,
        key=lambda tool: tool_score(tool, search_type),
        reverse=True,
    )
    if ranked and tool_score(ranked[0], search_type) > 0:
        return ranked[0]
    names = ", ".join(str(tool.get("name")) for tool in tools[:20])
    raise MCPError(f"No Hugging Face MCP tool matched {search_type}; available: {names}")


def tool_score(tool: dict[str, Any], search_type: str) -> int:
    text = " ".join(
        str(tool.get(key) or "")
        for key in ("name", "title", "description")
    ).lower()
    groups = {
        "repositories": ("repository", "repo", "model", "dataset", "space"),
        "papers": ("paper", "research"),
        "spaces": ("space", "app"),
        "docs": ("documentation", "docs"),
        "hub": ("hub query", "navigator", "social graph"),
        "repo_details": ("repository details", "repo details", "detailed information"),
    }
    score = sum(2 for word in groups.get(search_type, ()) if word in text)
    if "search" in text and search_type != "repo_details":
        score += 1
    if "details" in text and search_type == "repo_details":
        score += 1
    return score


def params_for_schema(tool: dict[str, Any], source: dict[str, Any], **values: Any) -> dict[str, Any]:
    schema = tool.get("inputSchema") or tool.get("input_schema") or {}
    properties = schema.get("properties") if isinstance(schema, dict) else {}
    keys = set(properties) if isinstance(properties, dict) else set()
    params: dict[str, Any] = {}
    set_first(params, keys, ("query", "q", "text"), values.get("query"))
    set_first(params, keys, ("repo_id", "repo", "repository", "id", "name"), values.get("repo_id"))
    set_first(params, keys, ("repo_type", "type"), values.get("repo_type"))
    set_first(params, keys, ("limit", "max_results", "top_k", "perPage"), source.get("max_results"))
    if not keys:
        params.update({key: value for key, value in values.items() if value not in (None, "")})
        if source.get("max_results"):
            params["max_results"] = source["max_results"]
    return {key: value for key, value in params.items() if value not in (None, "")}


def set_first(
    params: dict[str, Any],
    keys: set[str],
    candidates: tuple[str, ...],
    value: Any,
) -> None:
    if value in (None, ""):
        return
    for key in candidates:
        if key in keys:
            params[key] = value
            return


def call_hf_mcp(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = hf_mcp_client().call_tool(tool_name, arguments)
    return mcp_tool_result(tool_name, result)


def hf_result(name: str, result: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": result["ok"],
        "provider": "huggingface_mcp",
        "tool": result["tool"],
        "name": name,
        "arguments": arguments,
        "result": result["result"],
    }


@cache
def hf_mcp_client() -> StdioMCPClient | StreamableHTTPMCPClient:
    command = os.environ.get("HF_MCP_COMMAND")
    token = hf_token()
    if command:
        return StdioMCPClient(shlex.split(command), os.environ.copy(), TOOL_TIMEOUT)
    if not token and "HF_MCP_URL" not in os.environ:
        raise MCPError("Set HF_MCP_TOKEN, HF_TOKEN, HUGGINGFACE_TOKEN, or HF_MCP_COMMAND")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return StreamableHTTPMCPClient(os.environ.get("HF_MCP_URL") or DEFAULT_HF_MCP_URL, headers, TOOL_TIMEOUT)


def hf_token() -> str | None:
    for name in ("HF_MCP_TOKEN", "HF_TOKEN", "HUGGINGFACE_TOKEN"):
        value = os.environ.get(name)
        if value:
            return value
    return None


def parse_hf_repo(value: str, repo_type: str) -> tuple[str, str] | None:
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
