#!/usr/bin/env python3
"""Download OpenReview supplementary material for papers in the arXiv dataset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .arxiv_source_download import write_manifest
from .openreview_supplements import (
    DEFAULT_VENUE_ID,
    OPENREVIEW_API,
    download_jobs,
    load_dataset_papers,
    load_notes,
    match_jobs,
    write_job_csv,
)
from reprocli_vllm.config import DEFAULT_DATASET


DEFAULT_OUTPUT_DIR = Path("data/openreview_supplements")


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    papers = load_dataset_papers(args.dataset, args.limit_papers)
    notes = load_notes(
        Path(args.openreview_json) if args.openreview_json else None,
        args.api_base,
        args.venue_id,
        args.timeout,
    )
    jobs, misses = match_jobs(papers, notes)
    if args.limit_downloads:
        jobs = jobs[: args.limit_downloads]

    print(
        f"Matched {len(jobs)} OpenReview supplements from {len(papers)} papers "
        f"and {len(notes)} notes ({misses} title misses).",
        file=sys.stderr,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_job_csv(output_dir / "openreview_jobs.csv", jobs)
    if args.dry_run:
        for job in jobs[: min(10, len(jobs))]:
            print(f"{job.arxiv_id}\t{job.note_id}\t{job.source_url}")
        return 0

    results = download_jobs(
        jobs=jobs,
        output_dir=output_dir,
        retries=max(0, args.retries),
        timeout=max(1.0, args.timeout),
        overwrite=args.overwrite,
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
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--manifest", default="manifest.csv")
    parser.add_argument("--venue-id", default=DEFAULT_VENUE_ID)
    parser.add_argument("--api-base", default=OPENREVIEW_API)
    parser.add_argument("--openreview-json", help="Optional cached notes JSON.")
    parser.add_argument("--limit-papers", type=int)
    parser.add_argument("--limit-downloads", type=int)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--allow-failures", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
