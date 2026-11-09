"""Print every frontier slot value from the databook as Markdown.

Reads rebuttal/results/databook/frontier_cells.csv. Standard library only.
Reproduced means score >= 8 (the auditor's reproduced band), which matches the flag column.
"""
import argparse
import csv
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parents[1] / "results/databook/frontier_cells.csv"
PLANNED = {
    "codex-gpt-6.1-sol": 24,
    "codex-gpt-6-astra": 8,
    "thin-gpt-6.1-sol": 12,
    "miniswe": 6,
    "codex-gpt-6.1-sol-nudge": 8,
}
OPEN = ["dsv4", "minimax", "muse", "qwen3"]
VERDICTS = ["reproduced", "partial", "not_reproduced", "unverifiable", "disqualified"]
Z = 1.959964


def wilson(k, n):
    if n == 0:
        return None
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def fmt_rate(k, n):
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]"


def mcnemar_exact(b, c):
    m = b + c
    if m == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(m, i) for i in range(k + 1)) / 2 ** m
    return min(1.0, 2 * tail)


def exclusion(reason):
    if "void" in reason:
        return "void"
    if "no_gpu" in reason or "queue" in reason:
        return "no_gpu"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-queue-stops", action="store_true",
                    help="count no-GPU stops as failures instead of excluding them")
    args = ap.parse_args()

    rows = list(csv.DictReader(CSV_PATH.open(newline="")))
    excluded = Counter()
    kept = []
    for r in rows:
        why = exclusion(r["exit_reason"])
        if why == "void" or (why == "no_gpu" and not args.keep_queue_stops):
            excluded[(why, r["exit_reason"])] += 1
            continue
        kept.append(r)

    by_arm = defaultdict(list)
    for r in kept:
        by_arm[r["arm"]].append(r)

    total = len(kept)
    planned_total = sum(PLANNED.values())
    arms = list(PLANNED) + [a for a in by_arm if a not in PLANNED]
    short = any(len(by_arm[a]) < PLANNED.get(a, 0) for a in arms)
    print(f"# Frontier slots from {CSV_PATH.name}")
    if short:
        print(f"\n**partial: {total} of {planned_total} planned graded**\n")
    print(f"Rows in file: {len(rows)}. Graded rows used: {total}. "
          f"Flag --keep-queue-stops: {'on' if args.keep_queue_stops else 'off'}.\n")

    print("## Excluded rows")
    if not excluded:
        print("None.\n")
    for (why, reason), n in sorted(excluded.items()):
        print(f"- {n} x {why} (exit_reason `{reason}`)")
    print()

    print("## Per arm: graded, reproduced, verdicts")
    print("| arm | planned | graded | reproduced | rate, Wilson 95% | " +
          " | ".join(VERDICTS) + " |")
    print("|---|---|---|---|---|" + "---|" * len(VERDICTS))
    for a in arms:
        rs = by_arm.get(a, [])
        n = len(rs)
        k = sum(r["reproduced"] == "True" for r in rs)
        vc = Counter(r["verdict"] for r in rs)
        extra = [v for v in vc if v not in VERDICTS]
        cells = [str(vc.get(v, 0)) for v in VERDICTS]
        print(f"| {a} | {PLANNED.get(a, 'n/a')} | {n} | {k} | {fmt_rate(k, n)} | "
              + " | ".join(cells) + " |" + (f" other: {dict((e, vc[e]) for e in extra)}" if extra else ""))
    print()

    print("## Budget use and failure labels per arm")
    print("| arm | median % of GPU grant | agent_assessment on not-reproduced runs |")
    print("|---|---|---|")
    for a in arms:
        rs = by_arm.get(a, [])
        if not rs:
            print(f"| {a} | n/a | n/a |")
            continue
        share = statistics.median(float(r["spent_h100"]) / float(r["budget_h100"]) * 100 for r in rs)
        fail = Counter(r["agent_assessment"] for r in rs if r["reproduced"] != "True")
        print(f"| {a} | {share:.2f}% | {dict(fail)} |")
    print()

    print("## Paired harness comparison (codex-gpt-6.1-sol vs thin-gpt-6.1-sol)")
    sol = {r["paper"]: r for r in by_arm.get("codex-gpt-6.1-sol", [])}
    thin = {r["paper"]: r for r in by_arm.get("thin-gpt-6.1-sol", [])}
    both = sorted(set(sol) & set(thin))
    tt = sum(sol[p]["reproduced"] == "True" and thin[p]["reproduced"] == "True" for p in both)
    tf = sum(sol[p]["reproduced"] == "True" and thin[p]["reproduced"] != "True" for p in both)
    ft = sum(sol[p]["reproduced"] != "True" and thin[p]["reproduced"] == "True" for p in both)
    ff = len(both) - tt - tf - ft
    print(f"Papers graded under both: {len(both)}")
    print("| | thin reproduced | thin not reproduced |")
    print("|---|---|---|")
    print(f"| sol reproduced | {tt} | {tf} |")
    print(f"| sol not reproduced | {ft} | {ff} |")
    print(f"\nDiscordant pairs: sol-only {tf}, thin-only {ft}. Exact McNemar p = {mcnemar_exact(tf, ft):.4f}\n")

    print("## Open agents on the same papers (reproduced = original score >= 8)")
    print("| arm | agent | papers with a value | reproduced | rate, Wilson 95% |")
    print("|---|---|---|---|---|")
    for a in arms:
        rs = by_arm.get(a, [])
        if not rs:
            continue
        for ag in OPEN:
            vals = [(r, r[ag]) for r in rs if r[ag].strip() != ""]
            k = sum(int(float(v)) >= 8 for _, v in vals)
            print(f"| {a} | {ag} | {len(vals)} of {len(rs)} | {k} | {fmt_rate(k, len(vals))} |")
    print()
    print("Open-agent values are the 0 to 10 auditor-scale scores recorded in the databook; "
          "the paper's most-common-failure count is not in this CSV.")


if __name__ == "__main__":
    main()
