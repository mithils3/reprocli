"""Carve the eval-100 benchmark and a disjoint dev-15 split from the audit pool.

Source: ``outputs/v5/audit_pool_extracted.jsonl`` (the 200-row band-selected
audit pool from ``audit/select_pool.py``). The human audit lives in the
verify-app Supabase ``verifications`` table; papers a reviewer marked
``disagree`` on any artifact signal are dropped before selection.

Splits (disjoint partition):
  * eval-100  -- the frozen benchmark: tier-balanced, band-stratified,
                 cheapest-first (the documented ``select_pool --total 100``).
  * dev-15    -- 5 Easy / 5 Medium / 5 Hard, cheapest-first, drawn ONLY from
                 papers NOT in the eval-100, so dev never contaminates eval.

Usage::

    SUPABASE_SERVICE_KEY=... PYTHONPATH=src python tools/build_eval_dev_splits.py

Writes ``audit_pool_eval100_extracted.jsonl`` and
``audit_pool_dev15_extracted.jsonl`` next to the source pool, each row tagged
with a ``split`` field, plus prints the composition.
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any

from reprocli_vllm.audit.h100 import h100_band
from reprocli_vllm.audit.select_pool import (
    BAND_ORDER,
    EVAL_TIERS,
    audited_h100_hours,
    eligible,
    iter_jsonl,
    select_pool,
)

ROOT = Path(__file__).resolve().parent.parent
POOL = ROOT / "outputs/v5/audit_pool_extracted.jsonl"
EVAL_OUT = ROOT / "outputs/v5/audit_pool_eval100_extracted.jsonl"
DEV_OUT = ROOT / "outputs/v5/audit_pool_dev15_extracted.jsonl"
SUMMARY_OUT = ROOT / "outputs/v5/audit_pool_splits_summary.json"

SUPABASE_URL = "https://rjnkpoxwdslkgxjliakq.supabase.co"
SIGNAL_FIELDS = (
    "code_verdict",
    "dataset_verdict",
    "weights_verdict",
    "dataset_standard_verdict",
)
EVAL_TOTAL = 100
DEV_PER_TIER = 5
# Known human-rejected ids (any reviewer 'disagree' on an artifact signal), used
# as a fallback when SUPABASE_SERVICE_KEY is unset so the build stays reproducible.
FALLBACK_REJECTED = {
    "2410.15392",
    "2504.15785",
    "2505.24749",
    "2507.03340",
    "2507.06363",
    "2510.13462",
}


def fetch_human_rejected() -> set[str]:
    """Paper ids a reviewer marked 'disagree' on any artifact signal."""
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not key:
        print("  ! SUPABASE_SERVICE_KEY unset; using FALLBACK_REJECTED")
        return set(FALLBACK_REJECTED)
    cols = ",".join(("paper_id", *SIGNAL_FIELDS))
    url = f"{SUPABASE_URL}/rest/v1/verifications?select={cols}&limit=1000"
    req = urllib.request.Request(
        url, headers={"apikey": key, "Authorization": f"Bearer {key}"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        rows = json.loads(resp.read().decode("utf-8"))
    rejected = {
        r["paper_id"]
        for r in rows
        if any(r.get(f) == "disagree" for f in SIGNAL_FIELDS)
    }
    print(f"  fetched {len(rows)} verifications; {len(rejected)} human-rejected")
    return rejected


def enrich(row: dict[str, Any]) -> dict[str, Any]:
    """Recompute the selection fields the same way select_pool does."""
    row = dict(row)
    hours, adjudicated = audited_h100_hours(row)
    row["audited_h100_hours"] = hours
    row["h100_hours_adjudicated"] = adjudicated
    row["selection_band"] = h100_band(hours)
    return row


def pick_dev(kept: list[dict[str, Any]], eval_ids: set[str]) -> list[dict[str, Any]]:
    """Cheapest 5 per tier among eligible papers NOT chosen for eval."""
    by_tier: dict[str, list[dict[str, Any]]] = {t: [] for t in EVAL_TIERS}
    for row in kept:
        if row["custom_id"] in eval_ids or not eligible(row):
            continue
        enriched = enrich(row)
        if enriched["tier"] in EVAL_TIERS:
            by_tier[enriched["tier"]].append(enriched)
    dev: list[dict[str, Any]] = []
    for tier in EVAL_TIERS:
        bucket = sorted(by_tier[tier], key=lambda r: (r["audited_h100_hours"], r["custom_id"]))
        if len(bucket) < DEV_PER_TIER:
            raise SystemExit(f"only {len(bucket)} leftover {tier} papers; need {DEV_PER_TIER}")
        dev.extend(bucket[:DEV_PER_TIER])
    return dev


def write_jsonl(path: Path, rows: list[dict[str, Any]], split: str) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps({**row, "split": split}, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} rows -> {path}")


def composition(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"total": len(rows), "tiers": {}}
    for tier in EVAL_TIERS:
        tier_rows = [r for r in rows if r["tier"] == tier]
        out["tiers"][tier] = {
            "selected": len(tier_rows),
            "bands": {b: sum(1 for r in tier_rows if r["selection_band"] == b) for b in BAND_ORDER},
            "h100_hours": round(sum(r["audited_h100_hours"] for r in tier_rows), 1),
        }
    out["total_h100_hours"] = round(sum(r["audited_h100_hours"] for r in rows), 1)
    return out


def print_composition(name: str, rows: list[dict[str, Any]]) -> None:
    comp = composition(rows)
    print(f"\n=== {name}: {comp['total']} papers, {comp['total_h100_hours']} H100-h ===")
    print(f"  {'tier':<7} {'n':>3}  " + "  ".join(f"{b:>7}" for b in BAND_ORDER) + "   H100-h")
    for tier in EVAL_TIERS:
        info = comp["tiers"][tier]
        bands = "  ".join(f"{info['bands'][b]:>7}" for b in BAND_ORDER)
        print(f"  {tier:<7} {info['selected']:>3}  {bands}   {info['h100_hours']:>7}")


def main() -> None:
    rows = list(iter_jsonl(POOL))
    rejected = fetch_human_rejected()
    kept = [r for r in rows if r["custom_id"] not in rejected]
    dropped = sorted(r["custom_id"] for r in rows if r["custom_id"] in rejected)
    print(f"pool={len(rows)}  dropped_human_rejected={len(dropped)} {dropped}  kept={len(kept)}")

    eval_selection = select_pool(kept, EVAL_TOTAL)
    eval_rows = [r for tier in EVAL_TIERS for r in eval_selection[tier]]
    eval_ids = {r["custom_id"] for r in eval_rows}
    dev_rows = pick_dev(kept, eval_ids)
    dev_ids = {r["custom_id"] for r in dev_rows}

    overlap = eval_ids & dev_ids
    if overlap:
        raise SystemExit(f"eval/dev overlap: {sorted(overlap)}")
    if len(eval_rows) != EVAL_TOTAL:
        raise SystemExit(f"eval has {len(eval_rows)} rows, expected {EVAL_TOTAL}")
    if len(dev_rows) != DEV_PER_TIER * len(EVAL_TIERS):
        raise SystemExit(f"dev has {len(dev_rows)} rows, expected {DEV_PER_TIER * len(EVAL_TIERS)}")

    write_jsonl(EVAL_OUT, eval_rows, "eval")
    write_jsonl(DEV_OUT, dev_rows, "dev")
    SUMMARY_OUT.write_text(
        json.dumps(
            {
                "source_pool": str(POOL.relative_to(ROOT)),
                "human_rejected_dropped": dropped,
                "eval100": composition(eval_rows),
                "dev15": composition(dev_rows),
                "dev_ids": sorted(dev_ids),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {SUMMARY_OUT}")
    print_composition("EVAL-100", eval_rows)
    print_composition("DEV-15", dev_rows)
    print(f"\ndev ids: {sorted(dev_ids)}")


if __name__ == "__main__":
    main()
