"""Seeded, stratified, priority-ordered paper subset for the rebuttal runs.

Writes rebuttal/subset.json. Rule: rebuttal/PLAN.md Section 2, "Stratified subset".
Run: python3 rebuttal/subset.py   (prints the pool and pick counts per cell)
"""

import itertools
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from reprocli_repro.dataset import band_max_hours, band_of, load_lockfile_rows  # noqa: E402

SEED = 22528
EXCLUDE = {"2510.20725"}
TIER_OF = {"Easy": "run", "Medium": "retrain", "Hard": "reimplement"}
TIERS = ["run", "retrain", "reimplement"]
BANDS = ["0-8", "8-32", "32-96"]
SLOTS = {
    "run": [("0-8", 3), ("8-32", 1)],
    "retrain": [("0-8", 2), ("8-32", 1), ("32-96", 1)],
    "reimplement": [("0-8", 2), ("8-32", 1), ("32-96", 1)],
}
LOCK_EVAL = "hf://datasets/Mithilss/reclaim/eval_100.jsonl"
LOCK_DEV = "hf://datasets/Mithilss/reclaim/dev_split.jsonl"
INDEX = ROOT / "tools/anon_viewer/public/data/index.json"
OUT = ROOT / "rebuttal/subset.json"
RULE = (
    "Eval papers, excluding 2510.20725. Per tier x band x outcome cell (outcome = audit verdict "
    "'reproduced' by at least one of the four agents), candidate ids sorted and drawn with "
    "random.Random(22528). Core = papers 1-12: Run 3 at 0-8 and 1 at 8-32; Retrain and "
    "Reimplement 2 at 0-8, 1 at 8-32, 1 at 32-96; within each tier 2 reproduced and 2 not. "
    "Extension = papers 13-24, same recipe on the remaining papers. Output interleaves tiers "
    "(Run, Retrain, Reimplement). smoke_dev = 2 Run-tier 0-8 papers from dev_split.jsonl, "
    "drawn with random.Random(22528). Granted budget = band ceiling in H100-h (8, 32, 96)."
)


def clean(x):
    return int(x) if float(x).is_integer() else float(x)


def load_eval():
    rows = load_lockfile_rows(LOCK_EVAL)
    index = json.loads(INDEX.read_text())
    index_papers = {p["arxiv_id"]: p for p in index["papers"]}
    runs = defaultdict(list)
    for r in index["runs"]:
        runs[r["arxiv_id"]].append(r)

    info = {}
    for pid, row in rows.items():
        if pid in EXCLUDE:
            continue
        tier, band = TIER_OF[row["tier"]], band_of(row)
        budget = band_max_hours(row)
        ip = index_papers.get(pid)
        if ip is None or ip["tier"] != tier or ip["band"] != band:
            raise SystemExit(f"tier/band mismatch for {pid}")
        for r in runs.get(pid, []):
            if r["tier"] != tier or float(r["budget_h100"]) != budget:
                raise SystemExit(f"run tier/budget mismatch for {pid}")
        reproduced = any((r.get("audit") or {}).get("verdict") == "reproduced" for r in runs.get(pid, []))
        info[pid] = {"tier": tier, "band": band, "budget": budget, "reproduced": reproduced}
    return info, runs


def draw_recipe(pools, rng):
    picks = {}
    for tier in TIERS:
        slots = SLOTS[tier]
        options = []
        for rs in itertools.product(*(range(n + 1) for _, n in slots)):
            if sum(rs) != 2:
                continue
            if all(
                r <= len(pools[(tier, b, True)]) and n - r <= len(pools[(tier, b, False)])
                for (b, n), r in zip(slots, rs)
            ):
                options.append(rs)
        if not options:
            raise SystemExit(f"no feasible split for {tier}")
        rs = rng.choice(options)
        chosen = []
        for (band, n), r in zip(slots, rs):
            for outcome, k in ((True, r), (False, n - r)):
                cell = pools[(tier, band, outcome)]
                for pid in rng.sample(cell, k):
                    cell.remove(pid)
                    chosen.append((pid, band, outcome))
        rng.shuffle(chosen)
        picks[tier] = chosen
    return picks


def interleave(picks, first_rank, info):
    out = []
    for k in range(4):
        for tier in TIERS:
            pid, band, rep = picks[tier][k]
            out.append({
                "rank": first_rank + len(out),
                "paper_id": pid,
                "tier": tier,
                "band": band,
                "budget_h100": clean(info[pid]["budget"]),
                "reproduced_by_any": rep,
            })
    return out


def main():
    info, _ = load_eval()
    pools = defaultdict(list)
    for pid in sorted(info):
        d = info[pid]
        pools[(d["tier"], d["band"], d["reproduced"])].append(pid)
    start = {k: len(v) for k, v in pools.items()}

    rng = random.Random(SEED)
    core_picks = draw_recipe(pools, rng)
    core_pool = {k: len(v) for k, v in pools.items()}
    ext_picks = draw_recipe(pools, rng)
    core = interleave(core_picks, 1, info)
    ext = interleave(ext_picks, 13, info)

    dev_info = {}
    for pid, row in load_lockfile_rows(LOCK_DEV).items():
        dev_info[pid] = {"tier": TIER_OF[row["tier"]], "band": band_of(row), "budget": band_max_hours(row)}
    if set(dev_info) & set(info):
        raise SystemExit("dev and eval overlap")
    dev_pool = sorted(p for p, d in dev_info.items() if d["tier"] == "run" and d["band"] == "0-8")
    smoke = [
        {"rank": i + 1, "paper_id": pid, "tier": "run", "band": "0-8", "budget_h100": clean(dev_info[pid]["budget"])}
        for i, pid in enumerate(random.Random(SEED).sample(dev_pool, 2))
    ]

    out = {
        "seed": SEED,
        "rule": RULE,
        "core": core,
        "extension": ext,
        "smoke_dev": smoke,
        "granted_h100_core": clean(sum(x["budget_h100"] for x in core)),
        "granted_h100_all": clean(sum(x["budget_h100"] for x in core + ext)),
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")

    print("tier band outcome pool_all core_picks ext_picks")
    ext_count = defaultdict(int)
    for tier in TIERS:
        for pid, band, rep in ext_picks[tier]:
            ext_count[(tier, band, rep)] += 1
    core_count = defaultdict(int)
    for tier in TIERS:
        for pid, band, rep in core_picks[tier]:
            core_count[(tier, band, rep)] += 1
    for tier in TIERS:
        for band in BANDS:
            for rep in (True, False):
                k = (tier, band, rep)
                print(tier, band, "R" if rep else "N", start.get(k, 0), core_count[k], ext_count[k])
    print("pool after core:", {k: v for k, v in core_pool.items()})
    print("granted_h100_core", out["granted_h100_core"], "granted_h100_all", out["granted_h100_all"])


if __name__ == "__main__":
    main()
