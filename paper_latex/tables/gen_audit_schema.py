#!/usr/bin/env python3
"""Dump the auditor's structured output schema for Appendix C (app:rubric).

Source data: src/reprocli_vllm/schema/audit.py (AUDIT_JSON_SCHEMA).
Output:      paper_latex/prompts/audit_schema.json
Run:         python3 paper_latex/tables/gen_audit_schema.py

The dump is the schema object unchanged. Only the layout is chosen here: a
nested object whose own values are all scalars or scalar lists is printed on one
line, so the listing fits the appendix.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "paper_latex" / "prompts" / "audit_schema.json"

sys.path.insert(0, str(REPO / "src"))
from reprocli_vllm.schema.audit import AUDIT_JSON_SCHEMA  # noqa: E402


def leaf(node: dict) -> bool:
    """True when the object holds no nested object, so it fits on one line."""
    return all(
        not isinstance(v, dict)
        and (not isinstance(v, list) or all(not isinstance(i, (dict, list)) for i in v))
        for v in node.values()
    )


def render(node, indent: int = 0) -> str:
    pad, inner = " " * indent, " " * (indent + 2)
    if isinstance(node, dict):
        if leaf(node):
            return json.dumps(node)
        body = ",\n".join(f"{inner}{json.dumps(k)}: {render(v, indent + 2)}" for k, v in node.items())
        return "{\n" + body + "\n" + pad + "}"
    if isinstance(node, list):
        if all(not isinstance(i, (dict, list)) for i in node):
            body = ",\n".join(f"{inner}{json.dumps(i)}" for i in node)
            return "[\n" + body + "\n" + pad + "]"
        body = ",\n".join(f"{inner}{render(i, indent + 2)}" for i in node)
        return "[\n" + body + "\n" + pad + "]"
    return json.dumps(node)


text = render(AUDIT_JSON_SCHEMA) + "\n"
OUT.write_text(text, encoding="utf-8")
print(f"{OUT}: {text.count(chr(10))} lines")
