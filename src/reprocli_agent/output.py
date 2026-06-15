from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricResult:
    metric: str
    actual_value: float | None


@dataclass
class ReproResult:
    custom_id: str
    reproduction_status: str  # "success" | "partial" | "failed"
    metric_results: list[MetricResult] = field(default_factory=list)
    claim_supported: bool | None = None
    claim_assessment: str = ""
    failure_reason: str | None = None
    tool_rounds_used: int = 0

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "custom_id": self.custom_id,
            "reproduction_status": self.reproduction_status,
            "metric_results": [m.__dict__ for m in self.metric_results],
            "claim_supported": self.claim_supported,
            "claim_assessment": self.claim_assessment,
            "tool_rounds_used": self.tool_rounds_used,
        }
        if self.failure_reason is not None:
            d["failure_reason"] = self.failure_reason
        return d


def parse_output(custom_id: str, messages: list[dict], tool_rounds_used: int = 0) -> ReproResult:
    base = ReproResult(
        custom_id=custom_id,
        reproduction_status="failed",
        tool_rounds_used=tool_rounds_used,
    )
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        text = _extract_text(msg)
        if not text:
            continue
        parsed = _try_parse_json(text)
        if parsed and isinstance(parsed, dict):
            return _build_result(custom_id, parsed, tool_rounds_used)
    return base


def _extract_text(msg: dict) -> str:
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def _try_parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return None


def _build_result(custom_id: str, data: dict, tool_rounds_used: int) -> ReproResult:
    metric_results = [
        MetricResult(metric=m.get("metric", ""), actual_value=m.get("actual_value"))
        for m in (data.get("metric_results") or [])
        if isinstance(m, dict)
    ]
    return ReproResult(
        custom_id=custom_id,
        reproduction_status=str(data.get("reproduction_status", "failed")),
        metric_results=metric_results,
        claim_supported=data.get("claim_supported"),
        claim_assessment=str(data.get("claim_assessment", "")),
        failure_reason=data.get("failure_reason"),
        tool_rounds_used=tool_rounds_used,
    )
