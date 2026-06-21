from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterator

MAX_OUTPUT = 10_000
MAX_CHARS = 50_000
DEFAULT_TIMEOUT = 3600
_UA = {"User-Agent": "reprocli-repro-agent/0.1"}

# Schema definitions live in schemas.py; re-export for convenience.
from .schemas import TOOL_SCHEMAS_CONTAINER, TOOL_SCHEMAS_CONDA, get_tool_schemas  # noqa: E402


def dispatch(name: str, args: dict, workdir: str) -> str:
    try:
        if name == "bash":
            return _bash(
                args["command"], workdir,
                int(args.get("timeout") or DEFAULT_TIMEOUT),
                conda_env=args.get("conda_env"),
            )
        if name == "create_conda_env":
            return _create_conda_env(
                args["name"], args["python_version"],
                list(args.get("packages") or []), workdir,
            )
        if name == "list_files":
            return _list_files(
                args.get("path") or ".",
                workdir,
                int(args.get("max_depth") or 4),
                int(args.get("max_entries") or 300),
            )
        if name == "read_file":
            return _read_file(args["path"], workdir, int(args.get("max_chars") or MAX_OUTPUT))
        if name == "write_file":
            return _write_file(args["path"], str(args["content"]), workdir)
        if name == "fetch_url":
            return _fetch_url(str(args["url"]), int(args.get("max_chars") or MAX_CHARS))
        if name == "github_browse":
            return _github_browse(str(args["repo"]), args.get("path"), args.get("ref"))
        if name == "hf_browse":
            return _hf_browse(str(args["repo"]), str(args.get("repo_type") or "model"))
        return f"Unknown tool: {name}"
    except Exception as exc:
        return f"Error in {name}: {type(exc).__name__}: {exc}"


def _confined(workdir: str, rel: str) -> Path:
    base = Path(workdir).resolve()
    target = (base / rel).resolve()
    if base != target and base not in target.parents:
        raise ValueError(f"Path escapes workdir: {rel}")
    return target


_MINICONDA_BIN = Path.home() / "miniconda3" / "bin" / "conda"


def _conda_exe() -> str:
    """Return the conda executable, preferring system PATH then ~/miniconda3."""
    if shutil.which("conda"):
        return "conda"
    if _MINICONDA_BIN.exists():
        return str(_MINICONDA_BIN)
    return "conda"  # will fail with a clear error if missing


def _bash(command: str, workdir: str, timeout: int, conda_env: str | None = None) -> str:
    if conda_env:
        conda = _conda_exe()
        command = f"{conda} run -n {conda_env} --no-capture-output bash -c {_shell_quote(command)}"
    try:
        result = subprocess.run(
            command, shell=True, cwd=workdir,
            capture_output=True, text=True, timeout=timeout,
        )
        combined = (result.stdout + result.stderr).strip()
        body = combined or "(no output)"
        prefix = "" if result.returncode == 0 else f"[exit {result.returncode}]\n"
        return (prefix + body)[:MAX_OUTPUT]
    except subprocess.TimeoutExpired:
        return f"[exit TIMEOUT] command timed out after {timeout}s"


def _shell_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def _create_conda_env(name: str, python_version: str, packages: list[str], workdir: str) -> str:
    pkgs = " ".join(packages)
    conda = _conda_exe()
    cmd = f"{conda} create -n {name} python={python_version} {pkgs} -y 2>&1"
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=workdir,
            capture_output=True, text=True, timeout=DEFAULT_TIMEOUT,
        )
        combined = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            return f"[exit {result.returncode}]\n{combined}"[:MAX_OUTPUT]
        return f"Conda env '{name}' created (python={python_version}).\n{combined}"[:MAX_OUTPUT]
    except subprocess.TimeoutExpired:
        return f"[exit TIMEOUT] conda create timed out"


def _read_file(path: str, workdir: str, max_chars: int) -> str:
    target = _confined(workdir, path)
    return target.read_text(errors="replace")[:max_chars]


