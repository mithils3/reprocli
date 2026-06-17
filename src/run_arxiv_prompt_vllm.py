#!/usr/bin/env python3
"""Run prompts/prompt.txt over NeurIPS arXiv LaTeX papers with vLLM."""

from __future__ import annotations

import random
import sys

from reprocli_vllm.config.config import CLAIM_PLACEHOLDER, PLACEHOLDER
from reprocli_vllm.audit.inputs import build_audit_prompt, load_audit_rubric
from reprocli_vllm.config.cli_args import parse_args
from reprocli_vllm.hf_upload import hf_run_uploader
from reprocli_vllm.runtime.mre_records import load_mre_records
from reprocli_vllm.papers.bundles import load_bundle_papers
from reprocli_vllm.papers.papers import Paper
from reprocli_vllm.runtime.tool_loop import run_tool_loop
from reprocli_vllm.vllm.server import VllmServer


def main() -> int:
    args = parse_args()
    prompt_template = args.prompt_file.read_text(encoding="utf-8")
    required_placeholder = CLAIM_PLACEHOLDER if args.mode == "audit" else PLACEHOLDER
    if required_placeholder not in prompt_template:
        raise SystemExit(f"{args.prompt_file} must contain {required_placeholder}.")

    claim_records: dict[str, dict] = {}
    rubric = ""
    if args.mode == "audit":
        # Claims-only: the audit-pool rows ARE the paper list; the auditor reads
        # the agent's run directory (one per paper) with read-only run-dir tools,
        # not the paper text.
        claim_records = load_mre_records(args.claims)
        rubric = load_audit_rubric(args.rubric_file)
        papers = [
            Paper(arxiv_id=arxiv_id, run_dir=run_dir_for(args.runs_dir, arxiv_id))
            for arxiv_id in claim_records
        ]
    else:
        papers = load_bundle_papers(args.dataset)
        papers = [paper for paper in papers if paper.tex_files]
    if args.paper_ids_file:
        papers = filter_papers_by_ids(papers, args.paper_ids_file)
    papers_to_run = select_papers(papers, args.num_prompts)
    prompts = [
        build_prompt(prompt_template, paper, claim_records, rubric, args.mode, args.runs_dir)
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


def run_dir_for(runs_dir, arxiv_id: str) -> str:
    return str(runs_dir / arxiv_id) if runs_dir else ""


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


def build_prompt(
    template: str,
    paper: Paper,
    claim_records: dict[str, dict],
    rubric: str,
    mode: str,
    runs_dir,
) -> str:
    if mode == "audit":
        return build_audit_prompt(
            template, rubric, claim_records.get(paper.arxiv_id), paper.arxiv_id, runs_dir
        )
    return template.replace(PLACEHOLDER, paper.text())


def normalized_server_url(value: str) -> str:
    url = value.rstrip("/")
    if url.endswith("/v1"):
        url = url[:-3]
    return url


if __name__ == "__main__":
    raise SystemExit(main())
