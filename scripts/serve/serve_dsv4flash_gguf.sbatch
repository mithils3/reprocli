#!/bin/bash
# Serve DeepSeek-V4-Flash UD-Q8_K_XL via llama.cpp on 1x 4xGH200 (DeltaAI ghx4).
#
# Runbook: tasks/serve-gguf-llamacpp-gh200.md. vLLM cannot load this: its GGUF
# loader rejects deepseek* architectures (vllm#13665, closed not-planned), same
# dead end as the abandoned GLM-5.2 vLLM path.
#
# Quant choice: unsloth publishes no BF16/F16 for this repo, so UD-Q8_K_XL
# (162 GB, Q8_0 with select tensors upcast) is the closest-to-lossless option.
# Unlike GLM-5.2 (347 GB), weights use only ~41 GB of each 96 GB HBM, so the
# KV cache stays on GPU at f16. DeepSeek uses MLA (compressed KV, cheap per
# token) and MLA models may reject quantized KV (GLM runbook §6), so no
# -ctk/-ctv here.
#
# Download first (login node; ~162 GB to shared NVMe):
#   hf download unsloth/DeepSeek-V4-Flash-GGUF \
#     --include "UD-Q8_K_XL/*" --local-dir "$MODEL_DIR"
#
# Needs a llama.cpp build recent enough for the deepseek4 arch (V4-Flash
# launched 2026-04; git pull + rebuild per runbook §5 if the server dies with
# "unknown architecture").
#
#   sbatch scripts/serve/serve_dsv4flash_gguf.sbatch
#   # then, from a login node or another compute node:
#   #   <consumer> --vllm-server-url "$(jq -r .base_url "$ENDPOINT_FILE")"
#
# Model card wants temperature=1.0 top_p=1.0; set server-side as defaults,
# consumers can still override per-request.
#
#SBATCH -J reprocli_serve_dsv4flash_gguf
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --gpus-per-node=4
#SBATCH --gpu-bind=none
#SBATCH --mem=440G
#SBATCH --time=48:00:00
#SBATCH -o slurm-serve-dsv4flash-gguf-%j.out
#SBATCH -e slurm-serve-dsv4flash-gguf-%j.err
#SBATCH --export=ALL
#SBATCH --mail-user=mithils3@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# --- Paths and knobs (override from the environment) -------------------------
MODEL_DIR="${MODEL_DIR:-/work/nvme/bfvr/msalunkhe/models/DeepSeek-V4-Flash-Q8KXL}"
SHARD="${SHARD:-${MODEL_DIR}/UD-Q8_K_XL/DeepSeek-V4-Flash-UD-Q8_K_XL-00001-of-00005.gguf}"
ALIAS="${ALIAS:-deepseek-ai/DeepSeek-V4-Flash}" # what bench_serve.py / agents ask for
PORT="${PORT:-8080}"
CTX_SIZE="${CTX_SIZE:-131072}"             # TOTAL context, split across slots;
                                           # model does 1M, unsloth suggests
                                           # >=384K for max reasoning mode
PARALLEL="${PARALLEL:-1}"                  # slots; prompt cache is per-slot (§9)
# Publish on a SHARED filesystem so consumers on other nodes can find the URL.
ENDPOINT_FILE="${ENDPOINT_FILE:-/work/nvme/bfvr/msalunkhe/endpoints/dsv4flash.json}"

export PATH="$HOME/llama.cpp/build/bin:$PATH"
command -v llama-server >/dev/null || { echo "llama-server not on PATH; build per runbook §5" >&2; exit 1; }
[[ -f "$SHARD" ]] || { echo "missing shard $SHARD; download per header comment" >&2; exit 1; }

echo "host=$(hostname)  job=${SLURM_JOB_ID:-?}  endpoint_file=${ENDPOINT_FILE}"
echo "shard=${SHARD}  ctx=${CTX_SIZE}  parallel=${PARALLEL}  kv=GPU (f16)"
nvidia-smi topo -m || true

# --jinja: the HF repo ships no standard Jinja template (unsloth points at its
# encoding/ scripts), but the GGUF metadata carries one; if the server errors
# on template parse, drop --jinja first. No --split-mode/--tensor-split, no
# speculative flags (GLM runbook §6 hang, never root-caused). Point at shard 1
# only; llama.cpp finds the rest.
CUDA_VISIBLE_DEVICES=0,1,2,3 llama-server \
  --model "$SHARD" \
  --alias "$ALIAS" \
  -ngl 99 \
  --jinja \
  --temp 1.0 --top-p 1.0 \
  --reasoning-preserve \
  --ctx-size "$CTX_SIZE" --parallel "$PARALLEL" \
  --cache-reuse 256 \
  --host 0.0.0.0 --port "$PORT" &
SERVER_PID=$!

cleanup() {
  rm -f "$ENDPOINT_FILE"
  kill "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT

# --- Publish the endpoint once /health is green -------------------------------
# Discover a routable Slingshot fabric IP (hsn0..hsn3) so other nodes can reach
# us; the server itself binds 0.0.0.0. Poll forever: model load from shared
# NVMe takes minutes and a timeout here just kills a healthy bring-up.
HSN_IP="$(ip -4 -o addr show | awk '$2 ~ /^hsn/ {split($4, a, "/"); print a[1]; exit}')"
[[ -n "$HSN_IP" ]] || { echo "no hsn interface found" >&2; exit 1; }

until curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null; do
  kill -0 "$SERVER_PID" 2>/dev/null || { echo "llama-server exited before /health" >&2; exit 1; }
  sleep 10
done

mkdir -p "$(dirname "$ENDPOINT_FILE")"
printf '{"base_url": "http://%s:%s/v1", "model": "%s", "job_id": "%s"}\n' \
  "$HSN_IP" "$PORT" "$ALIAS" "${SLURM_JOB_ID:-?}" > "$ENDPOINT_FILE"
echo "endpoint published: http://${HSN_IP}:${PORT}/v1"

wait "$SERVER_PID"
