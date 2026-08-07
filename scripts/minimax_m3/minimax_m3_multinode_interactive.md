# MiniMax-M3 Multi-Node Interactive vLLM Serve on DeltaAI

A quick way to stand up `MiniMaxAI/MiniMax-M3` (MXFP8) interactively across 2
DeltaAI ghx4 nodes and throw a few classification prompts at it.

- Model: `MiniMaxAI/MiniMax-M3-MXFP8` (428B-param MoE, ~22B active, MiniMax
  Sparse Attention, native vision encoder). The MXFP8 weights (~428 GB) do not
  fit one node's 4×96 GB HBM, so this needs **2 nodes**.
- Topology: plain tensor parallel `8` spanning both nodes (inter-node TP over the
  Slingshot fabric, 4 GPUs each); the MoE experts are TP-sharded. No expert
  parallel — EP would add a MoE all-to-all over the inter-node socket fabric; add
  `--enable-expert-parallel` to opt back in.
- Total GPUs: `8` — head rank `0`, worker rank `1`

For the unattended full run, use
`scripts/minimax_m3/paper_classification_minimax_m3.sbatch` (it serves M3 on 2
nodes and classifies the whole dataset). Use this runbook when you want a server
in an interactive allocation you can poke at.

## 0. Prerequisites

The venv's vLLM must be new enough to support MiniMax-M3 — the `minimax_m3`
tool-call/reasoning parsers, MiniMax Sparse Attention kernels, and `--block-size
128`. The official recipe pins the `vllm/vllm-openai:minimax-m3` image; check
<https://recipes.vllm.ai/MiniMaxAI/MiniMax-M3> for the exact version and upgrade
the venv to match if `vllm serve` rejects `--reasoning-parser minimax_m3`.

A 428 GB checkpoint streams faster (and works offline) from a local dir:

```bash
hf download MiniMaxAI/MiniMax-M3-MXFP8 \
  --local-dir /work/hdd/bfvr/msalunkhe/models/MiniMax-M3-MXFP8
```

Then point `--model` at that path instead of the HF id below.

## 1. Start an Interactive Allocation

Run this on a DeltaAI login node.

```bash
salloc \
  --account=betw-dtai-gh \
  --partition=ghx4-interactive \
  --nodes=2 \
  --ntasks-per-node=1 \
  --gpus-per-node=4 \
  --cpus-per-task=32 \
  --mem=256G \
  --time=01:00:00
```

## 2. Prepare the Shell Inside the Allocation

```bash
set -euo pipefail

module load python/3.11.9
source /u/msalunkhe/reprocli/.venv/bin/activate
cd /u/msalunkhe/reprocli
export PYTHONPATH=/u/msalunkhe/reprocli/src:${PYTHONPATH:-}

export VLLM_CACHE_ROOT=/work/nvme/bfvr/msalunkhe/.cache/vllm
export TORCHINDUCTOR_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/torchinductor
export TRITON_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/triton
export SAFETENSORS_FAST_GPU=1
export CUDA_MODULE_LOADING=LAZY
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export PYTHONFAULTHANDLER=1
export NCCL_CUMEM_ENABLE=0
export NCCL_CUMEM_HOST_ENABLE=0
export NCCL_DEBUG="${NCCL_DEBUG:-INFO}"
export NCCL_NET_PLUGIN="${NCCL_NET_PLUGIN_OVERRIDE:-none}"
export OMP_NUM_THREADS=1
export TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC="${TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC:-1200}"
# Surface a stuck collective as a stack trace instead of an indefinite hang.
export TORCH_NCCL_ASYNC_ERROR_HANDLING="${TORCH_NCCL_ASYNC_ERROR_HANDLING:-1}"

ulimit -l unlimited || true
ulimit -s unlimited || true
```

## 3. Select the Fabric Interface and Discover HEAD_IP

The fabric interface and head IP must be discovered first — an empty
`IFACE_NAME` makes `ip addr show` grab loopback, so `HEAD_IP` silently becomes
`127.0.0.1` and the worker rank never joins the rendezvous (the launch then hangs
~10 min and dies with `4/8 clients joined`).

```bash
export IFACE_NAME=hsn0
srun --jobid="$SLURM_JOB_ID" --nodes=1 --ntasks=1 bash -lc "ip -o -4 addr show $IFACE_NAME"

export GLOO_SOCKET_IFNAME="$IFACE_NAME"
# Pin the four hsn NICs by exact name. A bare "hsn" prefix also matches the
# hsn0.561.. VLAN aliases (public 141.142.x IPs); mixing those with the private
# 172.28.x fabric makes the cross-node socket connect hang at NCCL init. The
# step-4 srun re-exports this same value inside the bash -lc payload, so the
# launch is correct even if this outer export is skipped or a bare "hsn" leaked
# in from ~/.bashrc -- check yours with: echo "$NCCL_SOCKET_IFNAME".
export NCCL_SOCKET_IFNAME=hsn0,hsn1,hsn2,hsn3

mapfile -t NODES < <(scontrol show hostnames "$SLURM_JOB_NODELIST")
HEAD_IP=$(srun --jobid="$SLURM_JOB_ID" --nodes=1 --ntasks=1 --nodelist="${NODES[0]}" \
  bash -lc "ip -o -4 addr show $IFACE_NAME | awk '{split(\$4,a,\"/\"); print a[1]; exit}'")
export HEAD_IP
echo "HEAD_IP=$HEAD_IP"   # must NOT be empty or 127.*
```

If `hsn0` is absent, inspect interfaces with
`srun --jobid="$SLURM_JOB_ID" --nodes=1 --ntasks=1 bash -lc "ip -o -4 addr show"`
and set `IFACE_NAME` to the routable fabric interface.

## 4. Launch the Two-Node Server

