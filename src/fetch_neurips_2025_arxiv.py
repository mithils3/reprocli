#!/usr/bin/env python3
"""Map NeurIPS 2025 proceedings papers to arXiv URLs via OpenAlex."""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


DEFAULT_YEAR = 2025
DEFAULT_PROCEEDINGS_URL = "https://papers.nips.cc/paper_files/paper/2025"
DEFAULT_OUTPUT = "data/neurips_2025_openalex_arxiv.csv"
OPENALEX_WORKS_URL = "https://api.openalex.org/works"
OPENALEX_SELECT = "id,title,publication_year,doi,ids,primary_location,best_oa_location,locations"
USER_AGENT = "reprocli-neurips-openalex-mapper/0.2"
ARXIV_RE = re.compile(
    r"(?i)(?:arxiv:|arxiv\.|abs/|pdf/)?"
    r"(?P<id>(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)"
)


@dataclass(frozen=True)
class Paper:
    title: str
    neurips_url: str


@dataclass(frozen=True)
class Match:
    work: dict[str, Any] | None
    score: float
    status: str


class NeuripsParser(HTMLParser):
    def __init__(self, base_url: str, year: int) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.year = year
        self.papers: list[Paper] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        href = dict(attrs).get("href") if tag == "a" else None
        if href and self._is_paper_link(href):
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._href:
            return
        title = clean_space("".join(self._text))
        if title:
            self.papers.append(
                Paper(
                    title=html.unescape(title),
                    neurips_url=urllib.parse.urljoin(self.base_url, self._href),
                )
            )
        self._href = None
        self._text = []

    def _is_paper_link(self, href: str) -> bool:
        path = urllib.parse.urlparse(urllib.parse.urljoin(self.base_url, href)).path
        return (
            f"/paper_files/paper/{self.year}/hash/" in path
            and "-Abstract-" in path
            and path.endswith(".html")
        )


class Throttle:
    def __init__(self, interval: float) -> None:
        self.interval = interval
        self.lock = threading.Lock()
        self.next_at = 0.0

    def wait(self) -> None:
        if self.interval <= 0:
            return
        with self.lock:
            now = time.monotonic()
            sleep_for = max(0.0, self.next_at - now)
            self.next_at = max(now, self.next_at) + self.interval
        if sleep_for:
            time.sleep(sleep_for)


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("OPENALEX_KEY")
    if not api_key:
        raise SystemExit("OPENALEX_KEY is required in the environment.")

    proceedings_url = args.proceedings_url or (
        DEFAULT_PROCEEDINGS_URL
        if args.year == DEFAULT_YEAR
        else f"https://papers.nips.cc/paper_files/paper/{args.year}"
    )
    output = args.output or (
        DEFAULT_OUTPUT
        if args.year == DEFAULT_YEAR
        else f"data/neurips_{args.year}_openalex_arxiv.csv"
    )

    print(f"Fetching NeurIPS {args.year} index: {proceedings_url}", file=sys.stderr)
    papers = fetch_neurips_papers(proceedings_url, args.year)
    if args.limit:
        papers = papers[: args.limit]
    print(f"Found {len(papers)} NeurIPS paper links.", file=sys.stderr)

    rows = resolve_arxiv_rows(
        papers=papers,
        year=args.year,
        api_key=api_key,
        workers=max(1, args.workers),
        delay=args.delay,
        batch_size=max(1, min(args.batch_size, 100)),
        batch_url_chars=max(500, args.batch_url_chars),
        min_score=args.min_score,
        retries=args.retries,
        fallback_search=args.fallback_search,
        search_per_page=args.search_per_page,
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
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--delay", type=float, default=0.05)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--batch-url-chars", type=int, default=3000)
    parser.add_argument("--min-score", type=float, default=0.88)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--search-per-page", type=int, default=10)
    parser.add_argument(
        "--no-fallback-search",
        action="store_false",
        dest="fallback_search",
        help="Do not run per-title OpenAlex search for batch misses.",
    )
    parser.set_defaults(fallback_search=True)
    return parser.parse_args()


def fetch_neurips_papers(url: str, year: int) -> list[Paper]:
    parser = NeuripsParser(url, year)
    parser.feed(http_get(url, retries=3))
    papers = dedupe_by_url(parser.papers)
    if not papers:
        raise RuntimeError(f"No NeurIPS {year} paper links found at {url}")
    return papers


