#!/usr/bin/env python3
"""Real token cost of one run, summed over every recorded model response.

Reads, in order, the first source that holds calls: RUN_DIR/usage.jsonl (one line per
response, written by reprocli_repro live_log), RUN_DIR/stats.json (per-round counts, no
tier), RUN_DIR/mini_trajectory.json (mini-SWE arm, per-step raw responses). Prints
{"input", "cached", "output", "usd", "calls", "tiers", "source"} and exits 2 when no
usage is recorded, so the caller can fall back to its estimate.

input is prompt_tokens, which includes cached tokens (OpenAI and Meta convention).
output is completion_tokens, which already includes reasoning tokens. Each response is
priced at its own service_tier: "flex" gets the flex rate, anything else (default,
standard, missing) gets the standard rate, 2x flex on OpenAI. Meta models have one rate.

Usage: thin_run_cost.py RUN_DIR --model MODEL
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# USD per 1M tokens: (input, cached input, output).
FLEX = {
    "gpt-6.1-sol": (1.00, 0.05, 5.00),
    "gpt-6.1-terra": (0.50, 0.025, 2.50),
    "gpt-6-astra": (5.00, 0.50, 25.00),
}
FLAT = {
    "muse-wonder-1.0": (4.00, 0.20, 20.00),
    "muse-spark-1.2": (1.25, 0.15, 4.25),
    "muse-spark-1.2-contributor": (1.25, 0.15, 4.25),
}
SOURCES = ("usage.jsonl", "stats.json", "mini_trajectory.json")


def rates(model: str, tier: str | None) -> tuple[float, float, float]:
    if model in FLAT:
        return FLAT[model]
    if model in FLEX:
        mult = 1.0 if tier == "flex" else 2.0
        return tuple(x * mult for x in FLEX[model])  # type: ignore[return-value]
    raise KeyError(f"no price for model {model!r}")


def norm(usage: dict | None, tier: str | None) -> tuple[int, int, int, str | None]:
    """(prompt, cached, completion, tier) from one OpenAI/Meta usage object."""
    u = usage or {}
    cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
    return (int(u.get("prompt_tokens") or 0), int(cached),
            int(u.get("completion_tokens") or 0), tier)


def calls_usage_jsonl(path: Path) -> list[tuple[int, int, int, str | None]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            rows.append(norm(rec.get("usage"), rec.get("service_tier")))
    return rows


def calls_stats(path: Path) -> list[tuple[int, int, int, str | None]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return [(int(r.get("prompt") or 0), int(r.get("cached") or 0),
             int(r.get("completion") or 0), None) for r in doc.get("rounds", [])]


def calls_mini(path: Path) -> list[tuple[int, int, int, str | None]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for msg in doc.get("messages", []):
        if msg.get("role") != "assistant":
            continue
        resp = (msg.get("extra") or {}).get("response") or {}
        if resp.get("usage"):
            rows.append(norm(resp["usage"], resp.get("service_tier")))
    return rows


READERS = {"usage.jsonl": calls_usage_jsonl, "stats.json": calls_stats,
           "mini_trajectory.json": calls_mini}


def summarise(run_dir: Path, model: str) -> dict:
    for name in SOURCES:
        path = run_dir / name
        if not path.is_file():
            continue
        calls = READERS[name](path)
        if not calls:
            continue
        tiers: dict[str, int] = {}
        usd = 0.0
        for prompt, cached, completion, tier in calls:
            pin, pcached, pout = rates(model, tier)
            usd += ((prompt - cached) * pin + cached * pcached + completion * pout) / 1e6
            key = tier or "unrecorded"
            tiers[key] = tiers.get(key, 0) + 1
        return {"input": sum(c[0] for c in calls), "cached": sum(c[1] for c in calls),
                "output": sum(c[2] for c in calls), "usd": round(usd, 6),
                "calls": len(calls), "tiers": tiers, "source": name}
    raise LookupError(f"no usage recorded under {run_dir}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--model", required=True)
    args = ap.parse_args()
    try:
        out = summarise(args.run_dir, args.model)
    except LookupError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
