from __future__ import annotations

from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


class ShardedBundleWriter:
    def __init__(
        self,
        output_data_dir: Path,
        target_shard_bytes: int,
        batch_bytes: int,
        batch_rows: int,
        compression: str,
        schema: pa.Schema,
    ) -> None:
        self.output_data_dir = output_data_dir
        self.target_shard_bytes = target_shard_bytes
        self.batch_bytes = batch_bytes
        self.batch_rows = batch_rows
        self.compression = compression
        self.schema = schema
        self.shard_index = -1
        self.shard_logical_bytes = 0
        self.writer: pq.ParquetWriter | None = None
        self.rows: list[dict[str, Any]] = []
        self.rows_logical_bytes = 0

    def write(self, row: dict[str, Any], logical_bytes: int) -> None:
        if (
            self.rows
            and self.shard_logical_bytes
            and self.shard_logical_bytes + self.rows_logical_bytes >= self.target_shard_bytes
        ):
            self.flush()
        self.rows.append(row)
        self.rows_logical_bytes += logical_bytes
        if len(self.rows) >= self.batch_rows or self.rows_logical_bytes >= self.batch_bytes:
            self.flush()

    def flush(self) -> None:
        if not self.rows:
            return
        if (
            self.writer is None
            or self.shard_logical_bytes >= self.target_shard_bytes
            or (
                self.shard_logical_bytes
                and self.shard_logical_bytes + self.rows_logical_bytes > self.target_shard_bytes
            )
        ):
            self._open_next_shard()
        assert self.writer is not None
        self.writer.write_table(pa.Table.from_pylist(self.rows, schema=self.schema))
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
        path = self.output_data_dir / f"train-{self.shard_index:05d}.parquet"
        self.writer = pq.ParquetWriter(path, self.schema, compression=self.compression)
