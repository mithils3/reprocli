from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from .config import (
    SERVER_STARTUP_TIMEOUT,
)
from .vllm_cache import subprocess_env


def local_open_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class VllmServer:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.port = local_open_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.process: subprocess.Popen | None = None

    def __enter__(self) -> str:
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
            "--tensor-parallel-size",
            str(self.args.tensor_parallel_size),
            "--reasoning-parser",
            self.args.reasoning_parser,
            "--tool-call-parser",
            self.args.tool_call_parser,
            "--enable-auto-tool-choice",
            "--max-model-len",
            str(self.args.max_model_len),
            "--gpu-memory-utilization",
            str(self.args.gpu_memory_utilization),
        ]
        if self.args.compilation_config:
            command.extend(["--compilation-config", self.args.compilation_config])
        if self.args.tokenizer_mode:
            command.extend(["--tokenizer-mode", self.args.tokenizer_mode])
        if self.args.kv_cache_dtype:
            command.extend(["--kv-cache-dtype", self.args.kv_cache_dtype])
        if self.args.block_size:
            command.extend(["--block-size", str(self.args.block_size)])
        if self.args.enable_expert_parallel:
            command.append("--enable-expert-parallel")
        if self.args.disable_flashinfer_autotune:
            command.append("--no-enable-flashinfer-autotune")
        if self.args.trust_remote_code:
            command.append("--trust-remote-code")
        env = subprocess_env(self.args.vllm_cache_dir)
        if env:
            print(f"Using VLLM_CACHE_ROOT={self.args.vllm_cache_dir}", file=sys.stderr)
        print("Starting persistent vLLM server: " + " ".join(command), file=sys.stderr)
        self.process = subprocess.Popen(command, env=env)
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
        deadline = time.monotonic() + SERVER_STARTUP_TIMEOUT
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
            f"{SERVER_STARTUP_TIMEOUT:.0f}s at {self.base_url}"
        )
