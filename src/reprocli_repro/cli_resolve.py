"""Cross-argument validation and derived-default resolution for the repro CLI.

Split out of ``cli_args.py`` to keep that module's surface (the argparse groups)
focused. ``parse_args`` calls ``validate`` to enforce the cross-argument rules and
``apply_defaults`` to resolve the repro defaults (system/final messages, the
JIT-allocation cluster profile, the advertised toolset, the trace path).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from reprocli_vllm.runtime.trace_io import trace_output_path

from reprocli_repro.cluster import from_args as resolve_cluster
from reprocli_repro.report import REPORT_RESPONSE_FORMAT
from reprocli_repro.tools import build_repro_tools

REPRO_SYSTEM_MESSAGE = (
    "You are a reproduction agent. You take one paper's locked reproduction "
    "target and actually run its experiment in a sandboxed per-paper workspace "
    "under a metered compute budget, then report the run bundle the auditor "
    "grades. Spend budget deliberately; write durable evidence as you go."
)
REPRO_FINAL_NO_TOOLS_MESSAGE = (
    "The tool phase is over. Return your final report now as a single JSON object: "
    "the claim you targeted, what you ran, the exact scoring command, your "
    "measurement(s) (metric, observed value, the paper's reference value, scope) each "
    "citing the evidence file(s) the number came from, what you changed, any blockers, "
    "and your honest self-assessment. This is your account of the run, not the verdict "
    "-- the auditor grades it. Return only the JSON object."
)

# Sampling + loop-limit knobs, formerly CLI flags (C7-approved: never varied non-default
# on the repro path — the serve profiles own sampling). Set on the resolved namespace so
# the shared build_chat_completion_request / compaction / loop read them straight off args.
TEMPERATURE = 1.0
TOP_P = 0.95
TOP_K = 40
# Qwen3.6 thinking-mode sampling for precise coding (temp/top_k/min_p; top_p stays
# 0.95). The defaults above match MiniMax's recommendation; apply_sampling_for_model
# swaps these in when the served model is a Qwen3 variant.
QWEN3_TEMPERATURE = 0.6
QWEN3_TOP_K = 20
QWEN3_MIN_P = 0.0
MAX_TOKENS = 32768
MAX_INPUT_TOKENS = 128000
REQUEST_WORKERS = 8
# Context management (guardrails.py): tool stdout stays verbatim until elide-compact
# fires once COMPACT_THRESHOLD of MAX_INPUT_TOKENS is crossed, then it shrinks the old
# span's bulky tool results in place to an on-disk pointer, keeping COMPACT_KEEP_TOKENS of
# recent turns — plus all assistant reasoning — verbatim. The full output stays recoverable
# under evidence/, so an elided number is re-read, not re-computed.
COMPACT_ENABLED = True
COMPACT_KEEP_TOKENS = 20000
COMPACT_THRESHOLD = 0.70

# The reproduction prompt template is a fixed repo asset (was --prompt-file).
DEFAULT_PROMPT_FILE = Path("prompts/prompt_reproduce.txt")


def validate(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.tool_rounds < 1:
        parser.error("--tool-rounds must be >= 1")
    if args.budget_h100_hours is not None and args.budget_h100_hours < 0:
        parser.error("--budget-h100-hours must be >= 0")


def apply_sampling_for_model(args: argparse.Namespace, model: str | None) -> None:
    """Switch to Qwen3's recommended thinking-mode sampling when the brain is a Qwen3.

    The defaults resolved in ``apply_defaults`` match MiniMax's recommendation. This
    is called once the served model id is known (``__main__``), so a Qwen3 brain gets
    temp 0.6 / top_k 20 / min_p 0.0 (top_p stays 0.95) without a CLI flag.
    """
    if model and "qwen3" in model.lower():
        args.temperature = QWEN3_TEMPERATURE
        args.top_k = QWEN3_TOP_K
        args.min_p = QWEN3_MIN_P


def apply_defaults(args: argparse.Namespace) -> None:
    args.system_message = REPRO_SYSTEM_MESSAGE
    args.final_no_tools_message = REPRO_FINAL_NO_TOOLS_MESSAGE
    args.use_tools = True
    args.prompt_file = DEFAULT_PROMPT_FILE
    # Fixed sampling + loop knobs (were CLI flags). The shared request builder, the
    # compaction tier, guardrails and the loop read these straight off the namespace.
    args.temperature = TEMPERATURE
    args.top_p = TOP_P
    args.top_k = TOP_K
    args.min_p = None
    args.max_tokens = MAX_TOKENS
    args.max_input_tokens = MAX_INPUT_TOKENS
    args.request_workers = REQUEST_WORKERS
    args.compact_enabled = COMPACT_ENABLED
    args.compact_keep_tokens = COMPACT_KEEP_TOKENS
    args.compact_threshold = COMPACT_THRESHOLD
    # Phase 5: the forced final pass (tools off) is schema-constrained to the agent's
    # report.json -- its account of the run, which the loop persists to the bundle for
    # the auditor to grade. build_chat_completion_request sends tools XOR this format.
    args.response_format = REPORT_RESPONSE_FORMAT
    # Resolve the JIT-allocation substrate once: the named profile merged with any
    # per-field overrides. slurm.py / the Phase-4 run_gpu tool read this.
    args.cluster_profile = resolve_cluster(args)
    # Phase 4: advertise the execution toolset (workspace_bash, file ops, the
    # metered run_gpu) to the model. run_gpu's GPU cap is the resolved cluster's
    # per-node size, so the model picks a valid GPU count for this substrate.
    args.tools = build_repro_tools(args.cluster_profile.gpus_per_node)
    args.trace_output = trace_output_path(args.output)
