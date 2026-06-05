from __future__ import annotations

import sys

from .papers import Paper

BUNDLE_REQUIRED_COLUMNS = frozenset(
    {
        "arxiv_id",
        "paper_tex_text",
        "paper_tex_files",
        "supplement_status",
        "supplement_files",
    }
)


def load_bundle_papers(dataset_name: str) -> list[Paper]:
    from datasets import load_dataset

    dataset = load_dataset(dataset_name, split="train")
    validate_bundle_columns(dataset_name, dataset)

    papers = []
    seen: set[str] = set()
    for row in dataset:
        arxiv_id = str(row["arxiv_id"])
        if not arxiv_id or arxiv_id in seen:
            continue
        seen.add(arxiv_id)
        papers.append(
            Paper(
                arxiv_id=arxiv_id,
                title=str(row.get("title") or ""),
                source_url=str(row.get("paper_source_url") or ""),
                tex_files=bundle_tex_files(row.get("paper_tex_files")),
                paper_tex_text=str(row.get("paper_tex_text") or ""),
                supplement_source_url=str(row.get("supplement_source_url") or ""),
                supplement_status=str(row.get("supplement_status") or ""),
                supplement_files=as_dicts(row.get("supplement_files")),
            )
        )

    print(f"Loaded {len(papers)} bundled papers from {dataset_name}", file=sys.stderr)
    return papers


def validate_bundle_columns(dataset_name: str, dataset) -> None:
    columns = set(getattr(dataset, "column_names", None) or [])
    missing = sorted(BUNDLE_REQUIRED_COLUMNS - columns)
    if missing:
        raise ValueError(
            f"{dataset_name} is missing required paper-bundle column(s): "
            f"{', '.join(missing)}"
        )


def bundle_tex_files(value: object) -> dict[str, str]:
    files = {}
    for item in as_dicts(value):
        path = str(item.get("relative_path") or item.get("filename") or "")
        text = str(item.get("text") or "")
        if path and text:
            files[path] = text
    return files


def as_dicts(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
