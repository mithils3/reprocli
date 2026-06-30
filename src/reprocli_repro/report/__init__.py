"""The reproduction agent's terminal report bundle (Phase 5).

The episode's forced final pass emits a schema-constrained ``report.json`` -- the
agent's account of the run (what it ran, the metric value(s) it measured, citations
into ``evidence/``), not a verdict and not a re-run contract. ``schema`` defines the
``response_format`` the tools-off pass sends; ``validate`` validates, finalizes, and
persists the returned object next to ``evidence/`` for the Stage-7 auditor.
"""

from __future__ import annotations

from reprocli_repro.report.schema import (
    AGENT_ASSESSMENTS,
    REPORT_JSON_SCHEMA,
    REPORT_RESPONSE_FORMAT,
    REPORT_SCHEMA_NAME,
)
from reprocli_repro.report.validate import (
    REPORT_FILENAME,
    coerce_report,
    validate_report,
    write_episode_report,
    write_report,
)

__all__ = [
    "AGENT_ASSESSMENTS",
    "REPORT_JSON_SCHEMA",
    "REPORT_RESPONSE_FORMAT",
    "REPORT_SCHEMA_NAME",
    "REPORT_FILENAME",
    "coerce_report",
    "validate_report",
    "write_episode_report",
    "write_report",
]
