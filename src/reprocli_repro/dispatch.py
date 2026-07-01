"""Tool-call dispatch for the reproduce loop — the key fork from the classifier.

Where the classifier runs ``execute_tool_call(call, paper=paper)``, the repro
loop runs ``execute_repro_tool_call(call, ctx)`` so each call acts on this
episode's ``ExecutionContext`` (workspace, budget meter, allocation, evidence)
rather than a read-only ``Paper``.

The handler routing itself lives in ``tools/__init__.py`` (``build_repro_tools`` —
the workspace shell, file read/write/patch, and the metered ``run_gpu`` tool); this
module owns only the conversation-shaping seam that records each call's result
into the running transcript.
"""

from __future__ import annotations

from reprocli_vllm.runtime.trace_io import assistant_message
from reprocli_vllm.vllm.io import tool_result_message

from reprocli_repro import live_log
from reprocli_repro.context import ExecutionContext
from reprocli_repro.tools import execute_repro_tool_call

__all__ = ["append_tool_results", "execute_repro_tool_call"]


def append_tool_results(
    messages: list[dict],
    message: dict,
    tool_calls: list[dict],
    ctx: ExecutionContext,
    round_index: int | None = None,
) -> None:
    messages.append(assistant_message(message, tool_calls))
    # Stream to <run_dir>/agent.log: the round's reasoning first, then each call's
    # command before it runs and its result the moment it returns (see live_log).
    live_log.log_round_open(ctx, message, round_index=round_index)
    for call in tool_calls:
        live_log.log_call_start(ctx, call)
        result = execute_repro_tool_call(call, ctx)
        messages.append(tool_result_message(call, result))
        live_log.log_call_result(ctx, result)
