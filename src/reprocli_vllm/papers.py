from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

from .config import TEX_EXTENSION


@dataclass
class Paper:
    arxiv_id: str
    title: str = ""
    source_url: str = ""
    tex_files: dict[str, str] = field(default_factory=dict)

    def text(self) -> str:
        header = [
            f"arxiv_id: {self.arxiv_id}",
            f"title: {self.title}",
            f"source_url: {self.source_url}",
        ]
        sections = [
            f"### {path}\n{content}"
            for path, content in sorted(self.tex_files.items())
        ]
        return "\n".join(header) + "\n\n" + "\n\n".join(sections)


def load_papers(dataset_name: str, split: str, cache_dir: str | None) -> list[Paper]:
    from datasets import load_dataset

    dataset_kwargs: dict[str, Any] = {"split": split}
    if cache_dir:
        dataset_kwargs["cache_dir"] = cache_dir
    dataset = load_dataset(dataset_name, **dataset_kwargs)

    papers: dict[str, Paper] = {}
    for row in dataset:
        arxiv_id = row["arxiv_id"]
        paper = papers.setdefault(
            arxiv_id,
            Paper(
                arxiv_id=arxiv_id,
                title=row.get("title") or "",
                source_url=row.get("source_url") or "",
            ),
        )
        if row.get("is_text") and row.get("extension") == TEX_EXTENSION and row.get("text"):
            paper.tex_files[row["relative_path"]] = row["text"]

    print(f"Loaded {len(papers)} papers from {dataset_name}", file=sys.stderr)
    return list(papers.values())
