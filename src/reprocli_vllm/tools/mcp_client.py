from __future__ import annotations

import atexit
import json
import select
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from typing import Any


MCP_PROTOCOL_VERSION = "2025-06-18"


class MCPError(RuntimeError):
    pass


class StreamableHTTPMCPClient:
    def __init__(self, url: str, headers: dict[str, str], timeout: float) -> None:
        self.url = url
        self.headers = headers
        self.timeout = timeout
        self.lock = threading.Lock()
        self.next_id = 1
        self.session_id: str | None = None
        self.protocol_version = MCP_PROTOCOL_VERSION
        self.initialized = False

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.ensure_initialized()
            return self.request("tools/call", {"name": name, "arguments": arguments})

    def list_tools(self) -> list[dict[str, Any]]:
        with self.lock:
            self.ensure_initialized()
            result = self.request("tools/list", {})
            tools = result.get("tools") or []
            return [tool for tool in tools if isinstance(tool, dict)]

    def ensure_initialized(self) -> None:
        if self.initialized:
            return
        result = self.request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "reprocli-vllm", "version": "0.1"},
            },
            initialize=True,
        )
        self.protocol_version = str(result.get("protocolVersion") or MCP_PROTOCOL_VERSION)
        self.notify("notifications/initialized", {})
        self.initialized = True

    def request(
        self,
        method: str,
        params: dict[str, Any],
        *,
        initialize: bool = False,
    ) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        response = self.post(message, expect_response=True, initialize=initialize)
        return response_result(response, request_id)

    def notify(self, method: str, params: dict[str, Any]) -> None:
        message = {"jsonrpc": "2.0", "method": method, "params": params}
        self.post(message, expect_response=False, initialize=False)

    def post(
        self,
        message: dict[str, Any],
        *,
        expect_response: bool,
        initialize: bool,
    ) -> dict[str, Any] | list[Any] | None:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            **self.headers,
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.protocol_version and not initialize:
            headers["MCP-Protocol-Version"] = self.protocol_version
        request = urllib.request.Request(
            self.url,
            data=json.dumps(message).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        status, response_headers, content_type, text = open_request(request, self.timeout)
        session_id = response_headers.get("Mcp-Session-Id")
        if session_id:
            self.session_id = session_id
        if status == 202 and not expect_response:
            return None
        if not 200 <= status < 300:
            raise MCPError(f"HTTP {status} from MCP server: {text[:500]}")
        if not text.strip():
            return None
        return decode_http_response(content_type, text)


class StdioMCPClient:
    def __init__(self, command: Sequence[str], env: dict[str, str], timeout: float) -> None:
        self.command = list(command)
        self.env = env
        self.timeout = timeout
        self.lock = threading.Lock()
        self.next_id = 1
        self.process: subprocess.Popen[str] | None = None
        self.protocol_version = MCP_PROTOCOL_VERSION
        self.initialized = False
        atexit.register(self.close)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.ensure_started()
            self.ensure_initialized()
            return self.request_locked("tools/call", {"name": name, "arguments": arguments})

    def list_tools(self) -> list[dict[str, Any]]:
        with self.lock:
            self.ensure_started()
            self.ensure_initialized()
            result = self.request_locked("tools/list", {})
            tools = result.get("tools") or []
            return [tool for tool in tools if isinstance(tool, dict)]

    def ensure_started(self) -> None:
        if self.process and self.process.poll() is None:
            return
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                env=self.env,
            )
        except OSError as exc:
            raise MCPError(f"Could not start MCP command {self.command!r}: {exc}") from exc
        self.initialized = False

    def ensure_initialized(self) -> None:
        if self.initialized:
            return
        result = self.request_locked(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "reprocli-vllm", "version": "0.1"},
            },
        )
        self.protocol_version = str(result.get("protocolVersion") or MCP_PROTOCOL_VERSION)
        self.notify_locked("notifications/initialized", {})
        self.initialized = True

    def request_locked(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        self.write_locked(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
        while True:
            response = self.read_locked()
            if response.get("id") == request_id:
                return response_result(response, request_id)

    def notify_locked(self, method: str, params: dict[str, Any]) -> None:
        self.write_locked({"jsonrpc": "2.0", "method": method, "params": params})

    def write_locked(self, message: dict[str, Any]) -> None:
        if not self.process or not self.process.stdin:
            raise MCPError("MCP process is not running")
        self.process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.process.stdin.flush()

    def read_locked(self) -> dict[str, Any]:
        if not self.process or not self.process.stdout:
            raise MCPError("MCP process is not running")
        deadline = time.monotonic() + self.timeout
        fd = self.process.stdout.fileno()
        while True:
            if self.process.poll() is not None:
                raise MCPError(f"MCP process exited with code {self.process.returncode}")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise MCPError("Timed out waiting for MCP response")
            ready, _, _ = select.select([fd], [], [], remaining)
            if not ready:
                continue
            line = self.process.stdout.readline()
            if not line:
                raise MCPError("MCP process closed stdout")
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value

    def close(self) -> None:
        process = self.process
        self.process = None
        if process and process.poll() is None:
            process.terminate()


def open_request(
    request: urllib.request.Request,
    timeout: float,
) -> tuple[int, Any, str, str]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read(2_000_000).decode("utf-8", errors="replace")
            return (
                response.status,
                response.headers,
                response.headers.get("Content-Type", ""),
                text,
            )
    except urllib.error.HTTPError as exc:
        text = exc.read(2_000_000).decode("utf-8", errors="replace")
        return exc.code, exc.headers, exc.headers.get("Content-Type", ""), text


def decode_http_response(content_type: str, text: str) -> dict[str, Any] | list[Any]:
    if "text/event-stream" not in content_type.lower():
        value = json.loads(text)
        if isinstance(value, (dict, list)):
            return value
        raise MCPError(f"Unexpected MCP response: {text[:500]}")
    events = []
    data_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").strip())
        elif not line.strip() and data_lines:
            events.append("\n".join(data_lines))
            data_lines = []
    if data_lines:
        events.append("\n".join(data_lines))
    for event in events:
        if event and event != "[DONE]":
            value = json.loads(event)
            if isinstance(value, (dict, list)):
                return value
    raise MCPError("MCP server returned no JSON-RPC event")


def response_result(response: Any, request_id: int) -> dict[str, Any]:
    if isinstance(response, list):
        matches = [
            item
            for item in response
            if isinstance(item, dict) and item.get("id") == request_id
        ]
        if not matches:
            raise MCPError(f"MCP response did not include id {request_id}")
        response = matches[0]
    if not isinstance(response, dict):
        raise MCPError(f"Unexpected MCP response type: {type(response).__name__}")
    if response.get("error"):
        raise MCPError(f"MCP error: {response['error']}")
    result = response.get("result")
    if not isinstance(result, dict):
        raise MCPError(f"Unexpected MCP result: {result!r}")
    return result
