srun -A betw-dtai-gh --time=02:00:00 --nodes=1 --ntasks-per-node=32 --partition=ghx4-interactive --gpus=4 --mem=256g --pty /bin/bash 
export TORCHINDUCTOR_CACHE_DIR=/projects/bgnp/msalunkhe/.cache/torchinductor
export TRITON_CACHE_DIR=/projects/bgnp/msalunkhe/.cache/triton
export VLLM_CACHE_ROOT=/projects/bgnp/msalunkhe/.cache/vllm   # defaults to ~/.cache/vllm
module load python/3.11.9 
source /u/msalunkhe/reprocli/.venv/bin/activate
cd /u/msalunkhe/reprocli/
python3 src/run_arxiv_prompt_vllm.py \
  --num-prompts 32 \
  --tool-rounds 32 \
  --max-input-tokens 128000 \
  --max-tokens 32768 \
  --request-workers 8 \
  --stream-first-response \
  --dataset /projects/bgnp/msalunkhe/datasets \
  --model /projects/bgnp/msalunkhe/MiniMax-M2.7 \
  --vllm-cache-dir /projects/bgnp/msalunkhe/MiniMax-M2.7/vllm_cache \
  --trust-remote-code \
  --compilation-config '{"mode":3,"pass_config":{"fuse_minimax_qk_norm":true}}'
