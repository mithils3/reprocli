from __future__ import annotations

from typing import Any


def signal_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["value", "evidence"],
        "properties": {
            "value": {"type": "boolean"},
            "evidence": {"type": "string"},
        },
    }


FINAL_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "repro_artifact_classification",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "central_claim",
                "claim_evidence",
                "mre_config",
                "web_verification",
                "verified_links",
                "signals",
                "verification_targets",
                "agent_task",
                "h100_hours_estimate",
                "h100_estimate_basis",
            ],
            "properties": {
                "central_claim": {"type": "string"},
                "claim_evidence": {"type": "string"},
                "mre_config": {"type": "string"},
                "web_verification": {
                    "type": "string",
                    "enum": ["available", "partial", "unavailable"],
                },
                "verified_links": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["paper_or_project", "code", "dataset", "weights"],
                    "properties": {
                        "paper_or_project": {"type": "array", "items": {"type": "string"}},
                        "code": {"type": "array", "items": {"type": "string"}},
                        "dataset": {"type": "array", "items": {"type": "string"}},
                        "weights": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "signals": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "code_available",
                        "dataset_available",
                        "weights_available",
                        "dataset_is_standard",
                    ],
                    "properties": {
                        "code_available": signal_schema(),
                        "dataset_available": signal_schema(),
                        "weights_available": signal_schema(),
                        "dataset_is_standard": signal_schema(),
                    },
                },
                "verification_targets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["metric", "expected_value", "source", "conditions"],
                        "properties": {
                            "metric":         {"type": "string"},
                            "expected_value": {"type": "number"},
                            "source":         {"type": "string"},
                            "conditions":     {"type": "string"},
                        },
                    },
                },
                "agent_task": {"type": "string"},
                "h100_hours_estimate": {"type": "number"},
                "h100_estimate_basis": {"type": "string"},
            },
        },
    },
}

FINAL_JSON_SCHEMA = FINAL_RESPONSE_FORMAT["json_schema"]["schema"]


def deterministic_score_and_tier(row: dict[str, Any]) -> tuple[int, str] | None:
    signals = row.get("signals")
    if not isinstance(signals, dict):
        return None

    values = {
        name: signal_value(signals.get(name))
        for name in (
            "code_available",
            "dataset_available",
            "weights_available",
            "dataset_is_standard",
        )
    }
    if any(value is None for value in values.values()):
        return None

    code_available = values["code_available"]
    dataset_available = values["dataset_available"]
    weights_available = values["weights_available"]
    dataset_is_standard = values["dataset_is_standard"]

    score = 0
    if not code_available:
        score += 2
    if not dataset_is_standard and not dataset_available:
        score += 3
    if not weights_available:
        score += 1
    return score, tier_for_score(score, dataset_available, dataset_is_standard)


def normalize_score_and_tier(row: dict[str, Any]) -> dict[str, Any]:
    computed = deterministic_score_and_tier(row)
    if computed is None:
        return row

    score, tier = computed
    normalized = dict(row)
    if (
        "score" in normalized
        and normalized.get("score") != score
        and "reported_score" not in normalized
    ):
        normalized["reported_score"] = normalized.get("score")
    if (
        "tier" in normalized
        and normalized.get("tier") != tier
        and "reported_tier" not in normalized
    ):
        normalized["reported_tier"] = normalized.get("tier")
    normalized["score"] = score
    normalized["tier"] = tier
    return normalized


def signal_value(signal: Any) -> bool | None:
    if not isinstance(signal, dict):
        return None
    value = signal.get("value")
    return value if isinstance(value, bool) else None


def tier_for_score(
    score: int,
    dataset_available: bool,
    dataset_is_standard: bool,
) -> str:
    if score == 0:
        return "Easy"
    if score == 1:
        return "Medium"
    if score == 2:
        return "Hard"
    if score == 3 and (dataset_available or dataset_is_standard):
        return "Hard"
    return "Artifact-Blocked"
