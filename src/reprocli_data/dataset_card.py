from __future__ import annotations

from pathlib import Path

from .parquet_artifacts import Stats


def write_dataset_card(
    output_dir: Path,
    stats: Stats,
    pretty_name: str = "NeurIPS 2025 arXiv LaTeX Source Files",
    source_description: str | None = None,
    source_note: str | None = None,
) -> None:
    description = source_description or (
        "This dataset contains file-level Parquet rows built from extracted raw arXiv\n"
        "source packages for papers mapped from the NeurIPS 2025 proceedings to arXiv\n"
        "records."
    )
    note = source_note or (
        "Licensing for arXiv source submissions varies by paper. Check the corresponding\n"
        "arXiv record and files for each paper before redistribution or reuse."
    )
    readme = output_dir / "README.md"
    readme.write_text(
        f"""---
license: other
language:
- en
pretty_name: {pretty_name}
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

# {pretty_name}

{description}

Each row is one file from one paper artifact package. Use `arxiv_id` to group
files back into papers.

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

{note}
""",
        encoding="utf-8",
    )
