"""Cross-argument validation and derived-default resolution for the repro CLI.

Split out of ``cli_args.py`` to keep that module's surface (the argparse groups)
focused. ``parse_args`` calls ``validate`` to enforce the cross-argument rules and
``apply_defaults`` to resolve the repro defaults (system/final messages, the
JIT-allocation cluster profile, the advertised toolset, the trace path).
"""

from __future__ import annotations

import argparse

from reprocli_vllm.runtime.trace_io import trace_output_path

from reprocli_repro.cluster import from_args as resolve_cluster
from reprocli_repro.tools import build_repro_tools

REPRO_SYSTEM_MESSAGE = (
    "You are a reproduction agent. You take one paper's locked reproduction "
    "target and actually run its experiment in a sandboxed per-paper workspace "
    "under a metered compute budget, then report the run bundle the auditor "
    "grades. Spend budget deliberately; write durable evidence as you go. "
    "(Phase 0 placeholder operating prompt; the full toolset and instructions "
    "land in later phases.)"
)
REPRO_FINAL_NO_TOOLS_MESSAGE = (
    "The tool phase is finished. Produce the final structured submission now "
    "from the evidence gathered above. Return only the requested object."
)


def validate(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.tool_rounds < 1:
        parser.error("--tool-rounds must be >= 1")
    if args.num_prompts is not None and args.num_prompts < 1:
        parser.error("--num-prompts must be >= 1")
    if args.request_workers < 1:
        parser.error("--request-workers must be >= 1")
    if args.max_input_tokens < 1:
        parser.error("--max-input-tokens must be >= 1")
    if args.top_k is not None and args.top_k < 1:
        parser.error("--top-k must be >= 1")
    if args.microcompact_keep < 0:
        parser.error("--microcompact-keep must be >= 0")
    if not 0 < args.microcompact_threshold <= 1:
        parser.error("--microcompact-threshold must be in (0, 1]")
    if args.summarize_keep_tokens < 1:
        parser.error("--summarize-keep-tokens must be >= 1")
    if not 0 < args.summarize_threshold <= 1:
        parser.error("--summarize-threshold must be in (0, 1]")
    if args.budget_h100_hours < 0:
        parser.error("--budget-h100-hours must be >= 0")
    if args.gpus_per_node is not None and args.gpus_per_node < 1:
        parser.error("--gpus-per-node must be >= 1")
    if args.max_input_tokens + args.max_tokens > args.max_model_len:
        parser.error("--max-input-tokens + --max-tokens must fit within --max-model-len")
    if getattr(args, "apptainer_image", None):
        parser.error(
            "--apptainer-image (or $REPRO_APPTAINER_SIF) is incompatible with the "
            "mandatory bwrap sandbox; unset it to run agent steps under bwrap."
        )


def apply_defaults(args: argparse.Namespace) -> None:
    args.system_message = REPRO_SYSTEM_MESSAGE
    args.final_no_tools_message = REPRO_FINAL_NO_TOOLS_MESSAGE
    args.use_tools = True
    args.response_format = None
    # Resolve the JIT-allocation substrate once: the named profile merged with any
    # per-field overrides. slurm.py / the Phase-4 run_gpu tool read this.
    args.cluster_profile = resolve_cluster(args)
    # Phase 4: advertise the execution toolset (workspace_bash, file ops, the
    # metered run_gpu) to the model. run_gpu's GPU cap is the resolved cluster's
    # per-node size, so the model picks a valid GPU count for this substrate. The
    # structured report (response_format) lands in Phase 5; until then the final
    # tools-off turn falls back to the classifier's default format.
    args.tools = build_repro_tools(args.cluster_profile.gpus_per_node)
    if args.trace_output is None:
        args.trace_output = trace_output_path(args.output)
