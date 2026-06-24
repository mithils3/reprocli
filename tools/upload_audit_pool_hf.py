"""Upload the 200-paper audit pool MRE records to a Hugging Face dataset.

The verification run reads these as
hf://datasets/<repo>/audit_pool_extracted.jsonl, so the cluster can pull the
audit pool straight from the Hub instead of a synced local file.

Auth: run `hf auth login` (or set HF_TOKEN) first, then:
    python tools/upload_audit_pool_hf.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FILE = ROOT / "outputs/v5/audit_pool_extracted.jsonl"
DEFAULT_REPO = "Mithilss/neurips-2025-audit-pool"
DEFAULT_PATH_IN_REPO = "audit_pool_extracted.jsonl"


def main() -> int:
    args = parse_args()
    if not args.file.exists():
        raise SystemExit(f"Audit pool file not found: {args.file}")
    n_rows = sum(1 for line in args.file.read_text(encoding="utf-8").splitlines() if line.strip())

    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(repo_id=args.repo, repo_type="dataset", private=args.private, exist_ok=True)
    commit_message = args.commit_message or f"Add audit pool MRE records ({n_rows} papers)"
    api.upload_file(
        path_or_fileobj=str(args.file),
        path_in_repo=args.path_in_repo,
        repo_id=args.repo,
        repo_type="dataset",
        commit_message=commit_message,
    )
    print(f"Uploaded {n_rows} rows to https://huggingface.co/datasets/{args.repo}")
    print(f"Use it with: --mre-records hf://datasets/{args.repo}/{args.path_in_repo}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--path-in-repo", default=DEFAULT_PATH_IN_REPO)
    parser.add_argument("--private", action="store_true")
    parser.add_argument("--commit-message", help="override the HF commit message")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
