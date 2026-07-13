#!/bin/bash
# Stand up a single-node vLLM server on 1x 4xGH200 (DeltaAI ghx4), reachable
# from any other Delta/DeltaAI node by the URL it publishes.
#
#   sbatch scripts/serve/serve_gh200.sbatch
#   # then, on a login node or another compute node:
#   #   export REPROCLI_ENDPOINT_FILE=$ENDPOINT_FILE   (same path as below)
#   #   <consumer> --vllm-server-url "$(jq -r .base_url "$ENDPOINT_FILE")"
#
#SBATCH -J reprocli_serve
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --gpus-per-node=2
#SBATCH --gpu-bind=none
#SBATCH --mem=220G
#SBATCH --time=24:00:00
#SBATCH -o slurm-serve-%j.out
#SBATCH -e slurm-serve-%j.err
#SBATCH --export=ALL
#SBATCH --mail-user=mithils3@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# --- Paths (override from the environment) ----------------------------------
REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"      # reprocli_serve lives in src/
VENV="${VENV:-/u/msalunkhe/reprocli/.venv}"        # any venv with vllm installed
MODEL="${MODEL:-cyankiwi/MiniMax-M2.7-AWQ-4bit}"   # 4-bit AWQ W4A16, fits 2xGH200
SERVED_NAME="${SERVED_NAME:-MiniMaxAI/MiniMax-M2.7}"
PORT="${PORT:-8000}"
# Publish on a SHARED filesystem so other nodes can read the URL.
ENDPOINT_FILE="${ENDPOINT_FILE:-/work/nvme/bfvr/msalunkhe/endpoints/minimax_m2.json}"

# --- Standardized DeltaAI env block (shared with reprocli/scripts/*.sbatch) --
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
export NCCL_DEBUG="${NCCL_DEBUG:-INFO}"
export NCCL_DEBUG_SUBSYS="${NCCL_DEBUG_SUBSYS:-INIT,ENV,NET}"
export NCCL_NET_PLUGIN="${NCCL_NET_PLUGIN_OVERRIDE:-none}"
export OMP_NUM_THREADS=1
export TORCH_NCCL_ASYNC_ERROR_HANDLING="${TORCH_NCCL_ASYNC_ERROR_HANDLING:-1}"
export TORCH_NCCL_ENABLE_MONITORING="${TORCH_NCCL_ENABLE_MONITORING:-1}"
export TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC="${TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC:-1200}"

ulimit -l unlimited || true
ulimit -s unlimited || true

module load python/3.11.9
source "${VENV}/bin/activate"
export PYTHONPATH="${REPROCLI}/src:${PYTHONPATH:-}"
cd "${REPROCLI}"

if [[ -z "${CXX:-}" || "${CXX}" == "CC" ]]; then
  if command -v g++ >/dev/null 2>&1; then export CXX="$(command -v g++)"; fi
fi
[[ -n "${CXX:-}" ]] && export TORCHINDUCTOR_CXX="${TORCHINDUCTOR_CXX:-${CXX}}"

echo "host=$(hostname)  job=${SLURM_JOB_ID:-?}  endpoint_file=${ENDPOINT_FILE}"
nvidia-smi topo -m || true

# Single 4xGH200 node => tensor-parallel 4 picked from the model profile.
# The launcher binds 0.0.0.0, discovers a routable hsn (hsn0..hsn3) fabric IP,
# and writes $ENDPOINT_FILE once /health is green. It blocks until the job ends.
python -m reprocli_serve \
  --model "${MODEL}" \
  --served-model-name "${SERVED_NAME}" \
  --port "${PORT}" \
  --tensor-parallel-size 2 \
  --max-model-len 196608 \
  --distributed-executor-backend mp \
  --compilation-config '{"mode":3,"pass_config":{"fuse_minimax_qk_norm":true}}' \
  --endpoint-file "${ENDPOINT_FILE}" \
  -- --kv-offloading-backend native --kv-offloading-size 64   # 64GB CPU RAM as KV-cache overflow (V1 replaces --swap-space)
