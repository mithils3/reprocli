from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .phases import Phase
    from .state import ReproState

AGENT_PREAMBLE = """\
You are a reproduction agent for ML papers running on an HPC cluster.
You work in phases controlled by a harness. Each phase has a single, specific goal.

Rules:
- Follow the phase instructions exactly. Do not jump ahead to a later phase.
- Only call the tools listed as "Allowed tools" for the current phase.
- Write all required artifacts using write_file before stopping.
- Do NOT emit the final reproduction JSON unless you are in the finalize phase.
- If a repair is needed (e.g. missing package, build failure), fix it and retry
  within the current phase — the harness will route you back if needed.
- Work entirely inside the sandbox working directory."""


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


def build_phase_messages(
    entry: BenchmarkEntry,
    state: ReproState,
    phase: Phase,
) -> list[dict[str, Any]]:
    """Build the [system, user] message pair for a single phase."""
    system = AGENT_PREAMBLE + "\n\n" + phase.prompt_builder(entry, state) + (
        f"\n\nAllowed tools: {', '.join(phase.allowed_tools)}"
    )

    user = build_prompt(entry) + "\n\n" + state.state_summary()
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
