#!/bin/bash
# One self-contained DeltaAI job: serve the brain (MiniMax-M2.7 on 4xGH200) and,
# once /health is green, drive the WHOLE dev-15 split through the S6 reproduction
# agent (`reprocli_repro`). The brain holds this node's 4 GPUs for the run; the
# orchestrator is a cheap CPU process co-located on the same node, and every
# `run_gpu` experiment step JIT-`salloc`s a SEPARATE ghx4 node and releases it on
# exit (see scripts/reproduce/minimax_m2/run_reproduce_minimax_m2.md).
#
#   sbatch scripts/reproduce/minimax_m2/dev15_minimax_m2.sbatch
#
# Why one GPU job instead of a CPU orchestrator job: DeltaAI has NO cpu-only
# partition (only ghx4 / ghx4-interactive, both GPU). The brain needs a ghx4 node
# regardless, so hosting the (GPU-less) orchestrator on that same node's spare
# CPUs is free. Each `run_gpu` step is a fresh top-level allocation:
#   salloc --no-shell ... ; srun --jobid=<that job> ...   (NOT srun-within-srun)
# which is the Slurm-sanctioned nesting. We scrub the batch job's inherited
# SLURM_* env first so those child salloc/srun build clean, independent steps.
#
# Prefer to keep the orchestrator on a login node instead (no 48h wall cap on the
# sweep)? Submit scripts/serve/serve_gh200.sbatch for the brain, then run the loop
# at the bottom of this file by hand on a login node — same commands.
#
#SBATCH -J repro_dev15_minimax
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=144
#SBATCH --gpus-per-node=2
#SBATCH --gpu-bind=none
#SBATCH --mem=220G
#SBATCH --time=48:00:00
#SBATCH -o slurm-repro-dev15-%j.out
#SBATCH -e slurm-repro-dev15-%j.err
#SBATCH --export=ALL
#SBATCH --mail-user=mithils3@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# --- Config (override from the environment) ---------------------------------
REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"
VENV="${VENV:-/u/msalunkhe/reprocli/.venv}"
MODEL="${MODEL:-cyankiwi/MiniMax-M2.7-AWQ-4bit}"   # 4-bit AWQ W4A16, fits 2xGH200
SERVED_NAME="${SERVED_NAME:-MiniMaxAI/MiniMax-M2.7}"
PORT="${PORT:-8000}"
SPLIT="${SPLIT:-dev}"                    # dev -> HF 'validation' (the dev-15 split)
LOCKFILE="${LOCKFILE:-Mithilss/reprobench-splits}"
BUDGET_H100_HOURS="${BUDGET_H100_HOURS:-}"   # empty -> per-paper budget from the selection band
TOOL_ROUNDS="${TOOL_ROUNDS:-300}"
MAX_PARALLEL="${MAX_PARALLEL:-5}"        # papers in flight at once; each adds 1 JIT ghx4 node

# Keep the agent's heavy I/O (bundles, per-paper uv venvs, run bundles) off $HOME.
export REPRO_WORK_ROOT="${REPRO_WORK_ROOT:-/work/nvme/bfvr/msalunkhe/reprocli}"
export HF_HOME="${HF_HOME:-/work/nvme/bfvr/msalunkhe/hf_cache}"
# The reproduction AGENT runs inside the Apptainer sandbox; send ONLY its in-container HF
# pulls (per-paper models + datasets, the bulk that filled /work) to node-local /tmp, which
# clears per job. APPTAINERENV_HF_HOME wins inside the wrap (sandbox.forward_env honors a
# pre-set value), so the served brain + orchestrator above keep the persistent /work cache.
export APPTAINERENV_HF_HOME="${APPTAINERENV_HF_HOME:-/tmp/hf_cache}"
# HF_TOKEN is inherited via --export=ALL; the lockfile + paper bundles need it.
if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "WARNING: HF_TOKEN is unset; the lockfile/bundle download from the Hub may fail." >&2
fi

