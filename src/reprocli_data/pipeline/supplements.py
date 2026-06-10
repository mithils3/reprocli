"""Supplements stage: match papers to OpenReview notes by note id and download attachments.

Matching uses the OpenReview forum id captured in the index; there is no
title-based fallback.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

from .attachments import (
    Note,
    SupplementJob,
    absolute_openreview_url,
    attachment_url,
    build_client,
    download_supplements,
    fetch_openreview_notes,
    write_job_csv,
)
from .common import (
    MANIFEST_FILENAME,
    NOTES_CACHE_FILENAME,
    SUPPLEMENTS_DIRNAME,
    DownloadResult,
    print_stage_summary,
    write_manifest,
)
from .index import IndexRecord


def stage_supplements(
    records: list[IndexRecord],
    data_dir: Path,
    *,
    notes_json: Path | None,
    api_base: str,
    venue_id: str,
    workers: int,
    delay: float,
    retries: int,
    overwrite: bool,
) -> list[DownloadResult]:
    output_dir = data_dir / SUPPLEMENTS_DIRNAME
    output_dir.mkdir(parents=True, exist_ok=True)
    notes_path = notes_json or (data_dir / NOTES_CACHE_FILENAME)
    notes = load_or_fetch_notes(notes_path, api_base, venue_id)
    notes_by_id = index_notes_by_id(notes)
    jobs, missing_id, missing_note, no_supplement = match_supplement_jobs(records, notes_by_id)
    print(
        f"Matched {len(jobs)} OpenReview supplements from {len(records)} papers "
        f"and {len(notes)} notes ({missing_id} without an OpenReview id, "
        f"{missing_note} ids not found, {no_supplement} notes without supplements).",
        file=sys.stderr,
    )
    write_job_csv(output_dir / "openreview_jobs.csv", jobs)
    results = download_supplements(
        jobs=jobs,
        output_dir=output_dir,
        retries=max(0, retries),
        api_base=api_base,
        overwrite=overwrite,
        delay=max(0.0, delay),
        workers=max(1, workers),
    )
    write_manifest(output_dir / MANIFEST_FILENAME, results)
    print_stage_summary("supplements", output_dir / MANIFEST_FILENAME, results)
    return results


def load_or_fetch_notes(path: Path, api_base: str, venue_id: str) -> list[Note]:
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw_notes = payload.get("notes", payload) if isinstance(payload, dict) else payload
        print(f"Loaded {len(raw_notes)} cached OpenReview notes from {path}.", file=sys.stderr)
    else:
        raw_notes = fetch_openreview_notes(build_client(api_base), venue_id)
        print(f"Fetched {len(raw_notes)} OpenReview notes for {venue_id}.", file=sys.stderr)
        try:
            path.write_text(
                json.dumps({"notes": [note_payload(note) for note in raw_notes]}),
                encoding="utf-8",
            )
            print(f"Cached notes to {path}.", file=sys.stderr)
        except (TypeError, ValueError, OSError) as error:
            print(f"Could not cache notes to {path}: {error}", file=sys.stderr)
    return [parse_note(raw) for raw in raw_notes]


def note_payload(raw: Any) -> Any:
    if isinstance(raw, dict):
        return raw
    to_json = getattr(raw, "to_json", None)
    if callable(to_json):
        return to_json()
    return raw.__dict__


def parse_note(raw: Any) -> Note:
    if isinstance(raw, dict):
        content = raw.get("content") or {}
        note_id = str(raw.get("id") or "")
        forum = str(raw.get("forum") or "")
    else:
        content = getattr(raw, "content", {}) or {}
        note_id = str(getattr(raw, "id", "") or "")
        forum = str(getattr(raw, "forum", "") or "")
    return Note(note_id=note_id, forum=forum, content=content)


def index_notes_by_id(notes: Iterable[Note]) -> dict[str, Note]:
    notes_by_id: dict[str, Note] = {}
    for note in notes:
        if note.note_id:
            notes_by_id.setdefault(note.note_id, note)
        if note.forum:
            notes_by_id.setdefault(note.forum, note)
    return notes_by_id


def match_supplement_jobs(
    records: list[IndexRecord],
    notes_by_id: dict[str, Note],
) -> tuple[list[SupplementJob], int, int, int]:
    jobs: list[SupplementJob] = []
    missing_id = missing_note = no_supplement = 0
    for index, record in enumerate(records, start=1):
        if not record.openreview_id:
            missing_id += 1
            continue
        note = notes_by_id.get(record.openreview_id)
        if note is None:
            missing_note += 1
            continue
        attachment = supplement_attachment(note)
        if not attachment:
            no_supplement += 1
            continue
        field_name, source_url = attachment
        jobs.append(
            SupplementJob(
                index,
                record.arxiv_id,
                record.title,
                note.note_id,
                field_name,
                source_url,
            )
        )
    return jobs, missing_id, missing_note, no_supplement


def supplement_attachment(note: Note) -> tuple[str, str] | None:
    for key, raw_value in note.content.items():
        if "supplement" not in key.casefold():
            continue
        value = content_value(raw_value)
        if isinstance(value, str) and value:
            return key, absolute_openreview_url(value)
        return key, attachment_url(note.note_id, key)
    return None


def content_value(value: Any) -> Any:
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value
