srun -A betw-dtai-gh --time=02:00:00 --nodes=1 --ntasks-per-node=32 --partition=ghx4-interactive --gpus=4 --mem=256g --pty /bin/bash 
module load python/3.11.9 
source /u/msalunkhe/reprocli/.venv/bin/activate

python src/run_arxiv_prompt_vllm.py \
    --model /projects/bgnp/msalunkhe/MiniMax-M2.7 \
    --num-prompts 10 \
    --dataset /projects/bgnp/msalunkhe/datasets