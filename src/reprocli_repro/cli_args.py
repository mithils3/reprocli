"""reprocli_repro CLI — its own argparse (deliberately not ``resolve_mode_settings``).

The reproduction agent attaches to an already-served brain (the same vLLM
endpoint the classifier/auditor use) and runs one paper's experiment under a
metered compute budget. ``parse_args`` returns a fully-resolved Namespace: repro
defaults applied (system/final messages, tool + response-format seams) and all
cross-argument validation enforced.

Phase 0 ships the stable surface the forked tool loop and the context-management
tiers need. Run-selection flags (``--paper-id`` / ``--lockfile`` / ``--runs-dir``)
are accepted now so the CLI shape is stable; they are consumed by the input
pipeline starting in Phase 1.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from reprocli_vllm.config.config import DEFAULT_MODEL

from reprocli_repro.cli_resolve import apply_defaults, validate
from reprocli_repro.inputs import DEFAULT_LOCKFILE_DATASET, DEFAULT_LOCKFILE_SPLIT

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
    group = parser.add_argument_group("run selection (consumed starting Phase 1)")
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
        "selection_band upper edge (0-8 -> 8h, 8-32 -> 32h, 32-96 -> 96h, "
        "96-192 -> 192h), falling back to 8h for unbanded rows.",
    )


def _add_outputs(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("outputs")
    group.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    group.add_argument("--save-round-jsonl", action="store_true")
