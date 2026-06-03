#!/usr/bin/env python3
"""Run prompt.txt over NeurIPS arXiv LaTeX papers with vLLM."""

from __future__ import annotations

import argparse
import json
import sys

from reprocli_vllm.config import (
    DEFAULT_DATASET,
    DEFAULT_EXTRACTED_OUTPUT,
    DEFAULT_MODEL,
    DEFAULT_OUTPUT,
    DEFAULT_REQUESTS_OUTPUT,
    PLACEHOLDER,
)
from reprocli_vllm.model_profiles import PROFILES, infer_profile_name
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
    print(f"Wrote extracted {args.extracted_format} to {args.extracted_output}", file=sys.stderr)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-prompts", type=int)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--prompt-file", type=argparse_path, default=argparse_path("prompt.txt"))
    parser.add_argument("--output", type=argparse_path, default=DEFAULT_OUTPUT)
    parser.add_argument("--extracted-output", type=argparse_path, default=DEFAULT_EXTRACTED_OUTPUT)
    parser.add_argument("--extracted-format", choices=("jsonl", "csv"), default="jsonl")
    parser.add_argument("--requests-output", type=argparse_path, default=DEFAULT_REQUESTS_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--model-profile", choices=["auto", *PROFILES], default="auto")
    parser.add_argument("--vllm-cache-dir", type=argparse_path)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--max-input-tokens", type=int, default=128000)
    parser.add_argument("--tool-rounds", type=int, default=10)
    parser.add_argument("--max-repeated-tool-calls", type=int, default=1)
    parser.add_argument("--request-workers", type=int, default=8)
    parser.add_argument("--reasoning-effort", choices=("auto", "none", "high", "max"), default="auto")
    parser.add_argument("--tensor-parallel-size", type=int)
    parser.add_argument("--max-model-len", type=int)
    parser.add_argument("--gpu-memory-utilization", type=float)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-p", type=float)
    parser.add_argument("--enable-expert-parallel", action="store_true")
    parser.add_argument("--enable-flashinfer-autotune", action="store_true")
    parser.add_argument("--stream-first-response", action="store_true")
    parser.add_argument("--save-round-jsonl", action="store_true")
    parser.add_argument("--disable-structured-final-output", action="store_true")
    parser.add_argument("--trust-remote-code", action="store_true")
    parser.add_argument(
        "--compilation-config",
        default=None,
        help="Optional vLLM compilation JSON override.",
    )
    args = parser.parse_args()
    apply_model_profile(args)
    if args.tool_rounds < 1:
        parser.error("--tool-rounds must be >= 1")
    if args.request_workers < 1:
        parser.error("--request-workers must be >= 1")
    if args.max_repeated_tool_calls < 1:
        parser.error("--max-repeated-tool-calls must be >= 1")
    if args.max_input_tokens < 1:
        parser.error("--max-input-tokens must be >= 1")
    if args.max_input_tokens + args.max_tokens > args.max_model_len:
        parser.error("--max-input-tokens + --max-tokens must fit within model context")
    if args.reasoning_effort == "max" and args.max_model_len < 393216:
        parser.error("--reasoning-effort max needs --max-model-len >= 393216")
    if args.vllm_cache_dir is None:
        args.vllm_cache_dir = default_cache_dir(args.model)
    if args.extracted_format == "csv" and args.extracted_output == DEFAULT_EXTRACTED_OUTPUT:
        args.extracted_output = args.extracted_output.with_suffix(".csv")
    return args


def apply_model_profile(args: argparse.Namespace) -> None:
    profile = PROFILES[infer_profile_name(args.model, args.model_profile)]
    if args.model == DEFAULT_MODEL:
        args.model = profile.model
    args.model_profile = profile.name
    args.tensor_parallel_size = args.tensor_parallel_size or profile.tensor_parallel_size
    args.max_model_len = args.max_model_len or profile.max_model_len
    args.gpu_memory_utilization = args.gpu_memory_utilization or profile.gpu_memory_utilization
    args.tool_call_parser = profile.tool_call_parser
    args.reasoning_parser = profile.reasoning_parser
    args.tokenizer_mode = profile.tokenizer_mode
    args.kv_cache_dtype = profile.kv_cache_dtype
    args.block_size = profile.block_size
    args.enable_expert_parallel = args.enable_expert_parallel or profile.enable_expert_parallel
    args.disable_flashinfer_autotune = (
        profile.disable_flashinfer_autotune and not args.enable_flashinfer_autotune
    )
    args.trust_remote_code = args.trust_remote_code or profile.trust_remote_code
    args.temperature = profile.temperature if args.temperature is None else args.temperature
    args.top_p = profile.top_p if args.top_p is None else args.top_p
    if args.compilation_config is None and profile.compilation_config is not None:
        args.compilation_config = json.dumps(profile.compilation_config, separators=(",", ":"))
    if args.reasoning_effort == "auto":
        args.reasoning_effort = profile.default_reasoning_effort
    args.chat_template_kwargs = chat_template_kwargs(args.reasoning_effort)


def chat_template_kwargs(reasoning_effort: str) -> dict | None:
    if reasoning_effort == "none":
        return None
    return {"thinking": True, "reasoning_effort": reasoning_effort}


def argparse_path(value: str):
    from pathlib import Path

    return Path(value)


if __name__ == "__main__":
    raise SystemExit(main())
