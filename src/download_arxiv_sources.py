#!/usr/bin/env python3
"""Download and extract arXiv source packages listed in a CSV file."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import re
import shutil
import sys
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


DEFAULT_DATA_DIR = Path("data")
DEFAULT_OUTPUT_DIR = Path("data/arxiv_sources")
DEFAULT_MANIFEST = "manifest.csv"
DEFAULT_WORKERS = 8
DEFAULT_DELAY = 0.25
USER_AGENT = "reprocli-arxiv-source-downloader/0.1"
ARXIV_ID_RE = re.compile(
    r"(?i)(?:arxiv:|arxiv\.org/(?:abs|pdf|e-print)/|doi\.org/10\.48550/arxiv\.)?"
    r"(?P<id>(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)"
    r"(?:\.pdf)?"
)
RETRYABLE_HTTP_CODES = {408, 429, 500, 502, 503, 504}


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
    manifest_path = output_dir / args.manifest
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
    parser.add_argument(
        "--input",
        help="CSV path. Defaults to the only *.csv file in data/.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--url-column", default="arxiv_url")
    parser.add_argument("--id-column", help="Optional column containing arXiv IDs.")
    parser.add_argument("--title-column", default="title")
    parser.add_argument("--limit", type=int, help="Download at most this many unique IDs.")
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of parallel download workers. Default: {DEFAULT_WORKERS}.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help=(
            "Minimum seconds between starting arXiv requests across all workers. "
            f"Default: {DEFAULT_DELAY}; use 0 for maximum throughput."
        ),
    )
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--keep-archive",
        action="store_true",
        help="Also keep the downloaded e-print package in each output directory.",
    )
    parser.add_argument("--allow-failures", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


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


def download_all(
    jobs: list[DownloadJob],
    output_dir: Path,
    workers: int,
    delay: float,
    retries: int,
    timeout: float,
    overwrite: bool,
    keep_archive: bool,
) -> list[DownloadResult]:
    throttle = Throttle(delay)
    results: list[DownloadResult] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                download_one,
                job,
                output_dir,
                retries,
                timeout,
                overwrite,
                keep_archive,
                throttle,
            ): job
            for job in jobs
        }
        for done, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            print(
                f"[{done}/{len(futures)}] {result.arxiv_id}: {result.status}",
                file=sys.stderr,
            )
    return sorted(results, key=lambda result: result.index)


def download_one(
    job: DownloadJob,
    output_dir: Path,
    retries: int,
    timeout: float,
    overwrite: bool,
    keep_archive: bool,
    throttle: Throttle,
) -> DownloadResult:
    target = output_dir / safe_dirname(job.arxiv_id)
    if target.exists() and target.is_dir() and any(target.iterdir()) and not overwrite:
        return DownloadResult(
            index=job.index,
            arxiv_id=job.arxiv_id,
            title=job.title,
            source_url=job.source_url,
            status="skipped_existing",
            output_path=str(target),
            files_written=count_files(target),
            bytes_downloaded=0,
        )
    if target.exists() and not target.is_dir() and not overwrite:
        return DownloadResult(
            index=job.index,
            arxiv_id=job.arxiv_id,
            title=job.title,
            source_url=job.source_url,
            status="failed",
            output_path=str(target),
            files_written=0,
            bytes_downloaded=0,
            error="output path exists and is not a directory",
        )

    tmp_dir = Path(tempfile.mkdtemp(dir=output_dir))
    try:
        throttle.wait()
        data, content_type = http_get_bytes(job.source_url, retries, timeout)
        if looks_like_html(data, content_type):
            raise RuntimeError("arXiv returned HTML instead of a source package")
        if keep_archive:
            (tmp_dir / f"{safe_dirname(job.arxiv_id)}.e-print").write_bytes(data)
        files_written = unpack_source_package(data, tmp_dir, job.arxiv_id)
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        tmp_dir.rename(target)
        return DownloadResult(
            index=job.index,
            arxiv_id=job.arxiv_id,
            title=job.title,
            source_url=job.source_url,
            status="downloaded",
            output_path=str(target),
            files_written=files_written,
            bytes_downloaded=len(data),
        )
    except Exception as error:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return DownloadResult(
            index=job.index,
            arxiv_id=job.arxiv_id,
            title=job.title,
            source_url=job.source_url,
            status="failed",
            output_path=str(target),
            files_written=0,
            bytes_downloaded=0,
            error=str(error),
        )


def http_get_bytes(url: str, retries: int, timeout: float) -> tuple[bytes, str]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                content_type = header_value(response.headers.get("Content-Type", ""))
                return response.read(), content_type
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in RETRYABLE_HTTP_CODES:
                raise RuntimeError(f"HTTP {error.code}") from None
            sleep_seconds = retry_delay(error, attempt)
        except urllib.error.URLError as error:
            last_error = error
            sleep_seconds = min(2**attempt, 30)

        if attempt < retries:
            time.sleep(sleep_seconds)

    raise RuntimeError(f"GET failed after {retries + 1} tries") from last_error


def retry_delay(error: urllib.error.HTTPError, attempt: int) -> int:
    retry_after = error.headers.get("Retry-After")
    if retry_after and retry_after.isdigit():
        return min(int(retry_after), 60)
    return min(2**attempt, 30)


def header_value(value: str | bytes) -> str:
    if isinstance(value, bytes):
        return value.decode("latin-1", errors="replace")
    return value


def unpack_source_package(data: bytes, output_dir: Path, arxiv_id: str) -> int:
    tar_count = try_extract_tar(data, output_dir)
    if tar_count is not None:
        return tar_count

    if data.startswith(b"\x1f\x8b"):
        decompressed = gzip.decompress(data)
        tar_count = try_extract_tar(decompressed, output_dir)
        if tar_count is not None:
            return tar_count
        if looks_like_html(decompressed, ""):
            raise RuntimeError("arXiv returned compressed HTML instead of source")
        return write_single_source_file(decompressed, output_dir, "source.tex")

    return write_single_source_file(data, output_dir, f"{safe_dirname(arxiv_id)}.source")


def try_extract_tar(data: bytes, output_dir: Path) -> int | None:
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            files_written = 0
            for member in archive.getmembers():
                target = safe_tar_target(output_dir, member.name)
                if target is None:
                    continue
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    source = archive.extractfile(member)
                    if source is None:
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source, target.open("wb") as handle:
                        shutil.copyfileobj(source, handle)
                    files_written += 1
            return files_written
    except tarfile.TarError:
        return None


def safe_tar_target(output_dir: Path, member_name: str) -> Path | None:
    pure_path = PurePosixPath(member_name.replace("\\", "/"))
    if pure_path.is_absolute() or ".." in pure_path.parts:
        return None
    clean_parts = [part for part in pure_path.parts if part not in {"", "."}]
    if not clean_parts:
        return None
    return output_dir.joinpath(*clean_parts)


def write_single_source_file(data: bytes, output_dir: Path, filename: str) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / filename).write_bytes(data)
    return 1


def looks_like_html(data: bytes, content_type: str) -> bool:
    if "text/html" in content_type.casefold():
        return True
    prefix = data[:512].lstrip().lower()
    return prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html")


def safe_dirname(arxiv_id: str) -> str:
    return arxiv_id.replace("/", "_")


def count_files(path: Path) -> int:
    return sum(1 for item in path.rglob("*") if item.is_file())


def write_manifest(path: Path, results: list[DownloadResult]) -> None:
    fields = [
        "index",
        "arxiv_id",
        "title",
        "source_url",
        "status",
        "output_path",
        "files_written",
        "bytes_downloaded",
        "error",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in results:
            writer.writerow(result.__dict__)


if __name__ == "__main__":
    raise SystemExit(main())
