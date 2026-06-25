"""Cluster profiles — the operator-set substrate for the JIT GPU allocator.

The reproduction agent provisions GPUs *just in time* (a fresh ``salloc`` per
``run_gpu`` step, released on completion — see ``slurm.py``); it never sits on a
pre-held allocation. A ``Cluster`` carries the facts an operator sets *once* and
the agent is merely *entitled to* — account, partition, node type (``hw``) — plus
the environment a GPU step needs (modules, optional Apptainer image, NVMe scratch
root). The model never picks these; per call it picks only ``gpus``/``minutes``
(metered in ``budget.py``).

``resolve_cluster`` merges a named built-in profile with per-field CLI overrides
so the substrate works on *any* SLURM cluster: pick the closest profile, override
the strings that differ. DeltaAI is the default, mirroring the live
``scripts/*.sbatch`` account/partition.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable

from reprocli_repro.budget import HW_MULTIPLIER

DEFAULT_CLUSTER = "deltaai"

# DeltaAI's mandatory-sandbox image. We default to a raw NVIDIA CUDA image (12.9 + cuDNN,
# the ``devel`` flavor so ``nvcc`` and the host compilers are present) rather than an NGC
# PyTorch image: torch is NOT prebuilt here, so the agent installs the matched torch family
# itself from the aarch64 CUDA wheel index (see prompts/prompt_reproduce.txt). This sidesteps
# the NGC ``+nv`` torch ABI wall — no stock ``torchaudio``/``torchvision`` wheel matches an
# NGC ``+nv`` torch, and NGC PyTorch images don't ship torchaudio at all. Every agent step
# runs inside this read-only container (see sandbox.py); swap per-run / per-paper with
# --apptainer-image / $REPRO_APPTAINER_SIF.
DEFAULT_APPTAINER_SIF = "/work/nvme/bfvr/msalunkhe/cuda1290-cudnn-devel.sif"


@dataclass(frozen=True)
class Cluster:
    """One SLURM cluster's allocation-time facts + GPU-step environment."""

    name: str
    hw: str                              # budget multiplier key (see budget.HW_MULTIPLIER)
    gpus_per_node: int                   # upper bound on a single step's --gpus
    account: str | None = None           # salloc -A  (every built-in JIT profile sets one)
    partition: str | None = None         # salloc -p
    modules: tuple[str, ...] = ()         # legacy host `module load` names — inert under the container sandbox
    apptainer_image: str | None = None   # MANDATORY sandbox .sif every step runs inside (sandbox.py); None => must pass --apptainer-image
    scratch_root: str | None = None      # NVMe root for per-paper workspaces (Phase 7)


# Built-ins. DeltaAI/Delta strings are the exact ones the live scripts pass
# (docs/slurm/clusters.md). Every profile is a real SLURM target — GPU steps
# always run through a JIT salloc, so an account/partition is mandatory.
_PROFILES: dict[str, Cluster] = {
    # Every step runs inside the mandatory Apptainer sandbox (sandbox.py): the CUDA
    # .sif is the read-only root, so the agent's CUDA toolchain — ``nvcc``, cuDNN, the
    # CUDA libraries — comes from the image. No host ``module load`` (it would not exist
    # inside the --cleanenv container). torch is NOT in the image; the agent installs a
    # GH200 (aarch64) CUDA torch from the PyTorch wheel index as its first setup step.
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
        scratch_root="/work/nvme",
        apptainer_image=DEFAULT_APPTAINER_SIF,
    ),
    # Delta H200 (x86) has no pinned sandbox image — pass --apptainer-image /
    # $REPRO_APPTAINER_SIF (require_apptainer hard-fails the run otherwise).
    "delta-h200": Cluster(
        name="delta-h200",
        hw="h200",
        gpus_per_node=8,
        account="bfvr-delta-gpu",
        partition="gpuH200x8-interactive",
        scratch_root="/work/nvme",
    ),
}


def cluster_names() -> tuple[str, ...]:
    """Names accepted by ``--cluster`` (for argparse ``choices``)."""
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
    account: str | None = None,
    partition: str | None = None,
    gpus_per_node: int | None = None,
    hw: str | None = None,
    modules: Iterable[str] | None = None,
    apptainer_image: str | None = None,
    scratch_root: str | None = None,
) -> Cluster:
    """Built-in profile ``name`` with any non-None field overridden by the caller."""
    try:
        base = _PROFILES[name]
    except KeyError:
        raise SystemExit(f"unknown --cluster {name!r}; choose from {', '.join(_PROFILES)}")
    if hw is not None and hw not in HW_MULTIPLIER:
        raise SystemExit(f"unknown --hw {hw!r}; known: {', '.join(sorted(HW_MULTIPLIER))}")
    return replace(
        base,
        account=account if account is not None else base.account,
        partition=partition if partition is not None else base.partition,
        gpus_per_node=gpus_per_node if gpus_per_node is not None else base.gpus_per_node,
        hw=hw if hw is not None else base.hw,
        modules=tuple(modules) if modules is not None else base.modules,
        apptainer_image=apptainer_image if apptainer_image is not None else base.apptainer_image,
        scratch_root=scratch_root if scratch_root is not None else base.scratch_root,
    )


def from_args(args: Any) -> Cluster:
    """Resolve the cluster from a parsed CLI namespace (``--cluster`` + overrides)."""
    raw_modules = (getattr(args, "modules", "") or "").split()
    return resolve_cluster(
        getattr(args, "cluster", DEFAULT_CLUSTER),
        account=getattr(args, "account", None),
        partition=getattr(args, "partition", None),
        gpus_per_node=getattr(args, "gpus_per_node", None),
        hw=getattr(args, "hw", None),
        modules=raw_modules or None,
        apptainer_image=getattr(args, "apptainer_image", None),
        scratch_root=getattr(args, "scratch_root", None),
    )
