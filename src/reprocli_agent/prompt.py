from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

SYSTEM_PROMPT = """\
You are a reproduction agent for an ML-paper benchmark.

You are given a benchmark entry describing a Minimal Reproduction Example (MRE).
Follow the agent_task steps in order:

  Step 1 — Browse: use github_browse, hf_browse, or fetch_url to read the
             repository README, key source files, and setup instructions.
  Step 2 — Setup: use bash to clone the repo and install dependencies.
  Step 3 — Run: use bash to execute the experiment as specified in mre_config.
  Step 4 — Report: emit a single JSON object (no prose, no fences) with keys:
               reproduction_status: "success" | "partial" | "failed"
               metric_results: [{"metric": <name>, "actual_value": <number|null>}]
               claim_supported: true | false | null
               claim_assessment: <one paragraph assessing the overall pattern of
                 results against central_claim, not each number in isolation>
               failure_reason: <string, only if failed>

The metric names in metric_results must exactly match verification_targets[].metric.
Do not skip steps. Do not fabricate values — only report what you observed from
actual command output. The first character of your final response must be { and
the last must be }."""


@dataclass
class SignalEntry:
    value: bool
    evidence: str


@dataclass
class VerificationTarget:
    metric: str
    expected_value: float
    source: str
    conditions: str


@dataclass
class BenchmarkEntry:
    custom_id: str
    central_claim: str
    claim_evidence: str
    mre_config: str
    web_verification: str
    verified_links: dict[str, list[str]]
    signals: dict[str, SignalEntry]
    verification_targets: list[VerificationTarget]
    agent_task: str
    h100_hours_estimate: float
    h100_estimate_basis: str
    score: int | None = None
    tier: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BenchmarkEntry:
        signals = {
            k: SignalEntry(value=v["value"], evidence=v["evidence"])
            for k, v in d.get("signals", {}).items()
        }
        targets = [
            VerificationTarget(
                metric=t["metric"],
                expected_value=t["expected_value"],
                source=t["source"],
                conditions=t["conditions"],
            )
            for t in d.get("verification_targets", [])
        ]
        return cls(
            custom_id=d["custom_id"],
            central_claim=d["central_claim"],
            claim_evidence=d.get("claim_evidence", ""),
            mre_config=d["mre_config"],
            web_verification=d.get("web_verification", ""),
            verified_links=d.get("verified_links", {}),
            signals=signals,
            verification_targets=targets,
            agent_task=d["agent_task"],
            h100_hours_estimate=d.get("h100_hours_estimate", 0.0),
            h100_estimate_basis=d.get("h100_estimate_basis", ""),
            score=d.get("score"),
            tier=d.get("tier"),
        )


def build_prompt(entry: BenchmarkEntry) -> str:
    availability = "\n".join(
        f"{k}: {s.value} — {s.evidence}" for k, s in entry.signals.items()
    )
    parts = [
        f"# Paper: {entry.custom_id}",
        f"## Central Claim\n{entry.central_claim}",
        f"## Claim Evidence\n{entry.claim_evidence}",
        f"## Artifact Availability\n{availability}",
        f"## Web Verification Notes\n{entry.web_verification}",
        f"## Verified Links\n{json.dumps(entry.verified_links, indent=2)}",
        f"## MRE Configuration\n{entry.mre_config}",
        f"## Estimated Compute\n{entry.h100_hours_estimate} H100-hours — {entry.h100_estimate_basis}",
        f"## Verification Targets\n{json.dumps([t.__dict__ for t in entry.verification_targets], indent=2)}",
        f"## Agent Task\n{entry.agent_task}",
    ]
    if entry.score is not None or entry.tier is not None:
        parts.append(f"## Difficulty\nscore: {entry.score}, tier: {entry.tier}")
    return "\n\n".join(parts)
