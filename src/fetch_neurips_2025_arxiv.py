#!/usr/bin/env python3
"""Fetch NeurIPS 2025 paper links and map them to arXiv URLs via OpenAlex."""

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
from typing import Any, Iterable


DEFAULT_YEAR = 2025
DEFAULT_PROCEEDINGS_URL = "https://papers.nips.cc/paper_files/paper/2025"
DEFAULT_OUTPUT_DIR = "data"
OPENALEX_WORKS_URL = "https://api.openalex.org/works"
USER_AGENT = "reprocli-neurips-openalex-mapper/0.1"
ARXIV_ID_RE = re.compile(
    r"(?i)(?:arxiv:|arxiv\.|abs/|pdf/)?"
    r"(?P<id>(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)"
)


@dataclass(frozen=True)
class NeuripsPaper:
    title: str
    url: str


@dataclass(frozen=True)
class OpenAlexMatch:
    work: dict[str, Any] | None
    score: float
    status: str


@dataclass(frozen=True)
class OpenAlexConfig:
    api_key: str
    per_page: int
    min_score: float
    retries: int


class RequestThrottle:
    def __init__(self, min_interval_seconds: float) -> None:
        self.min_interval_seconds = min_interval_seconds
        self._lock = threading.Lock()
        self._next_request_time = 0.0

    def wait(self) -> None:
        if self.min_interval_seconds <= 0:
            return

        with self._lock:
            now = time.monotonic()
            wait_seconds = max(0.0, self._next_request_time - now)
            self._next_request_time = (
                max(now, self._next_request_time) + self.min_interval_seconds
            )

        if wait_seconds > 0:
            time.sleep(wait_seconds)


