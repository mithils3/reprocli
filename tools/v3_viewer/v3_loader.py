from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from quality import record_quality

CUSTOM_ID_RE = re.compile(r'"custom_id"\s*:\s*"([^"]+)"')


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if not path.exists():
        return rows, [{"path": str(path), "line": None, "error": "file not found"}]

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                errors.append(
                    {
                        "path": str(path),
                        "line": line_no,
                        "error": exc.msg,
                        "custom_id": guess_custom_id(line),
                        "snippet": line[:500],
                    }
                )
    return rows, errors


def guess_custom_id(line: str) -> str | None:
    match = CUSTOM_ID_RE.search(line[:5000])
    return match.group(1) if match else None


def load_run(base_path: Path) -> dict[str, Any]:
    final_rows, final_errors = load_jsonl(base_path.with_suffix(".jsonl"))
    extracted_rows, extracted_errors = load_jsonl(Path(f"{base_path}_extracted.jsonl"))
    trace_rows, trace_errors = load_jsonl(Path(f"{base_path}_trace.jsonl"))

    records: dict[str, dict[str, Any]] = {}
    attach_rows(records, "final", final_rows)
    attach_rows(records, "extracted", extracted_rows)
    attach_rows(records, "trace", trace_rows)
    for error in trace_errors:
        custom_id = error.get("custom_id")
        if custom_id:
            records.setdefault(custom_id, {"custom_id": custom_id})["trace_error"] = error

    for custom_id, record in records.items():
        record["custom_id"] = custom_id
        record["quality"] = record_quality(record)
        record["trace_stats"] = trace_stats(record.get("trace"))

    return {
        "base_path": str(base_path),
        "records": records,
        "errors": {
            "final": final_errors,
            "extracted": extracted_errors,
            "trace": trace_errors,
        },
        "summary": summarize(records, final_rows, extracted_rows, trace_rows, trace_errors),
    }


def attach_rows(
    records: dict[str, dict[str, Any]], key: str, rows: list[dict[str, Any]]
) -> None:
    for row in rows:
        custom_id = row.get("custom_id")
        if not custom_id:
            continue
        record = records.setdefault(str(custom_id), {"custom_id": str(custom_id)})
        if key in record:
            record.setdefault(f"{key}_duplicates", []).append(row)
        else:
            record[key] = row


def trace_stats(trace: dict[str, Any] | None) -> dict[str, Any]:
    messages = (trace or {}).get("messages") or []
    roles = Counter(m.get("role") for m in messages if isinstance(m, dict))
    tool_calls: list[str] = []
    tool_results: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            tool_calls.append(function.get("name") or "unknown")
        if message.get("role") == "tool":
            tool_results.append(message.get("name") or "tool")
    return {
        "messages": len(messages),
        "roles": dict(roles),
        "tool_call_count": len(tool_calls),
        "tool_result_count": len(tool_results),
        "tool_counts": dict(Counter(tool_results or tool_calls)),
    }


def summarize(
    records: dict[str, dict[str, Any]],
    final_rows: list[dict[str, Any]],
    extracted_rows: list[dict[str, Any]],
    trace_rows: list[dict[str, Any]],
    trace_errors: list[dict[str, Any]],
) -> dict[str, Any]:
    qualities = [r["quality"] for r in records.values()]
    tiers = Counter((r.get("extracted") or {}).get("tier", "missing") for r in records.values())
    scores = Counter(str((r.get("extracted") or {}).get("score", "missing")) for r in records.values())
    issue_counts = Counter(issue for q in qualities for issue in q["issues"])
    return {
        "record_count": len(records),
        "final_rows": len(final_rows),
        "extracted_rows": len(extracted_rows),
        "trace_rows": len(trace_rows),
        "trace_errors": len(trace_errors),
        "tiers": dict(tiers),
        "scores": dict(scores),
        "issue_counts": dict(issue_counts),
        "clean_final_json": sum(1 for q in qualities if q["clean_final_json"]),
        "score_drift": sum(1 for q in qualities if q["score_drift"]),
        "round_limit": sum(1 for q in qualities if q["hit_tool_round_limit"]),
    }


def list_records(run: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for record in run["records"].values():
        extracted = record.get("extracted") or {}
        quality = record["quality"]
        records.append(
            {
                "custom_id": record["custom_id"],
                "title": extracted.get("central_claim", "")[:180],
                "score": extracted.get("score"),
                "tier": extracted.get("tier"),
                "computed_score": quality["computed_score"],
                "computed_tier": quality["computed_tier"],
                "web_verification": extracted.get("web_verification"),
                "quality": quality,
                "trace_stats": record["trace_stats"],
            }
        )
    return sorted(records, key=lambda row: row["custom_id"])


def view_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "custom_id": record["custom_id"],
        "final": record.get("final"),
        "extracted": record.get("extracted"),
        "trace": compact_trace(record.get("trace")),
        "trace_error": record.get("trace_error"),
        "quality": record.get("quality"),
        "trace_stats": record.get("trace_stats"),
        "duplicates": {
            "final": len(record.get("final_duplicates", [])),
            "extracted": len(record.get("extracted_duplicates", [])),
            "trace": len(record.get("trace_duplicates", [])),
        },
    }


def compact_trace(trace: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(trace, dict):
        return None
    return {
        "custom_id": trace.get("custom_id"),
        "messages": [compact_message(m) for m in trace.get("messages") or []],
        "tool_loop": trace.get("tool_loop"),
    }


def compact_message(message: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(message, dict):
        return {"role": "unknown", "content": repr(message)}
    compact = {
        "role": message.get("role"),
        "name": message.get("name"),
        "content": clip(message.get("content"), 12000),
        "content_chars": len(message.get("content") or "")
        if isinstance(message.get("content"), str)
        else None,
    }
    if message.get("tool_calls"):
        compact["tool_calls"] = [compact_tool_call(c) for c in message["tool_calls"]]
    return compact


def compact_tool_call(call: dict[str, Any]) -> dict[str, Any]:
    function = call.get("function") or {}
    return {
        "id": call.get("id"),
        "type": call.get("type"),
        "function": {
            "name": function.get("name"),
            "arguments": clip(function.get("arguments"), 4000),
        },
    }


def clip(value: Any, limit: int) -> Any:
    if not isinstance(value, str) or len(value) <= limit:
        return value
    hidden = len(value) - limit
    return f"{value[:limit]}\n\n[... trimmed {hidden} characters ...]"
