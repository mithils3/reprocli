#!/usr/bin/env bash
set -euo pipefail

# DeepSeek V4 Flash needs vLLM 0.20+ and DeepGEMM available in the environment.
# This launch uses 4 GPUs with tensor parallelism only.
srun -A betw-dtai-gh \
  --time=02:00:00 \
  --nodes=1 \
  --ntasks-per-node=32 \
  --partition=ghx4-interactive \
  --gpus=4 \
  --mem=0 \
  --pty /bin/bash

export TORCHINDUCTOR_CACHE_DIR=/projects/bgnp/msalunkhe/.cache/torchinductor
export TRITON_CACHE_DIR=/projects/bgnp/msalunkhe/.cache/triton
export VLLM_CACHE_ROOT=/projects/bgnp/msalunkhe/.cache/vllm

module load python/3.11.9
source /u/msalunkhe/reprocli/.venv/bin/activate
cd /u/msalunkhe/reprocli/

python3 src/run_arxiv_prompt_vllm.py \
  --num-prompts 32 \
  --tool-rounds 10 \
  --max-input-tokens 128000 \
  --max-tokens 8192 \
  --request-workers 8 \
  --stream-first-response \
  --dataset /projects/bgnp/msalunkhe/datasets \
  --model deepseek-ai/DeepSeek-V4-Flash \
  --model-profile deepseek_v4_flash \
  --reasoning-effort high \
  --tensor-parallel-size 4 \
  --vllm-cache-dir /projects/bgnp/msalunkhe/DeepSeek-V4-Flash/vllm_cache
