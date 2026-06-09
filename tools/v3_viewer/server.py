from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from v3_loader import list_records, load_run, view_record

DEFAULT_BASE = Path("outputs/v4/neurips_2025_minimax_m2_trial")
STATIC_DIR = Path(__file__).resolve().parent / "static"


class ViewerHandler(BaseHTTPRequestHandler):
    run_data: dict

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/summary":
            self.send_json(
                {
                    "base_path": self.run_data["base_path"],
                    "summary": self.run_data["summary"],
                    "errors": self.run_data["errors"],
                    "records": list_records(self.run_data),
                }
            )
            return
        if path.startswith("/api/records/"):
            custom_id = unquote(path.rsplit("/", 1)[-1])
            record = self.run_data["records"].get(custom_id)
            if not record:
                self.send_error(404, "record not found")
                return
            self.send_json(view_record(record))
            return
        self.send_static(path)

    def send_json(self, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, path: str) -> None:
        if path == "/":
            path = "/index.html"
        target = (STATIC_DIR / path.lstrip("/")).resolve()
        if STATIC_DIR not in target.parents and target != STATIC_DIR:
            self.send_error(403)
            return
        if not target.exists() or not target.is_file():
            self.send_error(404)
            return
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }.get(target.suffix, "application/octet-stream")
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect reprocli MiniMax JSONL outputs.")
    parser.add_argument("--run", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ViewerHandler.run_data = load_run(args.run)
    server = ThreadingHTTPServer((args.host, args.port), ViewerHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"MiniMax viewer serving {ViewerHandler.run_data['base_path']} at {url}")
    server.serve_forever()


if __name__ == "__main__":
    main()
