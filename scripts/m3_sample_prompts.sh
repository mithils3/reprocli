#!/bin/bash
# Small MiniMax-M3 classification smoke: attach the paper classifier to a running
# M3 server (by URL) and classify a few sample papers. Same runner, dataset, and
# flags as scripts/paper_classification.sbatch step 2 -- just capped with
# --num-prompts so you can eyeball the output quickly instead of running the full
# set. No --hf-repo here, so a smoke run never publishes to the results repo.
#
# Run it from a login node or any Delta node once the server is up ("vLLM server
# READY"). Point it at the server one of two ways:
#   ENDPOINT_FILE=/projects/bgnp/msalunkhe/endpoints/minimax_m3.json bash scripts/m3_sample_prompts.sh
#   REPROCLI_SERVER_URL=http://<head-ip>:8000 bash scripts/m3_sample_prompts.sh
#
# Override NUM_PROMPTS / REQUEST_WORKERS to classify more/fewer papers.
set -euo pipefail

REPROCLI="${REPROCLI:-/u/msalunkhe/reprocli}"
ENDPOINT_FILE="${ENDPOINT_FILE:-/projects/bgnp/msalunkhe/endpoints/minimax_m3.json}"
MODEL="${MODEL:-MiniMaxAI/MiniMax-M3}"
DATASET="${DATASET:-Mithilss/neurips-2025-paper-bundles}"
NUM_PROMPTS="${NUM_PROMPTS:-2}"
REQUEST_WORKERS="${REQUEST_WORKERS:-2}"

# Resolve the base URL: an explicit REPROCLI_SERVER_URL wins, else read the URL the
# server published into the endpoint file (python, so there's no jq dependency).
SERVER_URL="${REPROCLI_SERVER_URL:-}"
if [[ -z "${SERVER_URL}" ]]; then
  if [[ ! -f "${ENDPOINT_FILE}" ]]; then
    echo "No REPROCLI_SERVER_URL set and no endpoint file at ${ENDPOINT_FILE}." >&2
    echo "Is the serve job up? Check:  squeue --me  ;  cat ${ENDPOINT_FILE}" >&2
    exit 1
  fi
  SERVER_URL="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["base_url"])' "${ENDPOINT_FILE}")"
fi
SERVER_URL="${SERVER_URL%/}"
echo "Attaching classifier to ${SERVER_URL} (model ${MODEL}, ${NUM_PROMPTS} prompts)"

cd "${REPROCLI}"
export PYTHONPATH="${REPROCLI}/src:${PYTHONPATH:-}"
mkdir -p outputs

# Same runner + flags as paper_classification.sbatch step 2, capped to a few
# prompts. No tensor-parallel / parser flags here: those live on the server, and
# the runner is model-agnostic -- it only needs the URL and the served name.
python3 src/run_arxiv_prompt_vllm.py \
  --vllm-server-url "${SERVER_URL}" \
  --model "${MODEL}" \
  --num-prompts "${NUM_PROMPTS}" \
  --tool-rounds 12 \
  --max-input-tokens 128000 \
  --max-tokens 8192 \
  --request-workers "${REQUEST_WORKERS}" \
  --stream-first-response \
  --dataset "${DATASET}" \
  --output outputs/neurips_2025_minimax_m3_smoke.jsonl \
  --extracted-output outputs/neurips_2025_minimax_m3_smoke_extracted.jsonl \
  --save-round-jsonl \
  --max-model-len 196608

echo
echo "Done. Inspect the results:"
echo "  outputs/neurips_2025_minimax_m3_smoke.jsonl            # full transcripts"
echo "  outputs/neurips_2025_minimax_m3_smoke_extracted.jsonl  # extracted labels"
