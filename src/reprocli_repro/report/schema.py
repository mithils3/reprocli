"""JSON-schema contract for the reproduction agent's terminal ``report.json``.

The reproduction episode ends like the classifier/auditor modes: a budget/round
guard or a natural stop flips the loop tools-off for one final, schema-constrained
pass (``reprocli_vllm.vllm.io.build_chat_completion_request`` sends tools XOR a
``response_format``). For the reproduction agent that final pass carries
``REPORT_RESPONSE_FORMAT``, so the model's last message comes back as a single
object matching ``REPORT_JSON_SCHEMA``: the agent's **account** of the run -- what
it ran, the metric value(s) it measured, and citations into ``evidence/``.

It is deliberately **not** a verdict and **not** a re-run contract: there is no
``repro.yaml``, no ``submit`` tool, and no post-loop re-execution. The verdict is
the Stage-7 auditor's -- it reads this ``report.json`` plus ``evidence/`` and
renders ``reproduced / partial / not_reproduced / unverifiable`` itself.
"""

from __future__ import annotations

# The agent's own honest read of where its number landed -- explicitly its claim,
# NOT the graded verdict (the auditor renders that, with its own vocabulary).
# ``could_not_run`` is the honest "never produced a measured number" case.
AGENT_ASSESSMENTS = ("reproduced", "partial", "not_reproduced", "could_not_run")

REPORT_SCHEMA_NAME = "reproduction_report"


def measurement_schema() -> dict:
    """One metric the agent measured from its OWN run, with evidence citations."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["metric", "observed_value", "reference_value", "scope", "evidence"],
        "properties": {
            # Metric name with units explicit (e.g. "top-1 accuracy (%)").
            "metric": {"type": "string"},
            # What the agent's run produced -- a string so it tolerates "76.5%",
            # "2.37x", "8.56 kB", or a range / "mean+-std".
            "observed_value": {"type": "string"},
            # The paper's target value the agent compared against (the lockfile bar),
            # echoed for context -- null when the measurement is off-anchor.
            "reference_value": {"type": ["string", "null"]},
            # Dataset / split / benchmark-set the value was measured over.
            "scope": {"type": "string"},
            # Citations BACKING observed_value: evidence-relative paths, a
            # ``file:line`` into commands.log, or an output artifact under evidence/.
            "evidence": {"type": "array", "items": {"type": "string"}},
        },
    }


REPORT_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "paper_id",
        "claim",
        "what_ran",
        "scoring_command",
        "measurements",
        "agent_assessment",
        "changes_made",
        "blockers",
        "evidence_files",
    ],
    "properties": {
        "paper_id": {"type": "string"},
        # The claim / target the agent worked toward (its own restatement).
        "claim": {"type": "string"},
        # Narrative of what was actually executed: env built, config, the run.
        "what_ran": {"type": "string"},
        # A single command that reproduces the measured number from a clean state,
        # so the auditor can re-run it if it chooses. Empty when nothing ran.
        "scoring_command": {"type": "string"},
        "measurements": {"type": "array", "items": measurement_schema()},
        "agent_assessment": {"type": "string", "enum": list(AGENT_ASSESSMENTS)},
        # What the agent changed vs the reference (deviations, re-implementation).
        "changes_made": {"type": "string"},
        # What blocked a full reproduction, if anything (empty when nothing did).
        "blockers": {"type": "string"},
        # Key files under evidence/ the auditor should open first (REPORT.md,
        # commands.log, captured run stdout, ...).
        "evidence_files": {"type": "array", "items": {"type": "string"}},
    },
}

REPORT_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {"name": REPORT_SCHEMA_NAME, "schema": REPORT_JSON_SCHEMA},
}

__all__ = [
    "AGENT_ASSESSMENTS",
    "REPORT_SCHEMA_NAME",
    "REPORT_JSON_SCHEMA",
    "REPORT_RESPONSE_FORMAT",
    "measurement_schema",
]
