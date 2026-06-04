#!/usr/bin/env python3
"""Build one-row-per-paper Parquet bundles from arXiv and OpenReview files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .paper_bundle_dataset import build_dataset


def main() -> int:
    args = parse_args()
    stats = build_dataset(
        arxiv_manifest=Path(args.arxiv_manifest),
        supplement_manifest=Path(args.supplement_manifest),
        output_dir=Path(args.output_dir),
        shard_size_mb=args.shard_size_mb,
        compression=args.compression,
        overwrite=args.overwrite,
    )
    print(
        f"Wrote {stats.papers} paper rows with {stats.supplement_files} supplement "
        f"files to {stats.shards} shards in {args.output_dir}",
        file=sys.stderr,
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arxiv-manifest", default="data/arxiv_sources/manifest.csv")
    parser.add_argument("--supplement-manifest", default="data/openreview_supplements/manifest.csv")
    parser.add_argument("--output-dir", default="data/paper_bundle_dataset")
    parser.add_argument("--shard-size-mb", type=int, default=512)
    parser.add_argument("--compression", default="zstd")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
