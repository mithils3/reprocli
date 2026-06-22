"""Human-readable live transcript for the reproduce loop — a ``tail -f`` view.

The durable evidence sinks are for the auditor: ``commands.log`` is one terse line
per shell command, ``trajectory.jsonl`` is machine-readable and only written for
``run_gpu`` steps, and the model's natural-language reasoning never lands there at
all (it lives in the in-memory conversation and is flushed to ``reproduce.jsonl``
only when the episode *finishes*). So while a run is in flight there is nowhere to
watch *what the agent is thinking and doing*.

This module fills that gap. It writes ``<run_dir>/agent.log`` — a single
append-only file, formatted like an interactive agent session, that interleaves
per round: the model's reasoning, its visible text, each tool call, and a head of
each tool result. Point ``tail -f <run_dir>/agent.log`` at it to follow along.

It is best-effort and append-only: a logging failure must never break the loop, so
every writer swallows its own exceptions. Each episode writes its own file (keyed
by run_dir), and rounds within an episode are sequential, so no locking is needed.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from reprocli_repro.context import ExecutionContext

# Max stdout/stderr (or reasoning/text) lines shown per block; the full output
# stays in commands.log / the tool result. Keeps the live log skimmable.
HEAD_LINES = 24
RULE = "─" * 72


def _log_path(ctx: ExecutionContext) -> Path | None:
    """``<run_dir>/agent.log`` — sibling of the evidence dir — or None if unknown."""
    if ctx.evidence is None:
        return None
    return Path(ctx.evidence).parent / "agent.log"


def _stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _head(text: str, prefix: str) -> list[str]:
    body = (text or "").rstrip()
    if not body:
        return []
    lines = body.splitlines()
    shown = [prefix + ln for ln in lines[:HEAD_LINES]]
    extra = len(lines) - HEAD_LINES
    if extra > 0:
        shown.append(f"{prefix}… (+{extra} more line{'s' if extra != 1 else ''})")
    return shown


def _arguments(call: dict[str, Any]) -> dict[str, Any]:
    fn = call.get("function") or {}
    args = fn.get("arguments")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except (ValueError, TypeError):
            return {"_raw": args}
    return args if isinstance(args, dict) else {}


def _call_summary(call: dict[str, Any]) -> tuple[str, str]:
    """(tool name, the single most useful argument rendered for a human)."""
    name = str((call.get("function") or {}).get("name") or "?")
    args = _arguments(call)
    if "command" in args:
        detail = "$ " + str(args["command"])
    elif "diff" in args:
        path = args.get("path")
        detail = f"(apply diff{' to ' + str(path) if path else ''})"
    elif "path" in args:
        detail = str(args["path"])
    elif args:
        detail = json.dumps(args)[:300]
    else:
        detail = ""
    return name, detail


def _result_lines(result: dict[str, Any]) -> list[str]:
    ok = result.get("ok")
    mark = "✓" if ok else "✗"
    parts = [f"   {mark} ok={ok}"]
    if result.get("returncode") is not None:
        parts.append(f"rc={result['returncode']}")
    if result.get("duration_s") is not None:
        parts.append(f"{result['duration_s']}s")
    if result.get("run_seconds") is not None:
        parts.append(f"{result['run_seconds']}s")
    if result.get("retried"):
        parts.append("(retried)")
    lines = [" ".join(parts)]
    if result.get("error"):
        lines.append("   ! " + str(result["error"]).splitlines()[0])
    for key in ("path", "bytes_written", "cost_h100_hours", "remaining_h100_hours"):
        if key in result:
            lines.append(f"   · {key}={result[key]}")
    lines += _head(str(result.get("stdout") or ""), "   │ ")
    lines += _head(str(result.get("stderr") or ""), "   ┊ ")
    return lines


def _message_lines(message: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    reasoning = message.get("reasoning") or message.get("reasoning_content")
    if reasoning:
        lines.append(" 💭 reasoning")
        lines += _head(str(reasoning), "    ")
    content = message.get("content")
    if content and str(content).strip():
        lines.append(" 🗒  assistant")
        lines += _head(str(content), "    ")
    return lines


def _write(ctx: ExecutionContext, lines: list[str]) -> None:
    """Append ``lines`` and flush immediately so ``tail -f`` sees them at once.

    Each call opens/appends/closes, so writes stream out incrementally within a
    round rather than batching at round end — the agent's plan, the command it is
    about to run, and that command's result each land the moment they happen.
    """
    path = _log_path(ctx)
    if path is None or not lines:
        return
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
            handle.flush()
    except OSError:
        return


def log_round_open(
    ctx: ExecutionContext,
    message: dict[str, Any],
    *,
    round_index: int | None = None,
) -> None:
    """Open a round: flush the model's reasoning/text before any tool runs."""
    rnd = f"round {round_index}" if round_index is not None else "round"
    header = f" {rnd} · {getattr(ctx, 'arxiv_id', '?')} · {_stamp()}"
    _write(ctx, [RULE, header, RULE, *_message_lines(message)])


def log_call_start(ctx: ExecutionContext, call: dict[str, Any]) -> None:
    """Flush the tool call + its command *before* it executes (streams long steps)."""
    name, detail = _call_summary(call)
    lines = ["", f" ⏺ {name}"]
    if detail:
        lines.append("   " + detail)
    _write(ctx, lines)


def log_call_result(ctx: ExecutionContext, result: dict[str, Any]) -> None:
    """Flush a tool result the instant it returns."""
    _write(ctx, _result_lines(result))


def log_final(
    ctx: ExecutionContext,
    message: dict[str, Any],
    *,
    round_index: int | None = None,
    exit_reason: str = "",
) -> None:
    """Append the episode's terminal submission (final assistant turn)."""
    rnd = f" (round {round_index})" if round_index is not None else ""
    lines = [
        RULE,
        f" ✅ FINAL{rnd} · {getattr(ctx, 'arxiv_id', '?')} · exit={exit_reason} · {_stamp()}",
        RULE,
        *_message_lines(message),
        "",
    ]
    _write(ctx, lines)
