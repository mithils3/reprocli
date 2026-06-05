from __future__ import annotations

import urllib.parse
from typing import Any

from huggingface_hub import HfApi

DEFAULT_MAX_ENTRIES = 80
MAX_ALLOWED_ENTRIES = 500


def huggingface_repository_tree_tool(arguments: dict[str, Any]) -> dict[str, Any]:
    repo_type = normalize_repo_type(str(arguments.get("repo_type") or "auto"))
    parsed = parse_repo_arg(str(arguments.get("repo") or arguments.get("repo_id") or ""), repo_type)
    if not parsed:
        return {"ok": False, "error": "Missing repo"}
    repo_id, repo_type = parsed
    max_entries = bounded_max_entries(arguments.get("max_entries"))
    return repository_tree_payload(
        repo_id=repo_id,
        repo_type=repo_type,
        path=str(arguments.get("path") or "").strip() or None,
        revision=str(arguments.get("revision") or "").strip() or None,
        recursive=bool(arguments.get("recursive")),
        max_entries=max_entries,
    )


def safe_repository_tree_summary(
    repo_id: str,
    repo_type: str | None,
    *,
    max_entries: int,
) -> dict[str, Any]:
    try:
        return repository_tree_payload(
            repo_id=repo_id,
            repo_type=repo_type,
            path=None,
            revision=None,
            recursive=False,
            max_entries=max_entries,
        )
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def repository_tree_payload(
    *,
    repo_id: str,
    repo_type: str | None,
    path: str | None,
    revision: str | None,
    recursive: bool,
    max_entries: int,
) -> dict[str, Any]:
    formatted, observed_count, truncated = formatted_limited_entries(
        list_repo_tree(
            repo_id=repo_id,
            repo_type=None if repo_type == "auto" else repo_type,
            path=path,
            revision=revision,
            recursive=recursive,
        ),
        max_entries,
    )
    return {
        "ok": True,
        "provider": "huggingface_hub",
        "name": "huggingface_repository_tree",
        "repo": repo_id,
        "repo_type": repo_type or "auto",
        "path": path or "",
        "revision": revision,
        "recursive": recursive,
        "max_entries": max_entries,
        "entry_count": observed_count,
        "truncated": truncated,
        "entries": formatted,
    }


def list_repo_tree(
    *,
    repo_id: str,
    repo_type: str | None,
    path: str | None,
    revision: str | None,
    recursive: bool,
) -> Any:
    api = HfApi()
    return api.list_repo_tree(
        repo_id=repo_id,
        repo_type=repo_type,
        path_in_repo=path,
        revision=revision,
        recursive=recursive,
    )


def formatted_limited_entries(entries: Any, max_entries: int) -> tuple[list[dict[str, Any]], int, bool]:
    formatted = []
    for index, entry in enumerate(entries):
        if index >= max_entries:
            return formatted, index + 1, True
        formatted.append(format_tree_entry(entry))
    return formatted, len(formatted), False


def format_tree_entry(entry: Any) -> dict[str, Any]:
    item = {
        "path": str(getattr(entry, "path", "")),
        "type": entry_type(entry),
    }
    size = getattr(entry, "size", None)
    if size is not None:
        item["size"] = size
    lfs = getattr(entry, "lfs", None)
    if lfs:
        item["lfs"] = True
        if isinstance(lfs, dict) and lfs.get("size") is not None:
            item["lfs_size"] = lfs["size"]
    return item


def entry_type(entry: Any) -> str:
    class_name = type(entry).__name__.lower()
    if "folder" in class_name:
        return "directory"
    if "file" in class_name:
        return "file"
    return str(getattr(entry, "type", "unknown"))


def bounded_max_entries(value: Any) -> int:
    try:
        max_entries = int(value or DEFAULT_MAX_ENTRIES)
    except (TypeError, ValueError):
        max_entries = DEFAULT_MAX_ENTRIES
    return max(1, min(max_entries, MAX_ALLOWED_ENTRIES))


def normalize_repo_type(repo_type: str) -> str:
    aliases = {"datasets": "dataset", "spaces": "space", "models": "model", "": "auto"}
    normalized = repo_type.strip().lower()
    return aliases.get(normalized, normalized)


def parse_repo_arg(value: str, repo_type: str) -> tuple[str, str] | None:
    value = value.strip()
    if not value:
        return None
    parsed = urllib.parse.urlparse(value)
    if parsed.netloc.endswith("huggingface.co"):
        repo_type, repo_id = parse_hf_url_path(parsed.path, repo_type)
    else:
        repo_id = value
    return (repo_id, repo_type) if "/" in repo_id else None


def parse_hf_url_path(path: str, repo_type: str) -> tuple[str, str]:
    parts = [part for part in path.split("/") if part]
    if parts and parts[0] in {"models", "datasets", "spaces"}:
        repo_type = {"models": "model", "datasets": "dataset", "spaces": "space"}[parts[0]]
        parts = parts[1:]
    repo_parts = []
    for part in parts:
        if part in {"tree", "blob", "resolve", "files", "discussions"}:
            break
        repo_parts.append(part)
        if len(repo_parts) == 2:
            break
    return repo_type, "/".join(repo_parts)
