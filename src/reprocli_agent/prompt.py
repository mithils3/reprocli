from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

SYSTEM_PROMPT = """\
You are a reproduction agent for an ML-paper benchmark running on the Delta HPC cluster.
You reproduce papers inside Apptainer containers submitted through SLURM.
Work entirely inside the sandbox working directory unless a bash command explicitly
references an absolute path (e.g. /work/nvme/$USER).

Follow these steps in order. Save intermediate results as JSON/log files using write_file.

STEP 1 — INSPECT HOST ENVIRONMENT
Run the commands below and write the results to host_profile.json:
  uname -m
  which apptainer && apptainer --version
  nvidia-smi
  sinfo
  df -h
  ls -ld /work/nvme/$USER /work/hdd/$USER 2>/dev/null || true

Record host_arch (x86_64 or aarch64). This determines which base images are safe to use.

STEP 2 — CLONE AND INSPECT REPO
Clone from verified_links.code. Then:
  a. Call list_files(path="<repo-dir>") to see the full directory tree.
  b. Read the key files you find: README, requirements.txt, environment.yml,
     pyproject.toml, setup.py, Dockerfile, scripts/, configs/, examples/.
     Use read_file for local files after cloning, or github_browse(repo, path=<file>)
     before cloning. github_browse also accepts a directory path and returns a listing.
  c. Identify: required Python version, CUDA version, PyTorch/JAX version, packages,
     dataset/model download commands, training/eval entry-point commands.
Write all findings to repo_profile.json.

STEP 3 — PLAN ENVIRONMENT
Apptainer builds for the host architecture, so the container arch must match the
compute node arch. On Delta the compute nodes are x86_64; build on a Delta login node.

ALWAYS prefer NVIDIA NGC base images (nvcr.io/nvidia/) — they publish multi-arch
manifests covering both x86_64 and aarch64, so the same From: line works on either host:
  nvcr.io/nvidia/pytorch:24.05-py3          (PyTorch + CUDA, both arches)
  nvcr.io/nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04  (bare CUDA, both arches)

Avoid pytorch/pytorch:* or tensorflow/tensorflow:*-gpu — those are x86_64-only and
will fail on aarch64 build hosts even if the target compute node is x86_64.

If the repo requires a specific PyTorch version, pick the closest NGC tag and install
the exact version via pip inside %post rather than relying on the image's bundled version.

Write env_plan.json with: host_arch, base_image, python_version, cuda_version, packages, notes.

STEP 4 — BUILD CONTAINER
Write paper.def (Apptainer definition file). Example structure:
  Bootstrap: docker
  From: nvcr.io/nvidia/pytorch:24.05-py3
  %post
      pip install --upgrade pip
      pip install <repo-specific packages>
      ...
  %environment
      export PYTHONPATH=/workspace:$PYTHONPATH
Then run: apptainer build paper.sif paper.def   (use timeout=1800)
Capture stdout/stderr to build.log.
If the build fails with a manifest/architecture error, confirm the base image has a
manifest for the host arch (check with: apptainer inspect --deffile <image>).

STEP 5 — SMOKE TEST
  apptainer exec paper.sif python3 --version
  apptainer exec paper.sif python3 -c "import torch; print(torch.__version__)"
  srun --gres=gpu:nvidia_a100:1 apptainer exec --nv paper.sif \\
    python3 -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
Write to smoke_test.log and gpu_test.log.

STEP 6 — GENERATE LAUNCHERS
Write reproduce.sh — the experiment commands to run inside the container:
  #!/usr/bin/env bash
  set -euo pipefail
  cd /workspace
  python3 download_data.py   # if needed
  python3 train.py ...
  python3 eval.py ...

Write slurm_run.sh — the SBATCH script:
  #!/usr/bin/env bash
  #SBATCH -J paper_repro
  #SBATCH -A bfvr-delta-gpu
  #SBATCH -p gpuA100x4
  #SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
  #SBATCH --gres=gpu:nvidia_a100:1
  #SBATCH --mem=64G --time=04:00:00
  #SBATCH -o slurm-%j.out -e slurm-%j.err
  set -euo pipefail
  export APPTAINERENV_HF_HOME=/work/nvme/$USER/hf_cache
  export APPTAINERENV_WANDB_MODE=offline
  apptainer exec --nv \\
    --bind "$PWD":/workspace \\
    --bind /work/nvme/$USER:/scratch \\
    paper.sif bash /workspace/reproduce.sh

STEP 7 — RUN EXPERIMENT
Submit: sbatch slurm_run.sh
Poll with: squeue -u "$USER"
Read output: tail -n 200 slurm-<jobid>.out
Write combined output to run.log.

STEP 8 — REPAIR LOOP (if any step fails)
  Missing apt library          → edit paper.def, rebuild paper.sif (timeout=1800)
  Missing Python package       → edit paper.def %post section, rebuild
  Wrong CUDA/PyTorch version   → change base image in paper.def, rebuild
  Wrong repo command/path      → edit reproduce.sh only (no rebuild)
  Wrong SLURM resources        → edit slurm_run.sh only (no rebuild)
  Dataset/storage issue        → edit reproduce.sh or slurm_run.sh binds/env vars
  Code compatibility bug       → patch repo files; rebuild only if deps changed
Return to the relevant step and retry.

FINAL OUTPUT
Once you have metric values from run.log, emit a single JSON object — no prose, no fences:
  {
    "reproduction_status": "success" | "partial" | "failed",
    "metric_results": [{"metric": <name>, "actual_value": <number|null>}],
    "claim_supported": true | false | null,
    "claim_assessment": "<one paragraph assessing all results against central_claim>",
    "failure_reason": "<only if failed>"
  }

Metric names must exactly match verification_targets[].metric.
Do not fabricate values. Only report what you observed in actual command output."""


