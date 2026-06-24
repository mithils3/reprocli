#!/bin/bash
# Re-pin run: re-classify ONLY the 115 frozen benchmark papers (eval-100 +
# dev-15) with MiniMax-M2.7 and the updated prompt, so each row gains a coherent
# pinned `match_target` tuple. Same serve paradigm as paper_classification.sbatch
# (step 1 stands up the vLLM server, step 2 attaches the runner by URL), but
# scoped to the frozen ids via --paper-ids-file and written to outputs/v6/.
#
# After the job: merge onto the frozen splits and upload —
#   python tools/merge_repin_into_splits.py \
#     --repin outputs/v6/repin_eval_dev_115_extracted.jsonl \
#     --splits-repo Mithilss/reprobench-splits \
#     --out-eval outputs/v6/eval_100.jsonl --out-dev outputs/v6/dev_split.jsonl
#   python tools/upload_audit_pool_hf.py --repo Mithilss/reprobench-splits \
#     --file outputs/v6/eval_100.jsonl  --path-in-repo eval_100.jsonl
#   python tools/upload_audit_pool_hf.py --repo Mithilss/reprobench-splits \
#     --file outputs/v6/dev_split.jsonl --path-in-repo dev_split.jsonl
#
#SBATCH -J reprocli_repin_eval_dev_115
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --gpus-per-node=4
#SBATCH --gpu-bind=none
#SBATCH --mem=256G
#SBATCH --time=08:00:00
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
IDS_FILE="${IDS_FILE:-outputs/v6/eval_dev_115_ids.txt}"

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