class NeuripsIndexParser(HTMLParser):
    def __init__(self, base_url: str, year: int) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.year = year
        self.papers: list[NeuripsPaper] = []
        self._href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href and self._is_paper_abstract_link(href):
            self._href = href
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._href is None:
            return

        title = normalize_space("".join(self._text_parts))
        if title:
            self.papers.append(
                NeuripsPaper(
                    title=html.unescape(title),
                    url=urllib.parse.urljoin(self.base_url, self._href),
                )
            )

        self._href = None
        self._text_parts = []

    def _is_paper_abstract_link(self, href: str) -> bool:
        url = urllib.parse.urljoin(self.base_url, href)
        path = urllib.parse.urlparse(url).path
        year_fragment = f"/paper_files/paper/{self.year}/hash/"
        return (
            year_fragment in path
            and "-Abstract-" in path
            and path.endswith(".html")
        )


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("OPENALEX_KEY")
    if not api_key:
        raise SystemExit("OPENALEX_KEY is required in the environment.")

    if args.proceedings_url:
        proceedings_url = args.proceedings_url
    elif args.year == DEFAULT_YEAR:
        proceedings_url = DEFAULT_PROCEEDINGS_URL
    else:
        proceedings_url = f"https://papers.nips.cc/paper_files/paper/{args.year}"
    output_path = args.output or str(
        Path(DEFAULT_OUTPUT_DIR) / f"neurips_{args.year}_openalex_arxiv.csv"
    )

    print(f"Fetching NeurIPS {args.year} index: {proceedings_url}", file=sys.stderr)
    papers = fetch_neurips_papers(proceedings_url, args.year)
    if args.limit:
        papers = papers[: args.limit]
    print(f"Found {len(papers)} NeurIPS paper links.", file=sys.stderr)

    workers = max(1, args.workers)
    print(
        f"Querying OpenAlex with {workers} workers "
        f"and {args.delay:.3f}s between request starts.",
        file=sys.stderr,
    )
    rows = fetch_arxiv_rows(
        year=args.year,
        papers=papers,
        config=OpenAlexConfig(
            api_key=api_key,
            per_page=args.per_page,
            min_score=args.min_score,
            retries=args.retries,
        ),
        workers=workers,
        request_interval_seconds=args.delay,
    )

    write_rows(output_path, rows, args.format)
    print(f"Wrote {len(rows)} rows with arXiv URLs to {output_path}", file=sys.stderr)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch NeurIPS proceedings paper links and map each title to an "
            "arXiv URL when OpenAlex has one."
        )
    )
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument(
        "--proceedings-url",
        help=(
            "NeurIPS proceedings index URL to scrape. Defaults to the "
            "papers.nips.cc index for --year."
        ),
    )
    parser.add_argument(
        "--output",
        help=(
            "Output file path. Defaults to "
            "data/neurips_<year>_openalex_arxiv.csv."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("csv", "jsonl"),
        default="csv",
        help="Output format.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Only process the first N papers. Useful for smoke tests.",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=10,
        help="OpenAlex search results to inspect for each title.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.88,
        help="Minimum normalized-title similarity for accepting an OpenAlex match.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.12,
        help=(
            "Minimum seconds between starting OpenAlex requests across all "
            "workers. Keep this near 0.10+ to avoid rate limits."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=32,
        help="Parallel OpenAlex lookup workers. Use 1 for sequential behavior.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Retries for transient OpenAlex or NeurIPS HTTP errors.",
    )
    return parser.parse_args()


def fetch_neurips_papers(url: str, year: int) -> list[NeuripsPaper]:
    body = http_get_text(url, retries=3)
    parser = NeuripsIndexParser(url, year)
    parser.feed(body)

    seen: set[str] = set()
    papers: list[NeuripsPaper] = []
    for paper in parser.papers:
        if paper.url in seen:
            continue
        seen.add(paper.url)
        papers.append(paper)

    if not papers:
        raise RuntimeError(
            f"No NeurIPS {year} paper links found at {url}. "
            "Check whether the proceedings index URL has changed."
        )
    return papers


def fetch_arxiv_rows(
    year: int,
    papers: list[NeuripsPaper],
    config: OpenAlexConfig,
    workers: int,
    request_interval_seconds: float,
) -> list[dict[str, Any]]:
    throttle = RequestThrottle(request_interval_seconds)
    indexed_rows: list[tuple[int, dict[str, Any]]] = []
    total = len(papers)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_paper = {
            executor.submit(
                fetch_arxiv_row,
                year,
                paper,
                config,
                throttle,
            ): (index, paper)
            for index, paper in enumerate(papers, start=1)
        }

        for completed, future in enumerate(as_completed(future_to_paper), start=1):
            index, paper = future_to_paper[future]
            row = future.result()
            status = "arxiv" if row["arxiv_url"] else row["match_status"]
            print(
                f"[{completed}/{total}] #{index} {status}: {paper.title}",
                file=sys.stderr,
            )
            if row["arxiv_url"]:
                indexed_rows.append((index, row))

    return [row for _, row in sorted(indexed_rows, key=lambda item: item[0])]


def fetch_arxiv_row(
    year: int,
    paper: NeuripsPaper,
    config: OpenAlexConfig,
    throttle: RequestThrottle,
) -> dict[str, Any]:
    throttle.wait()
    match = find_openalex_match(
        title=paper.title,
        api_key=config.api_key,
        per_page=config.per_page,
        min_score=config.min_score,
        retries=config.retries,
    )
    return build_output_row(year, paper, match)


def find_openalex_match(
    title: str,
    api_key: str,
    per_page: int,
    min_score: float,
    retries: int,
) -> OpenAlexMatch:
    params = {
        "api_key": api_key,
        "search": title,
        "per-page": str(per_page),
    }
    url = f"{OPENALEX_WORKS_URL}?{urllib.parse.urlencode(params)}"
    payload = json.loads(http_get_text(url, retries=retries))

    works = payload.get("results", [])
    if not isinstance(works, list) or not works:
        return OpenAlexMatch(work=None, score=0.0, status="no_openalex_results")

    candidates: list[tuple[float, bool, bool, dict[str, Any]]] = []
    for work in works:
        if not isinstance(work, dict):
            continue
        candidate_title = str(work.get("title") or work.get("display_name") or "")
        score = title_similarity(title, candidate_title)
        candidates.append(
            (
                score,
                bool(extract_arxiv_url(work)),
                work_mentions_neurips(work),
                work,
            )
        )

    if not candidates:
        return OpenAlexMatch(work=None, score=0.0, status="no_openalex_results")

    best_score = max(candidate[0] for candidate in candidates)
    best_by_title = max(candidates, key=lambda candidate: candidate[0])
    if best_score < min_score:
        return OpenAlexMatch(
            work=best_by_title[3],
            score=best_score,
            status="low_confidence_openalex_match",
        )

    near_best = [
        candidate
        for candidate in candidates
        if candidate[0] >= max(min_score, best_score - 0.03)
    ]
    score, has_arxiv, _, work = max(
        near_best,
        key=lambda candidate: (candidate[1], candidate[2], candidate[0]),
    )
    if has_arxiv:
        return OpenAlexMatch(work=work, score=score, status="matched_arxiv")

    return OpenAlexMatch(work=work, score=score, status="matched_no_arxiv")


def build_output_row(
    year: int,
    paper: NeuripsPaper,
    match: OpenAlexMatch,
) -> dict[str, Any]:
    work = match.work or {}
    return {
        "year": year,
        "title": paper.title,
        "neurips_url": paper.url,
        "arxiv_url": extract_arxiv_url(work) if work else "",
        "openalex_id": work.get("id", ""),
        "openalex_title": work.get("title") or work.get("display_name") or "",
        "openalex_publication_year": work.get("publication_year", ""),
        "openalex_doi": work.get("doi", ""),
        "openalex_match_score": f"{match.score:.3f}",
        "match_status": match.status,
    }


def write_rows(path: str, rows: list[dict[str, Any]], output_format: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_format == "jsonl":
        with output_path.open("w", encoding="utf-8") as output_file:
            for row in rows:
                output_file.write(json.dumps(row, ensure_ascii=False) + "\n")
        return

    fieldnames = [
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
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def extract_arxiv_url(work: dict[str, Any]) -> str:
    for value in iter_openalex_urlish_values(work):
        arxiv_url = canonical_arxiv_url(value)
        if arxiv_url:
            return arxiv_url
    return ""


def iter_openalex_urlish_values(work: dict[str, Any]) -> Iterable[str]:
    for key in ("doi", "pdf_url", "landing_page_url"):
        value = work.get(key)
        if isinstance(value, str):
            yield value

    ids = work.get("ids")
    if isinstance(ids, dict):
        for value in ids.values():
            if isinstance(value, str):
                yield value

    for location_key in ("primary_location", "best_oa_location"):
        yield from iter_location_urlish_values(work.get(location_key))

    locations = work.get("locations")
    if isinstance(locations, list):
        for location in locations:
            yield from iter_location_urlish_values(location)


def iter_location_urlish_values(location: Any) -> Iterable[str]:
    if not isinstance(location, dict):
        return

    for key in ("landing_page_url", "pdf_url"):
        value = location.get(key)
        if isinstance(value, str):
            yield value

    source = location.get("source")
    if isinstance(source, dict):
        for key in (
            "id",
            "homepage_url",
            "display_name",
            "host_organization_name",
            "host_organization_lineage_names",
        ):
            value = source.get(key)
            if isinstance(value, str):
                yield value
            elif isinstance(value, list):
                yield from (str(item) for item in value)


def work_mentions_neurips(work: dict[str, Any]) -> bool:
    needles = ("neurips", "neural information processing systems")
    for value in iter_openalex_urlish_values(work):
        lowered = value.casefold()
        if any(needle in lowered for needle in needles):
            return True
    return False


def canonical_arxiv_url(value: str) -> str:
    if "arxiv" not in value.casefold():
        return ""

    match = ARXIV_ID_RE.search(value)
    if not match:
        return ""

    arxiv_id = match.group("id").removesuffix(".pdf")
    return f"https://arxiv.org/abs/{arxiv_id}"


def http_get_text(url: str, retries: int) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
                    "User-Agent": USER_AGENT,
                },
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                encoding = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(encoding, errors="replace")
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in {429, 500, 502, 503, 504}:
                safe_url = redact_url_query_param(url, "api_key")
                raise RuntimeError(
                    f"GET failed with HTTP {error.code}: {safe_url}"
                ) from None
        except urllib.error.URLError as error:
            last_error = error

        if attempt < retries:
            time.sleep(min(2**attempt, 30))

    safe_url = redact_url_query_param(url, "api_key")
    raise RuntimeError(
        f"GET failed after {retries + 1} attempts: {safe_url}"
    ) from last_error


def redact_url_query_param(url: str, name: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    redacted_query = [
        (key, "REDACTED" if key == name else value) for key, value in query
    ]
    return urllib.parse.urlunsplit(
        parsed._replace(query=urllib.parse.urlencode(redacted_query))
    )


def title_similarity(left: str, right: str) -> float:
    left_normalized = normalize_title(left)
    right_normalized = normalize_title(right)
    if not left_normalized or not right_normalized:
        return 0.0
    if left_normalized == right_normalized:
        return 1.0
    if left_normalized in right_normalized or right_normalized in left_normalized:
        shorter = min(len(left_normalized), len(right_normalized))
        longer = max(len(left_normalized), len(right_normalized))
        return shorter / longer
    return SequenceMatcher(None, left_normalized, right_normalized).ratio()


def normalize_title(value: str) -> str:
    value = html.unescape(value).casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return normalize_space(value)


def normalize_space(value: str) -> str:
    return " ".join(value.split())


if __name__ == "__main__":
    raise SystemExit(main())
