from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from .verifiers import (
    VerifierResult,
    v_inspect_host, v_clone_repo, v_inspect_repo, v_plan_environment,
    v_build_env_container, v_build_env_conda, v_smoke_test,
    v_generate_launchers,
    v_run_experiment, v_collect_results, v_finalize,
)

if TYPE_CHECKING:
    from .prompt import BenchmarkEntry
    from .state import ReproState

PromptBuilder = Callable[["BenchmarkEntry", "ReproState"], str]
Verifier = Callable[[str, "ReproState"], VerifierResult]


@dataclass
class Phase:
    name: str
    prompt_builder: PromptBuilder
    allowed_tools: list[str]
    max_rounds: int
    verifier: Verifier


def _static(text: str) -> PromptBuilder:
    return lambda entry, state: text


# ---------------------------------------------------------------------------
# Phase prompts
# ---------------------------------------------------------------------------

_CONTAINER_SIF = "/sw/user/NGC_containers/pytorch_25.08-py3.sif"

_INSPECT_HOST_CONTAINER = """\
PHASE: inspect_host
Your only job: confirm host_profile.json is present and read its facts.

host_profile.json should already be sitting in this workdir — it was generated
ahead of time by scripts/collect_host_profile.py and already contains the
host's arch/GPU/SLURM/disk facts AND an inspection of the fixed NGC container
({sif}): its python/torch/torchvision/numpy/pillow versions and __file__
paths, CUDA availability, and whether uv is present inside it. Read it; you do
not need to run uname/nvidia-smi/apptainer exec yourself — that work is
already done.

If host_profile.json is missing or fails to parse, fall back to collecting it
yourself:
  uname -m
  nvidia-smi 2>/dev/null || echo "no GPU"
  sinfo 2>/dev/null || echo "SLURM unavailable"
  df -h /home /tmp 2>/dev/null || df -h
  apptainer exec {sif} python3 -c "import torch, torchvision; print(torch.__version__, torchvision.__version__)"
and write host_profile.json yourself: {{arch, has_conda, conda_path, has_gpu,
slurm_available, disk_info, container: {{...}}}}

Stop as soon as host_profile.json exists and parses as JSON.""".format(sif=_CONTAINER_SIF)

_INSPECT_HOST_CONDA = """\
PHASE: inspect_host
Your only job: inspect the host and write host_profile.json.

Run:
  uname -m
  nvidia-smi 2>/dev/null || echo "no GPU"
  sinfo 2>/dev/null || echo "SLURM unavailable"
  df -h /home /tmp 2>/dev/null || df -h
  ls -ld /work/nvme/$USER /work/hdd/$USER 2>/dev/null || true
  which conda && conda --version || echo "conda not found"

If conda is NOT found, install Miniconda:
  ARCH=$(uname -m)
  wget "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-${ARCH}.sh" -O /tmp/miniconda.sh
  bash /tmp/miniconda.sh -b -p ~/miniconda3
  ~/miniconda3/bin/conda --version

Write host_profile.json: {arch, has_conda, conda_path, has_gpu, slurm_available, disk_info}
Stop as soon as host_profile.json is written."""

_CLONE_REPO = """\
PHASE: clone_repo
Your only job: clone the paper's code repository into the working directory.

Use the URL from verified_links.code. Run:
  git clone <url>
If the repo requires authentication or fails, try the alternative URLs in verified_links.

Write clone_info.json: {repo_dir, commit_sha, clone_url}
Stop as soon as the repo is cloned."""

_INSPECT_REPO = """\
PHASE: inspect_repo
Your only job: understand the repo structure and write repo_profile.json.

Steps:
1. Call list_files(path="<repo-dir>") to see the full tree.
2. Read key files you find: README, requirements.txt, environment.yml,
   pyproject.toml, setup.py, setup.cfg, any Dockerfile or .def file.
   Use read_file for local files; github_browse(repo, path=<file>) for extras.
3. Identify: python_version, cuda_version, pytorch_version, key_packages,
   dataset_download_commands, training_command, eval_command, entry_points.

Write repo_profile.json with all findings.
Stop as soon as repo_profile.json is written."""

