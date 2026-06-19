srun -A bfvr-delta-cpu -p cpu-interactive --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=64G --time=01:00:00 --pty bash
hf download moonshotai/Kimi-K2.6 --local-dir /work/hdd/bfvr/msalunkhe/models/Kimi-K2.6
srun -A bfvr-delta-cpu -p cpu-interactive --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=64G --time=01:00:00 --pty bash
srun -A bfvr-delta-gpu -p gpuH200x8-interactive \
  --nodes=1 --gpus-per-node=6 --ntasks-per-node=1 \
  --cpus-per-task=96 --mem=208g --time=01:00:00 --pty bash