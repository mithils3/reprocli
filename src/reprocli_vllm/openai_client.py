from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .batch_io import iter_batch_requests
from .vllm_batch import run_vllm_batch


def run_requests(args: argparse.Namespace, input_path: Path, output_path: Path) -> None:
    if args.batch_backend == "run-batch":
        run_vllm_batch(args, input_path, output_path)
        return
    run_openai_server_requests(args, input_path, output_path)


def run_openai_server_requests(
    args: argparse.Namespace,
    input_path: Path,
    output_path: Path,
) -> None:
    base_url = args.vllm_server_url.rstrip("/")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = iter_batch_requests(input_path)
    workers = max(1, min(args.request_workers, len(rows)))
    print(
        f"Posting {len(rows)} request(s) to {base_url} with {workers} worker(s)",
        file=sys.stderr,
    )
    responses = post_chat_completions(
        base_url,
        rows,
        args.request_timeout,
        workers,
        args.stream_first_response,
    )
    with output_path.open("w", encoding="utf-8") as handle:
        for row, response in zip(rows, responses, strict=True):
            json.dump(
                {
                    "custom_id": row["custom_id"],
                    "response": {
                        "status_code": 200,
                        "body": response,
                    },
                },
                handle,
                ensure_ascii=False,
            )
            handle.write("\n")


def post_chat_completions(
    base_url: str,
    rows: list[dict[str, Any]],
    timeout: float,
    workers: int,
    stream_first: bool,
) -> list[Any]:
    if stream_first and rows:
        return post_chat_completions_with_stream(base_url, rows, timeout, workers)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(
            executor.map(
                lambda row: post_chat_completion(base_url, row["body"], timeout),
                rows,
            )
        )


def post_chat_completions_with_stream(
    base_url: str,
    rows: list[dict[str, Any]],
    timeout: float,
    workers: int,
) -> list[Any]:
    responses: list[Any] = [None] * len(rows)
    with ThreadPoolExecutor(max_workers=max(1, workers - 1)) as executor:
        futures = [
            executor.submit(post_chat_completion, base_url, row["body"], timeout)
            for row in rows[1:]
        ]
        responses[0] = stream_chat_completion(base_url, rows[0], timeout)
        for index, future in enumerate(futures, start=1):
            responses[index] = future.result()
    return responses


def post_chat_completion(base_url: str, body: dict[str, Any], timeout: float) -> Any:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def stream_chat_completion(base_url: str, row: dict[str, Any], timeout: float) -> Any:
    body = dict(row["body"])
    body["stream"] = True
    print(f"\n--- streaming {row['custom_id']} ---", file=sys.stderr, flush=True)
    try:
        return post_streaming_chat_completion(base_url, body, timeout)
    finally:
        print(f"\n--- end stream {row['custom_id']} ---", file=sys.stderr, flush=True)


def post_streaming_chat_completion(
    base_url: str,
    body: dict[str, Any],
    timeout: float,
) -> Any:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    builder = StreamedResponseBuilder(body["model"])
    with urllib.request.urlopen(request, timeout=timeout) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line or line.startswith(":") or not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            builder.add_chunk(json.loads(payload))
    return builder.response()


class StreamedResponseBuilder:
    def __init__(self, model: str) -> None:
        self.model = model
        self.role = "assistant"
        self.content_parts: list[str] = []
        self.reasoning_parts: list[str] = []
        self.tool_calls: dict[int, dict[str, Any]] = {}
        self.finish_reason: str | None = None

    def add_chunk(self, chunk: dict[str, Any]) -> None:
        choices = chunk.get("choices") or []
        if not choices:
            return
        choice = choices[0]
        self.finish_reason = choice.get("finish_reason") or self.finish_reason
        delta = choice.get("delta") or {}
        self.role = delta.get("role") or self.role
        self.add_text_delta(delta)
        self.add_tool_call_deltas(delta.get("tool_calls") or [])

    def add_text_delta(self, delta: dict[str, Any]) -> None:
        content = delta.get("content")
        if content:
            self.content_parts.append(content)
            print(content, end="", file=sys.stderr, flush=True)
        reasoning = delta.get("reasoning") or delta.get("reasoning_content")
        if reasoning:
            self.reasoning_parts.append(reasoning)
            print(reasoning, end="", file=sys.stderr, flush=True)

    def add_tool_call_deltas(self, deltas: list[dict[str, Any]]) -> None:
        for delta in deltas:
            index = int(delta.get("index", len(self.tool_calls)))
            call = self.tool_calls.setdefault(
                index,
                {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
            )
            if delta.get("id"):
                call["id"] += delta["id"]
            function = delta.get("function") or {}
            if function.get("name"):
                call["function"]["name"] += function["name"]
            if function.get("arguments"):
                call["function"]["arguments"] += function["arguments"]
                print(function["arguments"], end="", file=sys.stderr, flush=True)

    def response(self) -> dict[str, Any]:
        message: dict[str, Any] = {
            "role": self.role,
            "content": "".join(self.content_parts) or None,
        }
        if self.reasoning_parts:
            message["reasoning"] = "".join(self.reasoning_parts)
        if self.tool_calls:
            message["tool_calls"] = [
                self.tool_calls[index] for index in sorted(self.tool_calls)
            ]
        return {
            "id": "streamed",
            "object": "chat.completion",
            "model": self.model,
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": self.finish_reason or "stop",
                }
            ],
        }
