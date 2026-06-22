"""Tool-call dispatch for the reproduce loop — the key fork from the classifier.

Where the classifier runs ``execute_tool_call(call, paper=paper)``, the repro
loop runs ``execute_repro_tool_call(call, ctx)`` so each call acts on this
episode's ``ExecutionContext`` (workspace, budget meter, allocation, evidence)
rather than a read-only ``Paper``.

The handler routing itself lives in ``tools/__init__.py`` (``REPRO_TOOLS`` — the
workspace shell, file read/write/patch, and the metered ``run_gpu`` tool); this
module owns only the conversation-shaping seam that records each call's result
into the running transcript and the loop-guard counters.
"""

from __future__ import annotations

from collections import Counter

from reprocli_vllm.runtime.loop_guards import record_tool_call
from reprocli_vllm.runtime.trace_io import assistant_message
from reprocli_vllm.vllm.io import tool_result_message

from reprocli_repro.context import ExecutionContext
from reprocli_repro.tools import execute_repro_tool_call

__all__ = ["append_tool_results", "execute_repro_tool_call"]


def append_tool_results(
    messages: list[dict],
    message: dict,
    tool_calls: list[dict],
    ctx: ExecutionContext,
    counts: Counter,
) -> None:
    messages.append(assistant_message(message, tool_calls))
    for call in tool_calls:
        result = execute_repro_tool_call(call, ctx)
        record_tool_call(counts, call, result)
        messages.append(tool_result_message(call, result))
