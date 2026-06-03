#!/usr/bin/env python3
"""Run prompt.txt over NeurIPS arXiv LaTeX papers with vLLM."""

from __future__ import annotations

import argparse
import json
import sys

from reprocli_vllm.config import (
    COMPILATION_CONFIG,
    DEFAULT_DATASET,
    DEFAULT_MODEL,
    DEFAULT_OUTPUT,
    DEFAULT_REQUESTS_OUTPUT,
    MAX_MODEL_LEN,
    PLACEHOLDER,
)
from reprocli_vllm.openai_server import VllmServer
from reprocli_vllm.papers import load_papers
from reprocli_vllm.tool_loop import run_tool_loop
from reprocli_vllm.vllm_cache import default_cache_dir


def main() -> int:
    args = parse_args()
    prompt_template = args.prompt_file.read_text(encoding="utf-8")
    if PLACEHOLDER not in prompt_template:
        raise SystemExit(f"{args.prompt_file} must contain {PLACEHOLDER}.")

    papers = load_papers(args.dataset)
    papers = [paper for paper in papers if paper.tex_files]
    papers_to_run = papers[: args.num_prompts] if args.num_prompts else papers
    prompts = [
        prompt_template.replace(PLACEHOLDER, paper.text())
        for paper in papers_to_run
    ]

    print(
        f"Running {len(prompts)} prompts "
        f"({'full dataset' if args.num_prompts is None else f'first {args.num_prompts}'})",
        file=sys.stderr,
    )
    with VllmServer(args) as server_url:
        run_tool_loop(args, papers_to_run, prompts, server_url)

    print(f"Wrote {len(prompts)} batch responses to {args.output}", file=sys.stderr)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-prompts", type=int)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--prompt-file", type=argparse_path, default=argparse_path("prompt.txt"))
    parser.add_argument("--output", type=argparse_path, default=DEFAULT_OUTPUT)
    parser.add_argument("--requests-output", type=argparse_path, default=DEFAULT_REQUESTS_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--vllm-cache-dir", type=argparse_path)
    parser.add_argument("--max-tokens", type=int, default=32768)
    parser.add_argument("--max-input-tokens", type=int, default=128000)
    parser.add_argument("--tool-rounds", type=int, default=32)
    parser.add_argument("--request-workers", type=int, default=8)
    parser.add_argument("--stream-first-response", action="store_true")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument(
        "--compilation-config",
        default=json.dumps(COMPILATION_CONFIG, separators=(",", ":")),
    )
    args = parser.parse_args()
    if args.tool_rounds < 1:
        parser.error("--tool-rounds must be >= 1")
    if args.request_workers < 1:
        parser.error("--request-workers must be >= 1")
    if args.max_input_tokens < 1:
        parser.error("--max-input-tokens must be >= 1")
    if args.max_input_tokens + args.max_tokens > MAX_MODEL_LEN:
        parser.error("--max-input-tokens + --max-tokens must fit within model context")
    if args.vllm_cache_dir is None:
        args.vllm_cache_dir = default_cache_dir(args.model)
    return args


def argparse_path(value: str):
    from pathlib import Path

    return Path(value)


if __name__ == "__main__":
    raise SystemExit(main())
