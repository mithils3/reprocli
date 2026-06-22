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
import os
from pathlib import Path

from reprocli_vllm.config.config import DEFAULT_MODEL, MAX_MODEL_LEN
from reprocli_vllm.runtime.trace_io import trace_output_path

from reprocli_repro.budget import HW_MULTIPLIER
from reprocli_repro.cluster import DEFAULT_CLUSTER, cluster_names, from_args as resolve_cluster
from reprocli_repro.inputs import DEFAULT_LOCKFILE_DATASET, DEFAULT_LOCKFILE_SPLIT
from reprocli_repro.reference import DEFAULT_DATASET as DEFAULT_BUNDLE_DATASET
from reprocli_repro.tools import REPRO_TOOLS

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
    _add_workspace(parser)
    _add_cluster(parser)
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
    group.add_argument("--seed", type=int, default=0, help="Sampling seed for --num-prompts (default: 0).")
    group.add_argument(
        "--run-id",
        help="Pin the run id (default: a fresh time+random id, so re-runs never collide).",
    )
    group.add_argument(
        "--lockfile",
        default=DEFAULT_LOCKFILE_DATASET,
        help=(
            "Audited lockfile carrying each paper's reproduction target. An HF dataset "
            "repo id (owner/name), an hf://datasets/<owner>/<name>/<file> reference, or "
            f"a local .jsonl path (default: {DEFAULT_LOCKFILE_DATASET})."
        ),
    )
    group.add_argument(
        "--split",
        default=DEFAULT_LOCKFILE_SPLIT,
        help=(
            "Which published split of the lockfile dataset to load: 'test' (the "
            "100-paper frozen benchmark, default) or 'validation' (the dev-15 split); "
            "aliases 'eval'/'dev' are accepted. Ignored for a local .jsonl / hf:// file."
        ),
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


def _add_workspace(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("workspace + reference (Phase 2)")
    group.add_argument(
        "--bundle-dataset",
        default=DEFAULT_BUNDLE_DATASET,
        help=f"Paper-bundle dataset the read-only reference/ is materialized from "
        f"(default: {DEFAULT_BUNDLE_DATASET}).",
    )
    group.add_argument(
        "--reference",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Materialize the read-only reference/ copy at setup (default: on).",
    )
    group.add_argument(
        "--build-venv",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Build the empty per-paper uv venv at setup (default: on).",
    )
    group.add_argument("--venv-python", help="Python version/path passed to `uv venv --python`.")


def _add_cluster(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("cluster / JIT GPU substrate")
    group.add_argument(
        "--cluster",
        choices=cluster_names(),
        default=DEFAULT_CLUSTER,
        help=f"Built-in cluster profile (account/partition/hw/modules) the agent's "
        f"JIT salloc uses (default: {DEFAULT_CLUSTER}). Override individual fields below.",
    )
    group.add_argument("--account", help="SLURM account (salloc -A); overrides the profile.")
    group.add_argument("--partition", help="SLURM partition (salloc -p); overrides the profile.")
    group.add_argument(
        "--gpus-per-node",
        type=int,
        help="Upper bound on a single step's --gpus; overrides the profile.",
    )
    group.add_argument(
        "--hw",
        choices=tuple(sorted(HW_MULTIPLIER)),
        help="Node hardware keying the H100-equiv budget multiplier; overrides the profile.",
    )
    group.add_argument(
        "--scratch-root",
        help="NVMe root for per-paper workspaces (Phase 7); overrides the profile.",
    )
    group.add_argument(
        "--apptainer-image",
        default=os.environ.get("REPRO_APPTAINER_SIF"),
        help="Phase 8 sandboxing seam: base .sif the GPU step is wrapped in. "
        "Defaults to $REPRO_APPTAINER_SIF.",
    )
    group.add_argument(
        "--modules",
        default="",
        help="Space-separated `module load` names prepended to each JIT GPU step; "
        "overrides the profile's modules.",
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
    if args.gpus_per_node is not None and args.gpus_per_node < 1:
        parser.error("--gpus-per-node must be >= 1")
    if args.max_input_tokens + args.max_tokens > args.max_model_len:
        parser.error("--max-input-tokens + --max-tokens must fit within --max-model-len")


def _apply_defaults(args: argparse.Namespace) -> None:
    args.system_message = REPRO_SYSTEM_MESSAGE
    args.final_no_tools_message = REPRO_FINAL_NO_TOOLS_MESSAGE
    args.use_tools = True
    # Phase 4: advertise the execution toolset (workspace_bash, file ops, the
    # metered run_gpu) to the model. The structured submission contract
    # (response_format) lands in Phase 5; until then the final tools-off turn
    # falls back to the classifier's default response format.
    args.tools = REPRO_TOOLS
    args.response_format = None
    # Resolve the JIT-allocation substrate once: the named profile merged with any
    # per-field overrides. slurm.py / the Phase-4 run_gpu tool read this.
    args.cluster_profile = resolve_cluster(args)
    if args.trace_output is None:
        args.trace_output = trace_output_path(args.output)
