from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .config import DEFAULT_PWC_ARTIFACTS, TEX_EXTENSION
from .supplements import supplement_text


@dataclass
class ArtifactMetadata:
    source: str
    match_key: str
    title: str = ""
    arxiv_id: str = ""
    github_links: list[str] = field(default_factory=list)
    project_pages: list[str] = field(default_factory=list)
    hf_models: list[str] = field(default_factory=list)
    hf_datasets: list[str] = field(default_factory=list)
    hf_spaces: list[str] = field(default_factory=list)

    def has_artifacts(self) -> bool:
        return any(
            (
                self.github_links,
                self.project_pages,
                self.hf_models,
                self.hf_datasets,
                self.hf_spaces,
            )
        )

    def text(self) -> str:
        lines = [
            "SUPPLEMENTAL_NEURIPS2025_ARTIFACTS:",
            f"source: {self.source}",
            f"match_key: {self.match_key}",
        ]
        add_lines(lines, "github_links", self.github_links)
        add_lines(lines, "project_pages", self.project_pages)
        add_lines(lines, "huggingface_models", hf_urls("model", self.hf_models))
        add_lines(lines, "huggingface_datasets", hf_urls("datasets", self.hf_datasets))
        add_lines(lines, "huggingface_spaces", hf_urls("spaces", self.hf_spaces))
        return "\n".join(lines)


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
    artifacts: ArtifactMetadata | None = None

    def text(self) -> str:
        header = [
            f"arxiv_id: {self.arxiv_id}",
            f"title: {self.title}",
            f"source_url: {self.source_url}",
        ]
        if self.artifacts and self.artifacts.has_artifacts():
            header.extend(["", self.artifacts.text()])
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


def load_papers(
    dataset_name: str,
    pwc_artifacts_path: Path | None = DEFAULT_PWC_ARTIFACTS,
) -> list[Paper]:
    from datasets import load_dataset

    dataset = load_dataset(dataset_name, split="train")
    artifacts = load_pwc_artifact_index(pwc_artifacts_path)

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

    attached = attach_artifacts(papers.values(), artifacts)
    print(f"Loaded {len(papers)} papers from {dataset_name}", file=sys.stderr)
    if pwc_artifacts_path:
        print(f"Attached Papers With Code candidates to {attached} paper(s)", file=sys.stderr)
    return list(papers.values())


def load_pwc_artifact_index(path: Path | None) -> dict[str, ArtifactMetadata]:
    if not path or not path.exists():
        return {}
    by_arxiv: dict[str, ArtifactMetadata] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            metadata = pwc_artifact_metadata(path, json.loads(line))
            if metadata.has_artifacts():
                by_arxiv[metadata.arxiv_id] = metadata
    print(f"Loaded {len(by_arxiv)} artifact-bearing rows from {path}", file=sys.stderr)
    return by_arxiv


def pwc_artifact_metadata(path: Path, row: dict) -> ArtifactMetadata:
    return ArtifactMetadata(
        source=str(path),
        match_key="arxiv_id",
        title=str(row.get("title") or ""),
        arxiv_id=str(row.get("arxiv_id") or ""),
        github_links=repo_urls(row.get("repositories") or []),
        project_pages=urls_from_rows(row.get("project_pages") or []),
        hf_models=as_list(row.get("hf_models")),
        hf_datasets=as_list(row.get("hf_datasets")),
        hf_spaces=as_list(row.get("hf_spaces")),
    )


def attach_artifacts(
    papers: Iterable[Paper],
    artifacts: dict[str, ArtifactMetadata],
) -> int:
    attached = 0
    for paper in papers:
        metadata = artifacts.get(paper.arxiv_id)
        if metadata is not None:
            paper.artifacts = metadata
            attached += 1
    return attached


def joined_tex_sections(tex_files: dict[str, str]) -> str:
    return "\n\n".join(
        f"### {path}\n{content}" for path, content in sorted(tex_files.items())
    )


def add_lines(lines: list[str], label: str, values: list[str]) -> None:
    if values:
        lines.append(f"{label}:")
        lines.extend(f"- {value}" for value in values)


def hf_urls(kind: str, ids: list[str]) -> list[str]:
    if kind == "model":
        return [f"https://huggingface.co/{repo_id}" for repo_id in ids]
    return [f"https://huggingface.co/{kind}/{repo_id}" for repo_id in ids]


def as_list(value: object) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def repo_urls(repos: list[object]) -> list[str]:
    urls = []
    for repo in repos:
        if isinstance(repo, dict) and repo.get("url"):
            urls.append(str(repo["url"]))
        elif repo:
            urls.append(str(repo))
    return urls


def urls_from_rows(rows: list[object]) -> list[str]:
    urls = []
    for row in rows:
        if isinstance(row, dict) and row.get("url"):
            urls.append(str(row["url"]))
        elif row:
            urls.append(str(row))
    return urls
