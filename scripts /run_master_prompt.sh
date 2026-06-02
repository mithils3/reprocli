srun -A betw-dtai-gh --time=02:00:00 --nodes=1 --ntasks-per-node=32 --partition=ghx4-interactive --gpus=4 --mem=256g --pty /bin/bash 
module load python/3.11.9 
source /u/msalunkhe/reprocli/.venv/bin/activate

python3 src/run_arxiv_prompt_vllm.py \
  --num-prompts 10 \
  --tool-rounds 4 \
  --no-compile \
  --enforce-eager \
  --request-workers 10 \
  --stream-first-response \
  --dataset /projects/bgnp/msalunkhe/datasets \
  --model /projects/bgnp/msalunkhe/MiniMax-M2.7
