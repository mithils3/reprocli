#!/usr/bin/env python3
"""Build a sharded Parquet dataset from extracted arXiv source folders."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


DEFAULT_SOURCE_DIR = Path("data/arxiv_sources")
DEFAULT_OUTPUT_DIR = Path("data/parquet_dataset")
DEFAULT_SHARD_SIZE_MB = 512
DEFAULT_BATCH_SIZE_MB = 64
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


class ShardedParquetWriter:
    def __init__(
        self,
        output_data_dir: Path,
        target_shard_bytes: int,
        batch_bytes: int,
        compression: str,
    ) -> None:
        self.output_data_dir = output_data_dir
        self.target_shard_bytes = target_shard_bytes
        self.batch_bytes = batch_bytes
        self.compression = compression
        self.shard_index = -1
        self.shard_logical_bytes = 0
        self.writer: pq.ParquetWriter | None = None
        self.rows: list[dict[str, Any]] = []
        self.rows_logical_bytes = 0

    def write(self, row: dict[str, Any]) -> None:
        self.rows.append(row)
        self.rows_logical_bytes += int(row["file_size"])
        if self.rows_logical_bytes >= self.batch_bytes:
            self.flush()

    def flush(self) -> None:
        if not self.rows:
            return
        if self.writer is None or self.shard_logical_bytes >= self.target_shard_bytes:
            self._open_next_shard()

        table = pa.Table.from_pylist(self.rows, schema=SCHEMA)
        assert self.writer is not None
        self.writer.write_table(table)
        self.shard_logical_bytes += self.rows_logical_bytes
        self.rows = []
        self.rows_logical_bytes = 0

    def close(self) -> int:
        self.flush()
        if self.writer is not None:
            self.writer.close()
            self.writer = None
        return self.shard_index + 1

    def _open_next_shard(self) -> None:
        if self.writer is not None:
            self.writer.close()
        self.shard_index += 1
        self.shard_logical_bytes = 0
        shard_path = self.output_data_dir / f"train-{self.shard_index:05d}.parquet"
        self.writer = pq.ParquetWriter(
            shard_path,
            SCHEMA,
            compression=self.compression,
            use_dictionary=["arxiv_id", "title", "source_url", "extension", "paper_status"],
        )


def main() -> int:
    args = parse_args()
    source_dir = Path(args.source_dir)
    output_dir = Path(args.output_dir)
    if output_dir.exists():
        if not args.overwrite:
            raise SystemExit(f"{output_dir} already exists. Pass --overwrite to replace it.")
        shutil.rmtree(output_dir)

    manifest_path = source_dir / "manifest.csv"
    papers = load_papers(manifest_path, source_dir, args.limit_papers)
    output_data_dir = output_dir / "data"
    output_data_dir.mkdir(parents=True, exist_ok=True)

    writer = ShardedParquetWriter(
        output_data_dir=output_data_dir,
        target_shard_bytes=args.shard_size_mb * 1024 * 1024,
        batch_bytes=args.batch_size_mb * 1024 * 1024,
        compression=args.compression,
    )
    stats = build_dataset(papers, writer, args.progress_every)
    stats.shards = writer.close()
    write_dataset_card(output_dir, stats)
    write_stats(output_dir, stats, args)

    print(
        f"Wrote {stats.files} file rows from {stats.papers} papers "
        f"to {stats.shards} Parquet shards in {output_dir}",
        file=sys.stderr,
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--shard-size-mb", type=int, default=DEFAULT_SHARD_SIZE_MB)
    parser.add_argument("--batch-size-mb", type=int, default=DEFAULT_BATCH_SIZE_MB)
    parser.add_argument("--compression", default="zstd")
    parser.add_argument("--limit-papers", type=int)
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


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
    writer: ShardedParquetWriter,
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


def write_dataset_card(output_dir: Path, stats: Stats) -> None:
    readme = output_dir / "README.md"
    readme.write_text(
        f"""---
license: other
language:
- en
pretty_name: NeurIPS 2025 arXiv LaTeX Source Files
tags:
- arxiv
- latex
- neurips
- parquet
- scholarly-documents
- source-corpus
size_categories:
- 1K<n<10K
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*.parquet
---

# NeurIPS 2025 arXiv LaTeX Source Files

This dataset contains file-level Parquet rows built from extracted raw arXiv
source packages for papers mapped from the NeurIPS 2025 proceedings to arXiv
records.

Each row is one file from one arXiv source package. Use `arxiv_id` to group files
back into papers.

## Columns

- `arxiv_id`: arXiv identifier for the source package.
- `title`: paper title from the mapping CSV.
- `source_url`: arXiv e-print source URL.
- `paper_index`, `paper_status`, `paper_files_written`,
  `paper_bytes_downloaded`: metadata from the download manifest.
- `relative_path`, `filename`, `extension`, `file_size`, `sha256`: file metadata
  inside the source package.
- `is_text`: whether `text` was decoded for a known text-like extension.
- `text`: decoded text for common LaTeX/source metadata files when available.
- `content`: original file bytes.

## Snapshot

- Papers: {stats.papers:,}
- File rows: {stats.files:,}
- Text rows: {stats.text_files:,}
- Logical source bytes: {stats.bytes:,}
- Parquet shards: {stats.shards:,}

## Usage

```python
from datasets import load_dataset

ds = load_dataset("parquet", data_files="data/train-*.parquet", split="train")
```

## Notes

Licensing for arXiv source submissions varies by paper. Check the corresponding
arXiv record and files for each paper before redistribution or reuse.
""",
        encoding="utf-8",
    )


def write_stats(output_dir: Path, stats: Stats, args: argparse.Namespace) -> None:
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


if __name__ == "__main__":
    raise SystemExit(main())
