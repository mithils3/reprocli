#!/usr/bin/env python3
"""Map NeurIPS proceedings papers to arXiv URLs with batched OpenAlex lookups."""

from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from .neurips_index import Paper, fetch_neurips_papers
from .openalex_lookup import (
    OPENALEX_SELECT,
    OpenAlexHTTPError,
    Throttle,
    choose_match,
    make_openalex_url,
    make_row,
    query_openalex_batch,
    write_rows,
)


DEFAULT_YEAR = 2025
DEFAULT_PROCEEDINGS_URL = "https://papers.nips.cc/paper_files/paper/2025"
DEFAULT_OUTPUT = "data/neurips_2025_openalex_arxiv.csv"
OPENALEX_WORKS_URL = "https://api.openalex.org/works"


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("OPENALEX_KEY")
    if not api_key:
        raise SystemExit("OPENALEX_KEY is required in the environment.")

    proceedings_url = args.proceedings_url or default_proceedings_url(args.year)
    output = args.output or default_output(args.year)

    print(f"Fetching NeurIPS {args.year} index: {proceedings_url}", file=sys.stderr)
    papers = fetch_neurips_papers(proceedings_url, args.year)
    papers = papers[: args.limit] if args.limit else papers
    print(f"Found {len(papers)} NeurIPS paper links.", file=sys.stderr)

    rows = resolve_rows(
        papers=papers,
        year=args.year,
        api_key=api_key,
        workers=max(1, args.workers),
        delay=args.delay,
        batch_size=max(1, min(args.batch_size, 100)),
        max_url_chars=max(500, args.batch_url_chars),
        min_score=args.min_score,
        retries=args.retries,
    )
    write_rows(output, rows, args.format)
    print(f"Wrote {len(rows)} rows with arXiv URLs to {output}", file=sys.stderr)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--proceedings-url")
    parser.add_argument("--output")
    parser.add_argument("--format", choices=("csv", "jsonl"), default="csv")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--batch-url-chars", type=int, default=3000)
    parser.add_argument("--min-score", type=float, default=0.88)
    parser.add_argument("--retries", type=int, default=2)
    return parser.parse_args()


def default_proceedings_url(year: int) -> str:
    if year == DEFAULT_YEAR:
        return DEFAULT_PROCEEDINGS_URL
    return f"https://papers.nips.cc/paper_files/paper/{year}"


def default_output(year: int) -> str:
    if year == DEFAULT_YEAR:
        return DEFAULT_OUTPUT
    return f"data/neurips_{year}_openalex_arxiv.csv"


def resolve_rows(
    papers: list[Paper],
    year: int,
    api_key: str,
    workers: int,
    delay: float,
    batch_size: int,
    max_url_chars: int,
    min_score: float,
    retries: int,
) -> list[dict[str, str]]:
    indexed = list(enumerate(papers, start=1))
    batchable = [(i, p) for i, p in indexed if can_batch(p.title)]
    skipped = len(indexed) - len(batchable)
    batches = make_batches(batchable, api_key, batch_size, max_url_chars)
    throttle = Throttle(delay)

    print(
        f"OpenAlex batch lookup: {len(batchable)} titles in {len(batches)} calls; "
        f"{skipped} titles skipped because they are unsafe for OR filters.",
        file=sys.stderr,
    )

    rows: list[tuple[int, dict[str, str]]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(fetch_batch_rows, batch, year, api_key, min_score, retries, throttle): n
            for n, batch in enumerate(batches, start=1)
        }
        for done, future in enumerate(as_completed(futures), start=1):
            batch_rows = future.result()
            rows.extend(batch_rows)
            print(f"[batch {done}/{len(futures)}] {len(batch_rows)} arXiv URLs", file=sys.stderr)

    return [row for _, row in sorted(rows, key=lambda item: item[0])]


def fetch_batch_rows(
    batch: list[tuple[int, Paper]],
    year: int,
    api_key: str,
    min_score: float,
    retries: int,
    throttle: Throttle,
) -> list[tuple[int, dict[str, str]]]:
    try:
        throttle.wait()
        works = query_openalex_batch([paper.title for _, paper in batch], api_key, retries)
    except OpenAlexHTTPError as error:
        if error.status != 400:
            raise
        if len(batch) == 1:
            print(f"Skipping rejected title: {batch[0][1].title}", file=sys.stderr)
            return []
        print(f"Splitting rejected batch of {len(batch)} titles.", file=sys.stderr)
        middle = len(batch) // 2
        return (
            fetch_batch_rows(batch[:middle], year, api_key, min_score, retries, throttle)
            + fetch_batch_rows(batch[middle:], year, api_key, min_score, retries, throttle)
        )

    rows: list[tuple[int, dict[str, str]]] = []
    for index, paper in batch:
        row = make_row(year, paper, choose_match(paper.title, works, min_score))
        if row["arxiv_url"]:
            rows.append((index, row))
    return rows


def make_batches(
    papers: list[tuple[int, Paper]],
    api_key: str,
    batch_size: int,
    max_url_chars: int,
) -> list[list[tuple[int, Paper]]]:
    batches: list[list[tuple[int, Paper]]] = []
    current: list[tuple[int, Paper]] = []
    for item in papers:
        proposed = current + [item]
        url = make_openalex_url(
            {
                "api_key": api_key,
                "filter": "display_name:" + "|".join(p.title for _, p in proposed),
                "per_page": "100",
                "select": OPENALEX_SELECT,
            }
        )
        if current and (len(proposed) > batch_size or len(url) > max_url_chars):
            batches.append(current)
            current = [item]
        else:
            current = proposed
    if current:
        batches.append(current)
    return batches


def can_batch(title: str) -> bool:
    return bool(title.strip()) and "," not in title and "|" not in title


if __name__ == "__main__":
    raise SystemExit(main())
