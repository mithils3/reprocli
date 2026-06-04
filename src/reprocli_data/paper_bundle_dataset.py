from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from .parquet_artifacts import TEXT_EXTENSIONS, decode_text


FILE_STRUCT = pa.struct(
    [
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

TEX_STRUCT = pa.struct(
    [
        ("relative_path", pa.string()),
        ("filename", pa.string()),
        ("file_size", pa.int64()),
        ("sha256", pa.string()),
        ("text", pa.string()),
    ]
)

SCHEMA = pa.schema(
    [
        ("arxiv_id", pa.string()),
        ("title", pa.string()),
        ("paper_source_url", pa.string()),
        ("paper_status", pa.string()),
        ("paper_tex_files", pa.list_(TEX_STRUCT)),
        ("paper_tex_text", pa.string()),
        ("supplement_source_url", pa.string()),
        ("supplement_status", pa.string()),
        ("supplement_files", pa.list_(FILE_STRUCT)),
    ]
)


@dataclass(frozen=True)
class ManifestRow:
    arxiv_id: str
    title: str
    source_url: str
    status: str
    output_path: str
    error: str


@dataclass
class Stats:
    papers: int = 0
    papers_with_tex: int = 0
    papers_with_supplement: int = 0
    tex_files: int = 0
    supplement_files: int = 0
    bytes: int = 0
    shards: int = 0


class ShardedWriter:
    def __init__(self, output_data_dir: Path, shard_bytes: int, compression: str) -> None:
        self.output_data_dir = output_data_dir
        self.shard_bytes = shard_bytes
        self.compression = compression
        self.shard_index = -1
        self.shard_logical_bytes = 0
        self.writer: pq.ParquetWriter | None = None

    def write(self, row: dict[str, Any], logical_bytes: int) -> None:
        if self.writer is None or self.shard_logical_bytes >= self.shard_bytes:
            self._open_next_shard()
        assert self.writer is not None
        self.writer.write_table(pa.Table.from_pylist([row], schema=SCHEMA))
        self.shard_logical_bytes += logical_bytes

    def close(self) -> int:
        if self.writer is not None:
            self.writer.close()
            self.writer = None
        return self.shard_index + 1

    def _open_next_shard(self) -> None:
        if self.writer is not None:
            self.writer.close()
        self.shard_index += 1
        self.shard_logical_bytes = 0
        path = self.output_data_dir / f"train-{self.shard_index:05d}.parquet"
        self.writer = pq.ParquetWriter(path, SCHEMA, compression=self.compression)


def load_manifest(path: Path) -> dict[str, ManifestRow]:
    rows: dict[str, ManifestRow] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            arxiv_id = row.get("arxiv_id") or ""
            if not arxiv_id:
                continue
            rows[arxiv_id] = ManifestRow(
                arxiv_id=arxiv_id,
                title=row.get("title") or "",
                source_url=row.get("source_url") or "",
                status=row.get("status") or "",
                output_path=row.get("output_path") or "",
                error=row.get("error") or "",
            )
    return rows


def build_dataset(
    arxiv_manifest: Path,
    supplement_manifest: Path,
    output_dir: Path,
    shard_size_mb: int,
    compression: str,
    overwrite: bool,
) -> Stats:
    if output_dir.exists():
        if not overwrite:
            raise SystemExit(f"{output_dir} already exists. Pass --overwrite to replace it.")
        shutil.rmtree(output_dir)
    output_data_dir = output_dir / "data"
    output_data_dir.mkdir(parents=True, exist_ok=True)

    arxiv_rows = load_manifest(arxiv_manifest)
    supplement_rows = load_manifest(supplement_manifest)
    writer = ShardedWriter(output_data_dir, shard_size_mb * 1024 * 1024, compression)
    stats = Stats()
    for arxiv_id in sorted(arxiv_rows):
        row, logical_bytes = make_row(arxiv_rows[arxiv_id], supplement_rows.get(arxiv_id))
        writer.write(row, logical_bytes)
        update_stats(stats, row, logical_bytes)
        if stats.papers % 100 == 0:
            print(f"[{stats.papers}/{len(arxiv_rows)}] bundled papers", file=sys.stderr)
    stats.shards = writer.close()
    write_readme(output_dir, stats)
    write_stats(output_dir, stats, arxiv_manifest, supplement_manifest)
    return stats


def make_row(arxiv: ManifestRow, supplement: ManifestRow | None) -> tuple[dict[str, Any], int]:
    paper_tex = tex_files(Path(arxiv.output_path))
    supplement_files = artifact_files(Path(supplement.output_path)) if supplement else []
    row = {
        "arxiv_id": arxiv.arxiv_id,
        "title": arxiv.title,
        "paper_source_url": arxiv.source_url,
        "paper_status": arxiv.status,
        "paper_tex_files": paper_tex,
        "paper_tex_text": join_tex(paper_tex),
        "supplement_source_url": supplement.source_url if supplement else "",
        "supplement_status": supplement.status if supplement else "missing",
        "supplement_files": supplement_files,
    }
    logical_bytes = sum(item["file_size"] for item in paper_tex + supplement_files)
    return row, logical_bytes


def tex_files(root: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.tex")) if root.is_dir() else []:
        content = path.read_bytes()
        text = decode_text(content) or ""
        files.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "filename": path.name,
                "file_size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "text": text,
            }
        )
    return files


def artifact_files(root: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")) if root.is_dir() else []:
        if not path.is_file():
            continue
        content = path.read_bytes()
        extension = path.suffix.casefold()
        text = decode_text(content) if extension in TEXT_EXTENSIONS else None
        files.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "filename": path.name,
                "extension": extension,
                "file_size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "is_text": text is not None,
                "text": text,
                "content": content,
            }
        )
    return files


