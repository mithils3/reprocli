from __future__ import annotations

import os
from typing import Any

from .config import TOOL_TIMEOUT
from .http_utils import build_url, http_json


def github_search_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query", "")).strip()
    max_results = int(arguments.get("max_results") or 5)
    search_type = str(arguments.get("search_type") or "repositories")
    max_results = max(1, min(max_results, 10))
    if not query:
        return {"ok": False, "error": "Missing query"}
    if search_type == "code":
        return github_code_search(query, max_results)
    return github_repo_search(query, max_results)


def github_repo_search(query: str, max_results: int) -> dict[str, Any]:
    data = http_json(
        build_url(
            "https://api.github.com/search/repositories",
            {"q": query, "per_page": str(max_results), "sort": "best-match"},
        ),
        TOOL_TIMEOUT,
        headers=github_headers(),
    )
    return {
        "ok": True,
        "provider": "github_search",
        "search_type": "repositories",
        "query": query,
        "total_count": data.get("total_count"),
        "results": [repo_result(item) for item in data.get("items", [])],
        "hint": "Verify candidate repos with github_repo before counting code as available.",
    }


def github_code_search(query: str, max_results: int) -> dict[str, Any]:
    data = http_json(
        build_url(
            "https://api.github.com/search/code",
            {"q": query, "per_page": str(max_results), "sort": "indexed"},
        ),
        TOOL_TIMEOUT,
        headers=github_headers(),
    )
    return {
        "ok": True,
        "provider": "github_search",
        "search_type": "code",
        "query": query,
        "total_count": data.get("total_count"),
        "results": [code_result(item) for item in data.get("items", [])],
        "hint": "Use github_repo on the parent repo before counting code as available.",
    }


def repo_result(item: dict[str, Any]) -> dict[str, Any]:
    owner = item.get("owner") or {}
    license_data = item.get("license") or {}
    return {
        "repo": item.get("full_name"),
        "url": item.get("html_url"),
        "description": item.get("description"),
        "private": item.get("private"),
        "fork": item.get("fork"),
        "archived": item.get("archived"),
        "stars": item.get("stargazers_count"),
        "updated_at": item.get("updated_at"),
        "pushed_at": item.get("pushed_at"),
        "default_branch": item.get("default_branch"),
        "license": license_data.get("spdx_id"),
        "owner_type": owner.get("type"),
    }


def code_result(item: dict[str, Any]) -> dict[str, Any]:
    repo = item.get("repository") or {}
    return {
        "name": item.get("name"),
        "path": item.get("path"),
        "url": item.get("html_url"),
        "repo": repo.get("full_name"),
        "repo_url": repo.get("html_url"),
        "repo_description": repo.get("description"),
    }


def github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
