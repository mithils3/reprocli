#!/usr/bin/env python3
"""Download and extract arXiv source packages listed in a CSV file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .arxiv_source_download import download_all, write_manifest
from .arxiv_source_inputs import (
    DEFAULT_DATA_DIR,
    DEFAULT_DELAY,
    DEFAULT_MANIFEST,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_WORKERS,
    discover_input_csv,
    load_jobs,
)


def main() -> int:
    args = parse_args()
    input_path = Path(args.input) if args.input else discover_input_csv(DEFAULT_DATA_DIR)
    output_dir = Path(args.output_dir)
    jobs, stats = load_jobs(
        input_path=input_path,
        url_column=args.url_column,
        id_column=args.id_column,
        title_column=args.title_column,
        limit=args.limit,
    )

    print(
        f"Loaded {len(jobs)} unique arXiv IDs from {input_path} "
        f"({stats.total_rows} rows, {stats.duplicate_ids} duplicates, "
        f"{stats.missing_ids} missing IDs).",
        file=sys.stderr,
    )
    if args.dry_run:
        for job in jobs[: min(10, len(jobs))]:
            print(f"{job.arxiv_id}\t{job.source_url}")
        return 0

    workers = max(1, args.workers)
    delay = max(0.0, args.delay)
    print(
        f"Downloading with {workers} workers and {delay:g}s request spacing.",
        file=sys.stderr,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    results = download_all(
        jobs=jobs,
        output_dir=output_dir,
        workers=workers,
        delay=delay,
        retries=max(0, args.retries),
        timeout=max(1.0, args.timeout),
        overwrite=args.overwrite,
        keep_archive=args.keep_archive,
    )
    manifest_path = output_dir / args.manifest
    write_manifest(manifest_path, results)

    failures = [result for result in results if result.status == "failed"]
    print(
        f"Wrote manifest to {manifest_path}. "
        f"{len(results) - len(failures)} succeeded/skipped, {len(failures)} failed.",
        file=sys.stderr,
    )
    return 0 if args.allow_failures or not failures else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="CSV path. Defaults to the only *.csv file in data/.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--url-column", default="arxiv_url")
    parser.add_argument("--id-column", help="Optional column containing arXiv IDs.")
    parser.add_argument("--title-column", default="title")
    parser.add_argument("--limit", type=int, help="Download at most this many unique IDs.")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--keep-archive", action="store_true")
    parser.add_argument("--allow-failures", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
