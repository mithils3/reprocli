"""Audit-mode inputs: render the central claim and (pending) the agent run bundle.

The auditor grades one agent reproduction attempt per paper. Its inputs are:
  - the paper's ``central_claim`` (from the classifier audit pool), and
  - the agent's run bundle: the code it wrote, the commands it ran, stdout/stderr,
    and output files from its reproduction attempt.

The run-bundle ingester is intentionally a stub: the agent reproduction-run
format is not decided yet. See ``load_run_bundle`` / TODO(agent-runs).
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import BUNDLE_PLACEHOLDER, CLAIM_PLACEHOLDER, RUBRIC_PLACEHOLDER

RUN_BUNDLE_PENDING_TEXT = (
    "(NO AGENT RUN BUNDLE WIRED YET. The agent reproduction-run format is not "
    "decided; see TODO(agent-runs) in audit_inputs.load_run_bundle. With no run "
    "to inspect, the only defensible verdict is `unverifiable`.)"
)


def load_audit_rubric(path) -> str:
    return Path(str(path)).read_text(encoding="utf-8")


def claim_block(record: dict | None) -> str:
    if not record:
        return "(no central claim found for this paper)"
    parts: list[str] = []
    claim = record.get("central_claim")
    if isinstance(claim, str) and claim.strip():
        parts.append(claim.strip())
    evidence = {key: record[key] for key in ("claim_evidence", "mre_config") if record.get(key)}
    if evidence:
        parts.append(
            "\nReported numbers / experiment context:\n"
            + json.dumps(evidence, ensure_ascii=False, indent=2)
        )
    return "\n".join(parts) if parts else "(no central claim found for this paper)"


def load_run_bundle(paper_id: str, runs_dir) -> str:
    # TODO(agent-runs): once the agent reproduction-run format is decided, load
    # this paper's run bundle here -- the code the agent wrote, the commands it
    # ran, stdout/stderr, and any output files -- packed as text under a token
    # budget. Until then the auditor receives the placeholder below and the
    # rubric forces an `unverifiable` verdict (no run = no evidence).
    return RUN_BUNDLE_PENDING_TEXT


def build_audit_prompt(
    template: str, rubric: str, record: dict | None, paper_id: str, runs_dir
) -> str:
    return (
        template.replace(CLAIM_PLACEHOLDER, claim_block(record))
        .replace(RUBRIC_PLACEHOLDER, rubric)
        .replace(BUNDLE_PLACEHOLDER, load_run_bundle(paper_id, runs_dir))
    )
