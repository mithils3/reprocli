#!/bin/bash
# Serve GLM-5.2 UD-IQ4_XS via llama.cpp on 1x 4xGH200 (DeltaAI ghx4), with the
# KV cache held in Grace CPU RAM (--no-kv-offload) instead of HBM.
#
# Runbook: tasks/serve-gguf-llamacpp-gh200.md (the vLLM path in
# tasks/serve-glm52-vllm-gh200.md is abandoned; do not resurrect it).
#
#   sbatch scripts/serve/serve_glm52_gguf.sbatch
#   # then, from a login node or another compute node:
#   #   <consumer> --vllm-server-url "$(jq -r .base_url "$ENDPOINT_FILE")"
#
# KV-on-CPU tradeoff (runbook §3/§6): attention reads KV every token at every
# layer, so decode goes over NVLink-C2C instead of HBM. The measured pure-HBM
# baseline is 40 t/s decode / ~575 t/s prefill; benchmark this config against
# it before pointing a sweep here. What KV-on-CPU buys is HBM headroom: the
# ~35 GiB the q8_0 pool would occupy stays free, so a large --ctx-size or more
# --parallel slots no longer competes with the 347 GiB of weights.
#
#SBATCH -J reprocli_serve_glm52_gguf
#SBATCH -A betw-dtai-gh
#SBATCH -p ghx4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=288
#SBATCH --gpus-per-node=4
#SBATCH --gpu-bind=none
#SBATCH --mem=440G
#SBATCH --time=48:00:00
#SBATCH -o slurm-serve-glm52-gguf-%j.out
#SBATCH -e slurm-serve-glm52-gguf-%j.err
#SBATCH --export=ALL
#SBATCH --mail-user=mithils3@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# --- Paths and knobs (override from the environment) -------------------------
MODEL_DIR="${MODEL_DIR:-/work/nvme/bfvr/msalunkhe/models/GLM-5.2-IQ4XS}"
SHARD="${SHARD:-${MODEL_DIR}/UD-IQ4_XS/GLM-5.2-UD-IQ4_XS-00001-of-00009.gguf}"
ALIAS="${ALIAS:-zai-org/GLM-5.2}"          # what bench_serve.py / agents ask for
PORT="${PORT:-8080}"
CTX_SIZE="${CTX_SIZE:-163840}"             # TOTAL context (fits 128000 in + 32768 out), split across slots
PARALLEL="${PARALLEL:-1}"                  # slots; prompt cache is per-slot (§9)
# Publish on a SHARED filesystem so consumers on other nodes can find the URL.
ENDPOINT_FILE="${ENDPOINT_FILE:-/work/nvme/bfvr/msalunkhe/endpoints/glm52.json}"

export PATH="$HOME/llama.cpp/build/bin:$PATH"
command -v llama-server >/dev/null || { echo "llama-server not on PATH; build per runbook §5" >&2; exit 1; }
[[ -f "$SHARD" ]] || { echo "missing shard $SHARD; download per runbook §4" >&2; exit 1; }

echo "host=$(hostname)  job=${SLURM_JOB_ID:-?}  endpoint_file=${ENDPOINT_FILE}"
echo "shard=${SHARD}  ctx=${CTX_SIZE}  parallel=${PARALLEL}  kv=CPU (q8_0)"
nvidia-smi topo -m || true

# --no-kv-offload: KV cache lives in Grace LPDDR, reached over 900 GB/s C2C.
# -ctk/-ctv q8_0 halve KV bytes vs f16; if the server dies with a KV-type
# error (MLA models may reject quantized KV, §6), drop those two flags first.
# No --split-mode/--tensor-split, no speculative flags (§6 hang, never
# root-caused). Point at shard 1 only; llama.cpp finds the rest.
CUDA_VISIBLE_DEVICES=0,1,2,3 llama-server \
  --model "$SHARD" \
  --alias "$ALIAS" \
  -ngl 99 \
  --no-kv-offload \
  -ctk q8_0 -ctv q8_0 \
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
