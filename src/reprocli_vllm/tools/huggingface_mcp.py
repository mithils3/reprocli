from __future__ import annotations

import os
import shlex
import urllib.parse
import json
from functools import cache
from typing import Any

from ..config import TOOL_TIMEOUT
from .huggingface_tree import safe_repository_tree_summary
from .mcp_client import MCPError, StdioMCPClient, StreamableHTTPMCPClient
from .mcp_results import mcp_tool_result


DEFAULT_HF_MCP_URL = "https://huggingface.co/mcp"


def huggingface_search_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    query = search_query(arguments)
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
    repo_ids, repo_type = parse_hf_repo_arguments(arguments)
    if not repo_ids:
        given = arguments.get("repo") or arguments.get("repo_ids")
        hint = "pass namespace/repo or a huggingface.co URL"
        return {"ok": False, "error": f"Could not parse Hugging Face repo from {given!r}; {hint}"}
    tool = choose_hf_tool("repo_details")
    params = params_for_schema(
        tool,
        arguments,
        repo_ids=repo_ids,
        repo_id=repo_ids[0],
        repo_type=repo_type,
        include_readme=True,
    )
    result = call_hf_mcp(str(tool["name"]), params)
    payload = hf_result("huggingface_repo", result, params)
    payload["root_tree"] = safe_repository_tree_summary(
        repo_ids[0],
        repo_type,
        max_entries=40,
    )
    return payload


def choose_hf_tool(search_type: str) -> dict[str, Any]:
    tools = hf_mcp_client().list_tools()
    for name in preferred_tool_names(search_type):
        for tool in tools:
            if tool.get("name") == name:
                return tool
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
    if "hub" in text and search_type in {"repositories", "hub"}:
        score += 1
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
    set_first(params, keys, ("message", "query", "q", "text"), values.get("query"))
    set_repo_param(params, keys, values.get("repo_ids"), values.get("repo_id"))
    set_first(params, keys, ("repo_type", "type"), values.get("repo_type"))
    set_first(
        params,
        keys,
        ("results_limit", "limit", "max_results", "top_k", "perPage", "per_page"),
        source.get("max_results"),
    )
    set_first(params, keys, ("include_readme", "includeReadme"), values.get("include_readme"))
    if not keys:
        params.update(default_schema_params(values))
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


def set_repo_param(
    params: dict[str, Any],
    keys: set[str],
    repo_ids: Any,
    repo_id: Any,
) -> None:
    if "repo_ids" in keys and repo_ids:
        params["repo_ids"] = repo_ids
        return
    set_first(params, keys, ("repo_id", "repo", "repository", "id", "name"), repo_id)


def default_schema_params(values: dict[str, Any]) -> dict[str, Any]:
    params = {}
    if values.get("query"):
        params["query"] = values["query"]
    if values.get("repo_ids"):
        params["repo_ids"] = values["repo_ids"]
    if values.get("repo_type"):
        params["repo_type"] = values["repo_type"]
    return params


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


def preferred_tool_names(search_type: str) -> tuple[str, ...]:
    names = {
        "repositories": ("hub_repo_search",),
        "papers": ("paper_search",),
        "spaces": ("space_search",),
        "hub": ("hf_hub_query",),
        "repo_details": ("hub_repo_details",),
    }
    return names.get(search_type, ())


def search_query(arguments: dict[str, Any]) -> str:
    for key in ("query", "message", "q", "text"):
        value = arguments.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def parse_hf_repo_arguments(arguments: dict[str, Any]) -> tuple[list[str], str | None]:
    repo_type = normalize_repo_type(str(arguments.get("repo_type") or "auto"))
    values = repo_ids_from_value(arguments.get("repo_ids"))
    if not values:
        values = repo_ids_from_value(arguments.get("repo"))
    repo_ids = []
    repo_types = []
    for value in values:
        parsed = parse_hf_repo(str(value), repo_type)
        if parsed:
            repo_id, parsed_type = parsed
            repo_ids.append(repo_id)
            if parsed_type != "auto":
                repo_types.append(parsed_type)
    return repo_ids, single_repo_type(repo_types)


def repo_ids_from_value(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, list):
            return [str(item).strip() for item in decoded if str(item).strip()]
        if isinstance(decoded, str):
            return [decoded.strip()] if decoded.strip() else []
        return [text] if text else []
    return [str(value).strip()]


def single_repo_type(repo_types: list[str]) -> str | None:
    unique = set(repo_types)
    if len(unique) == 1:
        return repo_types[0]
    return None


def normalize_repo_type(repo_type: str) -> str:
    aliases = {
        "models": "model",
        "datasets": "dataset",
        "spaces": "space",
        "repo": "auto",
        "repository": "auto",
        "": "auto",
    }
    return aliases.get(repo_type.strip().lower(), repo_type.strip().lower())


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
    if parts and parts[0] == "models":
        repo_type, parts = "model", parts[1:]
    elif parts and parts[0] == "datasets":
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