_PLAN_ENVIRONMENT_CONTAINER = """\
PHASE: plan_environment
Your only job: pick the minimum reproduction command and write env_plan.json.

Read repo_profile.json and host_profile.json.

From repo_profile.json's entry_points/training_command/eval_command, pick the
ONE command that runs the minimum reproduction experiment (inference/eval of
the paper's central claim — not training, not video pipelines, not legacy or
"old_project" code, not optional dataset utilities, unless that IS the selected
experiment). This is selected_command — record the exact invocation MINUS any
leading python/python3 interpreter token (e.g. "eval.py --config x.yaml", not
"python eval.py --config x.yaml"). Every later phase runs selected_command
through /workspace/venv/bin/python3, never a bare `python`/`python3` — so
selected_command must be just the script and its arguments. The environment
you build in the next phase only needs to support this command, not the rest
of the repo.

The container is fixed and already on disk — do not pick or build one:
  {sif}
It already provides torch, torchvision, CUDA, numpy, and pillow. Treat these as
immutable — they are never something you plan to install or upgrade.
host_profile.json's "container" section already has its exact versions and
__file__ paths (collected ahead of time) — use that instead of running
apptainer exec yourself to check.

Write env_plan.json: {{"selected_command": "...", "notes": "..."}}
Stop as soon as env_plan.json is written.""".format(sif=_CONTAINER_SIF)

_PLAN_ENVIRONMENT_CONDA = """\
PHASE: plan_environment
Your only job: decide the environment strategy and write env_plan.json.

Read repo_profile.json and host_profile.json.
Decide: python_version, cuda_version, conda_packages, extra_pip_packages,
notes (any known compatibility issues).

Write env_plan.json: {python_version, cuda_version, pip_packages, notes}
Stop as soon as env_plan.json is written."""

_BUILD_ENV_CONTAINER = """\
PHASE: build_environment
Your only job: get env_plan.json's selected_command running inside a uv-managed
venv layered on the container. You have a capped number of rounds for this
first-time setup — work the loop below efficiently rather than trying to
pre-install everything.

NEVER run `apptainer build` or write a .def file. The image is fixed, already
on disk, and must not be rebuilt:

  CONTAINER={sif}

The container already provides torch, torchvision, CUDA, numpy, and pillow.
These are immutable — never let pip/uv install or upgrade them in the venv.
Installing PyPI copies on top of the container's build breaks the ABI (e.g.
torchvision::nms registration errors from a mismatched torch/torchvision pair).

Mental model: the SIF is the base OS + CUDA + PyTorch stack; the venv
(--system-site-packages) is a thin project layer on top; every package you add
to it is a missing delta, installed with `uv pip install --no-deps` so its own
dependency resolution can never reach in and replace the container's stack.
`--no-deps` is the default for every install in this phase, not a fallback for
when you suspect a conflict.

selected_command is the only thing this environment needs to support — do not
try to make the rest of the repo importable (training code, old_project/legacy
code, video pipelines, optional dataset utilities), and do not blindly
`pip install -r requirements.txt` — that file lists dependencies for the whole
repo, many of which selected_command never touches and some of which may be
incompatible with this platform.

Hard rule — placeholders and env vars: selected_command may contain
${{...}}-style placeholders (paths, dataset roots, checkpoint dirs). Resolve
every one of them to a concrete /workspace path BEFORE running the command.
Never run selected_command with an unresolved ${{...}} still in it. Always run
it through `bash -lc` inside the container, defining any required env vars in
that same `bash -lc` invocation, and always through
/workspace/venv/bin/python3:
  bash("apptainer exec --bind \\"$PWD\\":/workspace $CONTAINER "
       "bash -lc 'export FOO=/workspace/<resolved>; export BAR=/workspace/<resolved>; "
       "/workspace/venv/bin/python3 <selected_command with placeholders resolved> "
       "2>&1 | tee build_attempt.log'")
If the command then fails with an argparse usage error because a required
argument resolved to empty (e.g. `error: argument --x: expected one argument`
or a path argument that's literally empty), that is NOT env_ready — it means a
placeholder didn't resolve. Fix the placeholder resolution and retry; do not
treat this as "environment is ready, belongs to a later phase."

The loop:
1. (First time only) Create the venv. uv is not on PATH under a plain
   `apptainer exec`, so use a login shell and set PATH explicitly:
   bash("apptainer exec --bind \\"$PWD\\":/workspace $CONTAINER "
        "bash -lc 'export PATH=$HOME/.local/bin:$PATH; command -v uv || pip install -q uv; "
        "uv venv --system-site-packages /workspace/venv'")
2. Try running selected_command (placeholders resolved) through bash -lc as
   shown above. Never invoke it with a bare `python`/`python3` — always
   /workspace/venv/bin/python3.
3. Read build_attempt.log.
   - If it's a missing-package error (ModuleNotFoundError/ImportError), install
     just that package with `--no-deps`, always — not just when you suspect a
     conflict (see the mental model above):
     bash("apptainer exec --bind \\"$PWD\\":/workspace $CONTAINER "
          "bash -lc 'export PATH=$HOME/.local/bin:$PATH; "
          "uv pip install --python /workspace/venv/bin/python --no-deps <pkg>'")
     If that package turns out to need a transitive dependency too (e.g. an
     ImportError for something it should have brought in), install that
     dependency the same way — its own `--no-deps` call — rather than dropping
     `--no-deps` on the original package.
   - If it's an argparse usage error from an unresolved/empty placeholder, fix
     the placeholder resolution (step 2) and retry — see the hard rule above.
   - If it's a data/checkpoint/argument error unrelated to missing Python
     packages or unresolved placeholders, the environment itself is ready —
     stop here, that belongs to a later phase.
4. Go back to step 2. Fix one error at a time until selected_command gets past
   environment setup (import errors and placeholder resolution both clean) —
   it doesn't need to finish successfully, just stop failing on missing/broken
   packages or unresolved placeholders.
5. Write env_ready.json: {{"container_path": "{sif}", "venv_path": "/workspace/venv",
   "selected_command": <from env_plan.json>, "packages_installed": [...]}}

Stop as soon as env_ready.json is written.""".format(sif=_CONTAINER_SIF)