OUTER_JOB="${SLURM_JOB_ID:-local}"
# One batch id per sbatch launch: every paper this sweep drives uploads with it,
# so the run viewer can show the whole launch as one group. (REPRO_* survives the
# SLURM_* env scrub below; override from the environment to join an older batch.)
export REPRO_BATCH_ID="${REPRO_BATCH_ID:-slurm-${OUTER_JOB}}"
export REPRO_BATCH_LABEL="${REPRO_BATCH_LABEL:-${SLURM_JOB_NAME:-repro_sweep} #${OUTER_JOB}}"
SWEEP_DIR="${SWEEP_DIR:-${REPRO_WORK_ROOT}/dev15_sweeps/${OUTER_JOB}}"
ENDPOINT_FILE="${ENDPOINT_FILE:-${SWEEP_DIR}/brain_endpoint.json}"
mkdir -p "${SWEEP_DIR}"

# Sweep-wall countdown surfaced to the agent every tool round (transcript.py reads
# this): the absolute epoch when SLURM kills this job. squeue %e is the scheduler's
# own end time; fall back to now + the #SBATCH --time cap if it is unavailable.
if end_ts="$(squeue -h -j "${SLURM_JOB_ID}" -o '%e' 2>/dev/null)" \
   && [ -n "${end_ts}" ] \
   && REPRO_WALL_DEADLINE_EPOCH="$(date -d "${end_ts}" +%s 2>/dev/null)"; then
  :
else
  REPRO_WALL_DEADLINE_EPOCH="$(( $(date +%s) + 48 * 3600 ))"
fi
export REPRO_WALL_DEADLINE_EPOCH

# --- Standardized DeltaAI serve env block (shared with scripts/serve/*) ------
export TORCHINDUCTOR_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/torchinductor
export TRITON_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/triton
export VLLM_CACHE_ROOT=/work/nvme/bfvr/msalunkhe/.cache/vllm
export SAFETENSORS_FAST_GPU=1
export CUDA_MODULE_LOADING=LAZY
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export PYTHONFAULTHANDLER=1
export MASTER_ADDR=127.0.0.1
export VLLM_HOST_IP=127.0.0.1
export NCCL_CUMEM_ENABLE=0
export NCCL_CUMEM_HOST_ENABLE=0
export NCCL_DEBUG="${NCCL_DEBUG:-WARN}"
export NCCL_NET_PLUGIN="${NCCL_NET_PLUGIN_OVERRIDE:-none}"
export OMP_NUM_THREADS=1
export TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC="${TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC:-1200}"

ulimit -l unlimited || true
ulimit -s unlimited || true

module load python/3.11.9
source "${VENV}/bin/activate"
export PYTHONPATH="${REPROCLI}/src:${PYTHONPATH:-}"
cd "${REPROCLI}"

echo "host=$(hostname)  job=${OUTER_JOB}  endpoint_file=${ENDPOINT_FILE}"
# Pass --budget-h100-hours only when a flat budget is set; otherwise the CLI
# derives each paper's ceiling from its selection band.
if [[ -n "${BUDGET_H100_HOURS}" ]]; then
  BUDGET_ARG=(--budget-h100-hours "${BUDGET_H100_HOURS}")
  BUDGET_LABEL="${BUDGET_H100_HOURS}h (flat)"
else
  BUDGET_ARG=()
  BUDGET_LABEL="per-band"
fi
echo "sweep_dir=${SWEEP_DIR}  split=${SPLIT}  budget=${BUDGET_LABEL}  rounds=${TOOL_ROUNDS}  parallel=${MAX_PARALLEL}"
nvidia-smi topo -m || true

# --- Step 1: serve the brain (background), wait for /health ------------------
python -m reprocli_serve \
  --model "${MODEL}" \
  --served-model-name "${SERVED_NAME}" \
  --port "${PORT}" \
  --tensor-parallel-size 2 \
  --max-model-len 196608 \
  --distributed-executor-backend mp \
  --compilation-config '{"mode":3,"pass_config":{"fuse_minimax_qk_norm":true}}' \
  --endpoint-file "${ENDPOINT_FILE}" \
  -- --kv-offloading-backend native --kv-offloading-size 64 &   # 64GB CPU RAM as KV-cache overflow (V1 replaces --swap-space)
SERVER_PID=$!
trap 'kill "${SERVER_PID}" 2>/dev/null || true' EXIT

