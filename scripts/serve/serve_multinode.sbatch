#!/bin/bash
# Stand up a MULTI-NODE vLLM server (e.g. Kimi-K2.6: TP=4 per node, PP=#nodes)
# on DeltaAI ghx4, reachable from any other node by the URL rank 0 publishes.
# Batch form of scripts/serve/serve_interactive.md.
#
#   sbatch --nodes=2 scripts/serve/serve_multinode.sbatch
#
#SBATCH -J reprocli_serve_mn
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --mem=256G
#SBATCH --time=12:00:00
#SBATCH -o slurm-serve-mn-%j.out
#SBATCH -e slurm-serve-mn-%j.err
#SBATCH --export=ALL
#SBATCH --mail-user=mithils3@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"      # reprocli_serve lives in src/
VENV="${VENV:-/u/msalunkhe/reprocli/.venv}"
MODEL="${MODEL:-/work/hdd/bfvr/msalunkhe/models/Kimi-K2.6}"
SERVED_NAME="${SERVED_NAME:-moonshotai/Kimi-K2.6}"
PORT="${PORT:-8000}"
ENDPOINT_FILE="${ENDPOINT_FILE:-/work/nvme/bfvr/msalunkhe/endpoints/kimi_k2_6.json}"
IFACE_NAME="${IFACE_NAME:-hsn0}"
TP="${TP:-4}"

# --- Standardized env block (no loopback pin: multi-node needs the fabric) ---
export TORCHINDUCTOR_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/torchinductor
export TRITON_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/triton
export VLLM_CACHE_ROOT=/work/nvme/bfvr/msalunkhe/.cache/vllm
export SAFETENSORS_FAST_GPU=1
export CUDA_MODULE_LOADING=LAZY
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export PYTHONFAULTHANDLER=1
export NCCL_CUMEM_ENABLE=0
export NCCL_CUMEM_HOST_ENABLE=0
export NCCL_DEBUG="${NCCL_DEBUG:-INFO}"
export NCCL_NET_PLUGIN="${NCCL_NET_PLUGIN_OVERRIDE:-none}"
export OMP_NUM_THREADS=1
export TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC="${TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC:-1200}"
# Gloo's TCPStore rendezvous needs one interface; NCCL data should use ALL four
# Slingshot NICs, so match the whole hsn family by prefix (NCSA guidance).
export GLOO_SOCKET_IFNAME="${IFACE_NAME}"
export NCCL_SOCKET_IFNAME="${NCCL_SOCKET_IFNAME:-hsn}"
ulimit -l unlimited || true
ulimit -s unlimited || true

module load python/3.11.9
source "${VENV}/bin/activate"
export PYTHONPATH="${REPROCLI}/src:${PYTHONPATH:-}"
cd "${REPROCLI}"

# --- Discover the head node's fabric IP (the rendezvous master) -------------
mapfile -t NODES < <(scontrol show hostnames "${SLURM_JOB_NODELIST}")
NNODES="${#NODES[@]}"
HEAD_NODE="${NODES[0]}"
HEAD_IP="$(
  srun --jobid="${SLURM_JOB_ID}" --nodes=1 --ntasks=1 --nodelist="${HEAD_NODE}" \
    bash -lc "ip -o -4 addr show ${IFACE_NAME} | awk '{split(\$4,a,\"/\"); print a[1]; exit}'"
)"
if [[ -z "${HEAD_IP}" || "${HEAD_IP}" == 127.* ]]; then
  echo "Bad HEAD_IP='${HEAD_IP}' from '${IFACE_NAME}' on ${HEAD_NODE}; check the fabric interface." >&2
  exit 1
fi
echo "NNODES=${NNODES} HEAD_NODE=${HEAD_NODE} HEAD_IP=${HEAD_IP} TP=${TP} PP=${NNODES}"

# --- One launcher process per node; only rank 0 serves the API & publishes ---
srun --jobid="${SLURM_JOB_ID}" --nodes="${NNODES}" --ntasks="${NNODES}" \
  --ntasks-per-node=1 --gpus-per-task="${TP}" --cpus-per-task=32 \
  bash -lc '
    set -euo pipefail
    module load python/3.11.9
    source "'"${VENV}"'/bin/activate"
    export PYTHONPATH="'"${REPROCLI}"'/src:${PYTHONPATH:-}"
    cd "'"${REPROCLI}"'"
    HEADLESS=()
    [[ "${SLURM_PROCID}" != "0" ]] && HEADLESS=(--headless)
    python -m reprocli_serve \
      --model "'"${MODEL}"'" \
      --served-model-name "'"${SERVED_NAME}"'" \
      --port "'"${PORT}"'" \
      --tensor-parallel-size "'"${TP}"'" \
      --pipeline-parallel-size "'"${NNODES}"'" \
      --nnodes "'"${NNODES}"'" \
      --node-rank "${SLURM_PROCID}" \
      --master-addr "'"${HEAD_IP}"'" \
      --advertise-ip "'"${HEAD_IP}"'" \
      --endpoint-file "'"${ENDPOINT_FILE}"'" \
      "${HEADLESS[@]}"
  '
