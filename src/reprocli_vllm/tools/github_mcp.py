from __future__ import annotations

import os
import shlex
import urllib.parse
from functools import cache
from typing import Any

from ..config import TOOL_TIMEOUT
from .mcp_client import MCPError, StdioMCPClient, StreamableHTTPMCPClient
from .mcp_results import mcp_tool_result


DEFAULT_GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"
README_CANDIDATES = ("README.md", "readme.md", "README.rst", "README.txt")


def github_search_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query", "")).strip()
    search_type = str(arguments.get("search_type") or "repositories")
    if not query:
        return {"ok": False, "error": "Missing query"}
    if search_type == "code":
        return github_search_code_tool(arguments)
    if search_type == "commits":
        return github_search_commits_tool(arguments)
    if search_type == "issues":
        return github_search_issues_tool(arguments)
    if search_type == "pull_requests":
        return github_search_pull_requests_tool(arguments)
    return github_search_repositories_tool(arguments)


def github_search_repositories_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    return github_query_tool(
        "search_repositories",
        arguments,
        {"minimal_output": True},
        "Use github_repo on promising candidates before counting code as available.",
    )


def github_search_code_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    return github_query_tool(
        "search_code",
        arguments,
        {},
        "Use github_file_contents or github_repo on parent repos before counting code.",
    )


def github_search_commits_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    return github_query_tool(
        "search_commits",
        arguments,
        {},
        "Use this to find artifact-release commits in known repos.",
    )


def github_search_issues_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    return github_query_tool(
        "search_issues",
        arguments,
        optional_repo_scope(arguments),
        "Use this for release-status, artifact, or reproduction issue evidence.",
    )


def github_search_pull_requests_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    return github_query_tool(
        "search_pull_requests",
        arguments,
        optional_repo_scope(arguments),
        "Use this for merged artifact-release or implementation PR evidence.",
    )


def github_file_contents_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    owner, repo = github_owner_repo(arguments)
    path = str(arguments.get("path") or "")
    params = {"owner": owner, "repo": repo, "path": path}
    optional_param(params, arguments, "ref")
    optional_param(params, arguments, "sha")
    result = call_github_mcp("get_file_contents", params)
    return github_result("github_file_contents", result, params)


def github_repository_tree_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    owner, repo = github_owner_repo(arguments)
    params: dict[str, Any] = {"owner": owner, "repo": repo}
    optional_param(params, arguments, "tree_sha")
    optional_param(params, arguments, "path_filter")
    if "recursive" in arguments:
        params["recursive"] = bool(arguments.get("recursive"))
    result = call_github_mcp("get_repository_tree", params)
    return github_result("github_repository_tree", result, params)


def github_repo_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    repo = parse_github_repo(str(arguments.get("repo", "")))
    if not repo:
        return {"ok": False, "error": "Could not parse GitHub repo"}
    owner, name = repo
    root = safe_call_github_mcp("get_file_contents", {"owner": owner, "repo": name, "path": ""})
    readme = first_readme(owner, name)
    release = safe_call_github_mcp("get_latest_release", {"owner": owner, "repo": name})
    tree = safe_call_github_mcp("get_repository_tree", {"owner": owner, "repo": name})
    return {
        "ok": root["ok"] or readme["ok"] or release["ok"] or tree["ok"],
        "provider": "github_mcp",
        "repo": f"{owner}/{name}",
        "html_url": f"https://github.com/{owner}/{name}",
        "root": root["result"],
        "readme": readme["result"],
        "latest_release": release["result"],
        "tree": tree["result"],
        "errors": [item for item in (root, readme, release, tree) if not item["ok"]],
        "hint": "GitHub evidence came through the GitHub MCP server.",
    }


def first_readme(owner: str, repo: str) -> dict[str, Any]:
    errors = []
    for path in README_CANDIDATES:
        result = safe_call_github_mcp(
            "get_file_contents",
            {"owner": owner, "repo": repo, "path": path},
        )
        if result["ok"]:
            result["result"]["path"] = path
            return result
        errors.append(result)
    return {
        "ok": False,
        "tool": "get_file_contents",
        "result": {"checked_paths": list(README_CANDIDATES)},
        "errors": errors[:2],
    }


