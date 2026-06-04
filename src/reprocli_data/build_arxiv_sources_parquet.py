#!/usr/bin/env python3
"""Build a sharded Parquet dataset from extracted arXiv source folders."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from .dataset_card import write_dataset_card
from .parquet_artifacts import SCHEMA, build_dataset, load_papers, write_stats


DEFAULT_SOURCE_DIR = Path("data/arxiv_sources")
DEFAULT_OUTPUT_DIR = Path("data/parquet_dataset")
DEFAULT_SHARD_SIZE_MB = 512
DEFAULT_BATCH_SIZE_MB = 64


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

    papers = load_papers(source_dir / "manifest.csv", source_dir, args.limit_papers)
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
    write_dataset_card(
        output_dir,
        stats,
        pretty_name=args.pretty_name,
        source_description=args.source_description,
        source_note=args.source_note,
    )
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
    parser.add_argument("--pretty-name", default="NeurIPS 2025 arXiv LaTeX Source Files")
    parser.add_argument("--source-description")
    parser.add_argument("--source-note")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
