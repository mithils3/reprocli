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


def parse_output(
    custom_id: str,
    messages: list[dict],
    tool_rounds_used: int = 0,
    workdir: str | None = None,
) -> ReproResult:
    """Parse the reproduction result.

    Prefers final_result.json written by the finalize phase — it's the
    model's actual judgment of whether metric_results support central_claim,
    backed by the reasoning in REASONING.txt. Falls back to results.json
    (raw metrics from collect_results, with no judgment attached) if finalize
    never ran or never wrote one, and finally to scanning assistant messages.
    """
    if workdir:
        from pathlib import Path

        final_path = Path(workdir) / "final_result.json"
        if final_path.exists():
            try:
                data = json.loads(final_path.read_text())
                if isinstance(data, dict):
                    return _build_result(custom_id, data, tool_rounds_used)
            except json.JSONDecodeError:
                pass

        results_path = Path(workdir) / "results.json"
        if results_path.exists():
            try:
                data = json.loads(results_path.read_text())
                if isinstance(data, dict):
                    return _build_result(custom_id, data, tool_rounds_used)
                if isinstance(data, list):
                    # No finalize judgment available — collect_results only
                    # extracted raw metrics, it never assessed central_claim.
                    # Status reflects whether metrics were actually captured,
                    # not a real judgment call.
                    has_metrics = bool(data) and all(
                        isinstance(m, dict) and m.get("actual_value") is not None
                        for m in data
                    )
                    return _build_result(
                        custom_id,
                        {
                            "reproduction_status": "success" if has_metrics else "failed",
                            "metric_results": data,
                            "failure_reason": None if has_metrics else (
                                "no metrics extracted" if not data else
                                "some metrics have null actual_value"
                            ),
                        },
                        tool_rounds_used,
                    )
            except json.JSONDecodeError:
                pass

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


_FINAL_JSON_KEYS = {"reproduction_status", "claim_supported"}


def looks_like_final_json(text: str | None) -> bool:
    """Heuristic: does this assistant message look like the final reproduction JSON?"""
    if not text:
        return False
    parsed = _try_parse_json(text)
    return isinstance(parsed, dict) and bool(_FINAL_JSON_KEYS & parsed.keys())


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


def parse_metrics_from_log(text: str, target_names: list[str]) -> list[dict[str, Any]]:
    """Regex fallback for metric extraction — used when the model's reported
    actual_value is null, so a single malformed JSON field doesn't lose a value
    that's plainly sitting in the log."""
    results: list[dict[str, Any]] = []
    for name in target_names:
        patterns = [
            rf"{re.escape(name)}\s*[:=]\s*([-+]?\d*\.?\d+)",
            rf"{re.escape(name.lower())}\s*[:=]\s*([-+]?\d*\.?\d+)",
            rf"{re.escape(name.upper())}\s*[:=]\s*([-+]?\d*\.?\d+)",
        ]
        value: float | None = None
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                value = float(m.group(1))
                break
        results.append({"metric": name, "actual_value": value})
    return results


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
