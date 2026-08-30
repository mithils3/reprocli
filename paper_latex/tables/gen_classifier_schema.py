"""Dump the Stage-I classifier's strict response format for the appendix listing.

Source data: src/reprocli_vllm/schema/output.py (FINAL_RESPONSE_FORMAT), the
json_schema response format the classifier's final tools-off request is
constrained to.

Usage (from the repository root):

    PYTHONPATH=src python3 paper_latex/tables/gen_classifier_schema.py

Writes: paper_latex/prompts/classifier_schema.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reprocli_vllm.schema.output import FINAL_RESPONSE_FORMAT

OUT = Path(__file__).resolve().parent.parent / "prompts" / "classifier_schema.json"


INLINE_WIDTH = 74


def render(value: Any, indent: int = 0) -> str:
    """Same JSON, one key per line, short objects and scalar arrays inlined."""
    pad = "  " * indent
    inner = "  " * (indent + 1)
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = [f"{inner}{json.dumps(k)}: {render(v, indent + 1)}" for k, v in value.items()]
        flat = json.dumps(value)
        if len(pad) + len(flat) <= INLINE_WIDTH and "\n" not in flat:
            return flat
        return "{\n" + ",\n".join(items) + f"\n{pad}}}"
    if isinstance(value, list):
        if all(not isinstance(item, (dict, list)) for item in value):
            return json.dumps(value)
        items = [f"{inner}{render(item, indent + 1)}" for item in value]
        return "[\n" + ",\n".join(items) + f"\n{pad}]"
    return json.dumps(value)


def main() -> None:
    text = render(FINAL_RESPONSE_FORMAT) + "\n"
    assert json.loads(text) == FINAL_RESPONSE_FORMAT
    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
