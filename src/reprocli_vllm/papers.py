from __future__ import annotations

import sys
from dataclasses import dataclass, field

from .config import TEX_EXTENSION
from .supplements import supplement_text


@dataclass
class Paper:
    arxiv_id: str
    title: str = ""
    source_url: str = ""
    tex_files: dict[str, str] = field(default_factory=dict)
    paper_tex_text: str = ""
    supplement_source_url: str = ""
    supplement_status: str = ""
    supplement_files: list[dict] = field(default_factory=list)

    def text(self) -> str:
        header = [
            f"arxiv_id: {self.arxiv_id}",
            f"title: {self.title}",
            f"source_url: {self.source_url}",
        ]
        chunks = []
        supplement = supplement_text(
            self.supplement_status,
            self.supplement_source_url,
            self.supplement_files,
        )
        if supplement:
            chunks.append(supplement)
        paper_text = self.paper_tex_text or joined_tex_sections(self.tex_files)
        if paper_text:
            chunks.append("PAPER_LATEX:\n" + paper_text)
        return "\n".join(header) + "\n\n" + "\n\n".join(chunks)


def load_papers(dataset_name: str) -> list[Paper]:
    from datasets import load_dataset

    dataset = load_dataset(dataset_name, split="train")

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


def joined_tex_sections(tex_files: dict[str, str]) -> str:
    return "\n\n".join(
        f"### {path}\n{content}" for path, content in sorted(tex_files.items())
    )
