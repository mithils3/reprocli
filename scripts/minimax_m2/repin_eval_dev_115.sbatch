#!/bin/bash
# Re-pin run: re-classify ONLY the 115 frozen benchmark papers (eval-100 +
# dev-15) with MiniMax-M2.7 and the updated prompt, so each row gains a coherent
# pinned `match_target` tuple, then publish the updated splits to Hugging Face.
# Same serve paradigm as paper_classification.sbatch (step 1 stands up the vLLM
# server, step 2 attaches the runner by URL), scoped to the frozen ids via
# --paper-ids-file. The M2 server runs fp8 KV cache (~2x the KV pool vs bf16) and
# offloads evicted KV blocks to Grace LPDDR5X over NVLink-C2C (~900 GB/s), so the
# 32 concurrent agentic conversations survive eviction during off-GPU tool steps
# instead of recomputing their multi-ten-k-token prefixes (KV_OFFLOAD_GB=0 opts
# out; KV_CACHE_DTYPE=auto reverts to bf16 KV). Steps 3-4 merge the re-pinned
# claim fields onto the frozen
# splits (preserving all selection metadata) and upload eval_100.jsonl /
# dev_split.jsonl to Mithilss/reprobench-splits.
#
# Upload needs HF auth on the compute node: export HF_TOKEN (write scope) before
# sbatch, or have a cached `hf auth login` token. Set DO_UPLOAD=0 to stop after
# the merge (writes outputs/v6/, no push) if you want to eyeball the tuples first
# — coherence is prompt-only, so spot-check MagCache/AIPW before publishing.
#
#SBATCH -J reprocli_repin_eval_dev_115
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --gpus-per-node=4
#SBATCH --gpu-bind=none
# --mem holds the CPU KV-offload pool too: offloaded blocks live in Grace LPDDR5X
# and must fit the Slurm cgroup, so size above the 4x KV_OFFLOAD_GB total. ghx4 is
# ~140GB LPDDR5/GH200, ~110GB usable after OS reserve -> ~440GB/node; cap at 400G.
#SBATCH --mem=400G
#SBATCH --time=08:00:00
#SBATCH -o slurm-%j.out
#SBATCH -e slurm-%j.err
#SBATCH --export=ALL
#SBATCH --mail-user=mithils3@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# Pinned (not ${MODEL:-...}): load + serve MiniMaxAI/MiniMax-M2.7 from the hub.
# Hardcoded so a stale MODEL exported in the submitting shell can't override it
# via --export=ALL — that leak made an earlier run serve a missing local path
# (/work/.../MiniMax-M2.7), which vLLM then mis-read as an HF repo id and rejected.
MODEL="MiniMaxAI/MiniMax-M2.7"
SERVED_NAME="MiniMaxAI/MiniMax-M2.7"
PORT="${PORT:-8000}"
ENDPOINT_FILE="${ENDPOINT_FILE:-${SLURM_TMPDIR:-/tmp}/minimax_endpoint_${SLURM_JOB_ID}.json}"
IDS_FILE="${IDS_FILE:-outputs/v6/eval_dev_115_ids.txt}"
SPLITS_REPO="${SPLITS_REPO:-Mithilss/reprobench-splits}"
DO_UPLOAD="${DO_UPLOAD:-1}"
# fp8 KV cache halves the KV footprint -> ~2x the on-GPU KV pool (more concurrent
# conversations resident before eviction); KV_CACHE_DTYPE=auto reverts to bf16.
# KV_OFFLOAD_GB sizes the CPU offload pool (per GPU); set 0 to serve fp8-only.
KV_CACHE_DTYPE="${KV_CACHE_DTYPE:-fp8}"
KV_OFFLOAD_GB="${KV_OFFLOAD_GB:-32}"

export TORCHINDUCTOR_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/torchinductor
export TRITON_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/triton
export VLLM_CACHE_ROOT=/work/nvme/bfvr/msalunkhe/.cache/vllm_cache
# Hub pull of M2.7 (~230B params) must land on /work/nvme, not the small $HOME
# quota — without this HF defaults to $HOME/.cache/huggingface and fills it.
export HF_HOME=/work/nvme/bfvr/msalunkhe/.cache/huggingface
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

# outputs/ is gitignored, so the id list is not committed — generate it (idempotent)
# from the live, public splits so the job targets exactly the frozen 115 papers.
if [[ ! -f "${IDS_FILE}" ]]; then
  echo "generating ${IDS_FILE} from Mithilss/reprobench-splits"
  mkdir -p "$(dirname "${IDS_FILE}")"
  PYTHONPATH=/u/msalunkhe/reprocli/src:${PYTHONPATH:-} python3 - "${IDS_FILE}" <<'PY'
