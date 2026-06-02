from __future__ import annotations

import argparse
import json
import sys
import urllib.request
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
    print(f"Posting {len(rows)} request(s) to {base_url}", file=sys.stderr)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            response = post_chat_completion(base_url, row["body"], args.request_timeout)
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
