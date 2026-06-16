# Kimi K2.6 Multi-Node Interactive vLLM Serve on DeltaAI

This runbook starts `moonshotai/Kimi-K2.6` as a raw interactive vLLM server
across 2 DeltaAI nodes with 4 GPUs per node:

- Tensor parallel size: `4`
- Pipeline parallel size: `2`
- Total GPUs: `8`
- Head rank: `0`
- Worker rank: `1`

Use this runbook when you want to test multi-node `vllm serve` directly or run
the repo classifier against an already-running multi-node server.

## 1. Start an Interactive Allocation

Run this on a DeltaAI login node. Replace the account, partition, time, CPU, and
memory settings if your allocation policy needs different values.

```bash
salloc \
  --account=betw-dtai-gh \
  --partition=ghx4-interactive \
  --nodes=2 \
  --ntasks-per-node=1 \
  --gpus-per-node=4 \
  --cpus-per-task=32 \
  --mem=256G \
  --time=02:00:00
```

If your project requires the interactive partition, use
`--partition=ghx4-interactive` instead.

If you SSH to one of the allocated compute nodes after `salloc`, Slurm may not
carry every allocation environment variable into the new shell. The commands
below recover the node list from `SLURM_JOB_ID` when needed.

## 2. Prepare the Shell Inside the Allocation

Run these commands after `salloc` returns an allocation shell.

```bash
set -euo pipefail

module load python/3.11.9
source /u/msalunkhe/reprocli/.venv/bin/activate
cd /u/msalunkhe/reprocli

export TORCHINDUCTOR_CACHE_DIR=/projects/bgnp/msalunkhe/.cache/torchinductor
export TRITON_CACHE_DIR=/projects/bgnp/msalunkhe/.cache/triton
export VLLM_CACHE_ROOT=/projects/bgnp/msalunkhe/.cache/vllm
export SAFETENSORS_FAST_GPU=1
export CUDA_MODULE_LOADING=LAZY
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export PYTHONFAULTHANDLER=1
export NCCL_CUMEM_ENABLE=0
export NCCL_CUMEM_HOST_ENABLE=0
export NCCL_DEBUG="${NCCL_DEBUG:-INFO}"
export NCCL_DEBUG_SUBSYS="${NCCL_DEBUG_SUBSYS:-INIT,ENV,NET}"
export NCCL_NET_PLUGIN="${NCCL_NET_PLUGIN_OVERRIDE:-none}"
export OMP_NUM_THREADS=1
export TORCH_NCCL_ASYNC_ERROR_HANDLING="${TORCH_NCCL_ASYNC_ERROR_HANDLING:-1}"
export TORCH_NCCL_ENABLE_MONITORING="${TORCH_NCCL_ENABLE_MONITORING:-1}"
export TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC="${TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC:-1200}"
export PYTHONPATH=/u/msalunkhe/reprocli/src:${PYTHONPATH:-}

ulimit -l unlimited || true
ulimit -s unlimited || true
```

## 3. Select the Inter-Node Network Interface

Use the high-speed fabric interface if it is available. On DeltaAI this is often
`hsn0`, but verify it on an allocated compute node before launching.

```bash
export IFACE_NAME="${IFACE_NAME:-hsn0}"
srun --nodes=1 --ntasks=1 bash -lc "ip -o -4 addr show ${IFACE_NAME}"

export GLOO_SOCKET_IFNAME="${IFACE_NAME}"
export NCCL_SOCKET_IFNAME="${IFACE_NAME}"
```

If `hsn0` is not present, inspect the compute-node interfaces and set
`IFACE_NAME` to the correct non-loopback fabric interface.

```bash
srun --nodes=1 --ntasks=1 bash -lc "ip -o -4 addr show"
export IFACE_NAME=<interface_name>
export GLOO_SOCKET_IFNAME="${IFACE_NAME}"
export NCCL_SOCKET_IFNAME="${IFACE_NAME}"
```

## 4. Discover Node Names and the Head IP

