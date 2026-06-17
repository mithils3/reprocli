"""reprocli_repro CLI — its own argparse (deliberately not ``resolve_mode_settings``).

The reproduction agent attaches to an already-served brain (the same vLLM
endpoint the classifier/auditor use) and runs one paper's experiment under a
metered compute budget. ``parse_args`` returns a fully-resolved Namespace: repro
defaults applied (system/final messages, tool + response-format seams) and all
cross-argument validation enforced.

Phase 0 ships the stable surface the forked tool loop and the context-management
tiers need. Run-selection flags (``--paper-id`` / ``--lockfile`` / ``--runs-dir``
/ ``--prompt-file`` / ``--num-prompts``) are accepted now so the CLI shape is
stable; they are consumed by the input pipeline starting in Phase 1.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from reprocli_vllm.config.config import DEFAULT_MODEL, MAX_MODEL_LEN
from reprocli_vllm.runtime.trace_io import trace_output_path

DEFAULT_OUTPUT = Path("outputs/repro/reproduce.jsonl")
DEFAULT_PROMPT_FILE = Path("prompts/prompt_reproduce.txt")
DEFAULT_RUNS_DIR = Path("outputs/repro/agent_runs")

# Phase 0 placeholders; Phase 1 swaps in the real operating prompt file and
# Phase 5 the structured submission contract. The loop reads these off ``args``.
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="reprocli_repro", description=__doc__)
    _add_run_selection(parser)
    _add_endpoint(parser)
    _add_sampling(parser)
    _add_context_management(parser)
    _add_outputs(parser)
    args = parser.parse_args(argv)
    _validate(parser, args)
    _apply_defaults(args)
    return args


def _add_run_selection(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("run selection (consumed starting Phase 1)")
    group.add_argument("--paper-id", help="arXiv id of the single paper to reproduce.")
    group.add_argument("--num-prompts", type=int, help="Reproduce a random N papers instead of one.")
    group.add_argument(
        "--lockfile",
        type=Path,
        help="Audit-pool extracted JSONL (the lockfile rows) carrying each paper's target.",
    )
    group.add_argument(
        "--prompt-file",
        type=Path,
        default=DEFAULT_PROMPT_FILE,
        help=f"Reproduction prompt template (default: {DEFAULT_PROMPT_FILE}).",
    )
    group.add_argument(
        "--runs-dir",
        type=Path,
        default=DEFAULT_RUNS_DIR,
        help=(
            "Root of the run bundles written to <runs-dir>/<arxiv_id>/...; this is "
            f"the S6->S7 contract the auditor reads (default: {DEFAULT_RUNS_DIR})."
        ),
    )


def _add_endpoint(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("brain endpoint")
    group.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Model id sent in chat-completion requests (default matches the served brain).",
    )
    group.add_argument(
        "--vllm-server-url",
        help=(
            "Base URL of the already-served brain. If omitted the runner also "
            "checks $REPROCLI_SERVER_URL and $REPROCLI_ENDPOINT_FILE (published by "
            "reprocli_serve). The repro agent does not self-host a model."
        ),
    )
    group.add_argument(
        "--served-model-name",
        help="Model id to send when attached to a server (defaults to the id it advertises).",
    )


def _add_sampling(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("sampling and loop limits")
    group.add_argument("--max-tokens", type=int, default=8192)
    group.add_argument("--max-input-tokens", type=int, default=128000)
    group.add_argument("--max-model-len", type=int, default=MAX_MODEL_LEN)
    group.add_argument("--temperature", type=float, default=1.0)
    group.add_argument("--top-p", type=float, default=0.95)
    group.add_argument("--top-k", type=int, default=40)
    group.add_argument(
        "--tool-rounds",
        type=int,
        default=40,
        help="Max model turns; the compute-budget guardrail is the real bound (default: 40).",
    )
    group.add_argument("--max-repeated-tool-calls", type=int, default=2)
    group.add_argument("--request-workers", type=int, default=8)
    group.add_argument(
        "--budget-h100-hours",
        type=float,
        default=8.0,
        help="Per-episode compute ceiling in H100-equiv hours the loop guardrail enforces.",
    )


def _add_context_management(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("context management")
    group.add_argument(
        "--microcompact",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Elide stale tool results once the soft threshold is crossed (default: on).",
    )
    group.add_argument(
        "--microcompact-keep",
        type=int,
        default=3,
        help="Number of most-recent tool results kept verbatim when compacting (default: 3).",
    )
    group.add_argument(
        "--microcompact-threshold",
        type=float,
        default=0.8,
        help="Soft threshold as a fraction of --max-input-tokens (default: 0.8).",
    )


def _add_outputs(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("outputs")
    group.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    group.add_argument("--trace-output", type=Path)
    group.add_argument("--save-round-jsonl", action="store_true")


def _validate(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.tool_rounds < 1:
        parser.error("--tool-rounds must be >= 1")
    if args.num_prompts is not None and args.num_prompts < 1:
        parser.error("--num-prompts must be >= 1")
    if args.request_workers < 1:
        parser.error("--request-workers must be >= 1")
    if args.max_repeated_tool_calls < 1:
        parser.error("--max-repeated-tool-calls must be >= 1")
    if args.max_input_tokens < 1:
        parser.error("--max-input-tokens must be >= 1")
    if args.top_k is not None and args.top_k < 1:
        parser.error("--top-k must be >= 1")
    if args.microcompact_keep < 0:
        parser.error("--microcompact-keep must be >= 0")
    if not 0 < args.microcompact_threshold <= 1:
        parser.error("--microcompact-threshold must be in (0, 1]")
    if args.budget_h100_hours < 0:
        parser.error("--budget-h100-hours must be >= 0")
    if args.max_input_tokens + args.max_tokens > args.max_model_len:
        parser.error("--max-input-tokens + --max-tokens must fit within --max-model-len")


def _apply_defaults(args: argparse.Namespace) -> None:
    args.system_message = REPRO_SYSTEM_MESSAGE
    args.final_no_tools_message = REPRO_FINAL_NO_TOOLS_MESSAGE
    args.use_tools = True
    # The repro toolset (Phase 4) and the structured submission contract (Phase 5)
    # fill these; left unset, the loop is import-clean but has nothing to dispatch.
    args.tools = None
    args.response_format = None
    if args.trace_output is None:
        args.trace_output = trace_output_path(args.output)