def call_github_mcp(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = github_mcp_client().call_tool(tool_name, arguments)
    return mcp_tool_result(tool_name, result)


def safe_call_github_mcp(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        return call_github_mcp(tool_name, arguments)
    except Exception as exc:
        return {
            "ok": False,
            "tool": tool_name,
            "result": {},
            "error": f"{type(exc).__name__}: {exc}",
        }


def github_query_tool(
    mcp_tool: str,
    arguments: dict[str, Any],
    extra: dict[str, Any],
    hint: str,
) -> dict[str, Any]:
    query = str(arguments.get("query", "")).strip()
    if not query:
        return {"ok": False, "error": "Missing query"}
    max_results = max(1, min(int(arguments.get("max_results") or 5), 20))
    params = {"query": query, "perPage": max_results, **extra}
    optional_param(params, arguments, "sort")
    optional_param(params, arguments, "order")
    result = call_github_mcp(mcp_tool, params)
    search_hint = (
        f"{hint} If results are weak, try a different title/acronym/arXiv ID/"
        "artifact-term query before concluding no GitHub artifact exists."
    )
    return github_result(mcp_tool, result, {"query": query}, hint=search_hint)


def github_result(
    name: str,
    result: dict[str, Any],
    arguments: dict[str, Any],
    *,
    hint: str | None = None,
) -> dict[str, Any]:
    payload = {
        "ok": result["ok"],
        "provider": "github_mcp",
        "tool": result["tool"],
        "name": name,
        "arguments": arguments,
        "result": result["result"],
    }
    if hint:
        payload["hint"] = hint
    return payload


def github_owner_repo(arguments: dict[str, Any]) -> tuple[str, str]:
    repo_value = str(arguments.get("repo", ""))
    repo = parse_github_repo(repo_value)
    owner = str(arguments.get("owner") or "").strip()
    name = str(arguments.get("name") or "").strip()
    if repo:
        return repo
    if owner and name:
        return owner, name
    raise ValueError("Provide repo as owner/name or provide owner and name")


def optional_repo_scope(arguments: dict[str, Any]) -> dict[str, Any]:
    result = {}
    optional_param(result, arguments, "owner")
    optional_param(result, arguments, "repo")
    return result


def optional_param(target: dict[str, Any], source: dict[str, Any], key: str) -> None:
    value = source.get(key)
    if value not in (None, ""):
        target[key] = value


@cache
def github_mcp_client() -> StdioMCPClient | StreamableHTTPMCPClient:
    command = os.environ.get("GITHUB_MCP_COMMAND")
    token = github_token()
    if command:
        env = os.environ.copy()
        if token and "GITHUB_PERSONAL_ACCESS_TOKEN" not in env:
            env["GITHUB_PERSONAL_ACCESS_TOKEN"] = token
        if "GITHUB_MCP_TOOLSETS" in env and "GITHUB_TOOLSETS" not in env:
            env["GITHUB_TOOLSETS"] = env["GITHUB_MCP_TOOLSETS"]
        return StdioMCPClient(shlex.split(command), env, TOOL_TIMEOUT)
    url = os.environ.get("GITHUB_MCP_URL") or DEFAULT_GITHUB_MCP_URL
    if not token and "GITHUB_MCP_URL" not in os.environ:
        raise MCPError(
            "Set GITHUB_MCP_TOKEN, GITHUB_TOKEN, GH_TOKEN, or GITHUB_MCP_COMMAND "
            "to use GitHub MCP tools"
        )
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    toolsets = os.environ.get("GITHUB_MCP_TOOLSETS", "repos,git,issues,pull_requests")
    if toolsets:
        headers["X-MCP-Toolsets"] = toolsets
    return StreamableHTTPMCPClient(url, headers, TOOL_TIMEOUT)


def github_token() -> str | None:
    for name in ("GITHUB_MCP_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(name)
        if value:
            return value
    return None


def parse_github_repo(value: str) -> tuple[str, str] | None:
    value = value.strip()
    if not value:
        return None
    parsed = urllib.parse.urlparse(value)
    parts = (
        [part for part in parsed.path.split("/") if part]
        if parsed.netloc.endswith("github.com")
        else [part for part in value.split("/") if part]
    )
    if len(parts) < 2:
        return None
    return parts[0], parts[1].removesuffix(".git")
