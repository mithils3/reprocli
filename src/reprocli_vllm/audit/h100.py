"""Arithmetic checks and compute-band assignment for model H100 estimates."""

from __future__ import annotations

from typing import Any

H100_BANDS = ((0.0, 8.0, "0-8"), (8.0, 32.0, "8-32"), (32.0, 96.0, "32-96"), (96.0, 192.0, "96-192"))
OVER_CAP_BAND = ">192"
MISMATCH_TOLERANCE = 0.2


def h100_band(hours: Any) -> str | None:
    value = as_number(hours)
    if value is None or value < 0:
        return None
    for low, high, label in H100_BANDS:
        if low <= value <= high:
            return label
    return OVER_CAP_BAND


def recomputed_hours(estimate: dict[str, Any]) -> float | None:
    gpu_count = as_number(estimate.get("gpu_count"))
    wallclock = as_number(estimate.get("wallclock_hours"))
    multiplier = as_number(estimate.get("h100_equivalent_multiplier"))
    if gpu_count is None or wallclock is None or multiplier is None:
        return None
    if gpu_count <= 0 or wallclock < 0 or multiplier <= 0:
        return None
    return gpu_count * wallclock * multiplier


def arithmetic_mismatch(hours: Any, recomputed: float | None) -> bool | None:
    reported = as_number(hours)
    if reported is None or recomputed is None:
        return None
    largest = max(abs(reported), abs(recomputed))
    if largest == 0:
        return False
    return abs(reported - recomputed) / largest > MISMATCH_TOLERANCE


def audit_h100_fields(row: dict[str, Any]) -> dict[str, Any]:
    estimate = row.get("h100_estimate")
    if not isinstance(estimate, dict):
        return legacy_audit_fields(row)
    hours = as_number(estimate.get("hours"))
    basis_kind = str(estimate.get("basis_kind") or "")
    recomputed = recomputed_hours(estimate)
    mismatch = arithmetic_mismatch(hours, recomputed)
    return {
        "h100_hours_estimate": hours,
        "h100_estimate_basis": basis_text(estimate, basis_kind),
        "h100_band": h100_band(hours),
        "h100_recomputed_hours": recomputed,
        "h100_arithmetic_mismatch": mismatch,
        "h100_needs_human_review": (
            basis_kind == "compute_unspecified" or recomputed is None or bool(mismatch)
        ),
    }


def legacy_audit_fields(row: dict[str, Any]) -> dict[str, Any]:
    hours = as_number(row.get("h100_hours_estimate"))
    return {
        "h100_band": h100_band(hours),
        "h100_recomputed_hours": None,
        "h100_arithmetic_mismatch": None,
        "h100_needs_human_review": True,
    }


def basis_text(estimate: dict[str, Any], basis_kind: str) -> str:
    basis = str(estimate.get("basis") or "")
    if basis_kind and basis_kind not in basis:
        return f"{basis_kind}: {basis}" if basis else basis_kind
    return basis


def as_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
