from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from .arxiv_source_download import safe_dirname
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


def build_dataset(
    dataset_name: str,
    supplement_dir: Path,
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

    papers = load_arxiv_dataset(dataset_name)
    writer = ShardedWriter(output_data_dir, shard_size_mb * 1024 * 1024, compression)
    stats = Stats()
    for arxiv_id in sorted(papers):
        row, logical_bytes = make_row(papers[arxiv_id], supplement_dir)
        writer.write(row, logical_bytes)
        update_stats(stats, row, logical_bytes)
        if stats.papers % 100 == 0:
            print(f"[{stats.papers}/{len(papers)}] bundled papers", file=sys.stderr)
    stats.shards = writer.close()
    write_readme(output_dir, stats)
    write_stats(output_dir, stats, dataset_name, supplement_dir)
    return stats


def load_arxiv_dataset(dataset_name: str) -> dict[str, dict[str, Any]]:
    from datasets import load_dataset

    papers: dict[str, dict[str, Any]] = {}
    for source_row in load_dataset(dataset_name, split="train"):
        arxiv_id = str(source_row.get("arxiv_id") or "")
        if not arxiv_id:
            continue
        paper = papers.setdefault(arxiv_id, new_paper(source_row, arxiv_id))
        if is_tex_row(source_row):
            paper["paper_tex_files"].append(tex_row(source_row))
    return papers


def new_paper(source_row: dict[str, Any], arxiv_id: str) -> dict[str, Any]:
    return {
        "arxiv_id": arxiv_id,
        "title": str(source_row.get("title") or ""),
        "source_url": str(source_row.get("source_url") or ""),
        "paper_status": str(source_row.get("paper_status") or ""),
        "paper_tex_files": [],
    }


def is_tex_row(row: dict[str, Any]) -> bool:
    extension = str(row.get("extension") or "").casefold()
    filename = str(row.get("filename") or "").casefold()
    return extension == ".tex" or filename.endswith(".tex")


def tex_row(row: dict[str, Any]) -> dict[str, Any]:
    text = row.get("text") or decode_text(row_bytes(row)) or ""
    return {
        "relative_path": str(row.get("relative_path") or ""),
        "filename": str(row.get("filename") or ""),
        "file_size": int(row.get("file_size") or len(text.encode("utf-8"))),
        "sha256": str(row.get("sha256") or hashlib.sha256(text.encode("utf-8")).hexdigest()),
        "text": text,
    }


def make_row(arxiv: dict[str, Any], supplement_dir: Path) -> tuple[dict[str, Any], int]:
    paper_tex = arxiv["paper_tex_files"]
    supplement_root = supplement_dir / safe_dirname(arxiv["arxiv_id"])
    supplement_files = artifact_files(supplement_root)
    row = {
        "arxiv_id": arxiv["arxiv_id"],
        "title": arxiv["title"],
        "paper_source_url": arxiv["source_url"],
        "paper_status": arxiv["paper_status"],
        "paper_tex_files": paper_tex,
        "paper_tex_text": join_tex(paper_tex),
        "supplement_source_url": "",
        "supplement_status": "downloaded" if supplement_files else "missing",
        "supplement_files": supplement_files,
    }
    logical_bytes = sum(item["file_size"] for item in paper_tex + supplement_files)
    return row, logical_bytes


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


def row_bytes(row: dict[str, Any]) -> bytes:
    content = row.get("content") or b""
    if isinstance(content, bytes):
        return content
    if isinstance(content, bytearray):
        return bytes(content)
    return str(content).encode("utf-8")


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


def write_stats(output_dir: Path, stats: Stats, dataset_name: str, supplement_dir: Path) -> None:
    payload = stats.__dict__ | {
        "dataset": dataset_name,
        "supplement_dir": str(supplement_dir),
    }
    (output_dir / "dataset_stats.json").write_text(json.dumps(payload, indent=2) + "\n")
