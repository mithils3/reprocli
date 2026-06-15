from __future__ import annotations

import argparse
import os
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator

# Shared with CommitScheduler so Hub snapshots never catch a half-written line.
OUTPUT_WRITE_LOCK = threading.Lock()


def run_output_paths(args: argparse.Namespace) -> list[Path]:
    paths = [args.output, args.extracted_output]
    if args.save_round_jsonl:
        paths.append(args.trace_output)
    return paths


@contextmanager
def hf_run_uploader(args: argparse.Namespace) -> Iterator[None]:
    """Push run outputs to a HF dataset repo during the run and once at the end."""
    if not args.hf_repo:
        yield
        return
    from huggingface_hub import CommitScheduler

    paths = [path.resolve() for path in run_output_paths(args)]
    folder = Path(os.path.commonpath([str(path.parent) for path in paths]))
    scheduler = CommitScheduler(
        repo_id=args.hf_repo,
        repo_type="dataset",
        folder_path=folder,
        path_in_repo=args.hf_path_in_repo or None,
        allow_patterns=[str(path.relative_to(folder)) for path in paths],
        every=args.hf_upload_every,
        private=args.hf_private,
    )
    scheduler.lock = OUTPUT_WRITE_LOCK
    print(
        f"Uploading run outputs to https://huggingface.co/datasets/{args.hf_repo} "
        f"every {args.hf_upload_every:g} min",
        file=sys.stderr,
    )
    try:
        yield
    finally:
        scheduler.trigger().result()
        scheduler.stop()
