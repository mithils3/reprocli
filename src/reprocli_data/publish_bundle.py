#!/usr/bin/env python3
"""Rebuild the Parquet bundle from already-downloaded files and upload it.

Shortcut for the last two pipeline stages: replaces any existing
paper_bundle_dataset output (no --force needed), writes fresh shards plus the
dataset card, then pushes the folder to the Hugging Face Hub. Sources and
supplements must already be on disk; run reprocli_data.build_dataset for the
download stages.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline.bundle import stage_bundle
from .pipeline.common import BUNDLE_DIRNAME, INDEX_FILENAME
from .pipeline.index import read_index_csv
from .pipeline.output import DEFAULT_REPO_ID, stage_upload


def main() -> int:
    args = parse_args()
    data_dir = Path(args.data_dir)
    records = read_index_csv(data_dir / INDEX_FILENAME)
    if args.limit:
        records = records[: args.limit]
    print(f"{len(records)} papers in scope for bundle + upload.", file=sys.stderr)

    stage_bundle(
        records,
        data_dir,
        shard_size_mb=args.shard_size_mb,
        batch_size_mb=max(1, args.batch_size_mb),
        batch_rows=max(1, args.batch_rows),
        compression=args.compression,
        force=True,
    )
    if not args.skip_upload:
        stage_upload(
            data_dir / BUNDLE_DIRNAME,
            repo_id=args.repo_id,
            private=args.private,
            commit_message=args.commit_message,
        )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--data-dir", default="data", help="Root for all pipeline artifacts.")
    parser.add_argument("--limit", type=int, help="Process at most this many papers.")
    parser.add_argument("--shard-size-mb", type=int, default=512)
    parser.add_argument("--batch-size-mb", type=int, default=64)
    parser.add_argument("--batch-rows", type=int, default=64)
    parser.add_argument("--compression", default="zstd")
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--private", action="store_true")
    parser.add_argument(
        "--commit-message",
        default="Upload NeurIPS 2025 paper bundle dataset",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Only rebuild the bundle; do not push to the Hub.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
