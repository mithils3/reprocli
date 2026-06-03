srun -A betw-dtai-gh --time=02:00:00 --nodes=1 --ntasks-per-node=32 --partition=ghx4-interactive --gpus=4 --mem=256g --pty /bin/bash 
module load python/3.11.9 
source /u/msalunkhe/reprocli/.venv/bin/activate
export VLLM_CACHE_ROOT=/projects/bgnp/msalunkhe/MiniMax-M2.7/vllm_cache
vllm bench throughput \
  --model /projects/bgnp/msalunkhe/MiniMax-M2.7 \
  --input-len 1024 \
  --output-len 1024 \
  --num-prompts 100 \
  --tensor-parallel-size 4 \
  --trust-remote-code \
  --compilation-config '{"mode":3,"pass_config":{"fuse_minimax_qk_norm":true}}'
