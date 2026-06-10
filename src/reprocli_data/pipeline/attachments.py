"""OpenReview client, note/job types, and supplement attachment downloads."""

from __future__ import annotations

import csv
import io
import os
import shutil
import sys
import tarfile
import tempfile
import threading
import time
import urllib.parse
import zipfile
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import Any

from .common import (
    DownloadResult,
    RequestThrottle,
    count_files,
    extract_tar_members,
    make_result,
    safe_archive_target,
    safe_dirname,
    write_single_source_file,
)


OPENREVIEW_API = "https://api2.openreview.net"
OPENREVIEW_SITE = "https://openreview.net"
DEFAULT_VENUE_ID = "NeurIPS.cc/2025/Conference"
THREAD_LOCAL = threading.local()


@dataclass(frozen=True)
class Note:
    note_id: str
    forum: str
    content: dict[str, Any]


@dataclass(frozen=True)
class SupplementJob:
    index: int
    arxiv_id: str
    title: str
    note_id: str
    attachment_name: str
    source_url: str


def build_client(api_base: str) -> Any:
    import openreview

    username = os.environ.get("OPENREVIEW_USERNAME")
    password = os.environ.get("OPENREVIEW_PASSWORD")
    return openreview.api.OpenReviewClient(
        baseurl=api_base,
        username=username,
        password=password,
    )


def thread_client(api_base: str) -> Any:
    client = getattr(THREAD_LOCAL, "openreview_client", None)
    if client is None:
        client = build_client(api_base)
        THREAD_LOCAL.openreview_client = client
    return client


def fetch_openreview_notes(client: Any, venue_id: str) -> list[Any]:
    return client.get_all_notes(content={"venueid": venue_id})


def attachment_url(note_id: str, field_name: str) -> str:
    query = urllib.parse.urlencode({"id": note_id, "name": field_name})
    return f"{OPENREVIEW_SITE}/attachment?{query}"


def absolute_openreview_url(value: str) -> str:
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("/"):
        return f"{OPENREVIEW_SITE}{value}"
    return value


def download_supplements(
    jobs: list[SupplementJob],
    output_dir: Path,
    retries: int,
    api_base: str,
    overwrite: bool,
    delay: float,
    workers: int,
) -> list[DownloadResult]:
    results: list[DownloadResult] = []
    pending_jobs = iter(jobs)
    throttle = RequestThrottle(delay)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(download_supplement_one, api_base, job, output_dir, retries, overwrite, throttle)
            for job in islice(pending_jobs, max(1, workers))
        }
        while futures:
            done_futures, futures = wait(futures, return_when=FIRST_COMPLETED)
            for future in done_futures:
                result = future.result()
                results.append(result)
                print(progress_line(len(results), len(jobs), result), file=sys.stderr)
                for job in islice(pending_jobs, 1):
                    futures.add(
                        pool.submit(
                            download_supplement_one, api_base, job, output_dir, retries, overwrite, throttle
                        )
                    )
    return sorted(results, key=lambda item: item.index)


def progress_line(done: int, total: int, result: DownloadResult) -> str:
    line = f"[{done}/{total}] {result.arxiv_id}: {result.status}"
    if result.error:
        return f"{line}: {result.error}"
    return line


def download_supplement_one(
    api_base: str,
    job: SupplementJob,
    output_dir: Path,
    retries: int,
    overwrite: bool,
    throttle: RequestThrottle,
) -> DownloadResult:
    target = output_dir / safe_dirname(job.arxiv_id)
    if target.is_dir() and any(target.iterdir()) and not overwrite:
        return make_result(
            job.index, job.arxiv_id, job.title, job.source_url, "skipped_existing", target, count_files(target), 0
        )
    tmp_dir = Path(tempfile.mkdtemp(dir=output_dir))
    try:
        client = thread_client(api_base)
        data = get_attachment_bytes(client, job, retries, throttle)
        files_written = unpack_archive(data, tmp_dir)
        if target.exists():
            shutil.rmtree(target)
        tmp_dir.rename(target)
        return make_result(
            job.index, job.arxiv_id, job.title, job.source_url, "downloaded", target, files_written, len(data)
        )
    except Exception as error:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return make_result(
            job.index, job.arxiv_id, job.title, job.source_url, "failed", target, 0, 0, str(error)
        )


def get_attachment_bytes(
    client: Any,
    job: SupplementJob,
    retries: int,
    throttle: RequestThrottle,
) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            throttle.wait()
            data = client.get_attachment(field_name=job.attachment_name, id=job.note_id)
            if isinstance(data, bytes):
                return data
            if isinstance(data, bytearray):
                return bytes(data)
            return str(data).encode("utf-8")
        except Exception as error:
            last_error = error
            message = str(error)
            if "404" in message or "not found" in message.casefold():
                raise RuntimeError(
                    f"OpenReview attachment not found: {job.attachment_name}"
                ) from None
            if attempt < retries:
                time.sleep(min(2**attempt, 60))
    raise RuntimeError(f"OpenReview attachment fetch failed: {last_error}") from last_error


def unpack_archive(data: bytes, output_dir: Path) -> int:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return extract_zip_members(archive, output_dir)
    except zipfile.BadZipFile:
        pass
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            return extract_tar_members(archive, output_dir)
    except tarfile.TarError:
        return write_single_source_file(data, output_dir, "supplementary_material.bin")


def extract_zip_members(archive: zipfile.ZipFile, output_dir: Path) -> int:
    files_written = 0
    for info in archive.infolist():
        target = safe_archive_target(output_dir, info.filename)
        if target is None or info.is_dir():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as source, target.open("wb") as handle:
            shutil.copyfileobj(source, handle)
        files_written += 1
    return files_written


def write_job_csv(path: Path, jobs: list[SupplementJob]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SupplementJob.__dataclass_fields__))
        writer.writeheader()
        for job in jobs:
            writer.writerow(job.__dict__)
