---
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

- Papers: 3,414
- File rows: 123,952
- Text rows: 45,808
- Logical source bytes: 27,011,690,085
- Parquet shards: 49

## Usage

```python
from datasets import load_dataset

ds = load_dataset("parquet", data_files="data/train-*.parquet", split="train")
```

## Notes

Licensing for arXiv source submissions varies by paper. Check the corresponding
arXiv record and files for each paper before redistribution or reuse.
