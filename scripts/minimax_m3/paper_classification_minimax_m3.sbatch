#!/bin/bash
# Full-dataset Stage-1 classification with MiniMax-M3 (MXFP8) on 2x DeltaAI ghx4
# nodes. Multi-node serve paradigm, in one job:
#   step 1  one reprocli_serve process per node -- plain TP=8 spanning the two
#           nodes (inter-node tensor parallel over the Slingshot fabric, 4 GPUs
#           each); the MXFP8 weights split over 8 GPUs. rank 0 serves the API and
#           publishes the endpoint file. (No expert parallel: EP would put a MoE
#           all-to-all on the inter-node socket fabric; with it off the experts
#           are TP-sharded and ride the same all-reduce as the rest of the model.
#           PP across nodes would be lighter still, but MiniMax-M3's vLLM arch
#           does not support pipeline parallel -- pin NCCL to the hsn NICs below.)
#   step 2  the model-agnostic classifier attaches by URL, runs the ENTIRE
#           paper-bundle dataset, and pushes results to a Hugging Face dataset
#           (incrementally + at the end, so a wall-time kill keeps partial results).
#
#   sbatch scripts/minimax_m3/paper_classification_minimax_m3.sbatch
#   # override the HF target / dataset from the environment if needed:
#   HF_REPO=Mithilss/neurips-2025-minimax-m3 sbatch scripts/minimax_m3/paper_classification_minimax_m3.sbatch
#
# HF upload needs a logged-in token (huggingface-cli login, or HF_TOKEN in the
# submitting env -- carried in by --export=ALL).
#
#SBATCH -J reprocli_m3_classification
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --mem=256G
#SBATCH --time=48:00:00
#SBATCH -o slurm-m3-classification-%j.out
#SBATCH -e slurm-m3-classification-%j.err
#SBATCH --export=ALL
#SBATCH --mail-user=mithils3@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"
VENV="${VENV:-/u/msalunkhe/reprocli/.venv}"
MODEL="${MODEL:-MiniMaxAI/MiniMax-M3-MXFP8}"
SERVED_NAME="${SERVED_NAME:-MiniMaxAI/MiniMax-M3}"
PORT="${PORT:-8000}"
IFACE_NAME="${IFACE_NAME:-hsn0}"
TP="${TP:-8}"                         # tensor parallel spans both nodes (4 GPUs each)
GPUS_PER_NODE="${GPUS_PER_NODE:-4}"   # GPUs each srun task binds (one task per node)
DATASET="${DATASET:-Mithilss/neurips-2025-paper-bundles}"
HF_REPO="${HF_REPO:-Mithilss/neurips-2025-minimax-m3}"
ENDPOINT_FILE="${ENDPOINT_FILE:-/work/nvme/bfvr/msalunkhe/outputs/minimax_m3_${SLURM_JOB_ID}.json}"

# --- Standardized multi-node env block (no loopback pin; the fabric is required) ---
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
# Surface a stuck collective as a stack trace instead of an indefinite hang.
export TORCH_NCCL_ASYNC_ERROR_HANDLING="${TORCH_NCCL_ASYNC_ERROR_HANDLING:-1}"
# Gloo's TCPStore rendezvous needs one interface; NCCL data should use the four
# Slingshot NICs. Pin them by exact name -- a bare "hsn" prefix also matches the
# hsn0.561.. VLAN aliases (public 141.142.x IPs), and mixing those with the
# private 172.28.x fabric makes the cross-node socket connect hang at NCCL init.
export GLOO_SOCKET_IFNAME="${IFACE_NAME}"
export NCCL_SOCKET_IFNAME="${NCCL_SOCKET_IFNAME:-hsn0,hsn1,hsn2,hsn3}"
ulimit -l unlimited || true
ulimit -s unlimited || true

module load python/3.11.9
source "${VENV}/bin/activate"
export PYTHONPATH="${REPROCLI}/src:${PYTHONPATH:-}"
cd "${REPROCLI}"
mkdir -p outputs

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
echo "NNODES=${NNODES} HEAD_NODE=${HEAD_NODE} HEAD_IP=${HEAD_IP} TP=${TP} EP=off"
echo "model=${MODEL} served=${SERVED_NAME} hf_repo=${HF_REPO} endpoint_file=${ENDPOINT_FILE}"
nvidia-smi topo -m || true

