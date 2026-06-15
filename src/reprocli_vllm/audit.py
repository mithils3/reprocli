"""Deterministic post-processing for audit-mode rows.

The LLM auditor proposes the verdict (audit_schema.py); this module enforces the
non-negotiable anti-cheat rule in code so it does not depend on the auditor's
goodwill: any HIGH-severity cheat flag caps the verdict at ``not_reproduced``.
It also derives a machine-aggregatable ``reproduced`` boolean and the run-health
``verification_status`` (degraded when the auditor output is malformed).
"""

from __future__ import annotations

from typing import Any

from .audit_schema import SEVERITIES, VERDICTS
from .run_health import INCOMPLETE_EXIT_REASONS, loop_exit_reason

DEGRADED = "degraded"
INCOMPLETE = "incomplete"
VERIFIED = "verified"

# Verdicts that count as a successful reproduction for the headline pass-rate.
REPRODUCED_VERDICTS = ("reproduced",)


def finalize_audit_row(parsed: dict[str, Any], tool_loop: dict[str, Any]) -> dict[str, Any]:
    row = dict(parsed)
    exit_reason = loop_exit_reason(tool_loop)
    row["exit_reason"] = exit_reason

    flags = _normalize_flags(parsed.get("cheat_flags"))
    row["cheat_flags"] = flags
    high_flags = [f for f in flags if f.get("severity") == "high"]
    row["has_high_cheat_flag"] = bool(high_flags)

    verdict = _normalize_verdict(parsed.get("verdict"))
    # Enforce the §3 rule in code, not in the prompt: a high-severity provenance
    # flag caps the verdict regardless of what the auditor concluded.
    if high_flags and verdict in ("reproduced", "partial"):
        row["reported_verdict"] = verdict
        verdict = "not_reproduced"
    row["verdict"] = verdict
    row["reproduced"] = verdict in REPRODUCED_VERDICTS

    row["verification_status"] = _verification_status(parsed, verdict, exit_reason)
    return row


def _normalize_flags(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    flags = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        severity = item.get("severity")
        flags.append(
            {
                "kind": str(item.get("kind") or "unknown"),
                "evidence": str(item.get("evidence") or ""),
                "severity": severity if severity in SEVERITIES else "low",
            }
        )
    return flags


def _normalize_verdict(value: Any) -> str | None:
    return value if value in VERDICTS else None


def _verification_status(parsed: dict[str, Any], verdict: str | None, exit_reason: str) -> str:
    if verdict is None or not _is_valid(parsed):
        return DEGRADED
    if exit_reason in INCOMPLETE_EXIT_REASONS:
        return INCOMPLETE
    return VERIFIED


def _is_valid(parsed: dict[str, Any]) -> bool:
    if not isinstance(parsed, dict):
        return False
    if not isinstance(parsed.get("paper_id"), str) or not parsed["paper_id"].strip():
        return False
    return isinstance(parsed.get("execution_verified"), bool)