_BUILD_ENV_CONDA = """\
PHASE: build_environment
Your only job: create a conda environment and install all dependencies.

1. Read env_plan.json for python_version and pip_packages.
2. Call create_conda_env(name="repro", python_version=<from plan>)
3. Install dependencies (always pass conda_env="repro"):
   bash("pip install -r requirements.txt", conda_env="repro")   # if exists
   bash("pip install -e .", conda_env="repro")                  # if setup.py/pyproject.toml
   bash("pip install <pip_packages from plan>", conda_env="repro")
4. Write env_ready.json: {env_name: "repro", python_version: ..., packages_installed: [...]}

Stop as soon as env_ready.json is written."""

_SMOKE_TEST_CONTAINER = """\
PHASE: smoke_test
Your only job: confirm the container + venv are correctly layered for
selected_command — nothing more.

CONTAINER={sif}
VENV=/workspace/venv

Read env_plan.json for selected_command.

Run (all bound the same way as the build step). Never invoke selected_command
or any Python entrypoint with a bare `python`/`python3` — always $VENV/bin/python3:
  apptainer exec --bind "$PWD":/workspace $CONTAINER $VENV/bin/python3 --version
  apptainer exec --bind "$PWD":/workspace $CONTAINER $VENV/bin/python3 -c "import torch, torchvision; print(torch.__file__); print(torchvision.__file__)"
  apptainer exec --nv --bind "$PWD":/workspace $CONTAINER $VENV/bin/python3 -c "import torch; print(torch.cuda.is_available())"

Then exercise ONLY selected_command's own script, via its real import/help
path — not a synthesized list of imports. Run selected_command's script with
--help (or the nearest no-op/dry-run flag it has) so Python actually imports
the script's module tree, exactly as it will be imported for real:
  apptainer exec --bind "$PWD":/workspace $CONTAINER bash -lc \\
    "cd /workspace/<repo-dir> && $VENV/bin/python3 <selected_command's script> --help"
e.g. for datacomp's evaluate.py, selected_command's smoke test is exactly:
  cd /workspace/datacomp
  /workspace/venv/bin/python3 evaluate.py --help
Do not import training.*, notebooks, FLYT training code, or any other module
selected_command itself doesn't import — only what's on selected_command's
actual import path gets exercised here.

torch and torchvision's __file__ paths must be under the container's system
site-packages (/usr/local/lib/python3.X/dist-packages), never under
/workspace/venv — that means a PyPI copy leaked into the venv and the ABI is
broken; go fix it in build_environment before continuing.

Capture all output to smoke_test.log (use: bash("... 2>&1 | tee smoke_test.log")).
If --help (or equivalent) succeeds and torch/torchvision resolve from the
container, append "SMOKE_OK" to smoke_test.log:
  bash("echo SMOKE_OK >> smoke_test.log")
Do not chase import errors for modules selected_command doesn't use.

Stop as soon as smoke_test.log contains SMOKE_OK.""".format(sif=_CONTAINER_SIF)