One process per node via `reprocli_serve`; only rank 0 serves the API and
publishes the endpoint file. `--tensor-parallel-size 8` spans both nodes (each
binds its 4 GPUs; the `--nnodes`/`--node-rank`/`--master-addr` rendezvous joins
them into one TP=8 group). The M3 flags (`--block-size 128`,
`--tool-call-parser minimax_m3`, `--reasoning-parser minimax_m3`,
`--kv-cache-dtype fp8`, `--mm-encoder-tp-mode data`, `--enable-auto-tool-choice`,
`--trust-remote-code`) come from the `minimax_m3` serving profile, so they don't
have to be retyped here. Expert parallel is off (TP-sharded MoE); pass
`--enable-expert-parallel` to opt in.

```bash
mkdir -p logs
ENDPOINT_FILE=/work/nvme/bfvr/msalunkhe/endpoints/minimax_m3.json

srun --jobid="$SLURM_JOB_ID" --nodes=2 --ntasks=2 --ntasks-per-node=1 \
  --gpus-per-task=4 --cpus-per-task=32 bash -lc '
    module load python/3.11.9
    source /u/msalunkhe/reprocli/.venv/bin/activate
    export PYTHONPATH=/u/msalunkhe/reprocli/src:${PYTHONPATH:-}
    cd /u/msalunkhe/reprocli
    # Pin NCCL to the four real Slingshot NICs INSIDE the srun payload, so a
    # bare "hsn" (or anything) leaked from the outer shell / ~/.bashrc can not
    # poison the inter-node bootstrap. A bare "hsn" prefix also matches the
    # hsn0.561.. VLAN aliases (public 141.142.x IPs); mixing those with the
    # private 172.28.x fabric hangs the cross-node socket connect right after
    # "vLLM is using nccl==..." (NCCL comm init), with NO progress past it.
    export NCCL_SOCKET_IFNAME=hsn0,hsn1,hsn2,hsn3
    export GLOO_SOCKET_IFNAME=hsn0
    export NCCL_DEBUG="${NCCL_DEBUG:-INFO}"
    # Pin vLLM internal RPC / multiproc message queue to the fabric. vLLMs
    # get_ip() otherwise picks the public 141.142.x VLAN (mq_connect_ip=...),
    # which is unroutable compute-to-compute, so workers finish NCCL on the
    # 172.28.x fabric then hang dialing the engine MQ. Each node uses its OWN
    # hsn0 IP, not HEAD_IP.
    export VLLM_HOST_IP="$(ip -o -4 addr show hsn0 | awk "{split(\$4,a,\"/\"); print a[1]; exit}")"
    H=(); [[ "$SLURM_PROCID" != "0" ]] && H=(--headless)
    python -m reprocli_serve \
      --model MiniMaxAI/MiniMax-M3-MXFP8 \
      --served-model-name MiniMaxAI/MiniMax-M3 \
      --port 8000 --tensor-parallel-size 8 \
      --nnodes 2 --node-rank "$SLURM_PROCID" --master-addr '"$HEAD_IP"' \
      --advertise-ip '"$HEAD_IP"' \
      --endpoint-file '"$ENDPOINT_FILE"' \
      "${H[@]}"
  ' >"logs/minimax-m3-multinode-${SLURM_JOB_ID}.log" 2>&1 &
export VLLM_SERVER_PID=$!

tail -f "logs/minimax-m3-multinode-${SLURM_JOB_ID}.log"   # wait for "vLLM server READY"
```

> Raw equivalent (no profile): swap `python -m reprocli_serve` for
> `vllm serve MiniMaxAI/MiniMax-M3-MXFP8 --host 0.0.0.0 --served-model-name
> MiniMaxAI/MiniMax-M3 --trust-remote-code --tensor-parallel-size 8
> --nnodes 2 --node-rank "$SLURM_PROCID"
> --master-addr "$HEAD_IP" --block-size 128 --kv-cache-dtype fp8
> --tool-call-parser minimax_m3 --reasoning-parser minimax_m3
> --enable-auto-tool-choice --mm-encoder-tp-mode data` (raw `vllm serve` does not
> publish the endpoint file).

## 5. Health Check

Once the log shows `vLLM server READY`:

```bash
curl -fsS "http://${HEAD_IP}:8000/health" && echo "  health: ok"
```

With `/health` green the server is ready for clients. Point a consumer at
`http://${HEAD_IP}:8000` — e.g. the reproduction agent (`python -m reprocli_repro
--vllm-server-url …`) or the auditor runner (`python3 src/run_arxiv_prompt_vllm.py
--mode audit --vllm-server-url …`). See `scripts/reproduce/minimax_m2/run_reproduce_minimax_m2.md`
for a full end-to-end client walkthrough.

## 6. Stop

```bash
kill "$VLLM_SERVER_PID"; wait "$VLLM_SERVER_PID" || true
exit   # also ends the allocation
```

## Notes

- **Scaling**: TP=8 over two nodes is the floor for MXFP8 (the weights need 8
  GPUs). For more nodes set `--tensor-parallel-size 4*N` and `--nnodes N`;
  `--node-rank` runs `0..N-1` and only rank 0 omits `--headless`. Expert parallel
  is off by default; add `--enable-expert-parallel` to shard whole experts
  (adds a MoE all-to-all over the fabric).
- **KV cache / context**: the serve already passes `--kv-cache-dtype fp8` (a
  ~1.5× KV pool). `--max-model-len` defaults to 196608; raise it for longer
  context, at the cost of more KV memory.
- **Full run / batch**: `sbatch scripts/minimax_m3/paper_classification_minimax_m3.sbatch`
  serves M3 on 2 nodes and classifies the entire dataset, pushing results to a
  Hugging Face dataset.
