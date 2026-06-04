from __future__ import annotations

import csv
import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_DATA_DIR = Path("data")
DEFAULT_OUTPUT_DIR = Path("data/arxiv_sources")
DEFAULT_MANIFEST = "manifest.csv"
DEFAULT_WORKERS = 8
DEFAULT_DELAY = 0.25
USER_AGENT = "reprocli-arxiv-source-downloader/0.1"
RETRYABLE_HTTP_CODES = {408, 429, 500, 502, 503, 504}
ARXIV_ID_RE = re.compile(
    r"(?i)(?:arxiv:|arxiv\.org/(?:abs|pdf|e-print)/|doi\.org/10\.48550/arxiv\.)?"
    r"(?P<id>(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)"
    r"(?:\.pdf)?"
)


@dataclass(frozen=True)
class DownloadJob:
    index: int
    arxiv_id: str
    title: str
    source_url: str


@dataclass(frozen=True)
class InputStats:
    total_rows: int
    missing_ids: int
    duplicate_ids: int


@dataclass(frozen=True)
class DownloadResult:
    index: int
    arxiv_id: str
    title: str
    source_url: str
    status: str
    output_path: str
    files_written: int
    bytes_downloaded: int
    error: str = ""


def discover_input_csv(data_dir: Path) -> Path:
    candidates = sorted(data_dir.glob("*.csv"))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise SystemExit(f"No CSV files found in {data_dir}. Pass --input.")
    choices = ", ".join(str(path) for path in candidates)
    raise SystemExit(f"Multiple CSV files found ({choices}). Pass --input.")


def load_jobs(
    input_path: Path,
    url_column: str,
    id_column: str | None,
    title_column: str,
    limit: int | None,
) -> tuple[list[DownloadJob], InputStats]:
    jobs: list[DownloadJob] = []
    seen: set[str] = set()
    total_rows = 0
    missing_ids = 0
    duplicate_ids = 0

    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require_columns(reader.fieldnames, [id_column or url_column])
        for total_rows, row in enumerate(reader, start=1):
            raw_value = row.get(id_column) if id_column else row.get(url_column)
            arxiv_id = extract_arxiv_id(raw_value or "")
            if not arxiv_id:
                missing_ids += 1
                continue
            if arxiv_id in seen:
                duplicate_ids += 1
                continue
            seen.add(arxiv_id)
            jobs.append(
                DownloadJob(
                    index=total_rows,
                    arxiv_id=arxiv_id,
                    title=row.get(title_column, ""),
                    source_url=arxiv_eprint_url(arxiv_id),
                )
            )
            if limit and len(jobs) >= limit:
                break

    return jobs, InputStats(total_rows, missing_ids, duplicate_ids)


def require_columns(fieldnames: list[str] | None, required: Iterable[str]) -> None:
    available = set(fieldnames or [])
    missing = [column for column in required if column and column not in available]
    if missing:
        raise SystemExit(
            f"Missing required CSV column(s): {', '.join(missing)}. "
            f"Available columns: {', '.join(fieldnames or [])}"
        )


def extract_arxiv_id(value: str) -> str:
    match = ARXIV_ID_RE.search(value.strip())
    if not match:
        return ""
    return match.group("id").removesuffix(".pdf")


def arxiv_eprint_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/e-print/{urllib.parse.quote(arxiv_id, safe='/')}"
