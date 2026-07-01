"""Pure PostgREST row builders for the audit sink.

Mirrors ``reprocli_repro.supabase_rows`` (the reproduce-run version) so the audit
transcript lands in ``audit_events`` with the SAME column shape the viewer's
``rowsToRounds`` already understands — the dashboard renders an audit exactly like
a run. Pure: an event payload in, a row ``dict`` out. The sink supplies ``base``
(``audit_run_id`` / ``seq`` / ``kind`` / ``round_index``).
"""

from __future__ import annotations

import json
from typing import Any

STDOUT_CAP = 8000  # chars per stdout/stderr/text cell


def cap(text: Any, limit: int = STDOUT_CAP) -> tuple[str, bool]:
    s = "" if text is None else str(text)
    if len(s) <= limit:
        return s, False
    return s[:limit] + f"\n…(+{len(s) - limit} chars truncated)", True


def arguments(call: dict[str, Any]) -> dict[str, Any]:
    fn = call.get("function") or {}
    args = fn.get("arguments")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (ValueError, TypeError):
            return {"_raw": args}
    return args if isinstance(args, dict) else {}


def message_row(base: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    msg = payload.get("message") or {}
    reasoning, _ = cap(msg.get("reasoning") or msg.get("reasoning_content"), STDOUT_CAP * 2)
    content, _ = cap(msg.get("content"), STDOUT_CAP * 2)
    base.update({"role": "assistant", "reasoning": reasoning or None, "content": content or None})
    if base.get("kind") == "final":
        base["exit_reason"] = payload.get("exit_reason") or None
    return base


def call_row(base: dict[str, Any], call: dict[str, Any]) -> dict[str, Any]:
    args = arguments(call)
    base["tool_name"] = str((call.get("function") or {}).get("name") or "?")
    if "command" in args:
        base.update(detail_kind="command", command=str(args["command"]))
    elif "path" in args:
        base.update(detail_kind="path", command=str(args["path"]))
    elif args:
        base.update(detail_kind="json", args=args)
    return base


def result_row(base: dict[str, Any], res: dict[str, Any]) -> dict[str, Any]:
    out, t1 = cap(res.get("stdout"))
    err, t2 = cap(res.get("stderr"))
    base.update({
        "ok": res.get("ok"), "rc": res.get("returncode"), "duration_s": res.get("duration_s"),
        "error": (str(res["error"]).splitlines()[0] if res.get("error") else None),
        "path": res.get("path"), "stdout": out or None, "stderr": err or None,
        "truncated": bool(t1 or t2),
    })
    return base
