"""Tool-call dispatch for the reproduce loop — the key fork from the classifier.

Where the classifier runs ``execute_tool_call(call, paper=paper)``, the repro
loop runs ``execute_repro_tool_call(call, ctx)`` so each call acts on this
episode's ``ExecutionContext`` (workspace, budget meter, allocation, evidence)
rather than a read-only ``Paper``.

Phase 0 ships the seam with a stub handler; Phase 4 replaces the stub with
``tools/`` handler routing (``REPRO_TOOLS``) — the workspace shell, file
read/write/patch, and the metered ``run_gpu`` tool.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from reprocli_vllm.runtime.loop_guards import record_tool_call
from reprocli_vllm.runtime.trace_io import assistant_message
from reprocli_vllm.vllm.io import tool_result_message

from reprocli_repro.context import ExecutionContext


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


def execute_repro_tool_call(call: dict[str, Any], ctx: ExecutionContext) -> dict[str, Any]:
    """Route one tool call through the episode's ``ExecutionContext``.

    Phase 4 wires ``tools/__init__.py`` here; until then the loop is
    import-clean and reports tools as unwired rather than executing anything.
    """
    name = str(((call.get("function") or {}).get("name")) or "unknown_tool")
    return {"ok": False, "tool": name, "error": "repro toolset is not wired until Phase 4"}