# reprocli_serve writes ENDPOINT_FILE only once /health is green; wait for it.
for _ in $(seq 1 720); do
  [[ -f "${ENDPOINT_FILE}" ]] && break
  if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
    echo "brain exited before publishing an endpoint" >&2; exit 1
  fi
  sleep 5
done
[[ -f "${ENDPOINT_FILE}" ]] || { echo "timed out waiting for ${ENDPOINT_FILE}" >&2; exit 1; }

BASE_URL="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["base_url"])' "${ENDPOINT_FILE}")"
curl -fsS "${BASE_URL}/health" >/dev/null && echo "brain up at ${BASE_URL}"

# The orchestrator auto-discovers the URL + served model from this file (zero-flag).
export REPROCLI_ENDPOINT_FILE="${ENDPOINT_FILE}"

# --- Step 2: scrub inherited SLURM_* so each run_gpu salloc/srun is clean ----
# Per the srun docs, a child srun inherits the batch job's export/cpu-bind env;
# unset everything from this allocation so `salloc --no-shell` + `srun --jobid`
# build fresh, independent GPU steps (and re-assert full env export into them).
for v in $(compgen -v | grep -E '^SLURM_' || true); do unset "$v"; done
export SLURM_EXPORT_ENV=ALL

# --- Step 3: enumerate the dev split and drive every paper ------------------
mapfile -t PAPER_IDS < <(
  python - "${LOCKFILE}" "${SPLIT}" <<'PY'
import sys
from reprocli_repro.inputs import load_lockfile_rows
rows = load_lockfile_rows(sys.argv[1], split=sys.argv[2])
for pid in rows:
    print(pid)
PY
)
if [[ "${#PAPER_IDS[@]}" -eq 0 ]]; then
  echo "no papers found in ${LOCKFILE} split=${SPLIT}" >&2; exit 1
fi
echo "dev split '${SPLIT}' has ${#PAPER_IDS[@]} papers: ${PAPER_IDS[*]}"

STATUS_FILE="${SWEEP_DIR}/status.tsv"
: > "${STATUS_FILE}"

run_one() {
  local pid="$1"
  local log="${SWEEP_DIR}/repro_${pid}.log"
  echo ">>> [$(date '+%F %T')] start ${pid}"
  python -m reprocli_repro \
    --paper-id "${pid}" \
    --split "${SPLIT}" \
    --lockfile "${LOCKFILE}" \
    "${BUDGET_ARG[@]}" \
    --tool-rounds "${TOOL_ROUNDS}" \
    --served-model-name "${SERVED_NAME}" \
    --output "${SWEEP_DIR}/reproduce_${pid}.jsonl" \
    --save-round-jsonl \
    >"${log}" 2>&1
  local rc=$?
  printf '%s\t%s\n' "${pid}" "${rc}" >> "${STATUS_FILE}"
  echo "<<< [$(date '+%F %T')] done  ${pid} rc=${rc} (log: ${log})"
  return 0
}

set +e   # one bad paper must not abort the sweep
# Track ONLY the per-paper PIDs. The brain server (SERVER_PID) is also a background
# job, so a bare `wait` blocks on it forever and the sbatch never exits even after
# all papers are done — wait on the paper jobs explicitly instead.
run_pids=()
inflight=0
for pid in "${PAPER_IDS[@]}"; do
  run_one "${pid}" &
  run_pids+=("$!")
  inflight=$((inflight + 1))
  if (( inflight >= MAX_PARALLEL )); then
    wait -n   # next paper to finish (the server never exits, so it's never this)
    inflight=$((inflight - 1))
  fi
done
wait "${run_pids[@]}" 2>/dev/null || true   # only the papers, not the brain

# --- Summary ----------------------------------------------------------------
echo "===== dev-15 sweep complete (job ${OUTER_JOB}) ====="
ok=$(awk -F'\t' '$2==0' "${STATUS_FILE}" | wc -l)
total=$(wc -l < "${STATUS_FILE}")
echo "papers ok: ${ok}/${total}  (per-paper rc in ${STATUS_FILE})"
sort "${STATUS_FILE}"
echo "run bundles: ${REPRO_WORK_ROOT}/agent_runs/<arxiv_id>/<budget>h/<run_id>/"
