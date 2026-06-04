from __future__ import annotations

import csv
import html
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


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
class Match:
    work: dict[str, Any] | None
    score: float
    status: str


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


def make_openalex_url(params: dict[str, str]) -> str:
    return f"{OPENALEX_WORKS_URL}?{urllib.parse.urlencode(params)}"


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


def make_row(year: int, paper: Any, match: Match) -> dict[str, str]:
    work = match.work or {}
    return {
        "year": str(year),
        "title": paper.title,
        "neurips_url": paper.neurips_url,
        "arxiv_url": arxiv_url(work) if work else "",
        "openalex_id": str(work.get("id", "")),
        "openalex_title": str(work.get("title") or work.get("display_name") or ""),
        "openalex_publication_year": str(work.get("publication_year", "")),
        "openalex_doi": str(work.get("doi", "")),
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
        values.extend(
            str(source.get(key) or "")
            for key in ("id", "homepage_url", "display_name", "host_organization_name")
        )
        values.extend(str(value) for value in source.get("host_organization_lineage_names") or [])
    return values


def mentions_neurips(work: dict[str, Any]) -> bool:
    text = " ".join(openalex_values(work)).casefold()
    return "neurips" in text or "neural information processing systems" in text


def write_rows(path: str, rows: list[dict[str, str]], fmt: str) -> None:
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
            print(f"Retrying in {sleep_seconds}s: {redact_key(url)}", file=sys.stderr)
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
    normalized = re.sub(r"[^a-z0-9]+", " ", html.unescape(value).casefold())
    return " ".join(normalized.split())
