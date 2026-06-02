#!/usr/bin/env python3
"""Serve a local JSONL conversation viewer for files in data/."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


DEFAULT_VIEWER = Path("tools/jsonl_conversation_viewer.html")
DEFAULT_SCAN_DIRS = (Path("data"), Path("outputs"))


@dataclass(frozen=True)
class ViewerConfig:
    root: Path
    viewer: Path
    scan_dirs: tuple[Path, ...]


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    viewer = resolve_under_root(root, args.viewer)
    if not viewer.is_file():
        raise SystemExit(f"Viewer file not found: {viewer}")

    scan_dirs = tuple(resolve_under_root(root, path) for path in args.scan_dir)
    config = ViewerConfig(root=root, viewer=viewer, scan_dirs=scan_dirs)
    handler = make_handler(config)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    host_label = args.host if args.host not in {"0.0.0.0", ""} else "localhost"
    print(f"Serving JSONL viewer at http://{host_label}:{args.port}", file=sys.stderr)
    print(
        "Scanning: "
        + ", ".join(str(path.relative_to(root)) for path in scan_dirs),
        file=sys.stderr,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
    finally:
        server.server_close()
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve a local browser UI for JSONL conversation files."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--viewer", type=Path, default=DEFAULT_VIEWER)
    parser.add_argument(
        "--scan-dir",
        type=Path,
        action="append",
        default=None,
        help="Directory to scan for .jsonl files. May be passed multiple times.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.scan_dir is None:
        args.scan_dir = list(DEFAULT_SCAN_DIRS)
    return args


def make_handler(config: ViewerConfig) -> type[BaseHTTPRequestHandler]:
    class ViewerHandler(BaseHTTPRequestHandler):
        server_version = "JsonlConversationViewer/1.0"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/viewer", "/viewer/"}:
                self.send_file(config.viewer)
                return
            if parsed.path == "/api/files":
                self.send_json({"files": list_jsonl_files(config)})
                return
            if parsed.path == "/api/file":
                self.send_jsonl_file(parsed.query)
                return
            if parsed.path == "/healthz":
                self.send_json({"ok": True})
                return
            if parsed.path == "/tools/jsonl_conversation_viewer.html":
                self.send_file(config.viewer)
                return
            if parsed.path.startswith("/tools/jsonl_viewer/"):
                self.send_static_asset(parsed.path)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def send_static_asset(self, request_path: str) -> None:
            relative = request_path.removeprefix("/")
            try:
                path = resolve_under_root(config.root, Path(unquote(relative)))
            except SystemExit:
                self.send_error(HTTPStatus.FORBIDDEN, "Path escapes root")
                return
            static_root = config.root / "tools" / "jsonl_viewer"
            if not is_relative_to(path, static_root) or not path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_file(path)

        def send_jsonl_file(self, query: str) -> None:
            params = parse_qs(query)
            requested = params.get("path", [""])[0]
            if not requested:
                self.send_error(HTTPStatus.BAD_REQUEST, "Missing path")
                return
            try:
                path = resolve_under_root(config.root, Path(unquote(requested)))
            except SystemExit:
                self.send_error(HTTPStatus.FORBIDDEN, "Path escapes root")
                return
            if not is_allowed_jsonl(config, path):
                self.send_error(HTTPStatus.FORBIDDEN, "Path is not an allowed JSONL file")
                return
            self.send_file(path, content_type="application/jsonl; charset=utf-8")

        def send_json(self, payload: object) -> None:
            data = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def send_file(self, path: Path, content_type: str | None = None) -> None:
            try:
                data = path.read_bytes()
            except OSError as exc:
                self.send_error(HTTPStatus.NOT_FOUND, str(exc))
                return
            guessed_type = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", guessed_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt: str, *args: object) -> None:
            print(f"{self.address_string()} - {fmt % args}", file=sys.stderr)

    return ViewerHandler


def list_jsonl_files(config: ViewerConfig) -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    for scan_dir in config.scan_dirs:
        if not scan_dir.is_dir():
            continue
        for path in sorted(scan_dir.rglob("*.jsonl")):
            if not path.is_file() or not is_allowed_jsonl(config, path):
                continue
            stat = path.stat()
            files.append(
                {
                    "path": str(path.relative_to(config.root)),
                    "size": stat.st_size,
                    "modified": int(stat.st_mtime),
                }
            )
    return sorted(files, key=lambda item: str(item["path"]))


def is_allowed_jsonl(config: ViewerConfig, path: Path) -> bool:
    if path.suffix != ".jsonl" or not path.is_file():
        return False
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return any(is_relative_to(resolved, scan_dir) for scan_dir in config.scan_dirs)


def resolve_under_root(root: Path, path: Path) -> Path:
    candidate = path if path.is_absolute() else root / path
    resolved = candidate.resolve()
    if not is_relative_to(resolved, root):
        raise SystemExit(f"Path escapes root: {path}")
    return resolved


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
