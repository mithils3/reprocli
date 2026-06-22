"""Repro toolset — the agent's hands, assembled and dispatched.

The reproduction agent acts on its episode through four tools:

* ``workspace_bash`` -- cwd-confined shell (clone, venv, installs, run CPU work),
* ``read_file`` / ``write_file`` / ``apply_patch`` -- path-confined file ops,
* ``run_gpu`` -- the one metered path to a GPU (JIT ``salloc``, budget-charged).

``REPRO_TOOLS`` is the schema list advertised to the model (wired onto
``args.tools`` in ``cli_args``); ``REPRO_TOOL_HANDLERS`` maps each name to its
``(arguments, ctx)`` handler. ``execute_repro_tool_call`` is the single entry the
loop dispatches through (``dispatch.append_tool_results``): it parses arguments,
routes to the handler against this episode's ``ExecutionContext``, retries a
transient failure once, and trims the result to the shared tool budget -- the same
posture as the classifier's ``web_tools.execute_tool_call``, minus the read-only
``Paper``.
"""

from __future__ import annotations

from typing import Any

from reprocli_vllm.config.config import TOOL_RESULT_MAX_CHARS
from reprocli_vllm.tools.result_limits import is_transient_error, truncate_tool_result
from reprocli_vllm.tools.web_tools import parse_tool_arguments

from reprocli_repro.context import ExecutionContext
from reprocli_repro.tools.files import FILE_TOOL_HANDLERS, FILE_TOOLS
from reprocli_repro.tools.run_gpu import RUN_GPU_HANDLERS, RUN_GPU_TOOL
from reprocli_repro.tools.workspace_bash import WORKSPACE_BASH_HANDLERS, WORKSPACE_BASH_TOOL

REPRO_TOOLS: list[dict] = [WORKSPACE_BASH_TOOL, *FILE_TOOLS, RUN_GPU_TOOL]

REPRO_TOOL_HANDLERS: dict[str, Any] = {
    **WORKSPACE_BASH_HANDLERS,
    **FILE_TOOL_HANDLERS,
    **RUN_GPU_HANDLERS,
}


def execute_repro_tool_call(call: dict[str, Any], ctx: ExecutionContext) -> dict[str, Any]:
    """Route one tool call through the episode's ``ExecutionContext`` and trim it."""
    result = _run_tool_call(call, ctx)
    if is_transient_error(result):
        result = _run_tool_call(call, ctx)
        result["retried"] = True
    return truncate_tool_result(result, TOOL_RESULT_MAX_CHARS)


def _run_tool_call(call: dict[str, Any], ctx: ExecutionContext) -> dict[str, Any]:
    function = call.get("function") or {}
    name = str(function.get("name") or "")
    handler = REPRO_TOOL_HANDLERS.get(name)
    if handler is None:
        available = ", ".join(REPRO_TOOL_HANDLERS)
        return {"ok": False, "error": f"Unknown tool: {name}. Available tools: {available}"}
    try:
        arguments = parse_tool_arguments(function.get("arguments", {}))
    except Exception as exc:
        return {"ok": False, "tool": name, "error": f"{type(exc).__name__}: {exc}"}
    try:
        return handler(arguments, ctx)
    except Exception as exc:
        return {"ok": False, "tool": name, "error": f"{type(exc).__name__}: {exc}"}


__all__ = ["REPRO_TOOLS", "REPRO_TOOL_HANDLERS", "execute_repro_tool_call"]
