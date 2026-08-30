#!/usr/bin/env python3
"""Dump one frozen lockfile row as a JSON listing for the dataset-schema appendix.

Source data (read live from the repository, never hand-copied):
  outputs/v6/app_rebuild/eval_100.jsonl   -> the frozen 100-paper eval split

Writes:
  paper_latex/prompts/example_row.json

The row is copied field for field. The only edit is length: the prose fields
listed in TRUNCATED are cut at a word boundary and closed with " ...". The
match_target tuple, the links, the signal values, and every numeric field are
left exactly as the lockfile has them.

Usage: python3 paper_latex/tables/gen_example_row.py [arxiv_id]
Override the lockfile location with RECLAIM_LOCKFILE_DIR.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LOCKFILE_DIR = Path(os.environ.get("RECLAIM_LOCKFILE_DIR", REPO / "outputs" / "v6" / "app_rebuild"))
EVAL = LOCKFILE_DIR / "eval_100.jsonl"
OUT = REPO / "paper_latex" / "prompts" / "example_row.json"

DEFAULT_ID = "2506.20990"  # SharpZO, the running example of Section 3.2

# Field paths cut for length. Everything else is verbatim.
TRUNCATED = (
    ("central_claim",),
    ("claim_evidence",),
    ("mre_config",),
    ("agent_task",),
    ("h100_estimate_basis",),
    ("h100_estimate", "basis"),
    ("signals", "code_available", "evidence"),
    ("signals", "dataset_available", "evidence"),
    ("signals", "weights_available", "evidence"),
    ("signals", "dataset_is_standard", "evidence"),
)
MAX_PROSE = 150
INLINE_WIDTH = 78


def clip(text: str, limit: int = MAX_PROSE) -> str:
    if len(text) <= limit:
        return text
    head = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.")
    return head + " ..."


def truncate(row: dict) -> dict:
    for path in TRUNCATED:
        node = row
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = clip(node[path[-1]])
    return row


def render(value, indent: int = 0) -> str:
    """Pretty-print JSON, inlining any object or array whose compact form is short."""
    pad = " " * indent
    compact = json.dumps(value, ensure_ascii=False, separators=(", ", ": "))
    if len(compact) + indent <= INLINE_WIDTH or not isinstance(value, (dict, list)):
        return compact
    inner = " " * (indent + 2)
    if isinstance(value, dict):
        items = [
            f"{inner}{json.dumps(k, ensure_ascii=False)}: {render(v, indent + 2)}"
            for k, v in value.items()
        ]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    items = [f"{inner}{render(v, indent + 2)}" for v in value]
    return "[\n" + ",\n".join(items) + "\n" + pad + "]"


def main() -> int:
    arxiv_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ID
    rows = [json.loads(line) for line in EVAL.read_text(encoding="utf-8").splitlines() if line.strip()]
    match = [r for r in rows if r["custom_id"] == arxiv_id]
    if not match:
        print(f"no row with custom_id={arxiv_id} in {EVAL}", file=sys.stderr)
        return 1
    row = truncate(match[0])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(row) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, custom_id={arxiv_id})")
    print("match_target:", json.dumps(row["match_target"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