def join_tex(files: list[dict[str, Any]]) -> str:
    chunks = []
    for item in files:
        chunks.append(f"% FILE: {item['relative_path']}\n{item['text']}")
    return "\n\n".join(chunks)


def update_stats(stats: Stats, row: dict[str, Any], logical_bytes: int) -> None:
    stats.papers += 1
    stats.papers_with_tex += int(bool(row["paper_tex_files"]))
    stats.papers_with_supplement += int(bool(row["supplement_files"]))
    stats.tex_files += len(row["paper_tex_files"])
    stats.supplement_files += len(row["supplement_files"])
    stats.bytes += logical_bytes


def write_readme(output_dir: Path, stats: Stats) -> None:
    (output_dir / "README.md").write_text(
        f"""---
license: other
language:
- en
pretty_name: NeurIPS 2025 Paper Sources and OpenReview Supplements
tags:
- arxiv
- openreview
- neurips
- parquet
- scholarly-documents
size_categories:
- 1K<n<10K
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*.parquet
---

# NeurIPS 2025 Paper Sources and OpenReview Supplements

One row per arXiv paper. Each row groups decoded paper `.tex` files with the
matched OpenReview supplementary material files.

## Snapshot

- Papers: {stats.papers:,}
- Papers with `.tex`: {stats.papers_with_tex:,}
- Papers with supplements: {stats.papers_with_supplement:,}
- Paper `.tex` files: {stats.tex_files:,}
- Supplement files: {stats.supplement_files:,}
- Logical bytes: {stats.bytes:,}
- Parquet shards: {stats.shards:,}

## Notes

Licensing varies by paper and supplementary archive. Check the arXiv record,
OpenReview page, and included files before redistribution or reuse.
""",
        encoding="utf-8",
    )


def write_stats(output_dir: Path, stats: Stats, arxiv_manifest: Path, supplement_manifest: Path) -> None:
    payload = stats.__dict__ | {
        "arxiv_manifest": str(arxiv_manifest),
        "supplement_manifest": str(supplement_manifest),
    }
    (output_dir / "dataset_stats.json").write_text(json.dumps(payload, indent=2) + "\n")
