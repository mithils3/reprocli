"""Between-round guardrails for the reproduce loop: compute budget + context tier.

Split out of ``loop.py`` to keep the driver focused. ``apply_guardrails`` runs once
between tool rounds and decides whether the next request still offers tools:

* force-final when the compute budget is spent;
* ``elide-compact`` — shrink the old span's bulky tool stdout in place so the loop
  keeps going (the tier that *replaces* the old hard context stop).

Compaction elides only ``role:"tool"`` result contents (see ``compact.py``); the
agent's own reasoning and its ``tool_calls`` stay verbatim, so the intent that was
live going into the compaction survives it. An earlier tier summarized the whole
span with a brain call, which flattened that intent and let agents finalize
prematurely; an even earlier microcompact elided results with no on-disk pointer,
which sent agents re-running whole GPU evals. Elision-with-pointer keeps both the
reasoning and a path back to the full output (durable in ``evidence/``).

The hard context cutoff no longer ends episodes; it survives only as a degraded
backstop for when elision frees nothing and we are already past the real ceiling,
so we never silently front-truncate the pinned system prompt + task head.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from reprocli_repro import compact
from reprocli_repro import evidence as evidence_mod
from reprocli_repro import gpu_session
from reprocli_repro.context import ExecutionContext


def apply_guardrails(
    custom_id: str,
    ctx: ExecutionContext,
    messages: list[dict[str, Any]],
    args: argparse.Namespace,
    exit_reasons: dict[str, str],
    include_tools: bool,
) -> bool:
    """Budget guardrail + context management, run between tool rounds.

    Returns whether the next request should still offer tools. Force-finals first
    when the compute budget is spent, then lets ``elide-compact`` shrink the old
    span's bulky tool stdout so the loop keeps going. The hard context cutoff no
    longer ends episodes; it survives only as a degraded backstop for when elision
    frees nothing and we are past the real ceiling (so we never silently
    front-truncate the prompt).
    """
    if not include_tools:
        gpu_session.release(ctx, "tools_off")
        return False
    # Bill any GPU wall held since the last charge so a held node depletes the budget
    # even across a long reasoning gap, and the ceiling is enforced mid-hold.
    gpu_session.charge_accrued(ctx)
    if ctx.budget is not None and ctx.budget.exhausted():
        gpu_session.release(ctx, "budget_exhausted")
        exit_reasons[custom_id] = "budget_exhausted"
        print(f"Stopping reproduce loop for {custom_id}: compute budget exhausted", file=sys.stderr)
        return False
    # The context tier gates on the model's own usage.prompt_tokens from the last
    # response (exact, free, backend-agnostic) — no chars-per-token estimate. That count
    # lags by this round's just-appended tool results, which is fine for a soft trigger:
    # the next round's real count catches up. When no usage has been recorded yet we skip
    # rather than estimate.
    if args.compact_enabled and _over(ctx, args, args.compact_threshold):
        elide_compaction(custom_id, ctx, messages, args, exit_reasons)
        if exit_reasons.get(custom_id) == "context_budget":
            return False
    return True


def elide_compaction(
    custom_id: str,
    ctx: ExecutionContext,
    messages: list[dict[str, Any]],
    args: argparse.Namespace,
    exit_reasons: dict[str, str],
) -> None:
    """Elide the old span's bulky tool stdout and keep going; degrade only on failure."""
    full_log = None if ctx.evidence is None else str(Path(ctx.evidence).parent / "agent.full.log")
    stats = compact.elide_compact(
        messages,
        keep_recent_tokens=args.compact_keep_tokens,
        full_log_path=full_log,
    )
    if stats["compacted"]:
        print(
            f"elide-compact {custom_id}: elided {stats['elided_messages']} tool result(s), "
            f"{stats['chars_before']}->{stats['chars_after']} chars",
            file=sys.stderr,
        )
        if ctx.evidence is not None:
            evidence_mod.append_trajectory(
                ctx.evidence,
                {
                    "type": "compaction",
                    "mode": "elide",
                    "custom_id": custom_id,
                    "elided_messages": stats["elided_messages"],
                    "chars_before": stats["chars_before"],
                    "chars_after": stats["chars_after"],
                },
            )
        return
    # Elision freed nothing (no old, bulky tool output). Keep going (retry next round)
    # unless the last real prompt-token count is already past the hard ceiling, in which
    # case end gracefully rather than let vLLM front-truncate the pinned system + task head.
    if _over(ctx, args, 1.0):
        gpu_session.release(ctx, "context_overflow")
        exit_reasons[custom_id] = "context_budget"
        print(
            f"Stopping reproduce loop for {custom_id}: context over ceiling and "
            f"elide-compact freed nothing ({stats.get('reason')})",
            file=sys.stderr,
        )


def _over(ctx: ExecutionContext, args: argparse.Namespace, threshold: float) -> bool:
    """True once the last measured prompt_tokens crosses ``threshold`` of the input budget.

    Uses the model's own ``usage.prompt_tokens`` (exact) — no chars-per-token estimate.
    Returns False when no usage has been recorded yet, so the caller skips compaction that
    round rather than guessing.
    """
    tokens = ctx.last_prompt_tokens
    return tokens is not None and tokens >= threshold * args.max_input_tokens
