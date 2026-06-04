from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .arxiv_source_inputs import DownloadResult
from .archive_extract import unpack_archive
from .arxiv_source_download import count_files, safe_dirname


OPENREVIEW_API = "https://api2.openreview.net"
OPENREVIEW_SITE = "https://openreview.net"
DEFAULT_VENUE_ID = "NeurIPS.cc/2025/Conference"


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
    attachment_name: str
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
        raw_notes = fetch_openreview_notes(build_client(api_base), venue_id)
    return [parse_note(note) for note in raw_notes]


def build_client(api_base: str) -> Any:
    import openreview

    username = os.environ.get("OPENREVIEW_USERNAME")
    password = os.environ.get("OPENREVIEW_PASSWORD")
    return openreview.api.OpenReviewClient(
        baseurl=api_base,
        username=username,
        password=password,
    )


def fetch_openreview_notes(client: Any, venue_id: str) -> list[Any]:
    return client.get_all_notes(content={"venueid": venue_id})


def parse_note(raw: Any) -> Note:
    if isinstance(raw, dict):
        content = raw.get("content") or {}
        note_id = str(raw.get("id") or raw.get("forum") or "")
    else:
        content = getattr(raw, "content", {}) or {}
        note_id = str(getattr(raw, "id", "") or getattr(raw, "forum", "") or "")
    return Note(
        note_id=note_id,
        title=str(content_value(content.get("title")) or ""),
        content=content,
    )


def match_jobs(papers: Iterable[Paper], notes: Iterable[Note]) -> tuple[list[SupplementJob], int, int]:
    notes_by_title = {normalize_title(note.title): note for note in notes if note.note_id}
    jobs: list[SupplementJob] = []
    misses = 0
    no_supplement = 0
    for paper in papers:
        note = notes_by_title.get(normalize_title(paper.title))
        if not note:
            misses += 1
            continue
        attachment = supplement_attachment(note)
        if not attachment:
            no_supplement += 1
            continue
        field_name, source_url = attachment
        jobs.append(
            SupplementJob(
                paper.index,
                paper.arxiv_id,
                paper.title,
                note.note_id,
                field_name,
                source_url,
            )
        )
    return jobs, misses, no_supplement


def supplement_attachment(note: Note) -> tuple[str, str] | None:
    for key, raw_value in note.content.items():
        if "supplement" not in key.casefold():
            continue
        value = content_value(raw_value)
        if isinstance(value, str) and value:
            return key, absolute_openreview_url(value)
        return key, attachment_url(note.note_id, key)
    return None


def attachment_url(note_id: str, field_name: str) -> str:
    query = urllib.parse.urlencode({"id": note_id, "name": field_name})
    return f"{OPENREVIEW_SITE}/attachment?{query}"


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
    api_base: str,
    overwrite: bool,
    delay: float,
) -> list[DownloadResult]:
    client = build_client(api_base)
    results: list[DownloadResult] = []
    for done, job in enumerate(jobs, start=1):
        if delay > 0 and done > 1:
            time.sleep(delay)
        result = download_one(client, job, output_dir, retries, overwrite)
        results.append(result)
        print(progress_line(done, len(jobs), result), file=sys.stderr)
    return results


def progress_line(done: int, total: int, result: DownloadResult) -> str:
    line = f"[{done}/{total}] {result.arxiv_id}: {result.status}"
    if result.error:
        return f"{line}: {result.error}"
    return line


def download_one(
    client: Any,
    job: SupplementJob,
    output_dir: Path,
    retries: int,
    overwrite: bool,
) -> DownloadResult:
    target = output_dir / safe_dirname(job.arxiv_id)
    if target.is_dir() and any(target.iterdir()) and not overwrite:
        return result(job, "skipped_existing", target, count_files(target), 0)
    tmp_dir = Path(tempfile.mkdtemp(dir=output_dir))
    try:
        data = get_attachment_bytes(client, job, retries)
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


def get_attachment_bytes(client: Any, job: SupplementJob, retries: int) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
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


def write_job_csv(path: Path, jobs: list[SupplementJob]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SupplementJob.__dataclass_fields__))
        writer.writeheader()
        for job in jobs:
            writer.writerow(job.__dict__)