```bash
SLURM_NODELIST_VALUE="${SLURM_JOB_NODELIST:-${SLURM_NODELIST:-}}"
if [[ -z "${SLURM_NODELIST_VALUE}" && -n "${SLURM_JOB_ID:-}" ]]; then
  SLURM_NODELIST_VALUE="$(
    scontrol show job "${SLURM_JOB_ID}" -o \
      | awk '{for (i = 1; i <= NF; i++) if ($i ~ /^NodeList=/) {sub(/^NodeList=/, "", $i); print $i; exit}}'
  )"
fi
if [[ -z "${SLURM_NODELIST_VALUE}" ]]; then
  echo "Could not find a Slurm node list; start a 2-node allocation with salloc first."
  return 1 2>/dev/null || exit 1
fi

SRUN_JOB_ARG=()
if [[ -n "${SLURM_JOB_ID:-}" ]]; then
  SRUN_JOB_ARG=(--jobid="${SLURM_JOB_ID}")
fi

mapfile -t NODES < <(scontrol show hostnames "${SLURM_NODELIST_VALUE}")
if [[ "${#NODES[@]}" -lt 2 ]]; then
  echo "Expected at least 2 allocated nodes, got ${#NODES[@]} from ${SLURM_NODELIST_VALUE}."
  return 1 2>/dev/null || exit 1
fi

export HEAD_NODE="${NODES[0]}"
export WORKER_NODE="${NODES[1]}"

if [[ -z "${IFACE_NAME:-}" ]]; then
  echo "IFACE_NAME is not set; run section 3 first. With an empty interface name,"
  echo "'ip addr show' lists every interface and the first match is loopback,"
  echo "which silently makes HEAD_IP=127.0.0.1 and breaks the multi-node rendezvous."
  return 1 2>/dev/null || exit 1
fi

export HEAD_IP
HEAD_IP=$(
  srun "${SRUN_JOB_ARG[@]}" --nodes=1 --ntasks=1 --nodelist="${HEAD_NODE}" bash -lc \
    "ip -o -4 addr show ${IFACE_NAME} | awk '{split(\$4,a,\"/\"); print a[1]; exit}'"
)

if [[ -z "${HEAD_IP}" || "${HEAD_IP}" == 127.* ]]; then
  echo "Bad HEAD_IP='${HEAD_IP}' from interface '${IFACE_NAME}' on ${HEAD_NODE}."
  echo "Inspect interfaces and pick the fabric one, then re-run this section:"
  echo "  srun --jobid=\${SLURM_JOB_ID} --nodes=1 --ntasks=1 --nodelist=${HEAD_NODE} bash -lc 'ip -o -4 addr show'"
  return 1 2>/dev/null || exit 1
fi

echo "HEAD_NODE=${HEAD_NODE}"
echo "WORKER_NODE=${WORKER_NODE}"
echo "HEAD_IP=${HEAD_IP}"
```

If the launch ever logs `master_addr=127.0.0.1` (visible in the vLLM
`DP group leader:` line), the worker node can never join the TCPStore at
port `29501` and startup fails after ~10 minutes with
`Timed out after 601 seconds waiting for clients. 4/8 clients joined`.
That always means HEAD_IP was wrong at launch time — fix it here first.

## 5. Launch the Two-Node vLLM Server

This starts one process per node. Rank `0` is the API-serving head process; rank
`1` is headless.

```bash
mkdir -p logs

srun \
  "${SRUN_JOB_ARG[@]}" \
  --nodes=2 \
  --ntasks=2 \
  --ntasks-per-node=1 \
  --gpus-per-task=4 \
  --cpus-per-task=32 \
  bash -lc '
    set -euo pipefail

    module load python/3.11.9
    source /u/msalunkhe/reprocli/.venv/bin/activate
    cd /u/msalunkhe/reprocli

    NODE_RANK="${SLURM_PROCID}"
    EXTRA_ARGS=()
    if [[ "${NODE_RANK}" != "0" ]]; then
      EXTRA_ARGS+=(--headless)
    fi

    echo "host=$(hostname) node_rank=${NODE_RANK}"
    echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"
    env | sort | grep -E "^(CUDA|NCCL|GLOO|VLLM|SLURM|MASTER|OMP|TORCH|TRITON|SAFETENSORS)_" || true
    nvidia-smi topo -m || true

    vllm serve /work/hdd/bfvr/msalunkhe/models/ \
      --host 0.0.0.0 \
      --port 8000 \
      --served-model-name moonshotai/Kimi-K2.6 \
      --trust-remote-code \
      --tensor-parallel-size 4 \
      --pipeline-parallel-size 2 \
      --nnodes 2 \
      --node-rank "${NODE_RANK}" \
      --master-addr "'"${HEAD_IP}"'" \
      --tool-call-parser kimi_k2 \
      --enable-auto-tool-choice \
      --reasoning-parser kimi_k2 \
      --mm-encoder-tp-mode data \
      "${EXTRA_ARGS[@]}"
  ' >"logs/kimi-k2-6-multinode-${SLURM_JOB_ID}.log" 2>&1 &

export VLLM_SERVER_PID=$!
```

The command stays in the foreground through the backgrounded `srun` job step.
Use the log to follow startup:

