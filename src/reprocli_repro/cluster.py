"""The DeltaAI cluster profile — the operator-set substrate for the held GPU allocation.

The reproduction agent holds **one** SLURM allocation for the episode: the first
``run_gpu`` call acquires it and every later step runs into the same held node (see
``slurm.py`` / ``gpu_session.py``). A ``Cluster`` carries the facts an operator sets
*once* and the agent is merely *entitled to* — account, partition, node type (``hw``) —
plus the Apptainer image a GPU step runs inside. The model never picks these; on the
call that starts the session it picks only ``gpus``/``minutes`` (the hold's size and
hard lifetime, billed as wall clock in ``budget.py``).

DeltaAI is the only profile. The two per-run overrides are ``--partition`` (pick a
different node pool) and ``--apptainer-image`` (swap the sandbox .sif); everything else
is pinned here. The pinned partition matches the live ``scripts/*.sbatch``; the account
deliberately does not — GPU steps charge ``bfvr-dtai-gh`` while the sbatch jobs that
serve the brain charge ``betw-dtai-gh``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from typing import Any

DEFAULT_CLUSTER = "deltaai"
# Selects the profile when a caller names none: RECLAIM_CLUSTER=delta runs the x86 A100 profile.
CLUSTER_ENV = "RECLAIM_CLUSTER"


def selected_cluster_name() -> str:
    return os.environ.get(CLUSTER_ENV) or DEFAULT_CLUSTER

# Env override for the Slurm account, read per call (not at import) so runs can charge
# another allocation (e.g. betw-dtai-gh) without editing the profile.
SLURM_ACCOUNT_ENV = "REPROCLI_SLURM_ACCOUNT"


def _slurm_account(default: str | None) -> str | None:
    return os.environ.get(SLURM_ACCOUNT_ENV) or default

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
    sandbox_mem_gb: int | None = None    # per-process address-space cap (GiB) for agent CPU steps; None = uncapped
    arch: str = "aarch64"                # node CPU arch, rendered into agent-facing text
    torch_rule: str = ""                 # agent-facing paragraph on installing the CUDA torch build
    host_env: str | None = None          # host venv the sweep orchestrator activates (api_sweep.sh)
    known_absent: str = ""               # agent-facing bullet on packages with no wheel for this arch
    cpus_per_gpu: int = 60               # salloc --cpus-per-gpu; must fit gpus_per_node GPUs on one node
    mem_gb_per_gpu: int = 100            # salloc --mem per GPU (GB); same node-fit rule


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
        # The agent's JIT GPU steps charge bfvr, not the betw account the sbatch jobs
        # carry: the two are billed separately, so a sweep's brain/orchestrator node
        # comes out of betw while every run_gpu hold comes out of bfvr. NOTE the two
        # names — the PROJECT is bfvr, the SLURM ACCOUNT string is bfvr-dtai-gh (the
        # bare project code is rejected at submit with "Invalid account or
        # account/partition combination specified"). The QOS string tracks the account
        # string on DeltaAI and the two settle one update apart, so a queued job issued
        # under the old account parks in InvalidQOS until it is resubmitted.
        account="bfvr-dtai-gh",
        # ``ghx4`` (the 48 h batch pool) is the default; the faster-queueing
        # ``ghx4-interactive`` (≤4 nodes, 2 h) is one of the partitions the agent can
        # discover via the ``list_partitions`` tool and select per-step by passing
        # ``partition`` to ``run_gpu``. The profile pins only the *default*.
        partition="ghx4",
        apptainer_image=DEFAULT_APPTAINER_SIF,
        # Per-paper share of the brain node's quarter-node request (72 cores / 110G
        # at 1 GPU): 12 cores + 16G per agent CPU step, so six agents plus the vLLM
        # brain fit the cgroup and one runaway build can't OOM-kill the brain again
        # (job 2666353; enforcement in sandbox.py, build fan-out capped there).
        sandbox_cpus=12,
        sandbox_mem_gb=16,
        known_absent='- KNOWN-ABSENT with no aarch64 wheel: conda/micromamba, X11/OpenGL headers, flash-attn,\n  pytorch3d, mujoco<3 and similar x86-pinned stacks. Do NOT build these from source (a\n  flash-attn build eats an hour and still fails). Substitute (SDPA for flash-attn), stub\n  imports off the scoring path, or record a platform-availability finding — not a 100-round\n  build fight.',
        torch_rule=(
            "The one rule that matters on this aarch64/Grace node: torch from that CUDA index, never\n"
            "default PyPI (its aarch64 torch is CPU-only). Install the three together (mismatches give\n"
            "`undefined symbol`). The paper's exact pin rarely has an aarch64 CUDA wheel — take the nearest\n"
            "and note the substitution. The venv is on shared disk and survives releases."
        ),
    ),
    "delta": Cluster(
        name="delta",
        hw="a100",
        gpus_per_node=4,
        account="bfvr-delta-gpu",
        partition="gpuA100x4",
        apptainer_image="/work/nvme/bfvr/msalunkhe/images/cuda1290-agent-x86.sif",
        arch="x86_64",
        torch_rule=(
            "The one rule that matters on this x86_64/A100 node: install torch from the CUDA index\n"
            "(standard x86_64 CUDA wheels), never a CPU-only build. Install the three together\n"
            "(mismatches give `undefined symbol`). Take the nearest wheel to the paper's pin and note\n"
            "the substitution. The venv is on shared disk and survives releases."
        ),
        # A Delta A100x4/A40x4 node has 64 cores and 257 GB for 4 GPUs, so the DeltaAI
        # sizing (60 cores, 100 GB per GPU) makes every request for 2+ GPUs fail with
        # "Requested node configuration is not available". 16 cores and 60 GB per GPU
        # fit 4 GPUs on one node and bill as the GPU count (CPU=62.5, Mem=16/GB, GPU=1000).
        cpus_per_gpu=16,
        mem_gb_per_gpu=60,
        host_env="/work/nvme/bfvr/msalunkhe/envs/delta-x86",
        known_absent="- KNOWN-ABSENT in the image: conda/micromamba and X11/OpenGL headers.",
    ),
}


def cluster_defaults() -> dict[str, dict[str, Any]]:
    """The built-in default substrate per known cluster (source for ``list_partitions``).

    One source of truth for "the default choice for our known clusters": each entry
    is the account / default partition / node size / hw the profile pins, which the
    ``list_partitions`` tool surfaces alongside the live ``sinfo`` partition list.
    """
    return {
        name: {
            "account": _slurm_account(c.account),
            "default_partition": c.partition,
            "gpus_per_node": c.gpus_per_node,
            "hw": c.hw,
        }
        for name, c in _PROFILES.items()
    }


def resolve_cluster(
    name: str | None = None,
    *,
    partition: str | None = None,
    apptainer_image: str | None = None,
) -> Cluster:
    """The selected profile (RECLAIM_CLUSTER, default deltaai) with the per-run overrides applied."""
    name = name or selected_cluster_name()
    try:
        base = _PROFILES[name]
    except KeyError:
        raise SystemExit(f"unknown cluster {name!r}; choose from {', '.join(_PROFILES)}")
    return replace(
        base,
        account=_slurm_account(base.account),
        partition=partition if partition is not None else base.partition,
        apptainer_image=apptainer_image if apptainer_image is not None else base.apptainer_image,
    )
