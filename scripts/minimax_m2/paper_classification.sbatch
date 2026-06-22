#!/bin/bash
# Stage-1 classifier (serve paradigm, single node): step 1 stands up the central
# vLLM server via reprocli_serve, step 2 attaches the model-agnostic runner by
# URL. Same dataset outputs as before; the model is now a swappable service, so
# changing providers is a server-step / URL change rather than a runner rewrite.
#
#SBATCH -J reprocli_paper_classification
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --gpus-per-node=4
#SBATCH --gpu-bind=none
#SBATCH --mem=256G
#SBATCH --time=48:00:00
#SBATCH -o slurm-%j.out
#SBATCH -e slurm-%j.err
#SBATCH --export=ALL
#SBATCH --mail-user=mithils3@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

MODEL="${MODEL:-/work/nvme/bfvr/msalunkhe/MiniMax-M2.7}"
SERVED_NAME="${SERVED_NAME:-MiniMaxAI/MiniMax-M2.7}"
PORT="${PORT:-8000}"
ENDPOINT_FILE="${ENDPOINT_FILE:-${SLURM_TMPDIR:-/tmp}/minimax_endpoint_${SLURM_JOB_ID}.json}"

export TORCHINDUCTOR_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/torchinductor
export TRITON_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/triton
export VLLM_CACHE_ROOT=/work/nvme/bfvr/msalunkhe/MiniMax-M2.7/vllm_cache
export SAFETENSORS_FAST_GPU=1
export CUDA_MODULE_LOADING=LAZY
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export PYTHONFAULTHANDLER=1
export MASTER_ADDR=127.0.0.1
export VLLM_HOST_IP=127.0.0.1
export NCCL_CUMEM_ENABLE=0
export NCCL_CUMEM_HOST_ENABLE=0
export NCCL_DEBUG="${NCCL_DEBUG:-INFO}"
export NCCL_NET_PLUGIN="${NCCL_NET_PLUGIN_OVERRIDE:-none}"
export OMP_NUM_THREADS=1
export TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC="${TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC:-1200}"

ulimit -l unlimited || true
ulimit -s unlimited || true

module load python/3.11.9
source /u/msalunkhe/reprocli/.venv/bin/activate
cd /u/msalunkhe/reprocli/

echo "host=$(hostname)  endpoint_file=${ENDPOINT_FILE}"
nvidia-smi topo -m || true

# --- Step 1: central server (background) -------------------------------------
PYTHONPATH=/u/msalunkhe/reprocli/src:${PYTHONPATH:-} python -m reprocli_serve \
  --model "${MODEL}" \
  --served-model-name "${SERVED_NAME}" \
  --port "${PORT}" \
  --tensor-parallel-size 4 \
  --max-model-len 196608 \
  --distributed-executor-backend mp \
  --compilation-config '{"mode":3,"pass_config":{"fuse_minimax_qk_norm":true}}' \
  --endpoint-file "${ENDPOINT_FILE}" &
SERVER_PID=$!
trap 'kill "${SERVER_PID}" 2>/dev/null || true' EXIT

# The launcher writes ENDPOINT_FILE only once /health is green; wait for it.
for _ in $(seq 1 360); do
  [[ -f "${ENDPOINT_FILE}" ]] && break
  if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
    echo "server exited before publishing an endpoint" >&2; exit 1
  fi
  sleep 5
done
[[ -f "${ENDPOINT_FILE}" ]] || { echo "timed out waiting for ${ENDPOINT_FILE}" >&2; exit 1; }
SERVER_URL="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["base_url"])' "${ENDPOINT_FILE}")"
echo "attaching classifier to ${SERVER_URL}"

# --- Step 2: model-agnostic runner attaches by URL (identical outputs) --------
export PYTHONPATH=/u/msalunkhe/reprocli/src:${PYTHONPATH:-}
python3 src/run_arxiv_prompt_vllm.py \
  --vllm-server-url "${SERVER_URL}" \
  --model "${SERVED_NAME}" \
  --tool-rounds 12 \
  --max-input-tokens 128000 \
  --max-tokens 8192 \
  --request-workers 32 \
  --stream-first-response \
  --dataset Mithilss/neurips-2025-paper-bundles \
  --output outputs/neurips_2025_minimax_m2_trial.jsonl \
  --extracted-output outputs/neurips_2025_minimax_m2_trial_extracted.jsonl \
  --save-round-jsonl \
  --max-model-len 196608 \
  --hf-repo Mithilss/neurips-2025-results
