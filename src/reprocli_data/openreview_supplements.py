from __future__ import annotations

import csv
import io
import json
import re
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .arxiv_source_inputs import RETRYABLE_HTTP_CODES, USER_AGENT, DownloadResult
from .arxiv_source_download import count_files, safe_dirname, write_single_source_file


OPENREVIEW_API = "https://api2.openreview.net"
OPENREVIEW_SITE = "https://openreview.net"
DEFAULT_VENUE_ID = "NeurIPS.cc/2025/Conference"
SUPPLEMENT_NAMES = ("supplementary_material", "supplementary material", "supplement")


@dataclass(frozen=True)
class Paper:
    index: int
    arxiv_id: str
    title: str


@dataclass(frozen=True)
class Note:
    note_id: str
    title: str
    content: dict[str, Any]


@dataclass(frozen=True)
class SupplementJob:
    index: int
    arxiv_id: str
    title: str
    note_id: str
    source_url: str


def load_dataset_papers(dataset_name: str, limit: int | None) -> list[Paper]:
    from datasets import load_dataset

    dataset = load_dataset(dataset_name, split="train")
    papers: list[Paper] = []
    seen: set[str] = set()
    for row in dataset:
        arxiv_id = str(row.get("arxiv_id") or "")
        title = str(row.get("title") or "")
        if not arxiv_id or arxiv_id in seen:
            continue
        seen.add(arxiv_id)
        papers.append(Paper(len(papers) + 1, arxiv_id, title))
        if limit and len(papers) >= limit:
            break
    return papers


def load_notes(path: Path | None, api_base: str, venue_id: str, timeout: float) -> list[Note]:
    if path:
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw_notes = payload.get("notes", payload) if isinstance(payload, dict) else payload
    else:
        raw_notes = fetch_openreview_notes(api_base, venue_id, timeout)
    return [parse_note(note) for note in raw_notes]


def fetch_openreview_notes(api_base: str, venue_id: str, timeout: float) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    offset = 0
    limit = 1000
    while True:
        query = urllib.parse.urlencode(
            {
                "content.venueid": venue_id,
                "limit": limit,
                "offset": offset,
            }
        )
        payload = http_get_json(f"{api_base.rstrip('/')}/notes?{query}", timeout)
        batch = payload.get("notes") or []
        notes.extend(batch)
        if len(batch) < limit:
            return notes
        offset += limit


def parse_note(raw: dict[str, Any]) -> Note:
    content = raw.get("content") or {}
    return Note(
        note_id=str(raw.get("id") or raw.get("forum") or ""),
        title=str(content_value(content.get("title")) or ""),
        content=content,
    )


def match_jobs(papers: Iterable[Paper], notes: Iterable[Note]) -> tuple[list[SupplementJob], int]:
    notes_by_title = {normalize_title(note.title): note for note in notes if note.note_id}
    jobs: list[SupplementJob] = []
    misses = 0
    for paper in papers:
        note = notes_by_title.get(normalize_title(paper.title))
        if not note:
            misses += 1
            continue
        source_url = supplement_url(note)
        if not source_url:
            continue
        jobs.append(SupplementJob(paper.index, paper.arxiv_id, paper.title, note.note_id, source_url))
    return jobs, misses


def supplement_url(note: Note) -> str:
    for key, raw_value in note.content.items():
        if "supplement" not in key.casefold():
            continue
        value = content_value(raw_value)
        if isinstance(value, str) and value:
            return absolute_openreview_url(value)
    quoted = urllib.parse.quote(note.note_id)
    return f"{OPENREVIEW_SITE}/attachment?id={quoted}&name=supplementary_material"


def absolute_openreview_url(value: str) -> str:
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("/"):
        return f"{OPENREVIEW_SITE}{value}"
    return value


def content_value(value: Any) -> Any:
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip()


def download_jobs(
    jobs: list[SupplementJob],
    output_dir: Path,
    retries: int,
    timeout: float,
    overwrite: bool,
) -> list[DownloadResult]:
    results: list[DownloadResult] = []
    for done, job in enumerate(jobs, start=1):
        result = download_one(job, output_dir, retries, timeout, overwrite)
        results.append(result)
        print(progress_line(done, len(jobs), result), file=sys.stderr)
    return results


def progress_line(done: int, total: int, result: DownloadResult) -> str:
    line = f"[{done}/{total}] {result.arxiv_id}: {result.status}"
    if result.error:
        return f"{line}: {result.error}"
    return line


def download_one(
    job: SupplementJob,
    output_dir: Path,
    retries: int,
    timeout: float,
    overwrite: bool,
) -> DownloadResult:
    target = output_dir / safe_dirname(job.arxiv_id)
    if target.is_dir() and any(target.iterdir()) and not overwrite:
        return result(job, "skipped_existing", target, count_files(target), 0)
    tmp_dir = Path(tempfile.mkdtemp(dir=output_dir))
    try:
        data = http_get_bytes(job.source_url, retries, timeout)
        files_written = unpack_archive(data, tmp_dir)
        if target.exists():
            shutil.rmtree(target)
        tmp_dir.rename(target)
        return result(job, "downloaded", target, files_written, len(data))
    except Exception as error:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return result(job, "failed", target, 0, 0, str(error))


def result(
    job: SupplementJob,
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


def extract_tar_members(archive: tarfile.TarFile, output_dir: Path) -> int:
    files_written = 0
    for member in archive.getmembers():
        target = safe_archive_target(output_dir, member.name)
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


def safe_archive_target(output_dir: Path, member_name: str) -> Path | None:
    pure_path = PurePosixPath(member_name.replace("\\", "/"))
    if pure_path.is_absolute() or ".." in pure_path.parts:
        return None
    parts = [part for part in pure_path.parts if part not in {"", "."}]
    return output_dir.joinpath(*parts) if parts else None


def http_get_json(url: str, timeout: float) -> dict[str, Any]:
    return json.loads(http_get_bytes(url, 3, timeout).decode("utf-8"))


def http_get_bytes(url: str, retries: int, timeout: float) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in RETRYABLE_HTTP_CODES and error.code != 404:
                raise RuntimeError(f"HTTP {error.code}") from None
            sleep_seconds = min(2**attempt, 30)
        except urllib.error.URLError as error:
            last_error = error
            sleep_seconds = min(2**attempt, 30)
        if attempt < retries:
            time.sleep(sleep_seconds)
    detail = f": {last_error}" if last_error else ""
    raise RuntimeError(f"GET failed after {retries + 1} tries{detail}") from last_error


def write_job_csv(path: Path, jobs: list[SupplementJob]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SupplementJob.__dataclass_fields__))
        writer.writeheader()
        for job in jobs:
            writer.writerow(job.__dict__)
