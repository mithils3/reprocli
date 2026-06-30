"""Validate, finalize, and persist the reproduction agent's ``report.json``.

The forced final pass (tools off, ``REPORT_RESPONSE_FORMAT`` attached) returns a
single schema-constrained JSON object. ``coerce_report`` parses that content,
structurally validates it against ``REPORT_JSON_SCHEMA``, and wraps it in a thin
harness envelope (``report_status`` + ``exit_reason``); ``write_report`` drops the
result at ``<run_dir>/report.json`` so the Stage-7 auditor's run-dir manifest picks
it up alongside ``evidence/``. A malformed final pass still yields a ``degraded``
report (carrying the raw excerpt + the validation errors) rather than a missing
file, so the auditor always has an account to grade.

Validation is hand-rolled (the repo carries no ``jsonschema`` dependency) and only
checks structure/types -- it does NOT judge the run. The verdict is the auditor's.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from reprocli_vllm.vllm.io import parse_json_content

from reprocli_repro.report.schema import AGENT_ASSESSMENTS, REPORT_JSON_SCHEMA

if TYPE_CHECKING:
    from reprocli_repro.context import ExecutionContext

REPORT_FILENAME = "report.json"
_RAW_EXCERPT_MAX = 4000
_REQUIRED = list(REPORT_JSON_SCHEMA["required"])
_STR_FIELDS = ("paper_id", "claim", "what_ran", "scoring_command", "changes_made", "blockers")


def validate_report(parsed: Any) -> list[str]:
    """Structurally check ``parsed`` against the report schema; ``[]`` means valid."""
    if not isinstance(parsed, dict):
        return [f"report must be a JSON object, got {type(parsed).__name__}"]
    errors: list[str] = [f"missing required field: {key}" for key in _REQUIRED if key not in parsed]
    for key in _STR_FIELDS:
        if key in parsed and not isinstance(parsed[key], str):
            errors.append(f"{key} must be a string")
    if "agent_assessment" in parsed and parsed["agent_assessment"] not in AGENT_ASSESSMENTS:
        errors.append(f"agent_assessment must be one of {', '.join(AGENT_ASSESSMENTS)}")
    if "evidence_files" in parsed and not _is_str_list(parsed["evidence_files"]):
        errors.append("evidence_files must be an array of strings")
    if "measurements" in parsed:
        errors.extend(_measurement_errors(parsed["measurements"]))
    return errors


def _measurement_errors(measurements: Any) -> list[str]:
    if not isinstance(measurements, list):
        return ["measurements must be an array"]
    errors: list[str] = []
    for i, m in enumerate(measurements):
        if not isinstance(m, dict):
            errors.append(f"measurements[{i}] must be an object")
            continue
        for key in ("metric", "observed_value", "scope"):
            if not isinstance(m.get(key), str):
                errors.append(f"measurements[{i}].{key} must be a string")
        ref = m.get("reference_value")
        if ref is not None and not isinstance(ref, str):
            errors.append(f"measurements[{i}].reference_value must be a string or null")
        if not _is_str_list(m.get("evidence")):
            errors.append(f"measurements[{i}].evidence must be an array of strings")
    return errors


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def coerce_report(content: str, *, paper_id: str, exit_reason: str) -> dict[str, Any]:
    """Parse + validate the final-pass content into the dict persisted to disk.

    Returns the agent's object under a thin harness envelope on success, or a
    ``degraded`` report (raw excerpt + the validation errors) when the content does
    not parse or fails validation -- so ``report.json`` is always present and
    informative, never silently missing.
    """
    parsed = parse_json_content(content or "")
    errors = validate_report(parsed)
    if errors:
        return {
            "paper_id": paper_id,
            "report_status": "degraded",
            "exit_reason": exit_reason,
            "validation_errors": errors,
            "raw": (content or "")[:_RAW_EXCERPT_MAX],
        }
    report = dict(parsed)
    # The harness owns paper_id + provenance; never let the model's echo override it.
    report["paper_id"] = paper_id
    report["report_status"] = "complete"
    report["exit_reason"] = exit_reason
    return report


def write_report(run_dir: Path, report: dict[str, Any]) -> Path:
    """Write ``report`` to ``<run_dir>/report.json`` (pretty-printed) and return it."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    target = run_dir / REPORT_FILENAME
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def write_episode_report(ctx: "ExecutionContext", content: str, exit_reason: str) -> Path | None:
    """Finalize the forced-final-pass ``content`` into ``<run_dir>/report.json``.

    No-op (returns ``None``) when the episode has no resolved run dir. Records a
    ``report`` step in ``trajectory.jsonl`` so the write shows up in the evidence
    alongside tool calls and compactions.
    """
    if ctx.run_dir is None:
        return None
    report = coerce_report(content, paper_id=ctx.arxiv_id, exit_reason=exit_reason)
    path = write_report(ctx.run_dir, report)
    if ctx.evidence is not None:
        from reprocli_repro import evidence as evidence_mod

        evidence_mod.append_trajectory(
            ctx.evidence,
            {
                "type": "report",
                "custom_id": ctx.arxiv_id,
                "report_status": report.get("report_status"),
                "exit_reason": exit_reason,
                "path": str(path),
            },
        )
    return path


__all__ = [
    "REPORT_FILENAME",
    "validate_report",
    "coerce_report",
    "write_report",
    "write_episode_report",
]
