"""Select low-confidence extracted rows for requeue and merge rerun outputs.

Usage:
    python -m reprocli_vllm.rerun select --extracted out.jsonl --output ids.txt
    python -m reprocli_vllm.rerun merge --base old.jsonl --update rerun.jsonl \
        --output merged.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

RERUN_STATUSES = ("incomplete", "degraded")
LEGACY_RERUN_WEB_VERIFICATION = ("partial", "unavailable")


def needs_rerun(row: dict[str, Any]) -> bool:
    status = row.get("verification_status")
    if status in RERUN_STATUSES:
        return True
    if status is None:
        # Legacy rows predate the computed status: requeue malformed rows and
        # the model-reported low-confidence buckets.
        if not isinstance(row.get("signals"), dict):
            return True
        if row.get("web_verification") in LEGACY_RERUN_WEB_VERIFICATION:
            return True
    return bool(row.get("h100_arithmetic_mismatch"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def select_rerun_ids(extracted_path: Path) -> list[str]:
    ids = []
    for row in read_jsonl(extracted_path):
        custom_id = str(row.get("custom_id") or "")
        if custom_id and needs_rerun(row) and custom_id not in ids:
            ids.append(custom_id)
    return ids


def merge_extracted(base_path: Path, update_path: Path) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in (*read_jsonl(base_path), *read_jsonl(update_path)):
        custom_id = str(row.get("custom_id") or "")
        if not custom_id:
            continue
        if custom_id in merged:
            row = dict(row)
            row["superseded_run_count"] = (
                int(merged[custom_id].get("superseded_run_count") or 0) + 1
            )
        else:
            order.append(custom_id)
        merged[custom_id] = row
    return [merged[custom_id] for custom_id in order]


def write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            json.dump(row, handle, ensure_ascii=False)
            handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select", help="List arXiv ids that need a rerun.")
    select.add_argument("--extracted", type=Path, required=True)
    select.add_argument("--output", type=Path, required=True)
    merge = commands.add_parser("merge", help="Merge rerun rows over a base file.")
    merge.add_argument("--base", type=Path, required=True)
    merge.add_argument("--update", type=Path, required=True)
    merge.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "select":
        ids = select_rerun_ids(args.extracted)
        write_lines(args.output, ids)
        print(f"Selected {len(ids)} row(s) for rerun -> {args.output}", file=sys.stderr)
        return 0
    rows = merge_extracted(args.base, args.update)
    write_jsonl(args.output, rows)
    print(f"Merged {len(rows)} row(s) -> {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
