from __future__ import annotations


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
                "score",
                "tier",
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
                "score": {"type": "integer"},
                "tier": {
                    "type": "string",
                    "enum": ["Easy", "Medium", "Hard", "Artifact-Blocked"],
                },
                "agent_task": {"type": "string"},
                "h100_hours_estimate": {"type": "number"},
                "h100_estimate_basis": {"type": "string"},
            },
        },
    },
}

FINAL_JSON_SCHEMA = FINAL_RESPONSE_FORMAT["json_schema"]["schema"]
