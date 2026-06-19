"""Trend analysis of the frozen eval-100 + dev-15 splits.

Reads the two split files written by ``tools/build_eval_dev_splits.py`` and
prints the tables that back ``notes/Analysis/Final Split Analysis
(eval-100 + dev-15).md``: artifact-signal x tier, compute band x tier, the
hand-curated domain x tier census, anchor-metric type, arXiv recency, GPU
hardware, and compute concentration.

The only non-mechanical input is ``DOMAIN`` -- a hand assignment of one primary
research area per paper, read off each row's ``central_claim`` + ``mre_config``
(keyword auto-tagging over-collapses, e.g. tabular/edge papers into "diffusion",
so the labels are curated, not derived). Everything else is computed from the
audited fields. Run from the repo root::

    python tools/split_analysis.py
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "outputs/v5/audit_pool_eval100_extracted.jsonl"
DEV = ROOT / "outputs/v5/audit_pool_dev15_extracted.jsonl"

TIERS = ("Easy", "Medium", "Hard")
BANDS = ("0-8", "8-32", "32-96", "96-192")
SIGNALS = ("code_available", "dataset_available", "weights_available", "dataset_is_standard")

DOMAIN_NAMES = {
    "A": "Generative vision (diffusion/flow)",
    "B": "Vision -- perception & 3D",
    "C": "LLM -- reasoning, RL & training",
    "D": "Efficiency & model compression",
    "E": "Agents & tooling",
    "F": "Multimodal / VLA / embodied",
    "G": "RL -- control & world models",
    "H": "Theory / optimization",
    "I": "Science / bio / med / physical",
    "J": "Graph / time-series / combinatorial / OT",
    "K": "Trust / safety / robustness / forensics",
    "L": "Other / core ML",
}

# Hand-curated primary domain per eval-100 paper (see module docstring).
DOMAIN = {
    "2110.03155": "G", "2402.04579": "K", "2410.14732": "I", "2411.06568": "G",
    "2502.00757": "K", "2502.01203": "C", "2502.05795": "D", "2502.06684": "L",
    "2502.08924": "C", "2502.13681": "E", "2503.02809": "H", "2503.09657": "D",
    "2503.14698": "B", "2503.17482": "A", "2503.18430": "B", "2503.23035": "A",
    "2504.04072": "K", "2504.09474": "E", "2504.12397": "D", "2504.12463": "D",
    "2504.13146": "K", "2504.13726": "K", "2504.20571": "C", "2505.02391": "C",
    "2505.10819": "G", "2505.10978": "E", "2505.11483": "D", "2505.12677": "K",
    "2505.14766": "J", "2505.14827": "C", "2505.15101": "L", "2505.15201": "C",
    "2505.16927": "C", "2505.17315": "C", "2505.17685": "F", "2505.17836": "H",
    "2505.18456": "C", "2505.18809": "A", "2505.18943": "C", "2505.19087": "H",
    "2505.19516": "F", "2505.19713": "C", "2505.20425": "F", "2505.20738": "K",
    "2505.21077": "D", "2505.21577": "E", "2505.22596": "B", "2505.22860": "K",
    "2505.23305": "A", "2505.23747": "F", "2505.24680": "D", "2505.24864": "C",
    "2505.24873": "A", "2506.00070": "F", "2506.02392": "J", "2506.02882": "B",
    "2506.04536": "I", "2506.05285": "B", "2506.06991": "K", "2506.07104": "C",
    "2506.08898": "J", "2506.10351": "I", "2506.12025": "J", "2506.13717": "B",
    "2506.17475": "H", "2506.18890": "B", "2506.19839": "A", "2506.20024": "I",
    "2506.20671": "B", "2506.20990": "D", "2506.21724": "B", "2506.23589": "A",
    "2507.01467": "A", "2507.06489": "K", "2508.21046": "F", "2509.16391": "K",
    "2509.16950": "K", "2510.04136": "F", "2510.05874": "I", "2510.08177": "B",
    "2510.10480": "I", "2510.15194": "B", "2510.18357": "B", "2510.19314": "G",
    "2510.20261": "F", "2510.20725": "H", "2510.21311": "F", "2510.21363": "K",
    "2510.22123": "I", "2510.23574": "A", "2510.23577": "J", "2510.25529": "G",
    "2511.01463": "F", "2511.02652": "D", "2511.06024": "B", "2511.09833": "E",
    "2511.16666": "A", "2511.19808": "K", "2512.02339": "B", "2512.13837": "C",
}

_EFF = re.compile(r"speed-?up|faster|×|latency|throughput|less ram|memory|"
                  r"efficien|reduce.*cost|fewer param|runtime reduction| seconds", re.I)
_PERF = re.compile(r"accuracy|map\b|miou|giou|f1|auroc|auc|success rate|win.?rate|"
                   r"psnr|chamfer|perplexity|mae|mse|state-of-the-art|outperform|"
                   r"sota|pq\b|displacement|regret|recall", re.I)
_SOTA = re.compile(r"outperform|state-of-the-art|sota|surpass|beats|better than|improv|"
                   r"achieves? (?:superior|state|competitive|the best|higher|strong)", re.I)


def load(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def metric_type(claim: str) -> str:
    eff, perf = bool(_EFF.search(claim)), bool(_PERF.search(claim))
    return ("quality+efficiency" if eff and perf else "efficiency/speed" if eff
            else "quality/accuracy" if perf else "other")


def arxiv_ym(cid: str) -> tuple[int, int]:
    base = cid.split("v")[0].split(".")[0]
    return 2000 + int(base[:2]), int(base[2:])


def true_rate(rows, signal):
    return sum(1 for r in rows if r["signals"][signal]["value"])


def report(name: str, rows: list[dict]) -> None:
    print(f"\n{'=' * 68}\n{name}  (n={len(rows)})\n{'=' * 68}")

    print("\n-- artifact signal TRUE / tier (+ median audited H100-h) --")
    print(f"  {'tier':<7} {'code':>7} {'data':>7} {'weights':>8} {'std':>6} {'medH':>7}")
    for tier in TIERS:
        tr = [r for r in rows if r["tier"] == tier]
        if not tr:
            continue
        hrs = sorted(r["audited_h100_hours"] for r in tr)
        print(f"  {tier:<7} {true_rate(tr, 'code_available'):>4}/{len(tr):<2} "
              f"{true_rate(tr, 'dataset_available'):>4}/{len(tr):<2} "
              f"{true_rate(tr, 'weights_available'):>5}/{len(tr):<2} "
              f"{true_rate(tr, 'dataset_is_standard'):>5} {hrs[len(hrs) // 2]:>7.1f}")

    print("\n-- compute band x tier --")
    ct: dict = defaultdict(lambda: defaultdict(int))
    for r in rows:
        ct[r["tier"]][r["selection_band"]] += 1
    print("  " + " " * 8 + " ".join(f"{b:>7}" for b in BANDS))
    for tier in TIERS:
        print(f"  {tier:<7} " + " ".join(f"{ct[tier][b]:>7}" for b in BANDS))

    if all(r["custom_id"] in DOMAIN for r in rows):
        print("\n-- primary domain x tier (+ Sigma audited H100-h) --")
        agg: dict = defaultdict(lambda: {"n": 0, **{t: 0 for t in TIERS}, "h": 0.0})
        for r in rows:
            a = agg[DOMAIN[r["custom_id"]]]
            a["n"] += 1
            a[r["tier"]] += 1
            a["h"] += r["audited_h100_hours"]
        for code in sorted(agg, key=lambda c: -agg[c]["n"]):
            a = agg[code]
            print(f"  {DOMAIN_NAMES[code]:<42} {a['n']:>3}  "
                  f"E{a['Easy']:>2} M{a['Medium']:>2} H{a['Hard']:>2}  {a['h']:>6.0f}h")

    print("\n-- anchor-metric type --")
    for kind, n in Counter(metric_type(r["central_claim"]) for r in rows).most_common():
        print(f"  {n:>3}  {kind}")
    sota = sum(1 for r in rows if _SOTA.search(r["central_claim"]))
    print(f"  comparative/SOTA-style claims: {sota}/{len(rows)}")

    print("\n-- arXiv first-preprint month --")
    for ym, n in sorted(Counter(arxiv_ym(r["custom_id"]) for r in rows).items()):
        print(f"  {ym[0]}-{ym[1]:02d}  {'#' * n} {n}")

    hrs = [r["audited_h100_hours"] for r in rows]
    top = sorted(rows, key=lambda r: -r["audited_h100_hours"])[:10]
    print(f"\n-- compute: Sigma={sum(hrs):.0f}  mean={sum(hrs) / len(hrs):.1f}  "
          f"zero={sum(1 for h in hrs if h == 0)}  top10={sum(r['audited_h100_hours'] for r in top):.0f}"
          f" ({100 * sum(r['audited_h100_hours'] for r in top) / sum(hrs):.0f}% of budget)")

    gpu = Counter(r["h100_estimate"]["gpu_type"] for r in rows if r["h100_estimate"]["gpu_type"])
    print("  GPU mix:", dict(gpu.most_common(6)))
    basis = Counter(r["h100_estimate"]["basis_kind"] for r in rows)
    print("  compute-basis:", dict(basis))


def main() -> None:
    eval_rows, dev_rows = load(EVAL), load(DEV)
    overlap = {r["custom_id"] for r in eval_rows} & {r["custom_id"] for r in dev_rows}
    print(f"eval={len(eval_rows)}  dev={len(dev_rows)}  overlap={len(overlap)}")
    report("EVAL-100", eval_rows)
    report("DEV-15", dev_rows)


if __name__ == "__main__":
    main()