def resolve_arxiv_rows(
    papers: list[Paper],
    year: int,
    api_key: str,
    workers: int,
    delay: float,
    batch_size: int,
    batch_url_chars: int,
    min_score: float,
    retries: int,
    fallback_search: bool,
    search_per_page: int,
) -> list[dict[str, Any]]:
    indexed = list(enumerate(papers, start=1))
    batchable = [(i, p) for i, p in indexed if can_batch_title(p.title)]
    fallback = [(i, p) for i, p in indexed if not can_batch_title(p.title)]
    batches = make_batches(batchable, api_key, batch_size, batch_url_chars)
    throttle = Throttle(delay)

    print(
        f"OpenAlex batch phase: {len(batchable)} titles in {len(batches)} calls; "
        f"{len(fallback)} titles need search fallback.",
        file=sys.stderr,
    )
    rows, unresolved = run_batch_phase(
        batches, year, api_key, min_score, retries, workers, throttle
    )
    fallback.extend(unresolved)

    if fallback_search and fallback:
        print(f"OpenAlex search fallback: {len(fallback)} titles.", file=sys.stderr)
        rows.extend(
            run_search_phase(
                fallback,
                year,
                api_key,
                min_score,
                retries,
                workers,
                throttle,
                search_per_page,
            )
        )
    elif fallback:
        print(
            f"Skipped {len(fallback)} unresolved titles. "
            "Drop --no-fallback-search to try them.",
            file=sys.stderr,
        )

    return [row for _, row in sorted(rows, key=lambda item: item[0])]


def run_batch_phase(
    batches: list[list[tuple[int, Paper]]],
    year: int,
    api_key: str,
    min_score: float,
    retries: int,
    workers: int,
    throttle: Throttle,
) -> tuple[list[tuple[int, dict[str, Any]]], list[tuple[int, Paper]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    unresolved: list[tuple[int, Paper]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(fetch_batch, b, year, api_key, min_score, retries, throttle): n
            for n, b in enumerate(batches, start=1)
        }
        for done, future in enumerate(as_completed(futures), start=1):
            batch_rows, batch_unresolved = future.result()
            rows.extend(batch_rows)
            unresolved.extend(batch_unresolved)
            print(
                f"[batch {done}/{len(futures)}] "
                f"{len(batch_rows)} arXiv, {len(batch_unresolved)} unresolved",
                file=sys.stderr,
            )
    return rows, unresolved


def fetch_batch(
    batch: list[tuple[int, Paper]],
    year: int,
    api_key: str,
    min_score: float,
    retries: int,
    throttle: Throttle,
) -> tuple[list[tuple[int, dict[str, Any]]], list[tuple[int, Paper]]]:
    try:
        throttle.wait()
        works = openalex_batch([paper.title for _, paper in batch], api_key, retries)
    except Exception:
        if len(batch) == 1:
            return [], batch
        middle = len(batch) // 2
        left = fetch_batch(batch[:middle], year, api_key, min_score, retries, throttle)
        right = fetch_batch(batch[middle:], year, api_key, min_score, retries, throttle)
        return left[0] + right[0], left[1] + right[1]
    return rows_from_matches(batch, works, year, min_score, fallback_no_arxiv=False)


def run_search_phase(
    papers: list[tuple[int, Paper]],
    year: int,
    api_key: str,
    min_score: float,
    retries: int,
    workers: int,
    throttle: Throttle,
    per_page: int,
) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                search_one, item, year, api_key, min_score, retries, throttle, per_page
            ): item
            for item in papers
        }
        for done, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            if result:
                rows.append(result)
            print(f"[search {done}/{len(futures)}]", file=sys.stderr)
    return rows


def search_one(
    item: tuple[int, Paper],
    year: int,
    api_key: str,
    min_score: float,
    retries: int,
    throttle: Throttle,
    per_page: int,
) -> tuple[int, dict[str, Any]] | None:
    index, paper = item
    throttle.wait()
    works = openalex_search(paper.title, api_key, retries, per_page)
    match = choose_match(paper.title, works, min_score, "search")
    row = row_for(year, paper, match)
    return (index, row) if row["arxiv_url"] else None


def rows_from_matches(
    papers: list[tuple[int, Paper]],
    works: list[dict[str, Any]],
    year: int,
    min_score: float,
    fallback_no_arxiv: bool,
) -> tuple[list[tuple[int, dict[str, Any]]], list[tuple[int, Paper]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    unresolved: list[tuple[int, Paper]] = []
    for index, paper in papers:
        match = choose_match(paper.title, works, min_score, "batch")
        row = row_for(year, paper, match)
        if row["arxiv_url"]:
            rows.append((index, row))
        elif fallback_no_arxiv or match.status != "batch_no_arxiv":
            unresolved.append((index, paper))
    return rows, unresolved


def openalex_batch(titles: list[str], api_key: str, retries: int) -> list[dict[str, Any]]:
    params = {
        "api_key": api_key,
        "filter": "display_name:" + "|".join(titles),
        "per_page": "100",
        "select": OPENALEX_SELECT,
    }
    return openalex_results(params, retries)


def openalex_search(
    title: str, api_key: str, retries: int, per_page: int
) -> list[dict[str, Any]]:
    return openalex_results(
        {
            "api_key": api_key,
            "search": title,
            "per_page": str(per_page),
            "select": OPENALEX_SELECT,
        },
        retries,
    )


def openalex_results(params: dict[str, str], retries: int) -> list[dict[str, Any]]:
    url = f"{OPENALEX_WORKS_URL}?{urllib.parse.urlencode(params)}"
    data = json.loads(http_get(url, retries))
    return [work for work in data.get("results", []) if isinstance(work, dict)]


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
        if current and (
            len(proposed) > batch_size
            or len(batch_url([paper.title for _, paper in proposed], api_key))
            > max_url_chars
        ):
            batches.append(current)
            current = [item]
        else:
            current = proposed
    return batches + ([current] if current else [])


def batch_url(titles: list[str], api_key: str) -> str:
    return f"{OPENALEX_WORKS_URL}?{urllib.parse.urlencode({
        'api_key': api_key,
        'filter': 'display_name:' + '|'.join(titles),
        'per_page': '100',
        'select': OPENALEX_SELECT,
    })}"