_SMOKE_TEST_CONDA = """\
PHASE: smoke_test
Your only job: verify the conda environment imports correctly.

Run (all with conda_env="repro"):
  bash("python -c \\"import sys; print(sys.version)\\"", conda_env="repro")
  bash("python -c \\"import torch; print(torch.__version__, torch.cuda.is_available())\\"", conda_env="repro")
  # also import key packages from repo_profile.json

Capture all output to smoke_test.log:
  bash("python -c '...' 2>&1 | tee -a smoke_test.log", conda_env="repro")
If all imports succeed, append "SMOKE_OK":
  bash("echo SMOKE_OK >> smoke_test.log")
If something fails, fix the conda env (install missing packages) and retry.

Stop as soon as smoke_test.log contains SMOKE_OK."""

_GENERATE_LAUNCHERS = """\
PHASE: generate_launchers
Your only job: write reproduce.sh and slurm_run.sh.

Read repo_profile.json for the training/eval commands.

Write reproduce.sh — the experiment script to run inside the container, using
the venv's python (base image's torch/cuda plus the repo's extra packages
installed via uv in build_environment). Read env_plan.json for
selected_command and run exactly that — never with a bare `python`/`python3`,
always /workspace/venv/bin/python3:
  #!/usr/bin/env bash
  set -euo pipefail
  cd /workspace/<repo-dir>
  /workspace/venv/bin/python3 download_data.py   # if needed
  /workspace/venv/bin/python3 <selected_command>

Write slurm_run.sh — the SLURM batch script:
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
    {sif} bash /workspace/reproduce.sh

Stop as soon as both files exist.""".format(sif=_CONTAINER_SIF)

_RUN_EXPERIMENT_CONTAINER_SLURM = """\
PHASE: run_experiment
Your only job: submit the SLURM job and collect output into run.log.

Steps:
1. Submit: bash("sbatch slurm_run.sh")  — note the job ID.
2. Poll: bash("squeue -u $USER") every 60s until job is no longer running.
3. Read output: bash("cat slurm-<jobid>.out slurm-<jobid>.err")
4. Write run.log with all combined output.

If the job fails, read the error output, fix reproduce.sh or slurm_run.sh, and resubmit.
Stop as soon as run.log is written with experiment output (not just "pending")."""

_RUN_EXPERIMENT_CONTAINER_DIRECT = """\
PHASE: run_experiment
Your only job: run selected_command directly and capture output to run.log.

You're already running on an allocated compute node (e.g. under srun) — there
is no SLURM job to submit. Run the real experiment the same way you ran it in
build_environment/smoke_test, just for real this time: --nv for GPU, no
--help, full args.

CONTAINER={sif}
VENV=/workspace/venv

Read env_plan.json for selected_command and resolve any ${{...}}-style
placeholders to concrete /workspace paths, exactly as in build_environment.
Never invoke with a bare `python`/`python3` — always $VENV/bin/python3:
  bash("apptainer exec --nv --bind \\"$PWD\\":/workspace $CONTAINER "
       "bash -lc 'cd /workspace/<repo-dir> && export HF_HOME=/work/nvme/$USER/hf_cache; "
       "export WANDB_MODE=offline; $VENV/bin/python3 <selected_command, resolved> "
       "2>&1 | tee run.log'", timeout=<generous — experiments can run long>)

If it fails, read run.log and fix the actual cause: missing data/checkpoint →
download it; bad/unresolved path → fix it; a package issue → that belongs back
in build_environment. Then retry.

Stop as soon as run.log is written with real experiment output (not just an
error).""".format(sif=_CONTAINER_SIF)

