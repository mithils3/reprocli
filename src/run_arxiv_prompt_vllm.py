#!/usr/bin/env python3
"""Run prompt.txt over NeurIPS arXiv LaTeX papers with vLLM."""

from __future__ import annotations

import argparse
import random
import sys

from reprocli_vllm.config import (
    DEFAULT_EXTRACTED_OUTPUT,
    DEFAULT_MODEL,
    DEFAULT_OUTPUT,
    DEFAULT_VLLM_DATASET,
    PAPER_BUNDLE_DATASET_URL,
    PLACEHOLDER,
)
from reprocli_vllm.hf_upload import hf_run_uploader
from reprocli_vllm.minimax_defaults import apply_model_defaults
from reprocli_vllm.paper_bundles import load_bundle_papers
from reprocli_vllm.tool_loop import run_tool_loop
from reprocli_vllm.trace_io import trace_output_path
from reprocli_vllm.vllm_server import VllmServer
from reprocli_vllm.vllm_cache import default_cache_dir


def main() -> int:
    args = parse_args()
    prompt_template = args.prompt_file.read_text(encoding="utf-8")
    if PLACEHOLDER not in prompt_template:
        raise SystemExit(f"{args.prompt_file} must contain {PLACEHOLDER}.")

    papers = load_bundle_papers(args.dataset)
    papers = [paper for paper in papers if paper.tex_files]
    if args.paper_ids_file:
        papers = filter_papers_by_ids(papers, args.paper_ids_file)
    papers_to_run = select_papers(papers, args.num_prompts)
    prompts = [
        prompt_template.replace(PLACEHOLDER, paper.text())
        for paper in papers_to_run
    ]

    print(
        f"Running {len(prompts)} prompts "
        f"({'full dataset' if args.num_prompts is None else f'random {args.num_prompts}'})",
        file=sys.stderr,
    )
    with hf_run_uploader(args):
        if args.vllm_server_url:
            server_url = normalized_server_url(args.vllm_server_url)
            print(f"Using existing vLLM server at {server_url}", file=sys.stderr)
            run_tool_loop(args, papers_to_run, prompts, server_url)
        else:
            with VllmServer(args) as server_url:
                run_tool_loop(args, papers_to_run, prompts, server_url)

    print(f"Finished writing {len(prompts)} responses to {args.output}", file=sys.stderr)
    print(f"Finished writing extracted JSONL to {args.extracted_output}", file=sys.stderr)
    if args.hf_repo:
        print(
            f"Uploaded run outputs to https://huggingface.co/datasets/{args.hf_repo}",
            file=sys.stderr,
        )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-prompts", type=int)
    parser.add_argument(
        "--dataset",
        default=DEFAULT_VLLM_DATASET,
        help=(
            "Paper-bundle dataset with LaTeX and OpenReview supplements. "
            f"Default: {PAPER_BUNDLE_DATASET_URL}"
        ),
    )
    parser.add_argument("--prompt-file", type=argparse_path, default=argparse_path("prompt.txt"))
    parser.add_argument("--output", type=argparse_path, default=DEFAULT_OUTPUT)
    parser.add_argument("--extracted-output", type=argparse_path, default=DEFAULT_EXTRACTED_OUTPUT)
    parser.add_argument("--trace-output", type=argparse_path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--vllm-server-url",
        help=(
            "Existing vLLM chat-completions server base URL. When set, the "
            "runner skips launching its embedded local server."
        ),
    )
    parser.add_argument(
        "--paper-ids-file",
        type=argparse_path,
        help=(
            "Run only the arXiv ids listed in this file (one per line), e.g. "
            "the output of `python -m reprocli_vllm.rerun select`."
        ),
    )
    parser.add_argument(
        "--hf-repo",
        help=(
            "Hugging Face dataset repo id (e.g. Mithilss/neurips-2025-results). "
            "When set, run outputs are pushed there incrementally and at the end."
        ),
    )
    parser.add_argument(
        "--hf-path-in-repo",
        default="",
        help="Optional subfolder inside the HF repo for the uploaded files.",
    )
    parser.add_argument(
        "--hf-upload-every",
        type=float,
        default=10.0,
        help="Minutes between incremental HF uploads (default: 10).",
    )
    parser.add_argument(
        "--hf-private",
        action="store_true",
        help="Create the HF repo as private when it does not exist yet.",
    )
    parser.add_argument("--vllm-cache-dir", type=argparse_path)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--max-input-tokens", type=int, default=128000)
    parser.add_argument("--tool-rounds", type=int, default=10)
    parser.add_argument("--max-repeated-tool-calls", type=int, default=2)
    parser.add_argument("--request-workers", type=int, default=8)
    parser.add_argument("--tensor-parallel-size", type=int)
    parser.add_argument("--distributed-executor-backend", choices=("mp", "ray"))
    parser.add_argument("--max-model-len", type=int)
    parser.add_argument("--gpu-memory-utilization", type=float)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-p", type=float)
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--tool-call-parser")
    parser.add_argument("--reasoning-parser")
    parser.add_argument("--tokenizer-mode")
    parser.add_argument("--kv-cache-dtype")
    parser.add_argument("--block-size", type=int)
    parser.add_argument("--mm-encoder-tp-mode")
    parser.add_argument("--stream-first-response", action="store_true")
    parser.add_argument("--save-round-jsonl", action="store_true")
    parser.add_argument(
        "--structured-outputs-backend",
        default=None,
        help=(
            "Structured outputs backend for the embedded vLLM server, passed as "
            "--structured-outputs-config.backend (e.g. xgrammar). Defaults to "
            "the server's auto selection."
        ),
    )
    parser.add_argument(
        "--compilation-config",
        default=None,
        help="Optional vLLM compilation JSON override.",
    )
    args = parser.parse_args()
    apply_model_defaults(args)
    if args.tool_rounds < 1:
        parser.error("--tool-rounds must be >= 1")
    if args.num_prompts is not None and args.num_prompts < 1:
        parser.error("--num-prompts must be >= 1")
    if args.request_workers < 1:
        parser.error("--request-workers must be >= 1")
    if args.max_repeated_tool_calls < 1:
        parser.error("--max-repeated-tool-calls must be >= 1")
    if args.max_input_tokens < 1:
        parser.error("--max-input-tokens must be >= 1")
    if args.hf_upload_every <= 0:
        parser.error("--hf-upload-every must be > 0")
    if args.top_k is not None and args.top_k < 1:
        parser.error("--top-k must be >= 1")
    if args.max_input_tokens + args.max_tokens > args.max_model_len:
        parser.error("--max-input-tokens + --max-tokens must fit within model context")
    if args.vllm_cache_dir is None:
        args.vllm_cache_dir = default_cache_dir(args.model)
    if args.trace_output is None:
        args.trace_output = trace_output_path(args.output)
    return args


def select_papers(papers: list, num_prompts: int | None) -> list:
    if num_prompts is None:
        return papers
    return random.sample(papers, min(num_prompts, len(papers)))


def filter_papers_by_ids(papers: list, ids_file) -> list:
    wanted = {
        line.strip()
        for line in ids_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    selected = [paper for paper in papers if paper.arxiv_id in wanted]
    missing = wanted - {paper.arxiv_id for paper in selected}
    if missing:
        print(
            f"Warning: {len(missing)} requested id(s) not in dataset: "
            f"{', '.join(sorted(missing)[:10])}",
            file=sys.stderr,
        )
    return selected


def normalized_server_url(value: str) -> str:
    url = value.rstrip("/")
    if url.endswith("/v1"):
        url = url[:-3]
    return url


def argparse_path(value: str):
    from pathlib import Path

    return Path(value)


if __name__ == "__main__":
    raise SystemExit(main())
