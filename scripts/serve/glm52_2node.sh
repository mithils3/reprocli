#!/bin/bash
# Per-rank launcher for GLM-5.2-AWQ-INT4 on 2x GH200 nodes, TP=4 + PP=2.
# One process per node; rank 0 serves the API, the rest run --headless.
# Runbook: tasks/serve-glm52-2node-vllm-gh200.md (letters below are its notes).
#
# Batch:       sbatch scripts/serve/serve_glm52.sbatch
# Interactive: export HEAD_IP=...   # runbook step 3
#   srun --jobid="$SLURM_JOB_ID" --nodes=2 --ntasks=2 --ntasks-per-node=1 \
#     --gpus-per-task=4 --cpus-per-task=32 bash scripts/serve/glm52_2node.sh \
#     > "logs/glm52-2node-${SLURM_JOB_ID}.log" 2>&1 &

set -o pipefail

REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"
VENV="${VENV:-${REPROCLI}/.venv}"
MODEL="${MODEL:-/work/nvme/bfvr/msalunkhe/models/GLM-5.2-AWQ-INT4}"
SERVED_NAME="${SERVED_NAME:-zai-org/GLM-5.2}"
PORT="${PORT:-8000}"
TP="${TP:-4}"
PP="${PP:-2}"
NNODES="${NNODES:-2}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-131072}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-16}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.90}"
IFACE="${IFACE:-hsn0}"
RANK="${SLURM_PROCID:-0}"

# rank 0's fabric address = the torch.distributed rendezvous master. Normally
# exported by the caller; fall back to fabric DNS, where compute-node hostnames
# already resolve (gh109.hsn.cm.delta.internal.ncsa.edu).
if [ -z "${HEAD_IP:-}" ]; then
  HEAD_NODE="$(scontrol show hostnames "${SLURM_JOB_NODELIST:-}" 2>/dev/null | head -1)"
  if [ -n "${HEAD_NODE}" ]; then
    HEAD_IP="$(getent ahostsv4 "${HEAD_NODE}.hsn.cm.delta.internal.ncsa.edu" 2>/dev/null | awk '{print $1; exit}')"
  fi
  if [ -n "${HEAD_IP:-}" ]; then
    export HEAD_IP
    echo "note: HEAD_IP was unset; derived ${HEAD_IP} from ${HEAD_NODE} via fabric DNS" >&2
  else
    echo "FATAL: HEAD_IP is unset and could not be derived." >&2
    echo "  Most likely you ran the step-3 discovery but skipped 'export HEAD_IP':" >&2
    echo "  srun does not propagate unexported variables." >&2
    exit 1
  fi
fi

case "${HEAD_IP}" in
  127.*|"") echo "FATAL: HEAD_IP=${HEAD_IP} is loopback; ranks will never rendezvous." >&2; exit 1 ;;
esac

module load python/3.11.9
# shellcheck disable=SC1091
source "${VENV}/bin/activate"

# DeepGEMM needs CUDA 13's libnvrtc, else the DSA indexer reports itself as
# unsupported ~7 min in. cuda_nvrtc/lib holds the wrong (v12) one. See C1.
export LD_LIBRARY_PATH="${VENV}/lib/python3.11/site-packages/nvidia/cu13/lib:${LD_LIBRARY_PATH:-}"

# Exact NIC names: a bare "hsn" prefix also matches the hsn0.561.. VLAN aliases
# and hangs NCCL init. See E2.
export NCCL_SOCKET_IFNAME="${NCCL_SOCKET_IFNAME:-hsn0,hsn1,hsn2,hsn3}"
export GLOO_SOCKET_IFNAME="${GLOO_SOCKET_IFNAME:-${IFACE}}"

# Each node advertises its OWN fabric IP for vLLM's internal RPC, not HEAD_IP.
# Always recompute: an inherited value names a host this node cannot bind and
# the engine dies with zmq "Cannot assign requested address". See E3.
VLLM_HOST_IP="$(ip -o -4 addr show "${IFACE}" | awk '{split($4,a,"/"); print a[1]; exit}')"
if [ -z "${VLLM_HOST_IP}" ]; then
  echo "FATAL: no IPv4 address on ${IFACE} at $(hostname -s)." >&2
  exit 1
fi
export VLLM_HOST_IP
unset MASTER_ADDR MASTER_PORT

# FlashInfer's mnnvl symm-mem all-reduce IMAs on GH200. This plus
# --disable-custom-all-reduce plus fuse_allreduce_rms:false are needed together
# (C3); the sampler is a separate known crash on this platform.
export VLLM_ALLREDUCE_USE_SYMM_MEM=0
export VLLM_USE_FLASHINFER_SAMPLER=0

if ! python -c "import vllm.third_party.deep_gemm" 2>/dev/null; then
  echo "FATAL: vllm.third_party.deep_gemm will not import on $(hostname)." >&2
  echo "       Fix LD_LIBRARY_PATH (needs nvidia/cu13/lib)." >&2
  exit 1
fi

# Followers run workers only; without --headless they start their own APIServer
# and die at KV init, after loading every weight first.
HEADLESS=()
if [ "${RANK}" != "0" ]; then
  HEADLESS=(--headless)
fi

echo "rank=${RANK} host=$(hostname -s) vllm_host_ip=${VLLM_HOST_IP} head_ip=${HEAD_IP} headless=${#HEADLESS[@]}"

exec vllm serve "${MODEL}" \
  --served-model-name "${SERVED_NAME}" \
  --tensor-parallel-size "${TP}" \
  --pipeline-parallel-size "${PP}" \
  --nnodes "${NNODES}" \
  --node-rank "${RANK}" \
  --master-addr "${HEAD_IP}" \
  --max-model-len "${MAX_MODEL_LEN}" \
  --max-num-seqs "${MAX_NUM_SEQS}" \
  --gpu-memory-utilization "${GPU_MEM_UTIL}" \
  --disable-custom-all-reduce \
  --compilation-config '{"pass_config":{"fuse_allreduce_rms":false}}' \
  --tool-call-parser glm47 \
  --reasoning-parser glm45 \
  --enable-auto-tool-choice \
  --enable-prompt-tokens-details \
  --trust-remote-code \
  --host 0.0.0.0 \
  --port "${PORT}" \
  ${HEADLESS[@]+"${HEADLESS[@]}"}
