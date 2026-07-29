#!/bin/bash
# Per-rank launcher for cyankiwi/GLM-5.2-AWQ-INT4 on 2x GH200 nodes, TP=4 + PP=2.
# Runbook: tasks/serve-glm52-2node-vllm-gh200.md
#
# One process per node; rank 0 serves the API, the rest run --headless. Exists so
# the launch is a single pasteable srun line instead of a nested-quoted payload:
#
#   export HEAD_IP=...          # see runbook step 3
#   srun --jobid="$SLURM_JOB_ID" --nodes=2 --ntasks=2 --ntasks-per-node=1 \
#     --gpus-per-task=4 --cpus-per-task=32 bash scripts/serve/glm52_2node.sh \
#     2>&1 | tee "logs/glm52-2node-${SLURM_JOB_ID}.log"
#
# Every setting is an env override, so no edits are needed to retune.

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

# HEAD_IP is rank 0's fabric address, the torch.distributed rendezvous master.
# Normally exported by the caller (runbook step 3). If it is missing, derive it:
# every rank can resolve the first node in the allocation on the hsn fabric,
# where compute-node hostnames already live (gh109.hsn.cm.delta.internal.ncsa.edu).
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
    echo "  Most likely: you ran the step-3 discovery but skipped 'export HEAD_IP'." >&2
    echo "  A bare  HEAD_IP=\$(srun ...)  sets it in your shell only; srun does not" >&2
    echo "  propagate unexported variables. Run:  export HEAD_IP; echo \$HEAD_IP" >&2
    exit 1
  fi
fi

case "${HEAD_IP}" in
  127.*|"") echo "FATAL: HEAD_IP=${HEAD_IP} is loopback; ranks will never rendezvous." >&2; exit 1 ;;
esac

module load python/3.11.9
# shellcheck disable=SC1091
source "${VENV}/bin/activate"

# DeepGEMM needs CUDA 13's libnvrtc; without it the DSA indexer reports itself
# as unsupported ~7 min into startup. See runbook D1.
export LD_LIBRARY_PATH="${VENV}/lib/python3.11/site-packages/nvidia/cu13/lib:${LD_LIBRARY_PATH:-}"

# Pin the four Slingshot NICs by exact name INSIDE the payload: a bare "hsn"
# prefix also matches the hsn0.561.. VLAN aliases and hangs NCCL init. See F3.
export NCCL_SOCKET_IFNAME="${NCCL_SOCKET_IFNAME:-hsn0,hsn1,hsn2,hsn3}"
export GLOO_SOCKET_IFNAME="${GLOO_SOCKET_IFNAME:-${IFACE}}"

# Each node advertises its OWN fabric IP for vLLM's internal RPC, not HEAD_IP.
# ALWAYS recompute: an inherited VLLM_HOST_IP (left over in the launching shell,
# or a 127.0.0.1 copied from a single-node sbatch) names a host this node cannot
# bind, and the engine dies with
#   zmq.error.ZMQError: Cannot assign requested address (addr='tcp://<other>:...')
# right after logging "mq_connect_ip=<other> (local)". Never honour the caller.
VLLM_HOST_IP="$(ip -o -4 addr show "${IFACE}" | awk '{split($4,a,"/"); print a[1]; exit}')"
if [ -z "${VLLM_HOST_IP}" ]; then
  echo "FATAL: no IPv4 address on ${IFACE} at $(hostname -s). Check the fabric interface." >&2
  exit 1
fi
export VLLM_HOST_IP

# Same reasoning: a stale MASTER_ADDR/MASTER_PORT in the environment (the
# single-node sbatch pins MASTER_ADDR=127.0.0.1) would fight --master-addr.
unset MASTER_ADDR MASTER_PORT

# FlashInfer's mnnvl symmetric-memory all-reduce IMAs on GH200. This env var is
# one of three required pieces; the other two are --disable-custom-all-reduce
# and fuse_allreduce_rms:false below. See runbook D4.
export VLLM_ALLREDUCE_USE_SYMM_MEM=0
# FlashInfer's top-k/top-p sampler crashes the profile run on this platform.
export VLLM_USE_FLASHINFER_SAMPLER=0

if ! python -c "import vllm.third_party.deep_gemm" 2>/dev/null; then
  echo "FATAL: vllm.third_party.deep_gemm will not import on $(hostname)." >&2
  echo "       Fix LD_LIBRARY_PATH (needs nvidia/cu13/lib, not cuda_nvrtc/lib)." >&2
  exit 1
fi

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
