"""Repro toolset — the agent's hands, assembled and dispatched.

The reproduction agent acts on its episode through these tools:

* ``workspace_bash`` -- cwd-confined shell (clone, venv, installs, run CPU work,
  **and all file reading** via ``grep``/``sed``/``cat`` -- there is no read_file
  tool: targeted shell reads are far cheaper than dumping whole files to context),
* ``write_file`` / ``apply_patch`` -- path-confined file writes/edits,
* ``fetch_url`` -- read-only fetch of a public http(s) URL (docs, wheel index, raw
  repo files); there is no general web search, so it fetches URLs the agent knows,
* ``list_partitions`` -- read-only ``sinfo`` of the cluster's partitions (node pools)
  + the known-cluster defaults, so the agent can pick a ``run_gpu`` ``partition``
  instead of the profile's hardcoded default,
* ``run_gpu`` -- the one metered path to a GPU: a ``salloc`` allocation held across
  calls (``srun --jobid`` per step, released on ``release=true``/teardown), billed by
  wall clock (``gpu_session``); ``partition`` (optional) selects the pool to hold.

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

from reprocli_repro.cluster import DEFAULT_CLUSTER, resolve_cluster
from reprocli_repro.context import ExecutionContext
from reprocli_repro.tools.fetch import FETCH_TOOL_HANDLERS, FETCH_TOOLS
from reprocli_repro.tools.files import FILE_TOOL_HANDLERS, FILE_TOOLS
from reprocli_repro.tools.partitions import LIST_PARTITIONS_HANDLERS, LIST_PARTITIONS_TOOLS
from reprocli_repro.tools.run_gpu import RUN_GPU_HANDLERS, run_gpu_tool
from reprocli_repro.tools.workspace_bash import WORKSPACE_BASH_HANDLERS, WORKSPACE_BASH_TOOL

# The per-node GPU cap baked into run_gpu's schema is cluster-specific; cli_args
# rebuilds the toolset with the resolved cluster's gpus_per_node. This default
# covers the common case (the default cluster profile).
_DEFAULT_GPUS_PER_NODE = resolve_cluster(DEFAULT_CLUSTER).gpus_per_node


def build_repro_tools(gpus_per_node: int = _DEFAULT_GPUS_PER_NODE) -> list[dict]:
    """The tool schemas advertised to the model, with run_gpu's GPU cap = node size."""
    return [
        WORKSPACE_BASH_TOOL,
        *FILE_TOOLS,
        *FETCH_TOOLS,
        *LIST_PARTITIONS_TOOLS,
        run_gpu_tool(gpus_per_node),
    ]


REPRO_TOOLS: list[dict] = build_repro_tools()

REPRO_TOOL_HANDLERS: dict[str, Any] = {
    **WORKSPACE_BASH_HANDLERS,
    **FILE_TOOL_HANDLERS,
    **FETCH_TOOL_HANDLERS,
    **LIST_PARTITIONS_HANDLERS,
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


__all__ = ["REPRO_TOOLS", "REPRO_TOOL_HANDLERS", "build_repro_tools", "execute_repro_tool_call"]
