#!/usr/bin/env python3
"""Build one-row-per-paper Parquet bundles from arXiv and OpenReview files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .paper_bundle_dataset import build_dataset
from .upload_dataset_folder import DEFAULT_REPO_ID, upload_dataset_folder
from reprocli_vllm.config import ARXIV_SOURCE_DATASET


DEFAULT_SUPPLEMENT_DIR = Path("/projects/bgnp/msalunkhe/openreview_supplements")
DEFAULT_BATCH_SIZE_MB = 64
DEFAULT_BATCH_ROWS = 64


def main() -> int:
    args = parse_args()
    stats = build_dataset(
        dataset_name=args.dataset,
        supplement_dir=Path(args.supplement_dir),
        output_dir=Path(args.output_dir),
        shard_size_mb=args.shard_size_mb,
        batch_size_mb=max(1, args.batch_size_mb),
        batch_rows=max(1, args.batch_rows),
        compression=args.compression,
        overwrite=args.overwrite,
    )
    print(
        f"Wrote {stats.papers} paper rows with {stats.supplement_files} supplement "
        f"files to {stats.shards} shards in {args.output_dir}",
        file=sys.stderr,
    )
    if not args.no_upload:
        upload_dataset_folder(
            input_dir=Path(args.output_dir),
            repo_id=args.repo_id,
            private=args.private,
            commit_message=args.commit_message,
        )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=ARXIV_SOURCE_DATASET)
    parser.add_argument("--supplement-dir", default=str(DEFAULT_SUPPLEMENT_DIR))
    parser.add_argument("--output-dir", default="data/paper_bundle_dataset")
    parser.add_argument("--shard-size-mb", type=int, default=512)
    parser.add_argument("--batch-size-mb", type=int, default=DEFAULT_BATCH_SIZE_MB)
    parser.add_argument("--batch-rows", type=int, default=DEFAULT_BATCH_ROWS)
    parser.add_argument("--compression", default="zstd")
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--private", action="store_true")
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument(
        "--commit-message",
        default="Upload NeurIPS 2025 paper bundle dataset",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
