"""Turn one Codex CLI run folder into the anon_viewer event list.

A run folder holds codex_events.jsonl (one JSON object per line), report.json
and codex_run.json. Line shape, made-up values:
{"type": "item.completed", "item": {"id": "item_3", "type": "command_execution", "command": "/bin/bash -lc 'ls'", "aggregated_output": "a.txt\\n", "exit_code": 0, "status": "completed"}}
"""
import json
from pathlib import Path


def _clean(value):
    """Drop None values, recursively, so the result holds no None."""
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_clean(v) for v in value if v is not None]
    return value


def _read_lines(path):
    records = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def events(run_dir):
    run_dir = Path(run_dir)
    out = []
    state = {"round": -1}

    def emit(ev):
        ev["seq"] = len(out)
        ev["round_index"] = state["round"]
        out.append(ev)

    def open_round(text=None, field="content"):
        state["round"] += 1
        ev = {"kind": "round_open", "role": "assistant"}
        if text:
            ev[field] = text
        emit(ev)

    def ensure_round():
        if state["round"] < 0:
            open_round()

    def add_call(tool_name, detail_kind, call_fields, result):
        ensure_round()
        start = {"kind": "call_start", "tool_name": tool_name, "detail_kind": detail_kind}
        start.update(call_fields)
        emit(start)
        emit(dict({"kind": "call_result"}, **result))

    for rec in _read_lines(run_dir / "codex_events.jsonl"):
        if rec.get("type") != "item.completed":
            continue
        item = rec.get("item") or {}
        itype = item.get("type")

        if itype == "agent_message":
            open_round(item.get("text"), "content")
        elif itype == "reasoning":
            open_round(item.get("text"), "reasoning")
        elif itype == "command_execution":
            exit_code = item.get("exit_code")
            rc = exit_code if isinstance(exit_code, int) and not isinstance(exit_code, bool) else None
            result = {
                "ok": item.get("status") == "completed" and exit_code == 0,
                "truncated": False,
            }
            if rc is not None:
                result["rc"] = rc
            if isinstance(item.get("aggregated_output"), str):
                result["stdout"] = item["aggregated_output"]
            call_fields = {"command": item.get("command")}
            add_call("shell", "bash", _clean(call_fields), _clean(result))
        elif itype is not None:
            args = _clean({k: v for k, v in item.items() if k != "id"})
            add_call(itype, "json", {"args": args}, {"ok": True, "truncated": False})

    report_path = run_dir / "report.json"
    report_text = report_path.read_text(encoding="utf-8")
    final = {"kind": "final", "role": "assistant", "content": report_text}
    try:
        exit_reason = json.loads(report_text).get("exit_reason")
    except (ValueError, AttributeError):
        exit_reason = None
    if exit_reason is not None:
        final["exit_reason"] = exit_reason
    emit(final)
    return out
