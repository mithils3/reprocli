"""Per-run token-usage accumulation for the Supabase sink.

Kept separate so ``supabase_sink.py`` stays focused (and under the file-size
budget). Pure in-memory bookkeeping: feed it each model response's ``usage`` and
each tool call; it yields the ``repro_runs`` aggregate fields and writes the
detailed ``stats.json`` document. No network, no globals.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_KEYS = ("prompt", "completion", "total", "cached", "reasoning")


def usage_fields(usage: Any) -> dict[str, int]:
    """OpenAI / vLLM ``usage`` object -> flat int counts (defensive about shape)."""
    if not isinstance(usage, dict):
        return {k: 0 for k in _KEYS}
    pt = int(usage.get("prompt_tokens") or 0)
    ct = int(usage.get("completion_tokens") or 0)
    tt = int(usage.get("total_tokens") or (pt + ct))
    ptd = usage.get("prompt_tokens_details")
    ctd = usage.get("completion_tokens_details")
    cached = int(ptd.get("cached_tokens") or 0) if isinstance(ptd, dict) else 0
    reasoning = int(ctd.get("reasoning_tokens") or 0) if isinstance(ctd, dict) else 0
    return {"prompt": pt, "completion": ct, "total": tt, "cached": cached, "reasoning": reasoning}


class RunStats:
    """Accumulates token usage + per-round records for a single run."""

    def __init__(self) -> None:
        self.tokens = {k: 0 for k in _KEYS}
        self.rounds: list[dict[str, Any]] = []
        self.tool_calls = 0

    def add_usage(self, round_index: int | None, kind: str | None, usage: Any) -> None:
        f = usage_fields(usage)
        for k in _KEYS:
            self.tokens[k] += f[k]
        self.rounds.append({
            "round_index": round_index, "kind": kind or "round",
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **f,
        })

    def add_tool_call(self) -> None:
        self.tool_calls += 1

    def run_fields(self) -> dict[str, Any]:
        """The aggregate columns patched onto the ``repro_runs`` row."""
        t = self.tokens
        return {
            "prompt_tokens": t["prompt"], "completion_tokens": t["completion"],
            "total_tokens": t["total"], "cached_tokens": t["cached"],
            "reasoning_tokens": t["reasoning"], "tool_calls": self.tool_calls,
        }

    def write_doc(self, path: Path, meta: dict[str, Any]) -> bool:
        """Write the detailed ``stats.json`` (meta + tokens + per-round). True on success."""
        doc = dict(meta)
        doc.update({"tokens": dict(self.tokens), "tool_calls": self.tool_calls, "rounds": self.rounds})
        try:
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
            return True
        except OSError:
            return False
