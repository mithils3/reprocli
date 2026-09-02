"""reprocli_repro CLI — its own argparse (deliberately not ``resolve_mode_settings``).

The reproduction agent attaches to an already-served brain (the same vLLM
endpoint the auditor uses) and runs one paper's experiment under a
metered compute budget. ``parse_args`` returns a fully-resolved Namespace: repro
defaults applied (system/final messages, tool + response-format seams) and all
cross-argument validation enforced.

``validate`` enforces the cross-argument rules and ``apply_defaults`` resolves the
repro defaults (system/final messages, the JIT-allocation cluster profile, the
advertised toolset, the trace path).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from reprocli_vllm.audit.h100 import band_ladder_text
from reprocli_vllm.config.config import DEFAULT_MODEL
from reprocli_vllm.runtime.trace_io import trace_output_path

from reprocli_repro.cleanup import DEFAULT_PRUNE_THRESHOLD_MB
from reprocli_repro.cluster import resolve_cluster
from reprocli_repro.dataset import DEFAULT_LOCKFILE_DATASET, DEFAULT_LOCKFILE_SPLIT
from reprocli_repro.inputs import DEFAULT_UNBANDED_BUDGET_H100_HOURS
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

# Sampling is left unset for every model: the request builder omits unset fields,
# so the served model's own generation_config defaults apply (vLLM recipe style).
MAX_TOKENS = 32768
# No harness-side input ceiling constant: __main__ reads the attached brain's own window
# off /v1/models and reserves MAX_TOKENS of it for the completion. This was a flat 128000
# for every model, which capped a 1M-context brain at 128K and made elide-compact fire
# against a ceiling the server had no part in -- DeepSeek-V4-Flash-0731 serves 1M and
# still died on context_budget in 16 of 27 runs of sweep 2883229.
REQUEST_WORKERS = 8
# Context management (guardrails in loop.py): tool stdout stays verbatim until elide-compact
# fires once COMPACT_THRESHOLD of the resolved input ceiling is crossed, then shrinks the old
# span's bulky tool results in place to an on-disk pointer, keeping COMPACT_KEEP_TOKENS of
# recent turns — plus all assistant reasoning — verbatim. The full output stays recoverable
# under evidence/, so an elided number is re-read, not re-computed.
COMPACT_ENABLED = True
COMPACT_KEEP_TOKENS = 20000
COMPACT_THRESHOLD = 0.70

# The reproduction prompt template is a fixed repo asset (was --prompt-file).
DEFAULT_PROMPT_FILE = Path("prompts/prompt_reproduce.txt")

# Run bundles + outputs land on the NVMe work filesystem, not the repo working
# dir — they get large and are scratch. Override the root with $REPRO_WORK_ROOT,
# or the individual paths with --runs-dir / --output. The prompt template stays a
# repo asset.
DEFAULT_WORK_ROOT = Path(os.environ.get("REPRO_WORK_ROOT", "/work/nvme/bfvr/msalunkhe/reprocli"))
DEFAULT_OUTPUT = DEFAULT_WORK_ROOT / "reproduce.jsonl"
DEFAULT_RUNS_DIR = DEFAULT_WORK_ROOT / "agent_runs"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="reprocli_repro", description=__doc__)
    _add_run_selection(parser)
    _add_workspace(parser)
    _add_cluster(parser)
    _add_endpoint(parser)
    _add_loop_limits(parser)
    _add_outputs(parser)
    args = parser.parse_args(argv)
    validate(parser, args)
    apply_defaults(args)
    return args


def _add_run_selection(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("run selection")
    group.add_argument("--paper-id", help="arXiv id of the single paper to reproduce.")
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
            "100-paper frozen benchmark, default) or 'validation' (the 14-paper dev split); "
            "aliases 'eval'/'dev' are accepted. Ignored for a local .jsonl / hf:// file."
        ),
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
        "--reference",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Materialize the read-only reference/ copy at setup (default: on).",
    )
    group.add_argument(
        "--prune-workspace-threshold-mb",
        type=float,
        default=DEFAULT_PRUNE_THRESHOLD_MB,
        help="When an episode finishes, delete workspace files larger than this many "
        "MB and workspace subdirectories whose total exceeds it, reclaiming accidental "
        "dataset downloads on the NVMe scratch. reference/ and evidence/ are never "
        f"touched; 0 disables (default: {DEFAULT_PRUNE_THRESHOLD_MB:g}).",
    )
    group.add_argument(
        "--prune-workspace-venv",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="When an episode finishes, delete the agent's Python venv(s) from the "
        "workspace whole (the multi-GB CUDA torch install is the biggest single "
        "reclaim). Applies even when the size threshold is 0 (default: on).",
    )


def _add_cluster(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("cluster / JIT GPU substrate (deltaai)")
    group.add_argument(
        "--partition",
        help="SLURM partition (salloc -p); overrides the deltaai profile's default (ghx4).",
    )
    group.add_argument(
        "--apptainer-image",
        default=os.environ.get("REPRO_APPTAINER_SIF"),
        help="Base .sif that backs the MANDATORY Apptainer sandbox — every agent step "
        "runs inside this read-only image. Defaults to the deltaai profile's pinned "
        "raw CUDA image (the agent installs torch itself); overrides it / $REPRO_APPTAINER_SIF.",
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


def _add_loop_limits(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("loop limits")
    group.add_argument(
        "--tool-rounds",
        type=int,
        default=300,
        help="Max model turns; the compute-budget guardrail is the real bound (default: 300).",
    )
    group.add_argument(
        "--budget-h100-hours",
        type=float,
        default=None,
        help="Flat per-episode compute ceiling in H100-equiv hours, applied to every "
        "paper. Omit to use the default: each paper's ceiling is derived from its "
        f"selection_band upper edge ({band_ladder_text()}), falling back to "
        f"{DEFAULT_UNBANDED_BUDGET_H100_HOURS:g}h for unbanded rows.",
    )


def _add_outputs(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("outputs")
    group.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    group.add_argument("--save-round-jsonl", action="store_true")


def validate(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.tool_rounds < 1:
        parser.error("--tool-rounds must be >= 1")
    if args.budget_h100_hours is not None and args.budget_h100_hours < 0:
        parser.error("--budget-h100-hours must be >= 0")


def _env_float(name: str) -> float | None:
    """Read an optional float override from the environment; unset/blank -> None."""
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be a number, got {raw!r}") from exc


def _env_int(name: str) -> int | None:
    """Read an optional int override from the environment; unset/blank -> None."""
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer, got {raw!r}") from exc


def apply_defaults(args: argparse.Namespace) -> None:
    args.system_message = REPRO_SYSTEM_MESSAGE
    args.final_no_tools_message = REPRO_FINAL_NO_TOOLS_MESSAGE
    args.use_tools = True
    args.prompt_file = DEFAULT_PROMPT_FILE
    # Sampling stays unset (the request builder omits None fields, deferring to the
    # served model's generation_config). REPROCLI_TOP_P is the one escape hatch: a
    # brain whose card recommends a different top_p for AGENTIC use than its
    # generation_config ships (DeepSeek-V4-Flash-0731: 0.95 agentic vs 1.0 in the
    # checkpoint) needs the agentic value, and this loop is that agentic case.
    # REPROCLI_TOP_K is the same hatch for a NON-OpenAI sampling field: top_k is not
    # an OpenAI chat-completions param, so a brain whose generation_config pins one
    # (Laguna-S-2.1: top_k 20) has it silently dropped by an OpenAI-compatible client
    # and runs off-distribution. Deferring to generation_config is not enough here --
    # vLLM only applies it to fields the request omits, and the omission is the bug.
    args.temperature = None
    args.top_p = _env_float("REPROCLI_TOP_P")
    args.top_k = _env_int("REPROCLI_TOP_K")
    args.max_tokens = MAX_TOKENS
    # Set from the attached brain's advertised window in __main__; a dry run attaches to
    # no server and issues no requests, so it stays None there.
    args.max_input_tokens = None
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
    args.cluster_profile = resolve_cluster(
        partition=getattr(args, "partition", None),
        apptainer_image=getattr(args, "apptainer_image", None),
    )
    # Phase 4: advertise the execution toolset (workspace_bash, file ops, the
    # metered run_gpu) to the model. run_gpu's GPU cap is the resolved cluster's
    # per-node size, so the model picks a valid GPU count for this substrate.
    args.tools = build_repro_tools(args.cluster_profile.gpus_per_node)
    args.trace_output = trace_output_path(args.output)
