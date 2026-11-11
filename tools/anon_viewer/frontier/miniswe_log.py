"""Convert one mini-swe-agent run folder into viewer events.

Input: <run_dir>/mini_trajectory.json (format tag "mini-swe-agent-1.1") and
<run_dir>/report.json. Output: the event list used by the run bundle.

Assistant message -> round_open, then one call_start per tool call, each
followed by its call_result. Tool message content is a JSON string:
  {"returncode": "0", "output": "...", "exception_info": "..."}
Elided results carry output_head / output_tail instead of output.
"""
import json
import re
from pathlib import Path

TRAJ = "mini_trajectory.json"
REPORT = "report.json"
NO_RESULT = "no result recorded"
ELIDED_MARK = "\n[... {n} chars elided ...]\n"
COST_KEYS = {"cost_h100_hours": "cost_h100", "remaining_h100_hours": "remaining_h100"}


def _timestamp(msg):
    ts = (msg.get("extra") or {}).get("timestamp")
    return float(ts) if isinstance(ts, (int, float)) else None


def _reasoning(msg):
    psf = msg.get("provider_specific_fields") or {}
    extra = msg.get("extra") or {}
    for src in (msg, psf, extra):
        for key in ("reasoning_content", "reasoning"):
            val = src.get(key)
            if isinstance(val, str) and val.strip():
                return val
    return None


def _parse_args(raw):
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else dict(raw or {})
    except json.JSONDecodeError:
        parsed = {"raw": raw}
    return parsed if isinstance(parsed, dict) else {"raw": parsed}


def _call_start(call, round_index, ts, t0):
    args = _parse_args(call.get("function", {}).get("arguments"))
    ev = {"kind": "call_start", "round_index": round_index,
          "tool_name": call.get("function", {}).get("name", "")}
    if isinstance(args.get("command"), str):
        ev["command"] = args["command"]
        ev["detail_kind"] = "bash"
    else:
        ev["args"] = args
        ev["detail_kind"] = "json"
    _stamp(ev, ts, t0)
    return ev


def _stamp(ev, ts, t0):
    if ts is not None and t0 is not None:
        ev["t_rel_s"] = round(ts - t0, 3)


def _cost_fields(output):
    try:
        obj = json.loads(output)
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(obj, dict):
        return {}
    out = {}
    for src, dst in COST_KEYS.items():
        val = obj.get(src)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            out[dst] = float(val)
    return out


def _call_result(tool_msg, round_index, t0):
    raw = tool_msg.get("content", "")
    ev = {"kind": "call_result", "round_index": round_index, "truncated": False}
    try:
        obj = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        obj = None
    if not isinstance(obj, dict):
        ev.update(ok=True, stdout=str(raw))
        _stamp(ev, _timestamp(tool_msg), t0)
        return ev

    rc = obj.get("returncode")
    try:
        rc = int(rc) if rc is not None else None
    except (TypeError, ValueError):
        rc = None
    if rc is not None:
        ev["rc"] = rc
    ev["ok"] = rc == 0 if rc is not None else not obj.get("exception_info")

    if "output" in obj:
        output = str(obj["output"])
    elif "output_head" in obj:
        output = str(obj.get("output_head", "")) + ELIDED_MARK.format(
            n=obj.get("elided_chars", "?")) + str(obj.get("output_tail", ""))
        ev["truncated"] = True
    else:
        output = None
    if output is not None:
        ev["stdout"] = output
        ev.update(_cost_fields(output))

    err = obj.get("exception_info") or obj.get("exception")
    if err:
        ev["error"] = str(err)

    exec_ms = (tool_msg.get("extra") or {}).get("exec_ms")
    if isinstance(exec_ms, (int, float)):
        ev["duration_s"] = float(exec_ms) / 1000.0

    _stamp(ev, _timestamp(tool_msg), t0)
    return ev


def _unanswered(round_index, t0, ts):
    ev = {"kind": "call_result", "round_index": round_index, "ok": False,
          "error": NO_RESULT, "truncated": False}
    _stamp(ev, ts, t0)
    return ev


def _final(run_dir, round_index):
    report = (Path(run_dir) / REPORT).read_text(encoding="utf-8")
    ev = {"kind": "final", "round_index": round_index, "role": "assistant",
          "content": report}
    try:
        reason = json.loads(report).get("exit_reason")
    except (json.JSONDecodeError, AttributeError):
        reason = None
    if reason is not None:
        ev["exit_reason"] = str(reason)
    return ev


def events(run_dir):
    run_dir = Path(run_dir)
    traj = json.loads((run_dir / TRAJ).read_text(encoding="utf-8"))
    messages = traj.get("messages", [])

    results = {}
    for msg in messages:
        if msg.get("role") == "tool" and msg.get("tool_call_id"):
            results[msg["tool_call_id"]] = msg

    t0 = None
    for msg in messages:
        if msg.get("role") == "assistant":
            t0 = _timestamp(msg)
            break

    out = []
    round_index = -1
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        round_index += 1
        ts = _timestamp(msg)
        opened = {"kind": "round_open", "round_index": round_index, "role": "assistant"}
        reasoning = _reasoning(msg)
        if reasoning:
            opened["reasoning"] = reasoning
        if isinstance(msg.get("content"), str) and msg["content"].strip():
            opened["content"] = msg["content"]
        _stamp(opened, ts, t0)
        out.append(opened)

        for call in msg.get("tool_calls") or []:
            out.append(_call_start(call, round_index, ts, t0))
            tool_msg = results.get(call.get("id"))
            if tool_msg is None:
                out.append(_unanswered(round_index, t0, ts))
            else:
                out.append(_call_result(tool_msg, round_index, t0))

    out.append(_final(run_dir, max(round_index, 0)))
    for seq, ev in enumerate(out):
        ev["seq"] = seq
    return out
