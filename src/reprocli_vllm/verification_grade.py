"""Deterministic post-processing for verification-target rows.

The model proposes the flat target.json; this module decides — with no further
model judgment — whether the spec is gradeable as written (``target_status``)
and applies the Verification.md §2 tolerance default so curation is auditable.
"""

from __future__ import annotations

from typing import Any

from .run_health import INCOMPLETE_EXIT_REASONS, loop_exit_reason
from .verification_schema import DEFAULT_REL_TOLERANCE, OPS

READY = "ready"
NEEDS_CURATION = "needs_curation"
EXCLUDED = "excluded"
INVALID = "invalid"

DEGRADED = "degraded"
INCOMPLETE = "incomplete"
VERIFIED = "verified"


def finalize_verification_row(parsed: dict[str, Any], tool_loop: dict[str, Any]) -> dict[str, Any]:
    row = dict(parsed)
    exit_reason = loop_exit_reason(tool_loop)
    row["exit_reason"] = exit_reason

    raw_targets = parsed.get("targets")
    targets = (
        [_normalize_target(t) for t in raw_targets if isinstance(t, dict)]
        if isinstance(raw_targets, list)
        else []
    )
    if isinstance(raw_targets, list):
        row["targets"] = targets
    row["n_targets"] = len(targets)

    status, reasons = _target_status(parsed, targets)
    row["target_status"] = status
    row["target_status_reasons"] = reasons
    row["requires_both_arms"] = _nonempty(parsed.get("baseline_cmd"))
    row["verification_status"] = _verification_status(status, exit_reason)
    return row


def _normalize_target(target: dict[str, Any]) -> dict[str, Any]:
    out = dict(target)
    op = out.get("op")
    tol = out.get("tol")
    if op == "abs_rel_within":
        # Value present, band absent -> corpus-default 5% relative band (§2).
        if not _is_number(tol) or tol == 0:
            out["tol"] = DEFAULT_REL_TOLERANCE
            out["tol_defaulted"] = True
    elif op in ("gte", "lte", "is_true"):
        out["tol"] = tol if _is_number(tol) else 0.0
    return out


def _target_status(parsed: dict[str, Any], targets: list[dict[str, Any]]) -> tuple[str, list[str]]:
    if not _nonempty(parsed.get("paper_id")) or not isinstance(parsed.get("targets"), list):
        return INVALID, ["missing paper_id or targets array"]

    exclusion = parsed.get("exclusion_reason")
    if isinstance(exclusion, str) and exclusion.strip():
        return EXCLUDED, []

    reasons: list[str] = []
    if not _nonempty(parsed.get("harness_cmd")):
        reasons.append("harness_cmd missing")
    if not _nonempty(parsed.get("artifact_path")):
        reasons.append("artifact_path missing")
    if not _nonempty(parsed.get("metric_name")):
        reasons.append("metric_name missing")
    if not targets:
        reasons.append("no targets")
    for index, target in enumerate(targets):
        for problem in _target_problems(target):
            reasons.append(f"target[{index}]: {problem}")

    if reasons:
        return NEEDS_CURATION, reasons
    return READY, []


def _target_problems(target: dict[str, Any]) -> list[str]:
    op = target.get("op")
    if op not in OPS:
        return ["invalid op"]
    problems: list[str] = []
    if op != "is_true" and not _is_number(target.get("value")):
        problems.append("missing value")
    if not _is_number(target.get("tol")):
        problems.append("missing tol")
    return problems


def _verification_status(target_status: str, exit_reason: str) -> str:
    if target_status == INVALID:
        return DEGRADED
    if exit_reason in INCOMPLETE_EXIT_REASONS:
        return INCOMPLETE
    return VERIFIED


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
