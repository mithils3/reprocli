#!/usr/bin/env python3
"""Upload a Hugging Face-ready dataset folder."""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_INPUT_DIR = Path("data/paper_bundle_dataset")
DEFAULT_REPO_ID = "Mithilss/neurips-2025-paper-bundles"


def main() -> int:
    args = parse_args()
    upload_dataset_folder(
        input_dir=args.input_dir,
        repo_id=args.repo_id,
        private=args.private,
        commit_message=args.commit_message,
    )
    return 0


def upload_dataset_folder(
    input_dir: Path,
    repo_id: str,
    private: bool,
    commit_message: str,
) -> None:
    validate_dataset_folder(input_dir)
    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True, private=private)
    api.upload_folder(
        folder_path=str(input_dir),
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=commit_message,
    )
    print(f"Uploaded {input_dir} to https://huggingface.co/datasets/{repo_id}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--private", action="store_true")
    parser.add_argument(
        "--commit-message",
        default="Upload NeurIPS 2025 paper bundle dataset",
    )
    return parser.parse_args()


def validate_dataset_folder(path: Path) -> None:
    if not path.is_dir():
        raise SystemExit(f"Missing dataset folder: {path}")
    if not (path / "README.md").is_file():
        raise SystemExit(f"Missing dataset card: {path / 'README.md'}")
    shards = sorted((path / "data").glob("*.parquet"))
    if not shards:
        raise SystemExit(f"No Parquet shards found under {path / 'data'}")
    print(f"Found {len(shards)} Parquet shard(s) under {path / 'data'}")


if __name__ == "__main__":
    raise SystemExit(main())