_RUN_EXPERIMENT_CONDA = """\
PHASE: run_experiment
Your only job: run the full experiment and capture output to run.log.

Run the experiment commands from agent_task using conda_env="repro".
Capture all output: bash("python train.py ... 2>&1 | tee run.log", conda_env="repro")

If the run fails, fix the issue and retry.
Stop as soon as run.log is written with experiment output."""

_COLLECT_RESULTS = """\
PHASE: collect_results
Your only job: parse metric values from run.log and write results.json.

Steps:
1. Read run.log.
2. Find the metric values that match verification_targets[].metric exactly.
3. Write results.json:
   [{"metric": "<name>", "actual_value": <number or null>, "source_line": "<log line>"}]
   Use null only if the metric truly could not be found.
Do not fabricate values. Only report what you observed in the actual log.

Stop as soon as results.json is written."""

_FINALIZE = """\
PHASE: finalize
Your only job: write REASONING.txt and final_result.json.

Read results.json and run.log. Compare metric_results against
verification_targets and central_claim.

1. Write REASONING.txt — a plain-text explanation, written for a human
   reviewer who has not read run.log, of exactly why these results do or do
   not support central_claim. For each verification target, cite the actual
   value you found in results.json/run.log (quote the literal log line or
   number), the expected_value, and whether they match within a reasonable
   tolerance. Then state your overall verdict and why. This is not a
   restatement of the metric_results JSON — it's the reasoning that produced
   the verdict, in prose. This file is the last artifact this pipeline
   produces; assume it's the only thing a reviewer reads.

2. Write final_result.json — no prose, no markdown fences:
   {
     "reproduction_status": "success" | "partial" | "failed",
     "metric_results": [{"metric": "<name>", "actual_value": <number|null>}],
     "claim_supported": true | false | null,
     "claim_assessment": "<one paragraph, consistent with REASONING.txt>",
     "failure_reason": "<only if failed or partial>"
   }
   Metric names must exactly match verification_targets[].metric.

Stop as soon as both REASONING.txt and final_result.json are written."""


# ---------------------------------------------------------------------------
# State-aware prompt builders — inject facts discovered in earlier phases so
# the model doesn't have to re-read artifact files it already wrote/read.
# ---------------------------------------------------------------------------

def _build_inspect_repo_prompt(entry: "BenchmarkEntry", state: "ReproState") -> str:
    text = _INSPECT_REPO
    if state.repo_path:
        text = text.replace('list_files(path="<repo-dir>")', f'list_files(path="{state.repo_path}")')
        text += f"\n\nThe cloned repo is at: {state.repo_path}"
    return text


def _build_env_prompt(static_text: str) -> PromptBuilder:
    def _build(entry: "BenchmarkEntry", state: "ReproState") -> str:
        text = static_text
        facts = []
        if state.host_arch:
            facts.append(f"host architecture: {state.host_arch}")
        if state.repo_path:
            facts.append(f"repo: {state.repo_path}")
        if facts:
            text += f"\n\nKnown host facts — {', '.join(facts)}."
        return text
    return _build


def _build_run_experiment_prompt(static_text: str) -> PromptBuilder:
    def _build(entry: "BenchmarkEntry", state: "ReproState") -> str:
        text = static_text
        if state.slurm_job_id:
            text += (
                f"\n\nA job was already submitted with ID {state.slurm_job_id} — "
                "poll its status instead of resubmitting unless it failed."
            )
        return text
    return _build


# ---------------------------------------------------------------------------
# Phase constructors
# ---------------------------------------------------------------------------

_INSPECT_HOST_CONTAINER_PHASE = Phase(
    name="inspect_host",
    prompt_builder=_static(_INSPECT_HOST_CONTAINER),
    allowed_tools=["bash", "read_file", "write_file"],
    max_rounds=5,
    verifier=v_inspect_host,
)

_INSPECT_HOST_CONDA_PHASE = Phase(
    name="inspect_host",
    prompt_builder=_static(_INSPECT_HOST_CONDA),
    allowed_tools=["bash", "write_file"],
    max_rounds=5,
    verifier=v_inspect_host,
)

_SHARED_CLONE_REPO = Phase(
    name="clone_repo",
    prompt_builder=_static(_CLONE_REPO),
    allowed_tools=["bash", "write_file"],
    max_rounds=5,
    verifier=v_clone_repo,
)

