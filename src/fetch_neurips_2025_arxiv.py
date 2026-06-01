#!/usr/bin/env python3
"""Map NeurIPS proceedings papers to arXiv URLs with batched OpenAlex lookups."""

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
USER_AGENT = "reprocli-neurips-openalex-mapper/0.3"
ARXIV_RE = re.compile(
    r"(?i)(?:arxiv:|arxiv\.|abs/|pdf/)?"
    r"(?P<id>(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)"
)


class OpenAlexHTTPError(RuntimeError):
    def __init__(self, status: int, url: str) -> None:
        super().__init__(f"OpenAlex HTTP {status}: {redact_key(url)}")
        self.status = status


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
        self.href: str | None = None
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        href = dict(attrs).get("href") if tag == "a" else None
        if href and self.is_paper_link(href):
            self.href = href
            self.text = []

    def handle_data(self, data: str) -> None:
        if self.href:
            self.text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self.href:
            return
        title = clean_space("".join(self.text))
        if title:
            self.papers.append(
                Paper(
                    html.unescape(title),
                    urllib.parse.urljoin(self.base_url, self.href),
                )
            )
        self.href = None
        self.text = []

    def is_paper_link(self, href: str) -> bool:
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


def fetch_neurips_papers(url: str, year: int) -> list[Paper]:
    parser = NeuripsParser(url, year)
    parser.feed(http_get(url, retries=3))

    seen: set[str] = set()
    papers: list[Paper] = []
    for paper in parser.papers:
        if paper.neurips_url not in seen:
            seen.add(paper.neurips_url)
            papers.append(paper)

    if not papers:
        raise RuntimeError(f"No NeurIPS {year} paper links found at {url}")
    return papers


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
) -> list[dict[str, Any]]:
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

    rows: list[tuple[int, dict[str, Any]]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(fetch_batch_rows, batch, year, api_key, min_score, retries, throttle): n
            for n, batch in enumerate(batches, start=1)
        }
        for done, future in enumerate(as_completed(futures), start=1):
            batch_rows = future.result()
            rows.extend(batch_rows)
            print(
                f"[batch {done}/{len(futures)}] {len(batch_rows)} arXiv URLs",
                file=sys.stderr,
            )

    return [row for _, row in sorted(rows, key=lambda item: item[0])]


def fetch_batch_rows(
    batch: list[tuple[int, Paper]],
    year: int,
    api_key: str,
    min_score: float,
    retries: int,
    throttle: Throttle,
) -> list[tuple[int, dict[str, Any]]]:
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

    rows: list[tuple[int, dict[str, Any]]] = []
    for index, paper in batch:
        match = choose_match(paper.title, works, min_score)
        row = make_row(year, paper, match)
        if row["arxiv_url"]:
            rows.append((index, row))
    return rows


def query_openalex_batch(
    titles: list[str],
    api_key: str,
    retries: int,
) -> list[dict[str, Any]]:
    data = json.loads(
        http_get(
            make_openalex_url(
                {
                    "api_key": api_key,
                    "filter": "display_name:" + "|".join(titles),
                    "per_page": "100",
                    "select": OPENALEX_SELECT,
                }
            ),
            retries,
        )
    )
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


def make_openalex_url(params: dict[str, str]) -> str:
    return f"{OPENALEX_WORKS_URL}?{urllib.parse.urlencode(params)}"


def can_batch(title: str) -> bool:
    return bool(title.strip()) and "," not in title and "|" not in title


def choose_match(title: str, works: list[dict[str, Any]], min_score: float) -> Match:
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
        return Match(None, 0.0, "batch_no_match")

    best_score = max(score for score, _, _, _ in candidates)
    if best_score < min_score:
        work = max(candidates, key=lambda item: item[0])[3]
        return Match(work, best_score, "batch_low_confidence")

    near_best = [c for c in candidates if c[0] >= max(min_score, best_score - 0.03)]
    score, has_arxiv, _, work = max(near_best, key=lambda item: (item[1], item[2], item[0]))
    return Match(work, score, "batch_arxiv" if has_arxiv else "batch_no_arxiv")


def make_row(year: int, paper: Paper, match: Match) -> dict[str, Any]:
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
    for value in openalex_values(work):
        if "arxiv" not in value.casefold():
            continue
        match = ARXIV_RE.search(value)
        if match:
            return f"https://arxiv.org/abs/{match.group('id').removesuffix('.pdf')}"
    return ""


def openalex_values(work: dict[str, Any]) -> list[str]:
    values = [str(work.get(key) or "") for key in ("doi", "pdf_url", "landing_page_url")]
    ids = work.get("ids")
    if isinstance(ids, dict):
        values.extend(str(value) for value in ids.values())
    for location in [work.get("primary_location"), work.get("best_oa_location")]:
        values.extend(location_values(location))
    for location in work.get("locations") or []:
        values.extend(location_values(location))
    return [value for value in values if value]


def location_values(location: Any) -> list[str]:
    if not isinstance(location, dict):
        return []
    source = location.get("source") or {}
    values = [str(location.get("landing_page_url") or ""), str(location.get("pdf_url") or "")]
    if isinstance(source, dict):
        values.extend(str(source.get(key) or "") for key in ("id", "homepage_url", "display_name", "host_organization_name"))
        values.extend(str(value) for value in source.get("host_organization_lineage_names") or [])
    return values


def mentions_neurips(work: dict[str, Any]) -> bool:
    text = " ".join(openalex_values(work)).casefold()
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
                raise OpenAlexHTTPError(error.code, url) from None
            retry_after = error.headers.get("Retry-After")
            sleep_seconds = (
                min(int(retry_after), 60)
                if retry_after and retry_after.isdigit()
                else min(2**attempt, 30)
            )
        except urllib.error.URLError as error:
            last_error = error
            sleep_seconds = min(2**attempt, 30)
        if attempt < retries:
            print(
                f"Retrying in {sleep_seconds}s after request failure: "
                f"{redact_key(url)}",
                file=sys.stderr,
            )
            time.sleep(sleep_seconds)
    if isinstance(last_error, urllib.error.HTTPError):
        raise OpenAlexHTTPError(last_error.code, url) from None
    raise RuntimeError(f"GET failed after {retries + 1} tries: {redact_key(url)}") from last_error


def redact_key(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query = [(key, "REDACTED" if key == "api_key" else value) for key, value in query]
    return urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(query)))


def title_similarity(left: str, right: str) -> float:
    left_norm = normalize_title(left)
    right_norm = normalize_title(right)
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
