#!/usr/bin/env python3
"""Plot the audit pool: composition and compute-feasibility by artifact tier.

Reads the selected-pool JSONL emitted by ``python -m reprocli_vllm.audit.select_pool``
and renders two panels:

  (a) pool composition — papers per selection band, grouped by tier;
  (b) feasibility curve — per tier, the fraction of MREs whose audited compute
      fits within a given agent budget, with the benchmark's 4/16/64/192
      H100-hour budgets marked.

Usage::

    python3 tools/plot_audit_pool.py
    python3 tools/plot_audit_pool.py --pool outputs/v5/audit_pool_extracted.jsonl \
        --out notes/figures/audit_pool_tier_hours
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reprocli_openai.recheck import iter_jsonl  # noqa: E402

TIERS = ("Easy", "Medium", "Hard")
TIER_COLORS = {"Easy": "#00795A", "Medium": "#D08700", "Hard": "#C44A00"}
BAND_LABELS = ("0–8", "8–32", "32–96", "96–192")
AGENT_BUDGETS = (4, 16, 64, 192)
ECDF_FLOOR = 0.1  # hours below this (incl. zero) plot at the axis floor


def tier_hours(rows: list[dict], tier: str) -> np.ndarray:
    return np.array(sorted(row["audited_h100_hours"] for row in rows if row["tier"] == tier))


def band_counts(rows: list[dict], tier: str) -> list[int]:
    bands = [row["selection_band"] for row in rows if row["tier"] == tier]
    return [bands.count(label.replace("–", "-")) for label in BAND_LABELS]


def plot_composition(ax, rows: list[dict]) -> None:
    width = 0.26
    for offset, tier in zip((-width, 0.0, width), TIERS):
        counts = band_counts(rows, tier)
        xs = np.arange(len(BAND_LABELS)) + offset
        bars = ax.bar(xs, counts, width=width * 0.92, color=TIER_COLORS[tier],
                      label=f"{tier} (n={len(tier_hours(rows, tier))})")
        ax.bar_label(bars, fontsize=8, color="0.3", padding=1.5)
    ax.set_xticks(range(len(BAND_LABELS)))
    ax.set_xticklabels(BAND_LABELS)
    ax.set_xlabel("Audited MRE compute band (H100-hours)", fontsize=9.5)
    ax.set_ylabel("Papers", fontsize=9.5)
    ax.set_ylim(0, 46)
    ax.legend(loc="upper right", fontsize=8.5, frameon=False)
    ax.set_title("(a) Pool composition: papers per tier and compute band",
                 fontsize=10, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=9)


def plot_feasibility(ax, rows: list[dict]) -> None:
    for tier in TIERS:
        hours = tier_hours(rows, tier)
        xs = np.clip(hours, ECDF_FLOOR, None)
        fraction = np.arange(1, len(xs) + 1) / len(xs) * 100
        ax.step(np.append(xs, 245), np.append(fraction, 100), where="post",
                color=TIER_COLORS[tier], linewidth=2, label=tier)
    for budget in AGENT_BUDGETS:
        ax.axvline(budget, color="0.6", linewidth=0.9, linestyle=(0, (4, 3)), zorder=1)
    ax.set_xscale("log")
    ax.set_xlim(ECDF_FLOOR, 245)
    ax.set_xticks([0.1, 1, 4, 16, 64, 192])
    ax.set_xticklabels(["≤0.1", "1", "4", "16", "64", "192"])
    ax.set_xticks([], minor=True)
    ax.set_ylim(0, 103)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Agent compute budget B (H100-hours, log scale)", fontsize=9.5)
    ax.set_ylabel("MREs with audited compute ≤ B (%)", fontsize=9.5)
    handles = [plt.Line2D([], [], color=TIER_COLORS[tier], linewidth=2, label=tier)
               for tier in TIERS]
    handles.append(plt.Line2D([], [], color="0.6", linewidth=0.9,
                              linestyle=(0, (4, 3)), label="agent budgets"))
    ax.legend(handles=handles, loc="lower right", fontsize=8.5, frameon=False)
    ax.set_title("(b) Compute feasibility: share of MREs that fit in a budget",
                 fontsize=10, loc="left")
    ax.grid(axis="y", color="0.92")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=9)


def plot(rows: list[dict], out_base: Path) -> None:
    fig, (left, right) = plt.subplots(1, 2, figsize=(10.2, 3.9),
                                      gridspec_kw={"wspace": 0.28})
    plot_composition(left, rows)
    plot_feasibility(right, rows)
    total = sum(row["audited_h100_hours"] for row in rows)
    fig.suptitle(
        f"ReproBench audit pool — {len(rows)} papers, "
        f"Σ {total:,.0f} audited H100-hours",
        fontsize=11, x=0.085, ha="left",
    )
    fig.subplots_adjust(left=0.065, right=0.985, top=0.78, bottom=0.16)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for suffix in (".png", ".pdf"):
        fig.savefig(out_base.with_suffix(suffix), dpi=300)
        print(f"Wrote {out_base.with_suffix(suffix)}")

    for tier in TIERS:  # console readout of the feasibility numbers
        hours = tier_hours(rows, tier)
        shares = "  ".join(
            f"≤{budget}h: {np.mean(hours <= budget) * 100:.0f}%" for budget in AGENT_BUDGETS
        )
        print(f"  {tier:<7} {shares}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", type=Path, default=Path("outputs/v5/audit_pool_extracted.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("notes/figures/audit_pool_tier_hours"))
    args = parser.parse_args()
    plot(list(iter_jsonl(args.pool)), args.out)


if __name__ == "__main__":
    main()