# --- Step 1: multi-node server (background); only rank 0 serves & publishes ---
# TP=8 spans both nodes: each srun task binds its node's 4 GPUs and the
# --nnodes/--node-rank/--master-addr rendezvous joins them into one TP=8 group.
# The M3 flags (--block-size 128, --tool-call-parser/--reasoning-parser
# minimax_m3, --mm-encoder-tp-mode data, --enable-auto-tool-choice,
# --trust-remote-code) come from the minimax_m3 serving profile
# (src/reprocli_serve/profiles.py), so they don't have to be retyped here.
# Expert parallel is off (TP-sharded MoE); add --enable-expert-parallel to opt in.
srun --jobid="${SLURM_JOB_ID}" --nodes="${NNODES}" --ntasks="${NNODES}" \
  --ntasks-per-node=1 --gpus-per-task="${GPUS_PER_NODE}" --cpus-per-task=32 \
  bash -lc '
    set -euo pipefail
    module load python/3.11.9
    source "'"${VENV}"'/bin/activate"
    export PYTHONPATH="'"${REPROCLI}"'/src:${PYTHONPATH:-}"
    cd "'"${REPROCLI}"'"
    # Pin vLLM internal RPC / multiproc message queue to the fabric. vLLMs
    # get_ip() otherwise picks the public 141.142.x VLAN (mq_connect_ip=...),
    # which is unroutable compute-to-compute, so workers finish NCCL on the
    # 172.28.x fabric then hang dialing the engine MQ. Each node uses its OWN
    # fabric IP, not HEAD_IP.
    export VLLM_HOST_IP="$(ip -o -4 addr show '"${IFACE_NAME}"' | awk "{split(\$4,a,\"/\"); print a[1]; exit}")"
    HEADLESS=()
    [[ "${SLURM_PROCID}" != "0" ]] && HEADLESS=(--headless)
    python -m reprocli_serve \
      --model "'"${MODEL}"'" \
      --served-model-name "'"${SERVED_NAME}"'" \
      --port "'"${PORT}"'" \
      --tensor-parallel-size "'"${TP}"'" \
      --nnodes "'"${NNODES}"'" \
      --node-rank "${SLURM_PROCID}" \
      --master-addr "'"${HEAD_IP}"'" \
      --advertise-ip "'"${HEAD_IP}"'" \
      --endpoint-file "'"${ENDPOINT_FILE}"'" \
      "${HEADLESS[@]}"
  ' &
SERVER_PID=$!
trap 'kill "${SERVER_PID}" 2>/dev/null || true; rm -f "${ENDPOINT_FILE}"' EXIT

# --- Wait for rank 0 to publish the endpoint (written only once /health green) -
echo "waiting for ${ENDPOINT_FILE} ..."
for _ in $(seq 1 720); do
  [[ -f "${ENDPOINT_FILE}" ]] && break
  if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
    echo "server exited before publishing an endpoint" >&2; exit 1
  fi
  sleep 5
done
[[ -f "${ENDPOINT_FILE}" ]] || { echo "timed out waiting for ${ENDPOINT_FILE}" >&2; exit 1; }
SERVER_URL="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["base_url"])' "${ENDPOINT_FILE}")"
echo "attaching classifier to ${SERVER_URL}"

# --- Step 2: model-agnostic runner classifies the FULL dataset & uploads to HF -
# No --num-prompts => the entire dataset. No tensor-parallel / parser flags here:
# those live on the server. M3's recommended sampling is temperature=1.0,
# top_p=0.95, top_k=40 (model card).
python3 src/run_arxiv_prompt_vllm.py \
  --vllm-server-url "${SERVER_URL}" \
  --model "${SERVED_NAME}" \
  --dataset "${DATASET}" \
  --tool-rounds 12 \
  --max-input-tokens 128000 \
  --max-tokens 8192 \
  --request-workers 32 \
  --temperature 1.0 \
  --top-p 0.95 \
  --top-k 40 \
  --stream-first-response \
  --save-round-jsonl \
  --max-model-len 196608 \
  --output outputs/neurips_2025_minimax_m3.jsonl \
  --extracted-output outputs/neurips_2025_minimax_m3_extracted.jsonl \
  --hf-repo "${HF_REPO}"
