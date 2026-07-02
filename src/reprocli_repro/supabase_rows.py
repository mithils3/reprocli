"""Pure PostgREST row builders for the Supabase sink.

Split out of ``supabase_sink.py`` to keep that module focused on the worker
thread + HTTP plumbing (and under the file-size budget). Everything here is
pure: a context / event payload in, a row ``dict`` out — no state, no network.
The sink supplies the ``base`` dict (``run_id`` / ``seq`` / ``kind`` /
``round_index``) since the sequence counter is stateful.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reprocli_repro import live_log

STDOUT_CAP = 8000  # chars per stdout/stderr/text cell (full text -> agent.full.log)


def cap(text: Any, limit: int = STDOUT_CAP) -> tuple[str, bool]:
    s = "" if text is None else str(text)
    if len(s) <= limit:
        return s, False
    return s[:limit] + f"\n…(+{len(s) - limit} chars — see agent.full.log)", True


def run_id_of(ctx) -> str | None:
    ev = getattr(ctx, "evidence", None)
    return Path(ev).parent.name if ev else None


def budget_of(ctx) -> tuple[float | None, float | None]:
    b = getattr(ctx, "budget", None)
    if b is None:
        return None, None
    return b.total_h100_hours, b.remaining()


def message_row(base: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    msg = payload.get("message") or {}
    reasoning, _ = cap(msg.get("reasoning") or msg.get("reasoning_content"), STDOUT_CAP * 2)
    content, _ = cap(msg.get("content"), STDOUT_CAP * 2)
    base.update({"role": "assistant", "reasoning": reasoning or None, "content": content or None})
    if base.get("kind") == "final":
        base["exit_reason"] = payload.get("exit_reason") or None
    return base


def call_row(base: dict[str, Any], call: dict[str, Any]) -> dict[str, Any]:
    args = live_log.call_arguments(call)
    name = str((call.get("function") or {}).get("name") or "?")
    base["tool_name"] = name
    if "command" in args:
        base.update(detail_kind="command", command=str(args["command"]))
    elif "diff" in args:
        path = args.get("path")
        base.update(detail_kind="diff", command=f"(apply diff{' to ' + str(path) if path else ''})")
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
        "cost_h100": res.get("cost_h100_hours"), "remaining_h100": res.get("remaining_h100_hours"),
        "error": (str(res["error"]).splitlines()[0] if res.get("error") else None),
        "path": res.get("path"), "stdout": out or None, "stderr": err or None,
        "truncated": bool(t1 or t2),
    })
    return base