import sys
from datasets import load_dataset
ids = []
for split in ("test", "validation"):
    for row in load_dataset("Mithilss/reprobench-splits", split=split):
        ids.append(row.get("custom_id") or row.get("arxiv_id"))
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    fh.write("\n".join(i for i in ids if i) + "\n")
print(f"wrote {len(ids)} ids")
PY
fi
echo "host=$(hostname)  endpoint_file=${ENDPOINT_FILE}  ids=$(wc -l < "${IDS_FILE}")"
nvidia-smi topo -m || true

# CPU KV-offload onto Grace LPDDR5X (NVLink-C2C ~900 GB/s, ~7x PCIe Gen5): the
# native connector keeps evicted KV blocks in Grace memory instead of recomputing
# them when the 32 concurrent workers contend during off-GPU tool steps. fp8 KV is
# usually pinned per conversation (APC), so this just extends that residency past
# the on-GPU pool. Flag form is vLLM 0.23.0 (--kv-offloading-* landed in 0.14).
SERVE_TAIL=()
if [[ "${KV_OFFLOAD_GB}" != "0" ]]; then
  SERVE_TAIL=(-- --kv-offloading-backend native --kv-offloading-size "${KV_OFFLOAD_GB}")
fi
echo "kv_cache_dtype=${KV_CACHE_DTYPE} offload_args=(${SERVE_TAIL[*]:-none})"

# --- Step 1: central server (background) -------------------------------------
PYTHONPATH=/u/msalunkhe/reprocli/src:${PYTHONPATH:-} python -m reprocli_serve \
  --model "${MODEL}" \
  --served-model-name "${SERVED_NAME}" \
  --port "${PORT}" \
  --tensor-parallel-size 4 \
  --max-model-len 196608 \
  --distributed-executor-backend mp \
  --compilation-config '{"mode":3,"pass_config":{"fuse_minimax_qk_norm":true}}' \
  --kv-cache-dtype "${KV_CACHE_DTYPE}" \
  --endpoint-file "${ENDPOINT_FILE}" \
  "${SERVE_TAIL[@]}" &
SERVER_PID=$!
trap 'kill "${SERVER_PID}" 2>/dev/null || true' EXIT

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

# --- Step 2: runner, scoped to the 115 frozen ids, v6 outputs ----------------
export PYTHONPATH=/u/msalunkhe/reprocli/src:${PYTHONPATH:-}
python3 src/run_arxiv_prompt_vllm.py \
  --vllm-server-url "${SERVER_URL}" \
  --model "${SERVED_NAME}" \
  --paper-ids-file "${IDS_FILE}" \
  --tool-rounds 12 \
  --max-input-tokens 128000 \
  --max-tokens 8192 \
  --request-workers 32 \
  --stream-first-response \
  --dataset Mithilss/neurips-2025-paper-bundles \
  --output outputs/v6/repin_eval_dev_115.jsonl \
  --extracted-output outputs/v6/repin_eval_dev_115_extracted.jsonl \
  --save-round-jsonl \
  --max-model-len 196608

# --- Step 3: merge re-pinned claim fields onto the frozen splits -------------
# Field-level overlay (claim fields + match_target) keyed by arXiv id; every
# selection-metadata field is preserved. Aborts (set -e) if any frozen paper has
# no re-pinned row, so we never publish a partial split.
python3 tools/merge_repin_into_splits.py \
  --repin outputs/v6/repin_eval_dev_115_extracted.jsonl \
  --splits-repo "${SPLITS_REPO}" \
  --out-eval outputs/v6/eval_100.jsonl \
  --out-dev  outputs/v6/dev_split.jsonl

# --- Step 4: publish the updated splits to Hugging Face ----------------------
if [[ "${DO_UPLOAD}" == "1" ]]; then
  MSG="Re-pin coherent match_target tuples (MiniMax-M2.7, eval-100 + dev-15)"
  python3 tools/upload_audit_pool_hf.py --repo "${SPLITS_REPO}" \
    --file outputs/v6/eval_100.jsonl  --path-in-repo eval_100.jsonl  --commit-message "${MSG}"
  python3 tools/upload_audit_pool_hf.py --repo "${SPLITS_REPO}" \
    --file outputs/v6/dev_split.jsonl --path-in-repo dev_split.jsonl --commit-message "${MSG}"
  echo "published updated splits to https://huggingface.co/datasets/${SPLITS_REPO}"
else
  echo "DO_UPLOAD=0 — merged splits written to outputs/v6/, not uploaded."
fi
