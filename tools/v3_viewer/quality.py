from __future__ import annotations

import json
from typing import Any


def signal_value(row: dict[str, Any], name: str) -> bool | None:
    signal = (row.get("signals") or {}).get(name)
    if not isinstance(signal, dict):
        return None
    value = signal.get("value")
    return value if isinstance(value, bool) else None


def computed_score_and_tier(row: dict[str, Any]) -> tuple[int, str] | None:
    code = signal_value(row, "code_available")
    data = signal_value(row, "dataset_available")
    weights = signal_value(row, "weights_available")
    standard = signal_value(row, "dataset_is_standard")
    if None in (code, data, weights, standard):
        return None

    score = 0
    if not code:
        score += 2
    if not standard and not data:
        score += 3
    if not weights:
        score += 1
    return score, tier_for_score(score, data, standard)


def tier_for_score(score: int, data: bool, standard: bool) -> str:
    if score == 0:
        return "Easy"
    if score == 1:
        return "Medium"
    if score == 2:
        return "Hard"
    if score == 3 and (data or standard):
        return "Hard"
    return "Artifact-Blocked"


def parse_final_content(final: dict[str, Any] | None) -> tuple[str, bool, str | None]:
    content = final_message(final).get("content") if final else ""
    content = content if isinstance(content, str) else ""
    stripped = content.strip()
    if not stripped:
        return content, False, "empty final content"
    if not stripped.startswith("{") or not stripped.endswith("}"):
        return content, False, "final content is not JSON-only"
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return content, False, f"invalid JSON: {exc.msg}"
    if not isinstance(parsed, dict):
        return content, False, "final JSON is not an object"
    return content, True, None


def final_message(final: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(final, dict):
        return {}
    body = ((final.get("response") or {}).get("body") or {})
    choices = body.get("choices") or []
    if not choices:
        return {}
    message = choices[0].get("message")
    return message if isinstance(message, dict) else {}


def final_body(final: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(final, dict):
        return {}
    body = ((final.get("response") or {}).get("body") or {})
    return body if isinstance(body, dict) else {}


def record_quality(record: dict[str, Any]) -> dict[str, Any]:
    final = record.get("final")
    extracted = record.get("extracted")
    content, clean_json, json_error = parse_final_content(final)
    computed = computed_score_and_tier(extracted or {})
    stored = None
    if isinstance(extracted, dict):
        stored = (extracted.get("score"), extracted.get("tier"))

    tool_loop = (final or {}).get("tool_loop") or {}
    message = final_message(final)
    body = final_body(final)
    finish = ((body.get("choices") or [{}])[0]).get("finish_reason")
    trace = record.get("trace")

    issues = []
    if not final:
        issues.append("missing final row")
    if not extracted:
        issues.append("missing extracted row")
    if not trace:
        issues.append("missing parsed trace row")
    if record.get("trace_error"):
        issues.append("corrupt trace row")
    if not clean_json:
        issues.append(json_error or "final JSON problem")
    if bool(tool_loop.get("hit_tool_round_limit")):
        issues.append("hit tool-round limit")
    if computed and stored != computed:
        issues.append("score/tier drift")
    if finish and finish != "stop":
        issues.append(f"finish_reason={finish}")

    return {
        "issues": issues,
        "clean_final_json": clean_json,
        "final_json_error": json_error,
        "computed_score": computed[0] if computed else None,
        "computed_tier": computed[1] if computed else None,
        "score_drift": bool(computed and stored != computed),
        "tool_rounds_used": tool_loop.get("tool_rounds_used"),
        "max_tool_rounds": tool_loop.get("max_tool_rounds"),
        "hit_tool_round_limit": bool(tool_loop.get("hit_tool_round_limit")),
        "finish_reason": finish,
        "status_code": ((final or {}).get("response") or {}).get("status_code"),
        "model": body.get("model"),
        "prompt_tokens": ((body.get("usage") or {}).get("prompt_tokens")),
        "completion_tokens": ((body.get("usage") or {}).get("completion_tokens")),
        "content_chars": len(content),
        "reasoning_chars": len(message.get("reasoning") or ""),
    }
