"""Deterministic run-health: the model reports evidence, this module computes status."""

from __future__ import annotations

import json
from typing import Any

from .h100_audit import audit_h100_fields
from .loop_guards import conversation_chars
from .output_schema import (
    NON_EMPIRICAL_TIER,
    SIGNAL_NAMES,
    VERIFICATION_STATES,
    normalize_score_and_tier,
)

VERIFIED = "verified"
INCOMPLETE = "incomplete"
DEGRADED = "degraded"
INCOMPLETE_EXIT_REASONS = ("round_limit", "repeated_call_cutoff", "context_budget")
UNVERIFIED_SIGNAL_STATES = ("tool_failed", "paper_text_only")
WEB_VERIFICATION_ALIAS = {
    VERIFIED: "available",
    INCOMPLETE: "partial",
    DEGRADED: "unavailable",
}


def loop_telemetry(messages: list[dict[str, Any]], max_input_tokens: int | None) -> dict[str, Any]:
    tool_calls = 0
    tool_errors = 0
    for message in messages:
        if message.get("role") != "tool":
            continue
        tool_calls += 1
        if tool_result_failed(str(message.get("content") or "")):
            tool_errors += 1
    chars = conversation_chars(messages)
    estimated_tokens = chars // 4
    return {
        "tool_calls": tool_calls,
        "tool_errors": tool_errors,
        "conversation_chars": chars,
        "estimated_input_tokens": estimated_tokens,
        "input_overflow": bool(max_input_tokens) and estimated_tokens >= max_input_tokens,
    }


def tool_result_failed(content: str) -> bool:
    try:
        envelope = json.loads(content)
    except json.JSONDecodeError:
        return False
    return isinstance(envelope, dict) and envelope.get("ok") is False


def verification_status(parsed: Any, tool_loop: dict[str, Any]) -> str:
    telemetry = tool_loop.get("telemetry") or {}
    if telemetry.get("input_overflow"):
        return DEGRADED
    states = signal_verification_states(parsed)
    if states is None:
        return DEGRADED
    exit_reason = loop_exit_reason(tool_loop)
    if exit_reason in INCOMPLETE_EXIT_REASONS:
        return INCOMPLETE
    applicable = [state for state in states if state != "not_applicable"]
    if any(state in UNVERIFIED_SIGNAL_STATES for state in applicable):
        return INCOMPLETE
    if applicable and telemetry.get("tool_calls") == 0:
        return INCOMPLETE
    return VERIFIED


def signal_verification_states(parsed: Any) -> list[str] | None:
    if not isinstance(parsed, dict):
        return None
    signals = parsed.get("signals")
    if not isinstance(signals, dict):
        return None
    states = []
    for name in SIGNAL_NAMES:
        signal = signals.get(name)
        if not isinstance(signal, dict) or not isinstance(signal.get("value"), bool):
            return None
        # Legacy rows without a verification field count as paper-text guesses.
        state = str(signal.get("verification") or "paper_text_only")
        if state not in VERIFICATION_STATES:
            return None
        states.append(state)
    return states


def loop_exit_reason(tool_loop: dict[str, Any]) -> str:
    reason = tool_loop.get("exit_reason")
    if reason:
        return str(reason)
    return "round_limit" if tool_loop.get("hit_tool_round_limit") else "natural"


def finalize_extracted_row(parsed: dict[str, Any], tool_loop: dict[str, Any]) -> dict[str, Any]:
    status = verification_status(parsed, tool_loop)
    row = dict(parsed)
    if "web_verification" in row:
        row["reported_web_verification"] = row.pop("web_verification")
    row["verification_status"] = status
    row["web_verification"] = WEB_VERIFICATION_ALIAS[status]
    row["exit_reason"] = loop_exit_reason(tool_loop)
    row.update(audit_h100_fields(row))
    if status == DEGRADED:
        return without_score(row)
    if str(row.get("paper_kind") or "empirical") != "empirical":
        row["score"] = None
        row["tier"] = NON_EMPIRICAL_TIER
        return row
    return normalize_score_and_tier(row)


def without_score(row: dict[str, Any]) -> dict[str, Any]:
    for field in ("score", "tier"):
        if row.get(field) is not None and f"reported_{field}" not in row:
            row[f"reported_{field}"] = row.get(field)
        row[field] = None
    return row


def degraded_row(custom_id: str, content: str, parsed: Any, tool_loop: dict[str, Any]) -> dict[str, Any]:
    return {
        "custom_id": custom_id,
        "extracted_json": parsed if not isinstance(parsed, dict) else None,
        "raw_content": content,
        "verification_status": DEGRADED,
        "web_verification": WEB_VERIFICATION_ALIAS[DEGRADED],
        "score": None,
        "tier": None,
        "exit_reason": loop_exit_reason(tool_loop),
    }
