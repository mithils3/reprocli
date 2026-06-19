# Interactive vLLM serve on DeltaAI (salloc)

The batch scripts (`serve_gh200.sbatch`, `serve_multinode.sbatch`) are the
preferred path. Use this runbook when you want a server in an interactive
allocation you can poke at, or to debug multi-node rendezvous.

## Single node (4xGH200, e.g. MiniMax-M2.7, TP=4)

```bash
salloc -A betw-dtai-gh -p ghx4-interactive \
  --nodes=1 --ntasks=1 --gpus-per-node=4 --cpus-per-task=16 \
  --mem=256G --time=02:00:00

module load python/3.11.9
source /u/msalunkhe/reprocli/.venv/bin/activate
export PYTHONPATH=/u/msalunkhe/reprocli/src:${PYTHONPATH:-}
cd /u/msalunkhe/reprocli

export VLLM_CACHE_ROOT=/projects/bgnp/msalunkhe/.cache/vllm

python -m reprocli_serve \
  --model /projects/bgnp/msalunkhe/MiniMax-M2.7 \
  --served-model-name MiniMaxAI/MiniMax-M2.7 \
  --port 8000 \
  --tensor-parallel-size 4 \
  --endpoint-file /projects/bgnp/msalunkhe/endpoints/minimax_m2.json
```

It prints the routable base URL once `/health` is green and writes the endpoint
file. From any other node:

```bash
curl -f "$(jq -r .base_url /projects/bgnp/msalunkhe/endpoints/minimax_m2.json)/health"
```

## Multi node (e.g. Kimi-K2.6, TP=4 per node, PP=#nodes)

A model too big for one node needs pipeline parallelism across nodes. The fabric
interface (`hsn0`) and head IP must be discovered first — an empty `IFACE_NAME`
makes `ip addr show` grab loopback and the worker rank never joins the rendezvous.

```bash
salloc -A betw-dtai-gh -p ghx4-interactive \
  --nodes=2 --ntasks-per-node=1 --gpus-per-node=4 \
  --cpus-per-task=32 --mem=256G --time=02:00:00

export IFACE_NAME=hsn0
mapfile -t NODES < <(scontrol show hostnames "$SLURM_JOB_NODELIST")
HEAD_IP=$(srun --jobid=$SLURM_JOB_ID --nodes=1 --ntasks=1 --nodelist="${NODES[0]}" \
  bash -lc "ip -o -4 addr show $IFACE_NAME | awk '{split(\$4,a,\"/\"); print a[1]; exit}'")
echo "HEAD_IP=$HEAD_IP"   # must NOT be empty or 127.*
```

Then launch one process per node (only rank 0 omits `--headless` and publishes):

```bash
export GLOO_SOCKET_IFNAME=$IFACE_NAME NCCL_SOCKET_IFNAME=$IFACE_NAME
srun --jobid=$SLURM_JOB_ID --nodes=2 --ntasks=2 --ntasks-per-node=1 \
  --gpus-per-task=4 --cpus-per-task=32 bash -lc '
    module load python/3.11.9
    source /u/msalunkhe/reprocli/.venv/bin/activate
    export PYTHONPATH=/u/msalunkhe/reprocli/src:${PYTHONPATH:-}
    cd /u/msalunkhe/reprocli
    H=(); [[ "$SLURM_PROCID" != "0" ]] && H=(--headless)
    python -m reprocli_serve \
      --model /work/hdd/bfvr/msalunkhe/models/Kimi-K2.6 \
      --served-model-name moonshotai/Kimi-K2.6 \
      --port 8000 --tensor-parallel-size 4 --pipeline-parallel-size 2 \
      --nnodes 2 --node-rank "$SLURM_PROCID" --master-addr '"$HEAD_IP"' \
      --advertise-ip '"$HEAD_IP"' \
      --endpoint-file /projects/bgnp/msalunkhe/endpoints/kimi_k2_6.json \
      "${H[@]}"
  '
```

For `N` nodes: keep `--tensor-parallel-size 4`, set `--pipeline-parallel-size N`
and `--nnodes N`, and `--node-rank` runs `0..N-1`.