@dataclass
class SignalEntry:
    value: bool
    evidence: str


@dataclass
class VerificationTarget:
    metric: str
    expected_value: float
    source: str
    conditions: str


@dataclass
class BenchmarkEntry:
    custom_id: str
    central_claim: str
    claim_evidence: str
    mre_config: str
    web_verification: str
    verified_links: dict[str, list[str]]
    signals: dict[str, SignalEntry]
    verification_targets: list[VerificationTarget]
    agent_task: str
    h100_hours_estimate: float
    h100_estimate_basis: str
    score: int | None = None
    tier: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BenchmarkEntry:
        signals = {
            k: SignalEntry(value=v["value"], evidence=v["evidence"])
            for k, v in d.get("signals", {}).items()
        }
        targets = [
            VerificationTarget(
                metric=t["metric"],
                expected_value=t["expected_value"],
                source=t["source"],
                conditions=t["conditions"],
            )
            for t in d.get("verification_targets", [])
        ]
        return cls(
            custom_id=d["custom_id"],
            central_claim=d["central_claim"],
            claim_evidence=d.get("claim_evidence", ""),
            mre_config=d["mre_config"],
            web_verification=d.get("web_verification", ""),
            verified_links=d.get("verified_links", {}),
            signals=signals,
            verification_targets=targets,
            agent_task=d["agent_task"],
            h100_hours_estimate=d.get("h100_hours_estimate", 0.0),
            h100_estimate_basis=d.get("h100_estimate_basis", ""),
            score=d.get("score"),
            tier=d.get("tier"),
        )


def build_prompt(entry: BenchmarkEntry) -> str:
    availability = "\n".join(
        f"{k}: {s.value} — {s.evidence}" for k, s in entry.signals.items()
    )
    parts = [
        f"# Paper: {entry.custom_id}",
        f"## Central Claim\n{entry.central_claim}",
        f"## Claim Evidence\n{entry.claim_evidence}",
        f"## Artifact Availability\n{availability}",
        f"## Web Verification Notes\n{entry.web_verification}",
        f"## Verified Links\n{json.dumps(entry.verified_links, indent=2)}",
        f"## MRE Configuration\n{entry.mre_config}",
        f"## Estimated Compute\n{entry.h100_hours_estimate} H100-hours — {entry.h100_estimate_basis}",
        f"## Verification Targets\n{json.dumps([t.__dict__ for t in entry.verification_targets], indent=2)}",
        f"## Agent Task\n{entry.agent_task}",
    ]
    if entry.score is not None or entry.tier is not None:
        parts.append(f"## Difficulty\nscore: {entry.score}, tier: {entry.tier}")
    return "\n\n".join(parts)