def _write_file(path: str, content: str, workdir: str) -> str:
    target = _confined(workdir, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return f"Written {len(content)} chars to {path}"


_SKIP_DIRS = {".git", "__pycache__", ".tox", "node_modules", ".mypy_cache", ".pytest_cache"}


def _list_files(path: str, workdir: str, max_depth: int, max_entries: int) -> str:
    root = _confined(workdir, path)
    if not root.exists():
        return f"Path does not exist: {path}"
    if root.is_file():
        return str(root.relative_to(Path(workdir).resolve()))

    lines: list[str] = [f"{path}/"]
    count = 0

    def _walk(directory: Path, depth: int, prefix: str) -> Iterator[str]:
        nonlocal count
        if depth > max_depth or count >= max_entries:
            return
        try:
            entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            return
        for i, entry in enumerate(entries):
            if count >= max_entries:
                yield f"{prefix}... (truncated)"
                return
            connector = "└── " if i == len(entries) - 1 else "├── "
            suffix = "/" if entry.is_dir() else ""
            yield f"{prefix}{connector}{entry.name}{suffix}"
            count += 1
            if entry.is_dir() and entry.name not in _SKIP_DIRS:
                extension = "    " if i == len(entries) - 1 else "│   "
                yield from _walk(entry, depth + 1, prefix + extension)

    lines.extend(_walk(root, 1, ""))
    return "\n".join(lines)


def _http_get(url: str, headers: dict | None = None, max_chars: int = MAX_CHARS) -> str:
    req = urllib.request.Request(url, headers={**_UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read(max_chars * 4)
            charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")[:max_chars]
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code}: {exc.reason}"


def _fetch_url(url: str, max_chars: int) -> str:
    return _http_get(url, max_chars=max_chars)


def _parse_github_repo(value: str) -> tuple[str, str] | None:
    import re
    m = re.search(r"github\.com/([^/]+)/([^/\s#?]+)", value)
    if m:
        return m.group(1), m.group(2).rstrip(".git")
    parts = [p for p in value.strip("/").split("/") if p]
    return (parts[0], parts[1]) if len(parts) >= 2 else None


def _github_browse(repo: str, path: str | None, ref: str | None) -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    parsed = _parse_github_repo(repo)
    if not parsed:
        return f"Could not parse GitHub repo: {repo}"
    owner, name = parsed
    ref_q = f"?ref={ref}" if ref else ""
    url = (
        f"https://api.github.com/repos/{owner}/{name}/contents/{path}{ref_q}"
        if path
        else f"https://api.github.com/repos/{owner}/{name}/readme"
    )
    raw = _http_get(url, headers=headers)
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "content" in data:
            # single file — decode and return content
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")[:MAX_CHARS]
        if isinstance(data, list):
            # directory listing — format as tree
            lines = [f"{path or '(root)/'}", ]
            for entry in sorted(data, key=lambda e: (e.get("type") == "file", e.get("name", ""))):
                suffix = "/" if entry.get("type") == "dir" else f"  ({entry.get('size', '')} bytes)"
                lines.append(f"  {entry.get('name', '')}{suffix}")
            return "\n".join(lines)
        return raw[:MAX_CHARS]
    except Exception:
        return raw[:MAX_CHARS]


def _hf_browse(repo: str, repo_type: str) -> str:
    import re
    m = re.search(r"huggingface\.co/([^/\s]+/[^/\s]+)", repo)
    repo_id = m.group(1) if m else repo.strip()
    prefix = "datasets/" if repo_type == "dataset" else ""
    raw = _http_get(f"https://huggingface.co/api/{prefix}{repo_id}")
    try:
        data = json.loads(raw)
        files = [f["rfilename"] for f in (data.get("siblings") or [])[:40]]
        card = json.dumps(data.get("cardData") or {}, indent=2)
        return (
            f"repo: {repo_id}\ntype: {repo_type}\n\nfiles:\n"
            + "\n".join(files)
            + f"\n\ncard:\n{card}"
        )
    except Exception:
        return raw[:MAX_CHARS]
