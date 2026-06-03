#!/usr/bin/env python3
"""Run prompt.txt over arXiv papers with the OpenAI Batch API."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from reprocli_vllm.config import DEFAULT_DATASET, PLACEHOLDER
from reprocli_vllm.openai_arxiv import (
    DEFAULT_MODEL,
    DEFAULT_PROMPT_CACHE_KEY,
    DEFAULT_PROMPT_CACHE_RETENTION,
    batch_request,
    extracted_row,
    final_rows,
)
from reprocli_vllm.openai_batch import (
    RESPONSES_ENDPOINT,
    append_batch_registry,
    batch_specific_path,
    batch_status,
    create_responses_batch,
    download_batch_files,
    load_jsonl,
    read_batch_registry,
    rewrite_batch_registry,
    wait_for_terminal_batch,
    write_batch_info,
    write_jsonl,
)
from reprocli_vllm.papers import Paper, load_papers

DEFAULT_OUTPUT = Path("outputs/neurips_2025_openai_gpt55.jsonl")
DEFAULT_EXTRACTED_OUTPUT = Path("outputs/neurips_2025_openai_gpt55_extracted.jsonl")


def main() -> int:
    args = parse_args()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set.")

    from openai import OpenAI

    client = OpenAI()
    if args.download:
        return download_saved_batches(client, args)

    papers = selected_papers(args)
    batch = client.batches.retrieve(args.batch_id) if args.batch_id else submit_batch(
        client, args, papers
    )
    write_batch_info(args.batch_info_output, batch)
    print_batch_saved(args, batch)

    if args.submit_only:
        save_batch_record(args, batch)
        return 0

    if batch_status(batch) not in {"completed", "failed", "expired", "cancelled"}:
        batch = wait_for_terminal_batch(client, batch.id, args.poll_interval_seconds)
        write_batch_info(args.batch_info_output, batch)

    if batch_status(batch) != "completed":
        download_batch_files(
            client,
            batch,
            output_path=args.batch_results_output,
            error_path=args.batch_errors_output,
        )
        raise SystemExit(f"Batch {batch.id} ended with status={batch_status(batch)}.")

    download_batch_files(
        client,
        batch,
        output_path=args.batch_results_output,
        error_path=args.batch_errors_output,
    )
    write_processed_outputs(args, papers, args.batch_results_output)
    remove_batch_record(args.batch_registry, batch.id)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-prompts", type=int, default=10)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--prompt-file", type=Path, default=Path("prompt.txt"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--extracted-output", type=Path, default=DEFAULT_EXTRACTED_OUTPUT)
    parser.add_argument("--batch-input", type=Path)
    parser.add_argument("--batch-info-output", type=Path)
    parser.add_argument("--batch-results-output", type=Path)
    parser.add_argument("--batch-errors-output", type=Path)
    parser.add_argument("--batch-registry", type=Path)
    parser.add_argument("--batch-id", help="Resume an existing OpenAI batch.")
    parser.add_argument("--download", action="store_true", help="Download pending saved batches.")
    parser.add_argument("--submit-only", action="store_true")
    parser.add_argument("--poll-interval-seconds", type=float, default=60.0)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument("--max-paper-chars", type=int, default=220_000)
    parser.add_argument("--reasoning-effort", choices=("minimal", "low", "medium", "high"), default="medium")
    parser.add_argument("--prompt-cache-key", default=DEFAULT_PROMPT_CACHE_KEY)
    parser.add_argument(
        "--prompt-cache-retention",
        choices=("in_memory", "24h", "none"),
        default=DEFAULT_PROMPT_CACHE_RETENTION,
    )
    parser.add_argument("--disable-openai-web-search", action="store_true")
    parser.add_argument("--store", action="store_true")
    parser.add_argument(
        "--request-workers",
        "--batch-size",
        dest="request_workers",
        type=int,
        default=10,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--disable-random-stream", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.poll_interval_seconds <= 0:
        parser.error("--poll-interval-seconds must be > 0")
    apply_batch_path_defaults(args)
    return args


def apply_batch_path_defaults(args: argparse.Namespace) -> None:
    stem = args.output.stem
    parent = args.output.parent
    args.batch_input = args.batch_input or parent / f"{stem}_batch_input.jsonl"
    args.batch_info_output = args.batch_info_output or parent / f"{stem}_batch.json"
    args.batch_results_output = args.batch_results_output or parent / f"{stem}_batch_results.jsonl"
    args.batch_errors_output = args.batch_errors_output or parent / f"{stem}_batch_errors.jsonl"
    args.batch_registry = args.batch_registry or parent / f"{stem}_batch_ids.jsonl"


def selected_papers(args: argparse.Namespace) -> list[Paper]:
    papers = [paper for paper in load_papers(args.dataset) if paper.tex_files]
    return papers[: args.num_prompts] if args.num_prompts else papers


def submit_batch(client: Any, args: argparse.Namespace, papers: list[Paper]) -> Any:
    prompt_template = args.prompt_file.read_text(encoding="utf-8")
    if PLACEHOLDER not in prompt_template:
        raise SystemExit(f"{args.prompt_file} must contain {PLACEHOLDER}.")

    requests = [
        batch_request(args, paper, prompt_template)
        for paper in papers
    ]
    write_jsonl(args.batch_input, requests)
    print(
        f"Submitting {len(requests)} requests to OpenAI Batch API at {RESPONSES_ENDPOINT}",
        file=sys.stderr,
    )
    batch = create_responses_batch(
        client,
        args.batch_input,
        metadata={
            "runner": "run_arxiv_prompt_openai",
            "dataset": str(args.dataset),
            "prompt_count": str(len(requests)),
        },
    )
    return batch


def print_batch_saved(args: argparse.Namespace, batch: Any) -> None:
    print(f"Batch {batch.id} status={batch_status(batch)}", file=sys.stderr)
    print(f"Batch input path: {args.batch_input}", file=sys.stderr)
    print(f"Batch metadata path: {args.batch_info_output}", file=sys.stderr)


def save_batch_record(args: argparse.Namespace, batch: Any) -> None:
    append_batch_registry(args.batch_registry, batch_record(args, batch.id))
    print(f"Saved batch id to {args.batch_registry}", file=sys.stderr)


def batch_record(args: argparse.Namespace, batch_id: str) -> dict[str, Any]:
    return {
        "batch_id": batch_id,
        "dataset": str(args.dataset),
        "num_prompts": args.num_prompts,
        "output": str(args.output),
        "extracted_output": str(args.extracted_output),
        "batch_info_output": str(batch_specific_path(args.batch_info_output, batch_id)),
        "batch_results_output": str(batch_specific_path(args.batch_results_output, batch_id)),
        "batch_errors_output": str(batch_specific_path(args.batch_errors_output, batch_id)),
    }


def download_saved_batches(client: Any, args: argparse.Namespace) -> int:
    records = read_batch_registry(args.batch_registry)
    if not records:
        print(f"No saved batch ids in {args.batch_registry}", file=sys.stderr)
        return 0

    remaining = []
    handled = 0
    for record in records:
        batch_id = record["batch_id"]
        batch = client.batches.retrieve(batch_id)
        status = batch_status(batch)
        print(f"Batch {batch_id} status={status}", file=sys.stderr)
        if status not in {"completed", "failed", "expired", "cancelled"}:
            remaining.append(record)
            continue
        download_terminal_batch(client, record_args(args, record), batch)
        handled += 1

    rewrite_batch_registry(args.batch_registry, remaining)
    print(
        f"Handled {handled} batch(es); {len(remaining)} still pending in {args.batch_registry}",
        file=sys.stderr,
    )
    return 0


def download_terminal_batch(client: Any, args: argparse.Namespace, batch: Any) -> None:
    write_batch_info(args.batch_info_output, batch)
    download_batch_files(
        client,
        batch,
        output_path=args.batch_results_output,
        error_path=args.batch_errors_output,
    )
    if batch_status(batch) != "completed":
        print(f"Saved terminal batch metadata/errors for {batch.id}", file=sys.stderr)
        return
    papers = selected_papers(args)
    write_processed_outputs(args, papers, args.batch_results_output)


def record_args(default_args: argparse.Namespace, record: dict[str, Any]) -> argparse.Namespace:
    args = argparse.Namespace(**vars(default_args))
    args.dataset = record.get("dataset", args.dataset)
    args.num_prompts = record.get("num_prompts", args.num_prompts)
    for key in (
        "output",
        "extracted_output",
        "batch_info_output",
        "batch_results_output",
        "batch_errors_output",
    ):
        setattr(args, key, Path(record.get(key, getattr(args, key))))
    return args


def write_processed_outputs(
    args: argparse.Namespace,
    papers: list[Paper],
    batch_results_output: Path,
) -> None:
    rows = final_rows(papers, load_jsonl(batch_results_output))
    write_jsonl(args.output, rows)
    write_jsonl(args.extracted_output, [extracted_row(row) for row in rows])
    print(f"Wrote {len(rows)} raw rows to {args.output}", file=sys.stderr)
    print(f"Wrote {len(rows)} extracted rows to {args.extracted_output}", file=sys.stderr)


def remove_batch_record(path: Path, batch_id: str) -> None:
    records = [
        record
        for record in read_batch_registry(path)
        if record.get("batch_id") != batch_id
    ]
    rewrite_batch_registry(path, records)


if __name__ == "__main__":
    raise SystemExit(main())
