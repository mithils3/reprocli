from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .config import PLACEHOLDER
from .openai_batch import load_jsonl, read_batch_registry
from .papers import Paper


def valid_processed_ids(output_paths: list[Path]) -> set[str]:
    ids = set()
    for path in output_paths:
        for row in load_jsonl(path):
            custom_id = row.get("custom_id")
            if custom_id and PLACEHOLDER not in json.dumps(row, ensure_ascii=False):
                ids.add(str(custom_id))
    return ids


def pending_ids(registry_path: Path) -> set[str]:
    ids = set()
    for record in read_batch_registry(registry_path):
        ids.update(str(custom_id) for custom_id in record.get("custom_ids") or [])
    return ids


def select_next_papers(
    papers: list[Paper],
    *,
    limit: int | None,
    skip_ids: set[str],
) -> list[Paper]:
    selected = [paper for paper in papers if paper.arxiv_id not in skip_ids]
    return selected[:limit] if limit else selected


def print_id_progress(
    *,
    processed: set[str],
    pending: set[str],
    submitting: list[Paper],
    total: int,
) -> None:
    print(f"Processed arXiv IDs {len(processed)}/{total}: {format_ids(processed)}", file=sys.stderr)
    print(f"Pending arXiv IDs {len(pending)}/{total}: {format_ids(pending)}", file=sys.stderr)
    print(
        f"Next arXiv IDs {len(submitting)}: {format_ids([paper.arxiv_id for paper in submitting])}",
        file=sys.stderr,
    )


def token_usage_fields(row: dict[str, Any]) -> dict[str, int]:
    body = row.get("response") or row.get("batch_response", {}).get("body") or {}
    usage = body.get("usage") or {}
    input_details = usage.get("input_tokens_details") or {}
    output_details = usage.get("output_tokens_details") or {}
    return {
        "input_tokens": int(usage.get("input_tokens") or 0),
        "cached_input_tokens": int(input_details.get("cached_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "reasoning_output_tokens": int(output_details.get("reasoning_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
    }


def print_token_usage(rows: list[dict[str, Any]]) -> None:
    totals = token_usage_totals(rows)
    if not totals["total_tokens"]:
        return
    print(
        "Token usage: "
        f"input={totals['input_tokens']} "
        f"cached_input={totals['cached_input_tokens']} "
        f"output={totals['output_tokens']} "
        f"reasoning_output={totals['reasoning_output_tokens']} "
        f"total={totals['total_tokens']}",
        file=sys.stderr,
    )


def token_usage_totals(rows: list[dict[str, Any]]) -> dict[str, int]:
    totals = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
        "total_tokens": 0,
    }
    for row in rows:
        for key, value in token_usage_fields(row).items():
            totals[key] += value
    return totals


def merge_rows_by_id(existing_rows: list[dict[str, Any]], new_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    order = []
    for row in [*existing_rows, *new_rows]:
        custom_id = row.get("custom_id")
        if not custom_id:
            continue
        if custom_id not in merged:
            order.append(custom_id)
        merged[custom_id] = row
    return [merged[custom_id] for custom_id in order]


def format_ids(ids: set[str] | list[str], *, max_items: int = 12) -> str:
    ordered = sorted(ids) if isinstance(ids, set) else ids
    shown = ordered[:max_items]
    suffix = f" ... +{len(ordered) - max_items} more" if len(ordered) > max_items else ""
    return ", ".join(shown) + suffix if shown else "-"
