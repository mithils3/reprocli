#!/usr/bin/env python3
"""Run prompt.txt over NeurIPS arXiv LaTeX papers with vLLM."""

from __future__ import annotations

import argparse
import sys

from reprocli_vllm.batch_io import initial_messages, write_batch_requests
from reprocli_vllm.config import (
    DEFAULT_DATASET,
    DEFAULT_MODEL,
    DEFAULT_OUTPUT,
    DEFAULT_REQUESTS_OUTPUT,
    PLACEHOLDER,
)
from reprocli_vllm.openai_client import run_requests
from reprocli_vllm.openai_server import VllmServer
from reprocli_vllm.papers import load_papers
from reprocli_vllm.tool_loop import run_tool_loop
from reprocli_vllm.vllm_cache import default_cache_dir


def main() -> int:
    args = parse_args()
    prompt_template = args.prompt_file.read_text(encoding="utf-8")
    if PLACEHOLDER not in prompt_template:
        raise SystemExit(f"{args.prompt_file} must contain {PLACEHOLDER}.")

    papers = load_papers(args.dataset, args.split, args.cache_dir)
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
    if args.batch_backend == "server" and not args.vllm_server_url:
        with VllmServer(args) as server_url:
            args.vllm_server_url = server_url
            run(args, papers_to_run, prompts)
    else:
        run(args, papers_to_run, prompts)

    print(f"Wrote {len(prompts)} batch responses to {args.output}", file=sys.stderr)
    return 0


def run(args: argparse.Namespace, papers_to_run, prompts: list[str]) -> None:
    if args.disable_web_tools or args.tool_rounds == 0:
        run_single_batch(args, papers_to_run, prompts)
    else:
        run_tool_loop(args, papers_to_run, prompts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-prompts", type=int)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--split", default="train")
    parser.add_argument("--cache-dir")
    parser.add_argument("--prompt-file", type=argparse_path, default=argparse_path("prompt.txt"))
    parser.add_argument("--output", type=argparse_path, default=DEFAULT_OUTPUT)
    parser.add_argument("--requests-output", type=argparse_path, default=DEFAULT_REQUESTS_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--vllm-cache-dir", type=argparse_path)
    parser.add_argument("--tensor-parallel-size", type=int, default=4)
    parser.add_argument("--max-model-len", type=int, default=196608)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.9)
    parser.add_argument("--max-tokens", type=int, default=32768)
    parser.add_argument("--max-input-tokens", type=int, default=128000)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--tool-rounds", type=int, default=4)
    parser.add_argument("--tool-timeout", type=float, default=20.0)
    parser.add_argument("--tool-max-chars", type=int, default=8000)
    parser.add_argument("--batch-backend", choices=("server", "run-batch"), default="server")
    parser.add_argument("--vllm-server-url")
    parser.add_argument("--vllm-server-port", type=int)
    parser.add_argument("--server-startup-timeout", type=float, default=1800.0)
    parser.add_argument("--request-timeout", type=float, default=1800.0)
    parser.add_argument("--request-workers", type=int, default=8)
    parser.add_argument("--stream-first-response", action="store_true")
    parser.add_argument("--first-tool-choice", choices=("required", "auto"), default="required")
    parser.add_argument("--disable-web-tools", action="store_true")
    parser.add_argument("--no-compile", action="store_true")
    parser.add_argument("--enforce-eager", action="store_true")
    args = parser.parse_args()
    if args.tool_rounds < 0:
        parser.error("--tool-rounds must be >= 0")
    if args.batch_backend == "server" and args.vllm_server_url and args.vllm_server_port:
        parser.error("--vllm-server-url cannot be combined with --vllm-server-port")
    if args.request_workers < 1:
        parser.error("--request-workers must be >= 1")
    if args.max_input_tokens < 1:
        parser.error("--max-input-tokens must be >= 1")
    if args.max_input_tokens + args.max_tokens > args.max_model_len:
        parser.error("--max-input-tokens + --max-tokens must fit within --max-model-len")
    if args.vllm_cache_dir is None:
        args.vllm_cache_dir = default_cache_dir(args.model)
    return args


def argparse_path(value: str):
    from pathlib import Path

    return Path(value)


def run_single_batch(args: argparse.Namespace, papers, prompts: list[str]) -> None:
    conversations = {
        paper.arxiv_id: initial_messages(prompt, include_web_system=False)
        for paper, prompt in zip(papers, prompts, strict=True)
    }
    write_batch_requests(
        args.requests_output,
        args.model,
        list(conversations),
        conversations,
        args,
        include_tools=False,
    )
    run_requests(args, args.requests_output, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
