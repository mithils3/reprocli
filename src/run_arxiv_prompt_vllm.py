#!/usr/bin/env python3
"""Run prompt.txt over NeurIPS arXiv LaTeX papers with vLLM run-batch."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_DATASET = "Mithilss/neurips-2025-arxiv-latex-sources"
DEFAULT_MODEL = "MiniMaxAI/MiniMax-M2.7"
DEFAULT_OUTPUT = Path("outputs/neurips_2025_minimax_m27.jsonl")
DEFAULT_REQUESTS_OUTPUT = Path("outputs/neurips_2025_minimax_m27_requests.jsonl")
PLACEHOLDER = "{PAPER_TEXT}"
TEX_EXTENSION = ".tex"
MINIMAX_PARSER = "minimax_m2"
COMPILATION_CONFIG = {
    "mode": 3,
    "pass_config": {"fuse_minimax_qk_norm": True},
}


@dataclass
class Paper:
    arxiv_id: str
    title: str = ""
    source_url: str = ""
    tex_files: dict[str, str] = field(default_factory=dict)

    def text(self) -> str:
        header = [
            f"arxiv_id: {self.arxiv_id}",
            f"title: {self.title}",
            f"source_url: {self.source_url}",
        ]
        sections = [
            f"### {path}\n{content}"
            for path, content in sorted(self.tex_files.items())
        ]
        return "\n".join(header) + "\n\n" + "\n\n".join(sections)


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

    write_batch_requests(args.requests_output, args.model, papers_to_run, prompts, args)
    run_vllm_batch(args)

    print(f"Wrote {len(prompts)} batch responses to {args.output}", file=sys.stderr)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--num-prompts",
        type=int,
        help="Number of papers to run. Omit this to run the full dataset.",
    )
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--split", default="train")
    parser.add_argument("--cache-dir")
    parser.add_argument("--prompt-file", type=Path, default=Path("prompt.txt"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--requests-output", type=Path, default=DEFAULT_REQUESTS_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--tensor-parallel-size", type=int, default=4)
    parser.add_argument("--max-model-len", type=int, default=196608)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.9)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    return parser.parse_args()


def load_papers(dataset_name: str, split: str, cache_dir: str | None) -> list[Paper]:
    from datasets import load_dataset

    dataset_kwargs: dict[str, Any] = {"split": split}
    if cache_dir:
        dataset_kwargs["cache_dir"] = cache_dir
    dataset = load_dataset(dataset_name, **dataset_kwargs)

    papers: dict[str, Paper] = {}
    for row in dataset:
        arxiv_id = row["arxiv_id"]
        paper = papers.setdefault(
            arxiv_id,
            Paper(
                arxiv_id=arxiv_id,
                title=row.get("title") or "",
                source_url=row.get("source_url") or "",
            ),
        )
        if row.get("is_text") and row.get("extension") == TEX_EXTENSION and row.get("text"):
            paper.tex_files[row["relative_path"]] = row["text"]

    print(f"Loaded {len(papers)} papers from {dataset_name}", file=sys.stderr)
    return list(papers.values())


def write_batch_requests(
    output_path: Path,
    model: str,
    papers: list[Paper],
    prompts: list[str],
    args: argparse.Namespace,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for paper, prompt in zip(papers, prompts, strict=True):
            request = {
                "custom_id": paper.arxiv_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": args.temperature,
                    "top_p": args.top_p,
                    "max_tokens": args.max_tokens,
                },
            }
            json.dump(request, handle, ensure_ascii=False)
            handle.write("\n")
    print(f"Wrote batch requests to {output_path}", file=sys.stderr)


def run_vllm_batch(args: argparse.Namespace) -> None:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "vllm.entrypoints.openai.run_batch",
        "--input-file",
        str(args.requests_output),
        "--output-file",
        str(args.output),
        "--model",
        args.model,
        "--trust-remote-code",
        "--tensor-parallel-size",
        str(args.tensor_parallel_size),
        "--compilation-config",
        json.dumps(COMPILATION_CONFIG, separators=(",", ":")),
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
    print("Running: " + " ".join(command), file=sys.stderr)
    subprocess.run(command, check=True)


if __name__ == "__main__":
    raise SystemExit(main())
