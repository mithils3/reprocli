"""Terminal finalization for one reproduce episode.

Split out of ``loop.py`` (kept under the repo's file-size cap) to hold the
end-of-episode seam: release the GPU, persist ``report.json``, flip the run row to a
terminal status via ``log_final``, then write the completed response row. Called from
``loop.handle_request_done`` on both a clean tools-off final pass and a failed model
call (``exit_reason="error"``), so a run always reaches a terminal state with an
account for the auditor rather than stranding as a permanently "running" row.

``report.json`` is written *before* ``log_final`` on purpose: the ``final`` event is
what flips the run row terminal and the Stage-7 auditor's manifest expects the report
to already exist. The write is best-effort — even a filesystem error still lets the run
reach a terminal status rather than stranding it live with no account to grade.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from reprocli_vllm.runtime.run_health import loop_telemetry

from reprocli_repro import cleanup, gpu_session, live_log, report
from reprocli_repro.context import ExecutionContext
from reprocli_repro.transcript import (
    EARLY_EXIT_REASONS,
    append_completed_outputs,
    append_final_message,
)


def finalize_episode(
    custom_id: str,
    row: dict[str, Any],
    message: dict[str, Any],
    tool_calls: list[dict],
    round_index: int,
    exit_reason: str,
    conversations: dict[str, list[dict]],
    final_rows: dict[str, dict],
    tool_rounds_used: dict[str, int],
    contexts_by_id: dict[str, ExecutionContext],
    args: argparse.Namespace,
) -> None:
    """End one episode: release its GPU, persist ``report.json``, then flip it terminal.

    Reached from the tools-off final pass (``exit_reason`` natural / round_limit / …) and
    from a failed model call (``exit_reason="error"``). The report is persisted before the
    ``log_final`` event so a finished run always has an account on disk for the auditor.
    """
    ctx = contexts_by_id[custom_id]
    # Free any GPU allocation still held at the end of the episode (the model is told
    # to release itself, but never leak a node if it didn't).
    gpu_session.release(ctx, exit_reason)
    row["tool_loop"] = {
        "tool_rounds_used": tool_rounds_used[custom_id],
        "max_tool_rounds": args.tool_rounds,
        "hit_tool_round_limit": exit_reason == "round_limit",
        "exit_reason": exit_reason,
        "telemetry": loop_telemetry(conversations[custom_id], args.max_input_tokens),
    }
    # The terminal branch is only reached with tools off, so the final message always
    # carries the tools-off user turn.
    append_final_message(
        conversations[custom_id],
        message,
        tool_calls,
        False,
        budget_note=exit_reason in EARLY_EXIT_REASONS,
        final_message=args.final_no_tools_message,
    )
    final_rows[custom_id] = row
    # Phase 5: persist the agent's account as report.json for the auditor — BEFORE the
    # terminal event below announces the run finished.
    _write_episode_report(ctx, message, exit_reason)
    live_log.log_final(ctx, message, round_index=round_index, exit_reason=exit_reason)
    append_completed_outputs(custom_id, row, conversations[custom_id], args)
    # Reclaim NVMe scratch: drop the agent's venv plus any oversized files/dirs it
    # left in the workspace (e.g. an accidental full-dataset download). The auditor
    # grades report.json + evidence/, never the workspace, so this is safe here.
    cleanup.prune_workspace(
        ctx.workspace,
        getattr(args, "prune_workspace_threshold_mb", cleanup.DEFAULT_PRUNE_THRESHOLD_MB),
        remove_venv=getattr(args, "prune_workspace_venv", True),
        label=ctx.arxiv_id,
    )


def _write_episode_report(ctx: ExecutionContext, message: dict[str, Any], exit_reason: str) -> None:
    """Best-effort ``report.json`` write; a filesystem error must not block finalization."""
    try:
        report_path = report.write_episode_report(ctx, message.get("content") or "", exit_reason)
    except OSError as exc:  # disk full / read-only run dir — degrade, don't strand the run
        print(
            f"report {ctx.arxiv_id}: write failed ({exc}); finalizing without report.json",
            file=sys.stderr,
        )
        return
    if report_path is not None:
        print(f"report {ctx.arxiv_id}: wrote {report_path}", file=sys.stderr)


__all__ = ["finalize_episode"]
