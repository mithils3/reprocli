from __future__ import annotations

import csv
import gzip
import io
import shutil
import sys
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath

from .arxiv_source_inputs import (
    RETRYABLE_HTTP_CODES,
    USER_AGENT,
    DownloadJob,
    DownloadResult,
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
            print(f"[{done}/{len(futures)}] {result.arxiv_id}: {result.status}", file=sys.stderr)
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
    existing = target.exists() and target.is_dir() and any(target.iterdir())
    if existing and not overwrite:
        return download_result(job, "skipped_existing", target, count_files(target), 0)
    if target.exists() and not target.is_dir() and not overwrite:
        return download_result(
            job,
            "failed",
            target,
            0,
            0,
            "output path exists and is not a directory",
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
        replace_with_tmp(target, tmp_dir)
        return download_result(job, "downloaded", target, files_written, len(data))
    except Exception as error:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return download_result(job, "failed", target, 0, 0, str(error))


def download_result(
    job: DownloadJob,
    status: str,
    target: Path,
    files_written: int,
    bytes_downloaded: int,
    error: str = "",
) -> DownloadResult:
    return DownloadResult(
        index=job.index,
        arxiv_id=job.arxiv_id,
        title=job.title,
        source_url=job.source_url,
        status=status,
        output_path=str(target),
        files_written=files_written,
        bytes_downloaded=bytes_downloaded,
        error=error,
    )


def replace_with_tmp(target: Path, tmp_dir: Path) -> None:
    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    tmp_dir.rename(target)


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
            return extract_tar_members(archive, output_dir)
    except tarfile.TarError:
        return None


def extract_tar_members(archive: tarfile.TarFile, output_dir: Path) -> int:
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
