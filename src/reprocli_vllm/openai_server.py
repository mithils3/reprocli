from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from .config import COMPILATION_CONFIG, MINIMAX_PARSER, NO_COMPILE_CONFIG


def local_open_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class VllmServer:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.port = args.vllm_server_port or local_open_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.process: subprocess.Popen | None = None

    def __enter__(self) -> str:
        compilation_config = NO_COMPILE_CONFIG if self.args.no_compile else COMPILATION_CONFIG
        command = [
            sys.executable,
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port),
            "--model",
            self.args.model,
            "--trust-remote-code",
            "--tensor-parallel-size",
            str(self.args.tensor_parallel_size),
            "--compilation-config",
            json.dumps(compilation_config, separators=(",", ":")),
            "--reasoning-parser",
            MINIMAX_PARSER,
            "--tool-call-parser",
            MINIMAX_PARSER,
            "--enable-auto-tool-choice",
            "--max-model-len",
            str(self.args.max_model_len),
            "--gpu-memory-utilization",
            str(self.args.gpu_memory_utilization),
        ]
        if self.args.enforce_eager:
            command.append("--enforce-eager")
        print("Starting persistent vLLM server: " + " ".join(command), file=sys.stderr)
        self.process = subprocess.Popen(command)
        self.wait_until_ready()
        return self.base_url

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()

    def wait_until_ready(self) -> None:
        deadline = time.monotonic() + self.args.server_startup_timeout
        health_url = f"{self.base_url}/health"
        while time.monotonic() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError(f"vLLM server exited with code {self.process.returncode}")
            try:
                with urllib.request.urlopen(health_url, timeout=5) as response:
                    if 200 <= response.status < 300:
                        print(f"vLLM server ready at {self.base_url}", file=sys.stderr)
                        return
            except (OSError, urllib.error.URLError):
                time.sleep(5)
        raise TimeoutError(
            f"vLLM server did not become ready within "
            f"{self.args.server_startup_timeout:.0f}s at {self.base_url}"
        )
