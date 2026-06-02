srun -A betw-dtai-gh --time=02:00:00 --nodes=1 --ntasks-per-node=32 --partition=ghx4-interactive --gpus=4 --mem=256g --pty /bin/bash 
module load python/3.11.9 
source /u/msalunkhe/reprocli/.venv/bin/activate
cd /u/msalunkhe/reprocli/
python3 src/run_arxiv_prompt_vllm.py \
  --num-prompts 8 \
  --tool-rounds 8 \
  --max-input-tokens 128000 \
  --max-tokens 32768 \
  --request-workers 8 \
  --stream-first-response \
  --dataset /projects/bgnp/msalunkhe/datasets \
  --model /projects/bgnp/msalunkhe/MiniMax-M2.7
