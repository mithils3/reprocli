from __future__ import annotations

import html
import urllib.parse
from dataclasses import dataclass
from html.parser import HTMLParser

from .openalex_lookup import http_get


@dataclass(frozen=True)
class Paper:
    title: str
    neurips_url: str


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


def clean_space(value: str) -> str:
    return " ".join(value.split())
