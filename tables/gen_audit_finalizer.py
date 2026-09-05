#!/usr/bin/env python3
"""Slice the deterministic audit finalizer for Appendix C (app:rubric).

Source data: src/reclaim_vllm/audit/audit.py (finalize_audit_row, _verdict).
Output:      paper_latex/prompts/audit_finalizer.py
Run:         python3 paper_latex/tables/gen_audit_finalizer.py

The excerpt is copied verbatim except for one character: U+00A7 is written as
"Section", because the appendix listings run through pdflatex, which rejects
that byte inside a listing. The printed line ranges go in the listing title.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "reprocli_vllm" / "audit" / "audit.py"
OUT = REPO / "paper_latex" / "prompts" / "audit_finalizer.py"


def block(lines: list[str], start: str, stop: str) -> tuple[int, int]:
    first = next(i for i, line in enumerate(lines) if line.startswith(start))
    last = next(i for i, line in enumerate(lines) if i > first and line.startswith(stop))
    while last > first and not lines[last - 1].strip():
        last -= 1
    return first, last


lines = SRC.read_text(encoding="utf-8").splitlines()
a0, a1 = block(lines, "def finalize_audit_row(", "def _normalize_score(")
b0, b1 = block(lines, "def _verdict(", "def _normalize_flags(")
excerpt = "\n".join(lines[a0:a1] + [""] + lines[b0:b1]) + "\n"
OUT.write_text(excerpt.replace("§", "Section "), encoding="utf-8")
print(f"{OUT}: lines {a0 + 1}-{a1} and {b0 + 1}-{b1} of {SRC.relative_to(REPO)}")
