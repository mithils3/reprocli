from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa


TEXT_EXTENSIONS = {
    ".aux",
    ".bbl",
    ".bib",
    ".bst",
    ".cfg",
    ".cls",
    ".csv",
    ".def",
    ".dtx",
    ".enc",
    ".html",
    ".idx",
    ".ins",
    ".json",
    ".ldf",
    ".log",
    ".md",
    ".out",
    ".sty",
    ".tex",
    ".txt",
    ".yaml",
    ".yml",
}

SCHEMA = pa.schema(
    [
        ("arxiv_id", pa.string()),
        ("title", pa.string()),
        ("source_url", pa.string()),
        ("paper_index", pa.int32()),
        ("paper_status", pa.string()),
        ("paper_files_written", pa.int32()),
        ("paper_bytes_downloaded", pa.int64()),
        ("relative_path", pa.string()),
        ("filename", pa.string()),
        ("extension", pa.string()),
        ("file_size", pa.int64()),
        ("sha256", pa.string()),
        ("is_text", pa.bool_()),
        ("text", pa.string()),
        ("content", pa.binary()),
    ]
)


@dataclass(frozen=True)
class Paper:
    arxiv_id: str
    title: str
    source_url: str
    paper_index: int
    paper_status: str
    paper_files_written: int
    paper_bytes_downloaded: int
    source_dir: Path


@dataclass
class Stats:
    papers: int = 0
    files: int = 0
    bytes: int = 0
    shards: int = 0
    text_files: int = 0


def load_papers(
    manifest_path: Path,
    source_root: Path,
    limit: int | None,
) -> list[Paper]:
    papers: list[Paper] = []
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("error"):
                continue
            arxiv_id = row["arxiv_id"]
            source_dir = source_root / arxiv_id.replace("/", "_")
            if not source_dir.is_dir():
                print(f"Skipping missing source folder: {source_dir}", file=sys.stderr)
                continue
            papers.append(
                Paper(
                    arxiv_id=arxiv_id,
                    title=row.get("title", ""),
                    source_url=row.get("source_url", ""),
                    paper_index=int(row.get("index") or 0),
                    paper_status=row.get("status", ""),
                    paper_files_written=int(row.get("files_written") or 0),
                    paper_bytes_downloaded=int(row.get("bytes_downloaded") or 0),
                    source_dir=source_dir,
                )
            )
            if limit and len(papers) >= limit:
                break
    return papers


def build_dataset(
    papers: list[Paper],
    writer: Any,
    progress_every: int,
) -> Stats:
    stats = Stats()
    start = time.monotonic()
    for paper in papers:
        stats.papers += 1
        for path in sorted(paper.source_dir.rglob("*")):
            if not path.is_file():
                continue
            row = make_file_row(paper, path)
            writer.write(row)
            stats.files += 1
            stats.bytes += int(row["file_size"])
            stats.text_files += int(bool(row["is_text"]))

        if progress_every and stats.papers % progress_every == 0:
            elapsed = max(time.monotonic() - start, 0.001)
            print(
                f"[{stats.papers}/{len(papers)} papers] "
                f"{stats.files} files, {stats.bytes / 1024**3:.2f} GiB logical, "
                f"{stats.files / elapsed:.1f} files/s",
                file=sys.stderr,
            )
    return stats


def make_file_row(paper: Paper, path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    relative_path = path.relative_to(paper.source_dir).as_posix()
    extension = path.suffix.casefold()
    text = decode_text(content) if extension in TEXT_EXTENSIONS else None
    return {
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "source_url": paper.source_url,
        "paper_index": paper.paper_index,
        "paper_status": paper.paper_status,
        "paper_files_written": paper.paper_files_written,
        "paper_bytes_downloaded": paper.paper_bytes_downloaded,
        "relative_path": relative_path,
        "filename": path.name,
        "extension": extension,
        "file_size": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "is_text": text is not None,
        "text": text,
        "content": content,
    }


def decode_text(content: bytes) -> str | None:
    for encoding in ("utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def write_stats(output_dir: Path, stats: Stats, args: Any) -> None:
    payload = {
        "papers": stats.papers,
        "files": stats.files,
        "text_files": stats.text_files,
        "logical_source_bytes": stats.bytes,
        "parquet_shards": stats.shards,
        "source_dir": args.source_dir,
        "shard_size_mb": args.shard_size_mb,
        "batch_size_mb": args.batch_size_mb,
        "compression": args.compression,
    }
    (output_dir / "dataset_stats.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