_SHARED_INSPECT_REPO = Phase(
    name="inspect_repo",
    prompt_builder=_build_inspect_repo_prompt,
    allowed_tools=["bash", "list_files", "read_file", "write_file", "github_browse", "fetch_url"],
    max_rounds=10,
    verifier=v_inspect_repo,
)

_PLAN_ENV_CONTAINER = Phase(
    name="plan_environment",
    prompt_builder=_static(_PLAN_ENVIRONMENT_CONTAINER),
    allowed_tools=["read_file", "write_file", "fetch_url", "github_browse", "hf_browse"],
    max_rounds=5,
    verifier=v_plan_environment,
)

_PLAN_ENV_CONDA = Phase(
    name="plan_environment",
    prompt_builder=_static(_PLAN_ENVIRONMENT_CONDA),
    allowed_tools=["read_file", "write_file", "fetch_url", "github_browse", "hf_browse"],
    max_rounds=5,
    verifier=v_plan_environment,
)

_SHARED_COLLECT = Phase(
    name="collect_results",
    prompt_builder=_static(_COLLECT_RESULTS),
    allowed_tools=["bash", "read_file", "write_file"],
    max_rounds=8,
    verifier=v_collect_results,
)

_SHARED_FINALIZE = Phase(
    name="finalize",
    prompt_builder=_static(_FINALIZE),
    allowed_tools=["read_file", "write_file"],
    max_rounds=5,
    verifier=v_finalize,
)

PHASES_CONTAINER_SLURM: list[Phase] = [
    _INSPECT_HOST_CONTAINER_PHASE,
    _SHARED_CLONE_REPO,
    _SHARED_INSPECT_REPO,
    _PLAN_ENV_CONTAINER,
    Phase("build_environment", _build_env_prompt(_BUILD_ENV_CONTAINER),
          ["bash", "read_file", "write_file"], 40, v_build_env_container),
    Phase("smoke_test", _static(_SMOKE_TEST_CONTAINER),
          ["bash", "write_file"], 12, v_smoke_test),
    Phase("generate_launchers", _static(_GENERATE_LAUNCHERS),
          ["bash", "read_file", "write_file"], 5, v_generate_launchers),
    Phase("run_experiment", _build_run_experiment_prompt(_RUN_EXPERIMENT_CONTAINER_SLURM),
          ["bash", "write_file"], 20, v_run_experiment),
    _SHARED_COLLECT,
    _SHARED_FINALIZE,
]

PHASES_CONTAINER_DIRECT: list[Phase] = [
    _INSPECT_HOST_CONTAINER_PHASE,
    _SHARED_CLONE_REPO,
    _SHARED_INSPECT_REPO,
    _PLAN_ENV_CONTAINER,
    Phase("build_environment", _build_env_prompt(_BUILD_ENV_CONTAINER),
          ["bash", "read_file", "write_file"], 40, v_build_env_container),
    Phase("smoke_test", _static(_SMOKE_TEST_CONTAINER),
          ["bash", "write_file"], 12, v_smoke_test),
    Phase("run_experiment", _build_run_experiment_prompt(_RUN_EXPERIMENT_CONTAINER_DIRECT),
          ["bash", "read_file", "write_file"], 20, v_run_experiment),
    _SHARED_COLLECT,
    _SHARED_FINALIZE,
]

PHASES_CONDA: list[Phase] = [
    _INSPECT_HOST_CONDA_PHASE,
    _SHARED_CLONE_REPO,
    _SHARED_INSPECT_REPO,
    _PLAN_ENV_CONDA,
    Phase("build_environment", _build_env_prompt(_BUILD_ENV_CONDA),
          ["bash", "read_file", "write_file", "create_conda_env"], 40, v_build_env_conda),
    Phase("smoke_test", _static(_SMOKE_TEST_CONDA),
          ["bash", "write_file"], 12, v_smoke_test),
    Phase("run_experiment", _build_run_experiment_prompt(_RUN_EXPERIMENT_CONDA),
          ["bash", "write_file"], 20, v_run_experiment),
    _SHARED_COLLECT,
    _SHARED_FINALIZE,
]


def get_phases(use_container: bool, use_slurm: bool = True) -> list[Phase]:
    if not use_container:
        return PHASES_CONDA
    return PHASES_CONTAINER_SLURM if use_slurm else PHASES_CONTAINER_DIRECT
