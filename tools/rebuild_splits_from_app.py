"""Rebuild eval-100 + dev-15 from the verify-app's verdicts ("app-truth").

The source of truth is the data-labeling app, in two layers:
  * model signal VALUES come from ``tools/verify_app/public/papers.json`` -- the
    OpenAI-recheck-updated values the reviewers actually saw in the app (these
    differ from the frozen ``audit_pool_extracted.jsonl`` for the 21 re-checked
    papers); then
  * each value is overridden by the human verdict in the Supabase
    ``verifications`` table: agree -> keep, disagree -> flip, unsure/absent ->
    keep. (Near-always a single reviewer; ties fall back to the model value.)

Score + tier are recomputed from those final values with the canonical scorer
(``reprocli_vllm.schema.output.deterministic_score_and_tier``). Papers whose MRE
requires a paid/closed API (OpenAI / Anthropic / Gemini) are dropped from the
pool before selection. ``select_pool`` then carves eval-100 (34/33/33,
band-stratified, cheapest-first) and ``pick_dev`` carves dev-15 (cheapest 5 per
tier, disjoint from eval). Everything else on each row (match_target, h100_*,
verified_links, claim, ...) is preserved from the audit pool verbatim.

Usage::

    PYTHONPATH=src python tools/rebuild_splits_from_app.py
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any

from reprocli_openai.recheck import write_jsonl as write_jsonl_rows
from reprocli_vllm.audit.h100 import h100_band
from reprocli_vllm.audit.select_pool import (
    BAND_ORDER,
    EVAL_TIERS,
    audited_h100_hours,
    eligible,
    iter_jsonl,
    select_pool,
)
from reprocli_vllm.schema.output import deterministic_score_and_tier

ROOT = Path(__file__).resolve().parent.parent
POOL = ROOT / "outputs/v5/audit_pool_extracted.jsonl"
PAPERS = ROOT / "tools/verify_app/public/papers.json"
OUT_DIR = ROOT / "outputs/v6/app_rebuild"
EVAL_OUT = OUT_DIR / "eval_100.jsonl"
DEV_OUT = OUT_DIR / "dev_split.jsonl"
SUMMARY_OUT = OUT_DIR / "splits_summary.json"

SUPABASE_URL = "https://rjnkpoxwdslkgxjliakq.supabase.co"
# Public anon key (already shipped in tools/verify_app/public/config.js, gated by
# RLS to read-only). Env overrides win if a service/anon key is exported.
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJqbmtw"
    "b3h3ZHNsa2d4amxpYWtxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEwMTQzNTYsImV4cCI6MjA5"
    "NjU5MDM1Nn0.-fVclxUX9I5xnY6QudwHQ51P8PTUjDWF5HjFXHhINdU"
)
SIGNAL_VERDICT = {
    "code_available": "code_verdict",
    "dataset_available": "dataset_verdict",
    "weights_available": "weights_verdict",
    "dataset_is_standard": "dataset_standard_verdict",
}
EVAL_TOTAL = 100
DEV_PER_TIER = 5

# Papers whose MRE itself calls a paid/closed model API -- unreproducible in the
# free harness, so dropped from the pool before selection. Adjudicated from each
# paper's full mre_config + agent_task (not a keyword match): false positives
# like "openai/multiagent-particle-envs" (a GitHub repo) or GPT-2 open weights
# are NOT here. 13 clear + 2 borderline (GPT-4o only for a data-gen sub-step).
PAID_API_DROP = {
    "2502.00757": "BlueAgentBreeder evolves scaffolds via OpenAI+Anthropic API keys",
    "2502.13681": "Repo2Run agent generates the Dockerfile with gpt-4o-2024-05-13",
    "2503.17195": "TreeSynth data generation requires the GPT-4o API",
    "2504.09474": "MigGPT retrieve/migrate run on gpt-3.5 via the OpenAI API",
    "2504.15785": "WALL-E ruleminer.py extracts rules with the GPT-4 API",
    "2505.10819": "PoE-World learns the world model via gpt-4o (~$20/run)",
    "2505.15101": "CaMVo needs 50-100K Claude/GPT-4o/o-series API calls",
    "2505.18943": "MetaMind evaluates ToMBench through the GPT-4 API",
    "2505.20738": "Silencer generates benchmarks via GPT-4o-mini/Claude APIs",
    "2505.21577": "RepoMaster agent runs on GPT-4o + Serper/Jina API keys",
    "2506.21924": "SPAZER zero-shot 3DVG inference runs on the GPT-4o API",
    "2511.09833": "ACT annotates/criticizes CIFAR10 with the GPT-4o API",
    "2602.20296": "SFT-Decomp needs a GPT-4o teacher to decompose the data",
    # borderline: GPT-4o used only for a data-gen sub-step (also huge / no code):
    "2509.24629": "WeSCon generates emotion-transition supervisions with GPT-4o",
    "2512.00762": "Force-recovery queries GPT-4o-Vision for material properties",
}


def fetch_verifications() -> list[dict[str, Any]]:
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY") or ANON_KEY
    cols = "paper_id,reviewer,status," + ",".join(SIGNAL_VERDICT.values())
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        url = f"{SUPABASE_URL}/rest/v1/verifications?select={cols}&limit=1000&offset={offset}"
        req = urllib.request.Request(url, headers={"apikey": key, "Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            batch = json.loads(resp.read().decode("utf-8"))
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return rows


def app_truth_signals(
    papers_signals: dict[str, Any], verifs: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[str]]:
    """papers.json signals with each value overridden by the human verdict."""
    completed = [v for v in verifs if v.get("status") == "completed"] or verifs
    signals = json.loads(json.dumps(papers_signals))  # deep copy
    flipped: list[str] = []
    for name, vfield in SIGNAL_VERDICT.items():
        sig = signals.get(name)
        if not isinstance(sig, dict) or not isinstance(sig.get("value"), bool):
            continue
        model_val = sig["value"]
        votes = []
        for v in completed:
            verdict = v.get(vfield)
            if verdict == "agree":
                votes.append(model_val)
            elif verdict == "disagree":
                votes.append(not model_val)
        if votes:
            t = sum(1 for b in votes if b)
            final = model_val if t * 2 == len(votes) else (t * 2 > len(votes))
        else:
            final = model_val
        if final != model_val:
            flipped.append(name)
            sig["evidence"] = f"[human-verified override -> {final}] " + str(sig.get("evidence") or "")
        sig["value"] = final
    return signals, flipped


def build_app_pool(verifs_by_paper: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], dict]:
    pool = list(iter_jsonl(POOL))
    papers = {p["custom_id"]: p for p in json.loads(PAPERS.read_text(encoding="utf-8"))}
    relabels: list[tuple[str, str, str]] = []
    flips: dict[str, list[str]] = {}
    rebuilt: list[dict[str, Any]] = []
    for row in pool:
        cid = row["custom_id"]
        base_sig = (papers.get(cid) or {}).get("signals") or row.get("signals") or {}
        new_sig, flipped = app_truth_signals(base_sig, verifs_by_paper.get(cid, []))
        row = dict(row)
        row["signals"] = new_sig
        computed = deterministic_score_and_tier(row)
        old_tier = row.get("tier")
        if computed is not None:
            row["score"], row["tier"] = computed
        if flipped:
            flips[cid] = flipped
        if row.get("tier") != old_tier:
            relabels.append((cid, old_tier, row.get("tier")))
        rebuilt.append(row)
    stats = {"relabels": sorted(relabels), "human_flips": flips}
    return rebuilt, stats


def enrich(row: dict[str, Any]) -> dict[str, Any]:
    row = dict(row)
    hours, adjudicated = audited_h100_hours(row)
    row["audited_h100_hours"] = hours
    row["h100_hours_adjudicated"] = adjudicated
    row["selection_band"] = h100_band(hours)
    return row


def pick_dev(kept: list[dict[str, Any]], eval_ids: set[str]) -> list[dict[str, Any]]:
    by_tier: dict[str, list[dict[str, Any]]] = {t: [] for t in EVAL_TIERS}
    for row in kept:
        if row["custom_id"] in eval_ids or not eligible(row):
            continue
        e = enrich(row)
        if e["tier"] in EVAL_TIERS:
            by_tier[e["tier"]].append(e)
    dev: list[dict[str, Any]] = []
    for tier in EVAL_TIERS:
        bucket = sorted(by_tier[tier], key=lambda r: (r["audited_h100_hours"], r["custom_id"]))
        if len(bucket) < DEV_PER_TIER:
            raise SystemExit(f"only {len(bucket)} leftover {tier} papers; need {DEV_PER_TIER}")
        dev.extend(bucket[:DEV_PER_TIER])
    return dev


def write_jsonl(path: Path, rows: list[dict[str, Any]], split: str) -> None:
    count = write_jsonl_rows(path, ({**row, "split": split} for row in rows))
    print(f"Wrote {count} rows -> {path}")


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
    verifs = fetch_verifications()
    by_paper: dict[str, list[dict[str, Any]]] = {}
    for v in verifs:
        by_paper.setdefault(v["paper_id"], []).append(v)
    print(f"fetched {len(verifs)} verifications across {len(by_paper)} papers")

    rebuilt, stats = build_app_pool(by_paper)
    print(f"rebuilt pool={len(rebuilt)}  tier relabels={len(stats['relabels'])}  "
          f"human-flipped papers={len(stats['human_flips'])}")

    kept = [r for r in rebuilt if r["custom_id"] not in PAID_API_DROP]
    dropped_in_pool = sorted(c for c in PAID_API_DROP if c in {r["custom_id"] for r in rebuilt})
    print(f"paid-API dropped from pool: {len(dropped_in_pool)} {dropped_in_pool}")

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
                "label_source": "verify_app (papers.json signals XOR Supabase verdicts)",
                "paid_api_dropped": {c: PAID_API_DROP[c] for c in dropped_in_pool},
                "tier_relabels": stats["relabels"],
                "human_flipped_signals": stats["human_flips"],
                "eval100": composition(eval_rows),
                "dev15": composition(dev_rows),
                "eval_ids": sorted(eval_ids),
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
