#!/usr/bin/env python3
"""Dump the harness's advertised tool schemas and report schema as JSON listings.

Source data (read live from the repository, never hand-copied):
  src/reprocli_repro/tools/run_gpu.py          -> run_gpu_tool(gpus_per_node)
  src/reprocli_repro/tools/workspace_bash.py   -> WORKSPACE_BASH_TOOL
  src/reprocli_repro/report/report.py          -> REPORT_JSON_SCHEMA
  src/reprocli_repro/cluster.py                -> cluster profile gpus_per_node

Writes:
  paper_latex/prompts/tool_run_gpu.json
  paper_latex/prompts/tool_workspace_bash.json
  paper_latex/prompts/report_schema.json

Usage: python3 paper_latex/tables/gen_tool_schemas.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from reprocli_repro.cluster import DEFAULT_CLUSTER, resolve_cluster  # noqa: E402
from reprocli_repro.report.report import REPORT_JSON_SCHEMA  # noqa: E402
from reprocli_repro.tools.run_gpu import run_gpu_tool  # noqa: E402
from reprocli_repro.tools.workspace_bash import WORKSPACE_BASH_TOOL  # noqa: E402

OUT = REPO / "paper_latex" / "prompts"


INLINE_WIDTH = 72


def render(value, indent: int = 0) -> str:
    """Pretty-print JSON, inlining any object/array whose compact form is short.

    Keeps the listing short enough for a page while leaving every key and value
    exactly as the source module defines it.
    """
    pad = " " * indent
    compact = json.dumps(value, ensure_ascii=False, separators=(", ", ": "))
    if len(compact) + indent <= INLINE_WIDTH or not isinstance(value, (dict, list)):
        return compact
    inner = " " * (indent + 2)
    if isinstance(value, dict):
        items = [f"{inner}{json.dumps(k, ensure_ascii=False)}: {render(v, indent + 2)}"
                 for k, v in value.items()]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    items = [f"{inner}{render(v, indent + 2)}" for v in value]
    return "[\n" + ",\n".join(items) + "\n" + pad + "]"


def write(name: str, payload: dict) -> None:
    target = OUT / name
    target.write_text(render(payload) + "\n", encoding="utf-8")
    print(f"wrote {target} ({target.stat().st_size} bytes)")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    gpus_per_node = resolve_cluster(DEFAULT_CLUSTER).gpus_per_node
    write("tool_run_gpu.json", run_gpu_tool(gpus_per_node))
    write("tool_workspace_bash.json", WORKSPACE_BASH_TOOL)
    write("report_schema.json", REPORT_JSON_SCHEMA)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