```bash
tail -f "logs/kimi-k2-6-multinode-${SLURM_JOB_ID}.log"
```

## 6. Health Check and Smoke Test

Wait for startup, then check the head node API from inside the allocation.

```bash
curl -f "http://${HEAD_IP}:8000/health"
```

Run a small chat request:

```bash
curl "http://${HEAD_IP}:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "moonshotai/Kimi-K2.6",
    "messages": [
      {"role": "user", "content": "Reply with one short sentence."}
    ],
    "max_tokens": 64
  }'
```

## 7. Run Paper Classification Through This Server

This uses the same classifier/tool loop as `scripts/paper_classification*.sbatch`,
but attaches it to the multi-node server instead of starting another local
server.

```bash
python3 src/run_arxiv_prompt_vllm.py \
  --vllm-server-url "http://${HEAD_IP}:8000" \
  --model moonshotai/Kimi-K2.6 \
  --num-prompts 2 \
  --tool-rounds 12 \
  --max-input-tokens 128000 \
  --max-tokens 8192 \
  --request-workers 2 \
  --stream-first-response \
  --dataset Mithilss/neurips-2025-paper-bundles \
  --output outputs/neurips_2025_kimi_k2_6_multinode_smoke.jsonl \
  --extracted-output outputs/neurips_2025_kimi_k2_6_multinode_smoke_extracted.jsonl \
  --save-round-jsonl \
  --max-model-len 196608
```

If the server was launched without `--served-model-name`, use the exact model
name from the vLLM startup log instead, for example
`--model /work/hdd/bfvr/msalunkhe/models/`.

Scale `--num-prompts` and `--request-workers` after the smoke run succeeds. The
server is already running, so do not pass tensor-parallel or vLLM launch flags
to this attached classifier command.

## 8. Stop the Server

```bash
kill "${VLLM_SERVER_PID}"
wait "${VLLM_SERVER_PID}" || true
```

If the allocation should end too:

```bash
exit
```

## Scaling Notes

For `N` nodes with 4 GPUs per node, keep `--tensor-parallel-size 4`, set
`--pipeline-parallel-size N`, set `--nnodes N`, and let `NODE_RANK` run from
`0` through `N - 1`. Only rank `0` should omit `--headless`.

If you use 8 GPUs per node instead, set `--tensor-parallel-size 8`. In that
case, a 2-node run has `TP=8`, `PP=2`, and `16` total GPUs.





## Summary

**Root cause:** `HEAD_IP` was `127.0.0.1` when you launched, so vLLM started with `master_addr=127.0.0.1`. The 4 workers on the second node (gh120) tried to reach the rendezvous TCPStore at their *own* loopback on port 29501, never joined, and the head node timed out with `4/8 clients joined`. This almost certainly happened because `IFACE_NAME` was empty when step 4 of the runbook ran — `ip -o -4 addr show` with no interface argument lists everything and the awk grabs the first address, which is `lo` → `127.0.0.1`. Your failed `curl` against `127.0.0.1:8000` is the same bad variable.

**To recover in your current allocation** (still has time on job 2448159):

1. `srun --jobid=$SLURM_JOB_ID --nodes=1 --ntasks=1 bash -lc "ip -o -4 addr show"` to confirm the fabric interface (likely `hsn0`; the head node's real IP is `141.142.249.0` per the log).
2. `export IFACE_NAME=hsn0; export GLOO_SOCKET_IFNAME=$IFACE_NAME; export NCCL_SOCKET_IFNAME=$IFACE_NAME`
3. Re-run the step-4 HEAD_IP discovery, verify `echo $HEAD_IP` prints a real address (not empty, not `127.x`).
4. Re-run the step-5 `srun ... vllm serve` block. The old job step already exited, so nothing needs killing.

**Runbook hardened:** I updated `scripts/kimi_k2_6_multinode_interactive.md` so step 4 now fails fast if `IFACE_NAME` is unset or if the derived `HEAD_IP` is empty/loopback, with a note explaining that `master_addr=127.0.0.1` in the vLLM log always means this exact failure. The change is unstaged on your `kimi-k2-6-model` branch — commit it when you're happy with it.
HEAD_IP=$(srun --jobid=$SLURM_JOB_ID --nodes=1 --ntasks=1 --nodelist=gh049 \
  ip -o -4 addr show hsn0 | awk '{split($4,a,"/"); print a[1]; exit}')
export HEAD_IP
echo "$HEAD_IP"


PYTHONPATH=src python3 -m reprocli_data.build_dataset \
    --data-dir /work/nvme/bfvr/msalunkhe/dataset \
    --workers 32 \
    --allow-failures \
    --stages upload \