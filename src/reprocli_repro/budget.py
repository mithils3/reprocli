"""Compute-budget metering, denominated in H100-equivalent hours.

The lockfile gives each paper a ``budget_h100_hours`` ceiling. Real GPU steps run
on whatever the cluster has (GH200/H200/...), so the meter converts a step's
*actual* GPU-hours on that node into a common H100-equivalent currency via
``HW_MULTIPLIER[hw]`` and charges it against the per-episode ``Budget``
(``context.Budget``). Everything here is pure: ``slurm.py`` runs the step and
times it, ``tools/run_gpu.py`` (Phase 4) calls ``affordable`` before launch and
``charge`` after.

Cost model: ``gpus x elapsed_hours x HW_MULTIPLIER[hw]``. SLURM only bills the
run, not the queue wait, so the meter is fed elapsed *run* time, never queue time.
``minutes`` (a step's ``--time`` cap) bounds the worst case, so ``affordable`` can
refuse a step *before* launching it.
"""

from __future__ import annotations

from reprocli_repro.context import Budget

# H100-equivalent throughput per GPU-hour. Hopper-class parts (H100/H200/GH200)
# share the GH100 compute die and differ mainly in HBM capacity/bandwidth, so they
# start at ~1.0 — only a memory-bound step would justify a small uplift. Non-Hopper
# entries are rough placeholders and MUST be calibrated empirically before use.
HW_MULTIPLIER: dict[str, float] = {
    "h100": 1.0,
    "h200": 1.0,
    "gh200": 1.0,
    "a100": 0.5,   # approx ~half H100 (FP16 dense) — placeholder, calibrate
    "b200": 2.2,   # approx Blackwell — placeholder, calibrate
}


def hw_multiplier(hw: str) -> float:
    try:
        return HW_MULTIPLIER[hw]
    except KeyError:
        raise SystemExit(f"unknown hw {hw!r}; known: {', '.join(sorted(HW_MULTIPLIER))}")


def h100_equiv_hours(gpus: int, hours: float, hw: str) -> float:
    """Convert ``gpus`` for ``hours`` on ``hw`` into H100-equivalent hours."""
    return max(0, gpus) * max(0.0, hours) * hw_multiplier(hw)


def step_cost_hours(gpus: int, elapsed_seconds: float, hw: str) -> float:
    """Actual cost of a finished step (elapsed run time, not queue wait)."""
    return h100_equiv_hours(gpus, elapsed_seconds / 3600.0, hw)


def pre_authorized_cost(gpus: int, minutes: float, hw: str) -> float:
    """Worst-case cost if a step ran to its full ``--time`` wall cap."""
    return h100_equiv_hours(gpus, minutes / 60.0, hw)


def affordable(budget: Budget, gpus: int, minutes: float, hw: str) -> tuple[bool, str]:
    """Whether a step's *worst case* fits the remaining budget; reason if not."""
    if budget.exhausted():
        return False, "compute budget exhausted"
    worst = pre_authorized_cost(gpus, minutes, hw)
    remaining = budget.remaining()
    if worst > remaining:
        return False, (
            f"step would cost up to {worst:.3g} H100-h "
            f"({gpus} gpu x {minutes:g} min x{hw_multiplier(hw):g} {hw}) "
            f"> {remaining:.3g} H100-h remaining"
        )
    return True, ""


def charge(budget: Budget, gpus: int, elapsed_seconds: float, hw: str) -> float:
    """Charge a finished step's actual cost against ``budget``; return remaining."""
    return budget.consume(step_cost_hours(gpus, elapsed_seconds, hw))
