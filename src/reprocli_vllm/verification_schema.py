"""Minimal deterministic verification-target schema (Phase-1 lockfile).

The model reads a paper plus its already-chosen MRE record and emits one flat
``target.json`` per paper. Every field here is consumed by the grader; there is
no risk/archetype/notes metadata. The ONE grading rule (Verification.md §1):

    delete stale_outputs; run harness_cmd (and baseline_cmd) in a clean sandbox;
    measured = metric(load(artifact_path)[metric_field], answer_key);
    PASS iff op(measured, target.value, target.tol) holds for every target.

Agent stdout, README, and shipped scalars are never read. ``exclusion_reason``
non-empty means the paper is not deterministically gradeable (§4).
"""

from __future__ import annotations


# The only comparators the grader dispatches on (Verification.md §1).
OPS = ("abs_rel_within", "gte", "lte", "is_true")
DEFAULT_REL_TOLERANCE = 0.05


_STR = {"type": "string"}
_NUM_OR_NULL = {"type": ["number", "null"]}


def _obj(properties: dict, required: list[str]) -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def _target_item() -> dict:
    return _obj(
        {
            "name": _STR,
            "value": _NUM_OR_NULL,
            "op": {"type": "string", "enum": list(OPS)},
            "tol": _NUM_OR_NULL,
        },
        ["name", "value", "op", "tol"],
    )


VERIFICATION_JSON_SCHEMA = _obj(
    {
        "paper_id": _STR,
        # "" = deterministically gradeable; non-empty = why it is excluded (§4).
        "exclusion_reason": _STR,
        # env lock: where the code lives and the version we pin.
        "repo": _STR,
        "commit": _STR,
        # what WE run (the injected input is encoded in these args/paths).
        "harness_cmd": _STR,
        "baseline_cmd": _STR,
        # the only file the grader reads; deleted siblings cannot be cached.
        "artifact_path": _STR,
        "stale_outputs": {"type": "array", "items": _STR},
        "answer_key": _STR,
        # scoring: which metric fn, which artifact field, and how measured is computed.
        "metric_name": _STR,
        "metric_field": _STR,
        "metric_spec": _STR,
        "targets": {"type": "array", "items": _target_item()},
    },
    [
        "paper_id",
        "exclusion_reason",
        "repo",
        "commit",
        "harness_cmd",
        "baseline_cmd",
        "artifact_path",
        "stale_outputs",
        "answer_key",
        "metric_name",
        "metric_field",
        "metric_spec",
        "targets",
    ],
)


VERIFICATION_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "verification_target",
        "schema": VERIFICATION_JSON_SCHEMA,
    },
}
