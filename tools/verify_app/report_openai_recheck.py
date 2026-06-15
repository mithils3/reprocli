#!/usr/bin/env python3
"""Report model-vs-GPT-5.5 differences before publishing label-app data."""
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any
from collections.abc import Iterable

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reprocli_openai import recheck  # noqa: E402

BASE_EXTRACTED = REPO / "outputs/v5/audit_pool_extracted.jsonl"
RECHECK_DIR = REPO / "outputs/v5/openai_hard_recheck_gpt55_low"
REPORT = RECHECK_DIR / "comparison_report.md"


def wait_for_recheck(poll_seconds: int) -> None:
    total = len(recheck.hard_no_code_ids(recheck.POOL))
    raw_path = RECHECK_DIR / recheck.RAW_NAME
    while True:
        done = 0
        if raw_path.exists():
            done = sum(
                1
                for body in recheck.raw_rows(raw_path).values()
                if body.get("status") == "completed"
            )
        print(f"recheck progress: {done}/{total}", flush=True)
        if done >= total:
            return
        time.sleep(poll_seconds)


def collect_results(allow_partial: bool) -> Path:
    total = len(recheck.hard_no_code_ids(recheck.POOL))
    raw_path = RECHECK_DIR / recheck.RAW_NAME
    done = sum(
        1
        for body in recheck.raw_rows(raw_path).values()
        if body.get("status") == "completed"
    )
    if done < total and not allow_partial:
        raise SystemExit(f"recheck is incomplete: {done}/{total}")
    if done < total:
        print(f"recheck is incomplete; reporting partial results: {done}/{total}", flush=True)
    recheck.collect(RECHECK_DIR)
    extracted = RECHECK_DIR / "recheck_extracted.jsonl"
    errors = [row for row in recheck.iter_jsonl(extracted) if "error" in row]
    if errors:
        raise SystemExit(f"{len(errors)} recheck rows have extraction errors")
    return extracted


def code_value(row: dict[str, Any]) -> bool | None:
    signal = (row.get("signals") or {}).get("code_available") or {}
    value = signal.get("value")
    return value if isinstance(value, bool) else None


def dist(rows: Iterable[dict[str, Any]], field: str) -> Counter[str]:
    return Counter(str(row.get(field)) for row in rows)


def format_counter(counter: Counter[str]) -> str:
    if not counter:
        return "(none)"
    return ", ".join(f"{key}: {counter[key]}" for key in sorted(counter, key=str))


def transition_label(old: bool | None, new: bool | None) -> str:
    return f"{old}->{new}"


def report(extracted_path: Path) -> str:
    old_rows = {str(row["custom_id"]): row for row in recheck.iter_jsonl(BASE_EXTRACTED)}
    new_rows = {str(row["custom_id"]): row for row in recheck.iter_jsonl(extracted_path)}
    wanted = set(recheck.hard_no_code_ids(recheck.POOL))
    missing = sorted(wanted - set(new_rows))
    ids = sorted(set(old_rows) & set(new_rows))
    transitions: Counter[str] = Counter()
    disagreements: list[tuple[str, bool | None, bool | None, Any, Any, Any, Any]] = []

    for cid in ids:
        old = old_rows[cid]
        new = new_rows[cid]
        old_code = code_value(old)
        new_code = code_value(new)
        transitions[transition_label(old_code, new_code)] += 1
        if old_code != new_code:
            disagreements.append(
                (
                    cid,
                    old_code,
                    new_code,
                    old.get("score"),
                    old.get("tier"),
                    new.get("score"),
                    new.get("tier"),
                )
            )

    merged_rows = []
    for cid, old in old_rows.items():
        merged_rows.append(new_rows.get(cid, old))

    lines = [
        "# GPT-5.5 Recheck Comparison",
        "",
        f"- Compared rows: {len(ids)}",
        f"- Missing recheck rows left unchanged: {len(missing)}"
        + (f" ({', '.join(missing)})" if missing else ""),
        f"- Code-approval disagreements: {len(disagreements)}",
        f"- Code transitions: {format_counter(transitions)}",
        "",
        "## Score Distribution",
        "",
        f"- Prior model on rechecked slice: {format_counter(dist((old_rows[i] for i in ids), 'score'))}",
        f"- GPT-5.5 on rechecked slice: {format_counter(dist(new_rows.values(), 'score'))}",
        f"- Full audit pool after replacing slice: {format_counter(dist(merged_rows, 'score'))}",
        "",
        "## Tier Distribution",
        "",
        f"- Prior model on rechecked slice: {format_counter(dist((old_rows[i] for i in ids), 'tier'))}",
        f"- GPT-5.5 on rechecked slice: {format_counter(dist(new_rows.values(), 'tier'))}",
        f"- Full audit pool after replacing slice: {format_counter(dist(merged_rows, 'tier'))}",
        "",
        "## Code-Approval Disagreements",
        "",
    ]
    if disagreements:
        lines.append("| custom_id | prior code | gpt-5.5 code | prior score/tier | gpt-5.5 score/tier |")
        lines.append("|---|---:|---:|---|---|")
        for cid, old_code, new_code, old_score, old_tier, new_score, new_tier in disagreements:
            lines.append(
                f"| {cid} | {old_code} | {new_code} | "
                f"{old_score} / {old_tier} | {new_score} / {new_tier} |"
            )
    else:
        lines.append("No code-approval disagreements.")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()

    if not args.no_wait:
        wait_for_recheck(args.poll_seconds)
    extracted = collect_results(args.allow_partial)
    text = report(extracted)
    REPORT.write_text(text, encoding="utf-8")
    print(text, flush=True)
    print(f"wrote {REPORT}", flush=True)


if __name__ == "__main__":
    main()
