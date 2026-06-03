from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .config import COMPILATION_CONFIG, MINIMAX_PARSER, NO_COMPILE_CONFIG
from .vllm_cache import subprocess_env


def run_vllm_batch(args: argparse.Namespace, input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    compilation_config = NO_COMPILE_CONFIG if args.no_compile else COMPILATION_CONFIG
    command = [
        sys.executable,
        "-m",
        "vllm.entrypoints.openai.run_batch",
        "--input-file",
        str(input_path),
        "--output-file",
        str(output_path),
        "--model",
        args.model,
        "--trust-remote-code",
        "--tensor-parallel-size",
        str(args.tensor_parallel_size),
        "--compilation-config",
        json.dumps(compilation_config, separators=(",", ":")),
        "--reasoning-parser",
        MINIMAX_PARSER,
        "--tool-call-parser",
        MINIMAX_PARSER,
        "--enable-auto-tool-choice",
        "--max-model-len",
        str(args.max_model_len),
        "--gpu-memory-utilization",
        str(args.gpu_memory_utilization),
    ]
    if args.enforce_eager:
        command.append("--enforce-eager")
    env = subprocess_env(args.vllm_cache_dir)
    if env:
        print(f"Using VLLM_CACHE_ROOT={args.vllm_cache_dir}", file=sys.stderr)
    print("Running: " + " ".join(command), file=sys.stderr)
    subprocess.run(command, check=True, env=env)