def can_batch_title(title: str) -> bool:
    return bool(title.strip()) and "," not in title and "|" not in title


def choose_match(
    title: str, works: list[dict[str, Any]], min_score: float, prefix: str
) -> Match:
    candidates = [
        (
            title_similarity(title, str(work.get("title") or work.get("display_name") or "")),
            bool(arxiv_url(work)),
            mentions_neurips(work),
            work,
        )
        for work in works
    ]
    if not candidates:
        return Match(None, 0.0, f"{prefix}_no_match")

    best_score = max(score for score, _, _, _ in candidates)
    if best_score < min_score:
        best = max(candidates, key=lambda item: item[0])
        return Match(best[3], best_score, f"{prefix}_low_confidence")

    near_best = [c for c in candidates if c[0] >= max(min_score, best_score - 0.03)]
    score, has_arxiv, _, work = max(near_best, key=lambda item: (item[1], item[2], item[0]))
    status = f"{prefix}_arxiv" if has_arxiv else f"{prefix}_no_arxiv"
    return Match(work, score, status)


def row_for(year: int, paper: Paper, match: Match) -> dict[str, Any]:
    work = match.work or {}
    return {
        "year": year,
        "title": paper.title,
        "neurips_url": paper.neurips_url,
        "arxiv_url": arxiv_url(work) if work else "",
        "openalex_id": work.get("id", ""),
        "openalex_title": work.get("title") or work.get("display_name") or "",
        "openalex_publication_year": work.get("publication_year", ""),
        "openalex_doi": work.get("doi", ""),
        "openalex_match_score": f"{match.score:.3f}",
        "match_status": match.status,
    }


def arxiv_url(work: dict[str, Any]) -> str:
    for value in openalex_url_values(work):
        if "arxiv" not in value.casefold():
            continue
        match = ARXIV_RE.search(value)
        if match:
            return f"https://arxiv.org/abs/{match.group('id').removesuffix('.pdf')}"
    return ""


def openalex_url_values(work: dict[str, Any]) -> list[str]:
    values: list[str] = []
    values.extend(str(work.get(key) or "") for key in ("doi", "pdf_url", "landing_page_url"))
    ids = work.get("ids")
    if isinstance(ids, dict):
        values.extend(str(value) for value in ids.values())
    for location in [work.get("primary_location"), work.get("best_oa_location")]:
        values.extend(location_values(location))
    locations = work.get("locations")
    if isinstance(locations, list):
        for location in locations:
            values.extend(location_values(location))
    return [value for value in values if value]


def location_values(location: Any) -> list[str]:
    if not isinstance(location, dict):
        return []
    source = location.get("source") or {}
    values = [str(location.get("landing_page_url") or ""), str(location.get("pdf_url") or "")]
    if isinstance(source, dict):
        for key in ("id", "homepage_url", "display_name", "host_organization_name"):
            values.append(str(source.get(key) or ""))
        for value in source.get("host_organization_lineage_names") or []:
            values.append(str(value))
    return values


def mentions_neurips(work: dict[str, Any]) -> bool:
    text = " ".join(openalex_url_values(work)).casefold()
    return "neurips" in text or "neural information processing systems" in text


def write_rows(path: str, rows: list[dict[str, Any]], fmt: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "jsonl":
        with output.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        return

    fields = [
        "year",
        "title",
        "neurips_url",
        "arxiv_url",
        "openalex_id",
        "openalex_title",
        "openalex_publication_year",
        "openalex_doi",
        "openalex_match_score",
        "match_status",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def http_get(url: str, retries: int) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=45) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in {429, 500, 502, 503, 504}:
                raise RuntimeError(f"GET {error.code}: {redact_key(url)}") from None
        except urllib.error.URLError as error:
            last_error = error
        if attempt < retries:
            time.sleep(min(2**attempt, 30))
    raise RuntimeError(f"GET failed after {retries + 1} tries: {redact_key(url)}") from last_error


def redact_key(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query = [(key, "REDACTED" if key == "api_key" else value) for key, value in query]
    return urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(query)))


def dedupe_by_url(papers: list[Paper]) -> list[Paper]:
    seen: set[str] = set()
    unique: list[Paper] = []
    for paper in papers:
        if paper.neurips_url not in seen:
            seen.add(paper.neurips_url)
            unique.append(paper)
    return unique


def title_similarity(left: str, right: str) -> float:
    left_norm, right_norm = normalize_title(left), normalize_title(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def normalize_title(value: str) -> str:
    return clean_space(re.sub(r"[^a-z0-9]+", " ", html.unescape(value).casefold()))


def clean_space(value: str) -> str:
    return " ".join(value.split())


if __name__ == "__main__":
    raise SystemExit(main())
