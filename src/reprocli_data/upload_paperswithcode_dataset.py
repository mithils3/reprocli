#!/usr/bin/env python3
"""Upload scraped Papers with Code arXiv artifacts to Hugging Face."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from reprocli_vllm.config import DEFAULT_PWC_ARTIFACTS


DEFAULT_REPO_ID = "Mithilss/neurips-2025-paperswithcode-artifacts"


def main() -> int:
    args = parse_args()
    validate_jsonl(args.input)
    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(args.repo_id, repo_type="dataset", exist_ok=True, private=args.private)
    api.upload_file(
        path_or_fileobj=str(args.input),
        path_in_repo=args.path_in_repo,
        repo_id=args.repo_id,
        repo_type="dataset",
        commit_message="Upload Papers with Code arXiv artifact scrape",
    )
    print(f"Uploaded {args.input} to {args.repo_id}/{args.path_in_repo}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_PWC_ARTIFACTS)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--path-in-repo", default="paperswithcode_arxiv_artifacts.jsonl")
    parser.add_argument("--private", action="store_true")
    return parser.parse_args()


def validate_jsonl(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Missing input file: {path}")
    rows = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                json.loads(line)
                rows += 1
    if rows == 0:
        raise SystemExit(f"No JSONL rows in {path}")
    print(f"Validated {rows} row(s) from {path}")


if __name__ == "__main__":
    raise SystemExit(main())
