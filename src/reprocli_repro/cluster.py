"""The DeltaAI cluster profile — the operator-set substrate for the JIT GPU allocator.

The reproduction agent provisions GPUs *just in time* (a fresh ``salloc`` per
``run_gpu`` step, released on completion — see ``slurm.py``); it never sits on a
pre-held allocation. A ``Cluster`` carries the facts an operator sets *once* and
the agent is merely *entitled to* — account, partition, node type (``hw``) — plus
the Apptainer image a GPU step runs inside. The model never picks these; per call
it picks only ``gpus``/``minutes`` (metered in ``budget.py``).

DeltaAI is the only profile. The two per-run overrides are ``--partition`` (pick a
different node pool for a step) and ``--apptainer-image`` (swap the sandbox .sif);
everything else is pinned to the live ``scripts/*.sbatch`` account/partition.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

DEFAULT_CLUSTER = "deltaai"

# DeltaAI's mandatory-sandbox image. We default to a raw NVIDIA CUDA image (12.9 + cuDNN,
# the ``devel`` flavor so ``nvcc`` and the host compilers are present) rather than an NGC
# PyTorch image: torch is NOT prebuilt here, so the agent installs the matched torch family
# itself from the aarch64 CUDA wheel index (see prompts/prompt_reproduce.txt). This sidesteps
# the NGC ``+nv`` torch ABI wall — no stock ``torchaudio``/``torchvision`` wheel matches an
# NGC ``+nv`` torch, and NGC PyTorch images don't ship torchaudio at all. The pinned sif is
# the CUDA base with the agent's CLI tools (git/curl/build tools/ffmpeg) layered in — built
# by scripts/cluster/build_cuda_sandbox.sh, since a bare CUDA image ships none of them and
# host ``module load`` can't reach inside the --cleanenv sandbox. Every agent step runs
# inside this read-only container (see sandbox.py); swap per-run / per-paper with
# --apptainer-image / $REPRO_APPTAINER_SIF.
DEFAULT_APPTAINER_SIF = "/work/nvme/bfvr/msalunkhe/cuda1290-agent.sif"


@dataclass(frozen=True)
class Cluster:
    """DeltaAI's allocation-time facts + GPU-step environment."""

    name: str
    hw: str                              # budget multiplier key (see budget.HW_MULTIPLIER)
    gpus_per_node: int                   # upper bound on a single step's --gpus
    account: str | None = None           # salloc -A
    partition: str | None = None         # salloc -p
    apptainer_image: str | None = None   # MANDATORY sandbox .sif every step runs inside (sandbox.py)
    sandbox_cpus: int | None = None      # cores per agent CPU step on the shared orchestrator node; None = uncapped


# The single built-in profile. DeltaAI strings are the exact ones the live scripts pass.
# GPU steps always run through a JIT salloc, so account/partition
# are mandatory. Every step runs inside the mandatory Apptainer sandbox (sandbox.py): the
# CUDA .sif is the read-only root, so the agent's CUDA toolchain — ``nvcc``, cuDNN, the CUDA
# libraries — comes from the image. No host ``module load`` (it would not exist inside the
# --cleanenv container). torch is NOT in the image; the agent installs a GH200 (aarch64)
# CUDA torch from the PyTorch wheel index as its first setup step.
_PROFILES: dict[str, Cluster] = {
    "deltaai": Cluster(
        name="deltaai",
        hw="gh200",
        gpus_per_node=4,
        account="betw-dtai-gh",
        # ``ghx4`` (the 48 h batch pool) is the default; the faster-queueing
        # ``ghx4-interactive`` (≤4 nodes, 2 h) is one of the partitions the agent can
        # discover via the ``list_partitions`` tool and select per-step by passing
        # ``partition`` to ``run_gpu``. The profile pins only the *default*.
        partition="ghx4",
        apptainer_image=DEFAULT_APPTAINER_SIF,
        # Caps each agent's CPU shell steps to 4 cores: six agents can share the node's
        # cgroup without one uncapped `-j nproc` build blowing the --mem cap and OOM-
        # killing the vLLM brain (see sandbox_limits.py).
        sandbox_cpus=4,
    ),
}


def cluster_names() -> tuple[str, ...]:
    """Names of the built-in profiles (just ``deltaai``)."""
    return tuple(_PROFILES)


def cluster_defaults() -> dict[str, dict[str, Any]]:
    """The built-in default substrate per known cluster (source for ``list_partitions``).

    One source of truth for "the default choice for our known clusters": each entry
    is the account / default partition / node size / hw the profile pins, which the
    ``list_partitions`` tool surfaces alongside the live ``sinfo`` partition list.
    """
    return {
        name: {
            "account": c.account,
            "default_partition": c.partition,
            "gpus_per_node": c.gpus_per_node,
            "hw": c.hw,
        }
        for name, c in _PROFILES.items()
    }


def resolve_cluster(
    name: str = DEFAULT_CLUSTER,
    *,
    partition: str | None = None,
    apptainer_image: str | None = None,
) -> Cluster:
    """The deltaai profile with the two per-run overrides (partition / image) applied."""
    try:
        base = _PROFILES[name]
    except KeyError:
        raise SystemExit(f"unknown cluster {name!r}; choose from {', '.join(_PROFILES)}")
    return replace(
        base,
        partition=partition if partition is not None else base.partition,
        apptainer_image=apptainer_image if apptainer_image is not None else base.apptainer_image,
    )


def from_args(args: Any) -> Cluster:
    """Resolve the deltaai profile from a parsed CLI namespace (--partition / --apptainer-image)."""
    return resolve_cluster(
        partition=getattr(args, "partition", None),
        apptainer_image=getattr(args, "apptainer_image", None),
    )
