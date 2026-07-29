#!/bin/bash
# Serve GLM-5.2 AWQ-INT4 via vLLM on 2x ghx4 (8x GH200), TP=4 + PP=2, no offload.
# Runbook: tasks/serve-glm52-2node-vllm-gh200.md
#
#   sbatch scripts/serve/serve_glm52.sbatch
#   <consumer> --vllm-server-url "$(jq -r .base_url "$ENDPOINT_FILE")"
#
# Replaces the llama.cpp GGUF serve (40 t/s decode / 575 t/s prefill). MEASURED
# 2026-07-29: 78.6 t/s decode, 6822 t/s cold prefill, 280.2 t/s aggregate over
# 8 agents, 8m47s to /health.
#
#SBATCH -J reprocli_serve_glm52
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=288
#SBATCH --mem=440G
#SBATCH --time=48:00:00
#SBATCH -o slurm-serve-glm52-%j.out
#SBATCH -e slurm-serve-glm52-%j.err
#SBATCH --export=ALL
#SBATCH --mail-user=mithils3@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

export REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"
export VENV="${VENV:-${REPROCLI}/.venv}"
export MODEL="${MODEL:-/work/nvme/bfvr/msalunkhe/models/GLM-5.2-AWQ-INT4}"
export SERVED_NAME="${SERVED_NAME:-zai-org/GLM-5.2}"
export PORT="${PORT:-8000}"
export TP="${TP:-4}"
export MAX_MODEL_LEN="${MAX_MODEL_LEN:-131072}"
export MAX_NUM_SEQS="${MAX_NUM_SEQS:-16}"
export GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.90}"
export IFACE="${IFACE:-hsn0}"
ENDPOINT_FILE="${ENDPOINT_FILE:-/work/nvme/bfvr/msalunkhe/endpoints/glm52.json}"

export VLLM_CACHE_ROOT=/work/nvme/bfvr/msalunkhe/.cache/vllm
export TORCHINDUCTOR_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/torchinductor
export TRITON_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/triton
export SAFETENSORS_FAST_GPU=1 CUDA_MODULE_LOADING=LAZY CUDA_DEVICE_ORDER=PCI_BUS_ID
export PYTHONFAULTHANDLER=1
export NCCL_CUMEM_ENABLE=0 NCCL_CUMEM_HOST_ENABLE=0
export NCCL_NET_PLUGIN="${NCCL_NET_PLUGIN_OVERRIDE:-none}"
export OMP_NUM_THREADS=1
export TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC=1800
export TORCH_NCCL_ASYNC_ERROR_HANDLING=1
unset VLLM_HOST_IP MASTER_ADDR MASTER_PORT   # per-node facts; inherited ones bind the wrong host (E3)
ulimit -l unlimited || true
ulimit -s unlimited || true

module load python/3.11.9
source "${VENV}/bin/activate"
export PYTHONPATH="${REPROCLI}/src:${PYTHONPATH:-}"
cd "${REPROCLI}"

mapfile -t NODES < <(scontrol show hostnames "${SLURM_JOB_NODELIST}")
export NNODES="${#NODES[@]}"
export PP="${PP:-${NNODES}}"
HEAD_IP="$(
  srun --jobid="${SLURM_JOB_ID}" --nodes=1 --ntasks=1 --nodelist="${NODES[0]}" \
    bash -lc "ip -o -4 addr show ${IFACE} | awk '{split(\$4,a,\"/\"); print a[1]; exit}'"
)"
[[ -n "${HEAD_IP}" && "${HEAD_IP}" != 127.* ]] || {
  echo "bad HEAD_IP='${HEAD_IP}' from ${IFACE} on ${NODES[0]}" >&2; exit 1; }
export HEAD_IP
echo "nodes=${NNODES} head=${NODES[0]} head_ip=${HEAD_IP} tp=${TP} pp=${PP}"

# Two seconds here, versus ~7 min to fail at the DSA indexer (C1).
srun --jobid="${SLURM_JOB_ID}" --nodes="${NNODES}" --ntasks="${NNODES}" bash -c \
  "source ${VENV}/bin/activate
   export LD_LIBRARY_PATH=${VENV}/lib/python3.11/site-packages/nvidia/cu13/lib:\${LD_LIBRARY_PATH:-}
   python -c 'import vllm.third_party.deep_gemm'" \
  || { echo "deep_gemm import failed; fix LD_LIBRARY_PATH per runbook C1" >&2; exit 1; }

srun --jobid="${SLURM_JOB_ID}" --nodes="${NNODES}" --ntasks="${NNODES}" \
  --ntasks-per-node=1 --gpus-per-task="${TP}" --cpus-per-task=32 \
  bash scripts/serve/glm52_2node.sh &
SERVER_PID=$!

trap 'rm -f "${ENDPOINT_FILE}"; kill "${SERVER_PID}" 2>/dev/null || true' EXIT

# ~9 min cold. Poll rather than deadline: a timeout only kills a healthy bring-up.
until curl -sf "http://${HEAD_IP}:${PORT}/health" >/dev/null; do
  kill -0 "${SERVER_PID}" 2>/dev/null || { echo "vLLM exited before /health" >&2; exit 1; }
  sleep 10
done

mkdir -p "$(dirname "${ENDPOINT_FILE}")"
python3 - "${ENDPOINT_FILE}" <<PY
import json, sys
payload = {
    "base_url": "http://${HEAD_IP}:${PORT}/v1",
    "host": "${HEAD_IP}",
    "port": ${PORT},
    "served_model_name": "${SERVED_NAME}",
    "model_path": "${MODEL}",
    "node": "${NODES[0]}",
    "job_id": "${SLURM_JOB_ID}",
    "health": "ready",
}
with open(sys.argv[1], "w") as f:
    json.dump(payload, f, indent=2)
    f.write("\n")
PY
echo "endpoint published: http://${HEAD_IP}:${PORT}/v1"

wait "${SERVER_PID}"
