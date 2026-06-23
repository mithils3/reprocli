"""Between-round guardrails for the reproduce loop: compute budget + context tiers.

Split out of ``loop.py`` to keep the driver focused. ``apply_guardrails`` runs once
between tool rounds and decides whether the next request still offers tools:

* force-final when the compute budget is spent;
* ``microcompact`` — cheap, no model call: elide stale tool stdout;
* ``summarize-compact`` — one brain call that summarizes the old span so the loop
  keeps going (the tier that *replaces* the old hard context stop).

The hard context cutoff no longer ends episodes; it survives only as a degraded
backstop for when summarization itself fails and we are already past the real
ceiling, so we never silently front-truncate the system prompt + summary head.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from reprocli_vllm.runtime.loop_guards import BUDGET_CHARS_PER_TOKEN, context_budget_exceeded

from reprocli_repro import evidence as evidence_mod
from reprocli_repro import gpu_session, summarize
from reprocli_repro.compaction import microcompact
from reprocli_repro.context import ExecutionContext


def apply_guardrails(
    custom_id: str,
    ctx: ExecutionContext,
    messages: list[dict[str, Any]],
    args: argparse.Namespace,
    exit_reasons: dict[str, str],
    include_tools: bool,
    server_url: str,
    model: str,
) -> bool:
    """Budget guardrail + context management, run between tool rounds.

    Returns whether the next request should still offer tools. Force-finals first
    when the compute budget is spent, then lets ``microcompact`` reclaim cheap room
    and ``summarize-compact`` summarize the old span so the loop keeps going. The
    hard context cutoff no longer ends episodes; it survives only as a degraded
    backstop for when summarization itself fails and we are past the real ceiling
    (so we never silently front-truncate the prompt).
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
    if args.microcompact:
        stats = microcompact(
            messages,
            keep_recent_tool_results=args.microcompact_keep,
            soft_limit_chars=microcompact_soft_limit(args),
        )
        if stats["compacted"]:
            print(
                f"microcompact {custom_id}: elided {stats['elided_messages']} stale tool "
                f"result(s), {stats['chars_before']}->{stats['chars_after']} chars",
                file=sys.stderr,
            )
    if args.summarize_compact and _over_summarize_mark(messages, args):
        summarize_compaction(custom_id, ctx, messages, args, exit_reasons, server_url, model)
        if exit_reasons.get(custom_id) == "context_budget":
            return False
    return True


def summarize_compaction(
    custom_id: str,
    ctx: ExecutionContext,
    messages: list[dict[str, Any]],
    args: argparse.Namespace,
    exit_reasons: dict[str, str],
    server_url: str,
    model: str,
) -> None:
    """Summarize the old span (one brain call) and keep going; degrade only on failure."""
    stats = summarize.summarize_compact(
        messages,
        server_url=server_url,
        model=model,
        args=args,
        custom_id=custom_id,
        keep_recent_tokens=args.summarize_keep_tokens,
        previous_summary=ctx.summary,
        previous_modified=ctx.modified_files,
    )
    if stats["compacted"]:
        ctx.summary = stats["summary"]
        ctx.modified_files = stats["modified_files"]
        print(
            f"summarize-compact {custom_id}: summarized {stats['summarized_messages']} message(s), "
            f"{stats['chars_before']}->{stats['chars_after']} chars",
            file=sys.stderr,
        )
        if ctx.evidence is not None:
            evidence_mod.append_trajectory(
                ctx.evidence,
                {
                    "type": "compaction",
                    "custom_id": custom_id,
                    "summarized_messages": stats["summarized_messages"],
                    "chars_before": stats["chars_before"],
                    "chars_after": stats["chars_after"],
                },
            )
        return
    # Summarization could not reduce the prompt. Keep going (retry next round) unless
    # we are already past the hard ceiling, in which case end gracefully rather than
    # let vLLM silently front-truncate the system prompt + summary head away.
    if context_budget_exceeded(messages, args.max_input_tokens):
        gpu_session.release(ctx, "context_overflow")
        exit_reasons[custom_id] = "context_budget"
        print(
            f"Stopping reproduce loop for {custom_id}: context over ceiling and "
            f"summarize-compact failed ({stats.get('reason')})",
            file=sys.stderr,
        )


def microcompact_soft_limit(args: argparse.Namespace) -> int:
    return int(args.microcompact_threshold * args.max_input_tokens * BUDGET_CHARS_PER_TOKEN)


def _over_summarize_mark(messages: list[dict[str, Any]], args: argparse.Namespace) -> bool:
    """True once the conversation crosses ``summarize_threshold`` of the input budget."""
    return context_budget_exceeded(messages, int(args.summarize_threshold * args.max_input_tokens))
