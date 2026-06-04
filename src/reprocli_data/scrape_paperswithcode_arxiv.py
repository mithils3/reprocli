#!/usr/bin/env python3
"""Scrape Papers with Code artifact metadata for arXiv IDs in the source dataset."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from reprocli_vllm.config import ARXIV_SOURCE_DATASET, DEFAULT_PWC_ARTIFACTS


PWC_API = "https://paperswithcode.co/api/v1/papers/arxiv"


def main() -> int:
    args = parse_args()
    ids = arxiv_ids(args.dataset)
    done = read_done(args.output) if args.resume else set()
    pending = [arxiv_id for arxiv_id in ids if arxiv_id not in done]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"Scraping {len(pending)} pending id(s) of {len(ids)} total", file=sys.stderr)
    with args.output.open("a" if args.resume else "w", encoding="utf-8") as handle:
        for index, arxiv_id in enumerate(pending, 1):
            row = fetch_pwc(arxiv_id, args.timeout)
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
            print(progress_line(index, len(pending), row), file=sys.stderr)
            if args.sleep_seconds:
                time.sleep(args.sleep_seconds)
    summarize(args.output)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=ARXIV_SOURCE_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_PWC_ARTIFACTS)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.25)
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def arxiv_ids(dataset_name: str) -> list[str]:
    from datasets import load_dataset

    dataset = load_dataset(dataset_name, split="train")
    seen = set()
    ids = []
    for row in dataset:
        arxiv_id = str(row["arxiv_id"])
        if arxiv_id not in seen:
            ids.append(arxiv_id)
            seen.add(arxiv_id)
    return ids


def read_done(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                done.add(json.loads(line).get("arxiv_id"))
    return {str(item) for item in done if item}


def fetch_pwc(arxiv_id: str, timeout: float) -> dict[str, Any]:
    url = f"{PWC_API}/{arxiv_id}?include_resources=true"
    command = ["curl", "-L", "-sS", "--max-time", str(timeout), "-w", "\n%{http_code}", url]
    completed = subprocess.run(command, capture_output=True, check=False, text=True)
    body, _, status_text = completed.stdout.rpartition("\n")
    status = int(status_text) if status_text.isdigit() else 0
    base = {"arxiv_id": arxiv_id, "pwc_url": url, "status": status}
    if completed.returncode != 0:
        return {**base, "found": False, "error": completed.stderr.strip()}
    if status == 404:
        return {**base, "found": False}
    if not 200 <= status < 300:
        return {**base, "found": False, "error": body[:500]}
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {**base, "found": False, "error": body[:500]}
    return {**base, **artifact_row(data)}


def artifact_row(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "found": True,
        "pwc_id": data.get("id"),
        "title": data.get("title"),
        "url_abs": data.get("url_abs"),
        "repositories": repo_rows(data.get("repositories") or []),
        "project_pages": page_rows(data.get("project_pages") or []),
        "hf_models": data.get("hf_models") or [],
        "hf_datasets": data.get("hf_datasets") or [],
        "hf_spaces": data.get("hf_spaces") or [],
    }


def repo_rows(repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "url": repo.get("url"),
            "owner": repo.get("owner"),
            "name": repo.get("name"),
            "stars": repo.get("num_stars"),
            "is_official": repo.get("is_official"),
            "source": repo.get("source"),
        }
        for repo in repos
    ]


def page_rows(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "url": page.get("url"),
            "is_official": page.get("is_official"),
        }
        for page in pages
    ]


def progress_line(index: int, total: int, row: dict[str, Any]) -> str:
    repos = len(row.get("repositories") or [])
    hf = sum(len(row.get(key) or []) for key in ("hf_models", "hf_datasets", "hf_spaces"))
    return f"[{index}/{total}] {row['arxiv_id']} status={row['status']} repos={repos} hf={hf}"


def summarize(path: Path) -> None:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    found = [row for row in rows if row.get("found")]
    repos = sum(bool(row.get("repositories")) for row in found)
    hf = sum(any(row.get(key) for key in ("hf_models", "hf_datasets", "hf_spaces")) for row in found)
    print(f"Wrote {len(rows)} rows to {path}", file=sys.stderr)
    print(f"Found {len(found)} PWC pages; repos={repos}; hf_artifacts={hf}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
