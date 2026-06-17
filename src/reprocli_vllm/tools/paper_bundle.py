from __future__ import annotations

import posixpath
from typing import Any

from reprocli_vllm.config.config import BUNDLE_FILE_DEFAULT_CHARS, BUNDLE_FILE_MAX_CHARS
from reprocli_vllm.papers.papers import Paper


def paper_bundle_file_contents_tool(
    arguments: dict[str, Any],
    paper: Paper,
) -> dict[str, Any]:
    path_result = normalize_manifest_path(arguments.get("path"))
    if not path_result["ok"]:
        return path_result
    path = str(path_result["path"])
    files_by_path = supplement_files_by_path(paper)
    item = files_by_path.get(path)
    if item is None:
        return {
            "ok": False,
            "error": f"Unknown supplement file path: {path}",
            "available_paths": manifest_path_listing(files_by_path),
        }
    max_chars = bounded_max_chars(arguments.get("max_chars"))
    payload = file_metadata(item, path)
    if not item.get("is_text"):
        return {"ok": True, **payload}
    text = str(item.get("text") or "")
    payload.update(
        {
            "text": text[:max_chars],
            "truncated": len(text) > max_chars,
            "max_chars": max_chars,
        }
    )
    return {"ok": True, **payload}


def normalize_manifest_path(value: Any) -> dict[str, Any]:
    path = str(value or "").strip()
    if not path:
        return {"ok": False, "error": "Missing supplement file path"}
    if "\\" in path:
        return {"ok": False, "error": "Backslash paths are not supported"}
    if path.startswith("/"):
        return {"ok": False, "error": "Absolute paths are not supported"}
    parts = path.split("/")
    if ".." in parts:
        return {"ok": False, "error": "Path traversal is not supported"}
    if parts and parts[0] == "supplement":
        path = "/".join(parts[1:])
    normalized = posixpath.normpath(path)
    if normalized in {"", "."}:
        return {"ok": False, "error": "Missing supplement file path"}
    return {"ok": True, "path": normalized}


def manifest_path_listing(files_by_path: dict[str, dict], limit: int = 40) -> list[str]:
    paths = sorted(files_by_path)
    if len(paths) > limit:
        return [*paths[:limit], f"... and {len(paths) - limit} more"]
    return paths


def supplement_files_by_path(paper: Paper) -> dict[str, dict]:
    files = {}
    for item in paper.supplement_files:
        path = normalize_manifest_path(item.get("relative_path") or item.get("filename"))
        if path["ok"]:
            files[str(path["path"])] = item
    return files


def bounded_max_chars(value: Any) -> int:
    if value in (None, ""):
        return BUNDLE_FILE_DEFAULT_CHARS
    try:
        requested = int(value)
    except (TypeError, ValueError):
        return BUNDLE_FILE_DEFAULT_CHARS
    return max(1, min(requested, BUNDLE_FILE_MAX_CHARS))


def file_metadata(item: dict, path: str) -> dict[str, Any]:
    return {
        "path": path,
        "filename": str(item.get("filename") or path.rsplit("/", 1)[-1]),
        "extension": str(item.get("extension") or ""),
        "file_size": int(item.get("file_size") or 0),
        "sha256": str(item.get("sha256") or ""),
        "is_text": bool(item.get("is_text")),
    }
