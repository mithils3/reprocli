#!/usr/bin/env bash
set -euo pipefail

# MiniMax M2 trial launch using 4 GPUs with tensor parallelism only.
srun -A betw-dtai-gh \
  --time=02:00:00 \
  --nodes=1 \
  --ntasks-per-node=32 \
  --partition=ghx4-interactive \
  --gpus=4 \
  --mem=256G \
  --pty /bin/bash

export TORCHINDUCTOR_CACHE_DIR=/projects/bgnp/msalunkhe/.cache/torchinductor
export TRITON_CACHE_DIR=/projects/bgnp/msalunkhe/.cache/triton
export VLLM_CACHE_ROOT=/projects/bgnp/msalunkhe/.cache/vllm
export PYTHONPATH=/u/msalunkhe/reprocli/src:${PYTHONPATH:-}

module load python/3.11.9
source /u/msalunkhe/reprocli/.venv/bin/activate
cd /u/msalunkhe/reprocli/

python3 src/run_arxiv_prompt_vllm.py \
  --num-prompts 16 \
  --tool-rounds 12 \
  --max-input-tokens 128000 \
  --max-tokens 8192 \
  --request-workers 16 \
  --stream-first-response \
  --dataset Mithilss/neurips-2025-paper-bundles \
  --model MiniMaxAI/MiniMax-M2.7 \
  --model-profile minimax_m2 \
  --vllm-cache-dir /projects/bgnp/msalunkhe/MiniMax-M2.7/vllm_cache \
  --output outputs/neurips_2025_minimax_m2_trial.jsonl \
  --extracted-output outputs/neurips_2025_minimax_m2_trial_extracted.jsonl \
  --requests-output outputs/neurips_2025_minimax_m2_trial_requests.jsonl \
  --save-round-jsonl \
  --max-model-len 196608 \
  --structured-outputs-config.backend xgrammar
