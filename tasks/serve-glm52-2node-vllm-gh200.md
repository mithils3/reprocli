# Serving GLM-5.2 AWQ-INT4 with vLLM on 2x GH200 NODES (DeltaAI)

`cyankiwi/GLM-5.2-AWQ-INT4` on **two ghx4 nodes = 8 GH200**.
Config: **TP=4 + PP=2, bf16 KV, no MTP, no CPU offload.**

> **STATUS: PARTIALLY VERIFIED (job 2765627, 2026-07-29).** Weights load on 8
> GPUs with no offload, both attention backends select correctly, torch.compile
> completes in 90-108 s, and the preflight passes on both nodes. The server has
> NOT yet reached `/health`. Two attempts, two fixed causes: a missing
> `--headless` on rank 1, then the FlashInfer mnnvl all-reduce fusion IMA in the
> profiling run (D4). Both are fixed in step 5. Lines marked MEASURED are from
> those runs; everything else is arithmetic.

Commands first. Everything after the `NOTES` divider is why, and none of it is
needed to run this.

---

# COMMANDS

## 1. Download (once, to shared FS — both nodes must see it)

```bash
hf download cyankiwi/GLM-5.2-AWQ-INT4 \
  --local-dir /work/nvme/bfvr/msalunkhe/models/GLM-5.2-AWQ-INT4
```

474 GB, ~3-6 min. Plain flags only — no `HF_XET_*`, no big `--max-workers` (E).

## 2. Allocate

```bash
salloc --account=betw-dtai-gh --partition=ghx4-interactive \
  --nodes=2 --ntasks-per-node=1 --gpus-per-node=4 \
  --cpus-per-task=32 --mem=440G --time=02:00:00
```

## 3. Shell prep + discover the head IP

```bash
module load python/3.11.9
source /u/msalunkhe/reprocli/.venv/bin/activate
cd /u/msalunkhe/reprocli
export PYTHONPATH=/u/msalunkhe/reprocli/src:${PYTHONPATH:-}

export VLLM_CACHE_ROOT=/work/nvme/bfvr/msalunkhe/.cache/vllm
export TORCHINDUCTOR_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/torchinductor
export TRITON_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/triton
export SAFETENSORS_FAST_GPU=1 CUDA_MODULE_LOADING=LAZY CUDA_DEVICE_ORDER=PCI_BUS_ID
export PYTHONFAULTHANDLER=1
export NCCL_CUMEM_ENABLE=0 NCCL_CUMEM_HOST_ENABLE=0
export NCCL_NET_PLUGIN="${NCCL_NET_PLUGIN_OVERRIDE:-none}"
export OMP_NUM_THREADS=1
export TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC=1800
export TORCH_NCCL_ASYNC_ERROR_HANDLING=1
ulimit -l unlimited || true; ulimit -s unlimited || true

export IFACE_NAME=hsn0
mapfile -t NODES < <(scontrol show hostnames "$SLURM_JOB_NODELIST")
HEAD_IP=$(srun --jobid="$SLURM_JOB_ID" --nodes=1 --ntasks=1 --nodelist="${NODES[0]}" \
  bash -lc "ip -o -4 addr show $IFACE_NAME | awk '{split(\$4,a,\"/\"); print a[1]; exit}'")
export HEAD_IP
echo "HEAD_IP=$HEAD_IP"    # must NOT be empty or 127.*
```

## 4. Preflight — 2 seconds, saves ~45 minutes

```bash
srun --jobid="$SLURM_JOB_ID" --nodes=2 --ntasks=2 bash -lc \
  'export LD_LIBRARY_PATH=/u/msalunkhe/reprocli/.venv/lib/python3.11/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH
   python -c "import vllm.third_party.deep_gemm; print(\"$(hostname) deep_gemm ok\")"'
```

Both nodes must print `ok`. If not, fix `LD_LIBRARY_PATH` before launching (D1).

## 5. Launch

```bash
mkdir -p logs
MODEL=/work/nvme/bfvr/msalunkhe/models/GLM-5.2-AWQ-INT4

srun --jobid="$SLURM_JOB_ID" --nodes=2 --ntasks=2 --ntasks-per-node=1 \
  --gpus-per-task=4 --cpus-per-task=32 bash -lc '
    module load python/3.11.9
    source /u/msalunkhe/reprocli/.venv/bin/activate
    export LD_LIBRARY_PATH=/u/msalunkhe/reprocli/.venv/lib/python3.11/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH
    export NCCL_SOCKET_IFNAME=hsn0,hsn1,hsn2,hsn3
    export GLOO_SOCKET_IFNAME=hsn0
    export VLLM_HOST_IP="$(ip -o -4 addr show hsn0 | awk "{split(\$4,a,\"/\"); print a[1]; exit}")"
    export VLLM_ALLREDUCE_USE_SYMM_MEM=0
    export VLLM_USE_FLASHINFER_SAMPLER=0
    HEADLESS=()
    if [[ "$SLURM_PROCID" != "0" ]]; then HEADLESS=(--headless); fi
    vllm serve '"$MODEL"' \
      --served-model-name zai-org/GLM-5.2 \
      --tensor-parallel-size 4 \
      --pipeline-parallel-size 2 \
      --nnodes 2 --node-rank "$SLURM_PROCID" --master-addr '"$HEAD_IP"' \
      --max-model-len 131072 \
      --max-num-seqs 16 \
      --gpu-memory-utilization 0.90 \
      --disable-custom-all-reduce \
      --compilation-config '\''{"pass_config":{"fuse_allreduce_rms":false}}'\'' \
      --tool-call-parser glm47 \
      --reasoning-parser glm45 \
      --enable-auto-tool-choice \
      --enable-prompt-tokens-details \
      --trust-remote-code \
      --host 0.0.0.0 --port 8000 \
      "${HEADLESS[@]}"
  ' >"logs/glm52-2node-${SLURM_JOB_ID}.log" 2>&1 &
export VLLM_SERVER_PID=$!

tail -f "logs/glm52-2node-${SLURM_JOB_ID}.log"
```

The `'\''` around the JSON is not decoration: the payload is single-quoted, so a
bare `'` would end it. `'\''` closes, emits a literal quote, reopens.

**`--headless` on every rank but 0 is mandatory.** Only rank 0 runs the API
server and the EngineCore; followers run workers only. Without it, node 1 starts
its own `APIServer` + `EngineCore`, which dies at KV-cache init with
`AssertionError: collective_rpc should not be called on follower node`
(MEASURED, job 2765627 — it gets all the way past weight loading first, so this
costs a full ~7 min to discover).

MEASURED weight load, job 2765627: **304 s** (stage 0) / **363 s** (stage 1),
`Model loading took` 323 s / 381 s. Far faster than the single-node 874 s — no
offload, and `/work/nvme`.

These log lines look like failures and are not: `shm_broadcast: No available
shared memory broadcast block found in 60 seconds` (repeats through
torch.compile), and NCCL INIT chatter.

**Do not add** `--cpu-offload-gb`, `--kv-cache-dtype fp8`, `--speculative-config`,
or `--enable-expert-parallel`. Each is wrong here for a specific reason (B, D2).

**Do not drop** `--disable-custom-all-reduce`, `fuse_allreduce_rms:false`, or
`VLLM_ALLREDUCE_USE_SYMM_MEM=0`. All three are required together (D4).

## 6. Health

```bash
curl -fsS "http://${HEAD_IP}:8000/health" && echo "  health: ok"
```

Sanity-check the load lines. MEASURED, job 2765627:

    Worker_PP0_*  Model loading took 51.29 GiB    backend DEEPSEEK_V32_INDEXER
    Worker_PP1_*  Model loading took 58.0  GiB    backend FLASH_ATTN_MLA_SPARSE

Both backends are correct — the indexer and the sparse-MLA attention are
separate specs, and neither is the FLASHMLA_SPARSE that fp8 KV would have forced
(D2). The **6.7 GiB stage asymmetry is expected but not fully explained** (A).

## 7. Benchmark

```bash
# Cold/warm prefill + decode on an ~85k agentic transcript, plus the npp/ntg
# table shaped to match serve-gguf-llamacpp-gh200.md section 8.
# Start this BEFORE the server is up: it polls /health forever and prints
# elapsed minutes, so it doubles as the startup timer.
python scripts/serve/bench_serve.py \
  --base-url "http://${HEAD_IP}:8000/v1" \
  --model zai-org/GLM-5.2 --scenario both

# Sweep-shaped traffic. THIS is the number that matters — PP=2 is bubble-bound
# at batch 1, so bench_serve.py's single-stream decode is a floor, not the
# operating point (G).
python scripts/serve/bench_agent_sim.py \
  --base-url "http://${HEAD_IP}:8000/v1" \
  --model zai-org/GLM-5.2 --agents 8 --turns 10

# Stock random-prompt throughput, for comparability outside this repo.
vllm bench serve --base-url "http://${HEAD_IP}:8000" \
  --model zai-org/GLM-5.2 --dataset-name random \
  --random-input-len 8192 --random-output-len 1024 \
  --num-prompts 64 --max-concurrency 8 --seed 42
```

### Fill this in

| | llama.cpp IQ4_XS | vLLM TP=4+PP=2 |
|---|---|---|
| decode t/s (1 stream) | **40** MEASURED | |
| decode t/s (8 agents) | — | |
| cold prefill t/s | **575** MEASURED | |
| warm prefill t/s | — | |
| cached share, 8 agents x 10 turns | — | |
| time to `/health` | ~0 | |
| KV pool actually allocated | — | |

## 8. Stop

```bash
kill "$VLLM_SERVER_PID"; wait "$VLLM_SERVER_PID" || true
exit    # also ends the allocation
```

## 9. Later: through the harness, once startup is measured

`reprocli_serve` publishes the endpoint file that `reprocli_repro` and the
auditor read. Same srun wrapper as step 5, different payload:

```bash
    python -m reprocli_serve \
      --model '"$MODEL"' --served-model-name zai-org/GLM-5.2 \
      --port 8000 --tensor-parallel-size 4 --pipeline-parallel-size 2 \
      --nnodes 2 --node-rank "$SLURM_PROCID" --master-addr '"$HEAD_IP"' \
      --advertise-ip '"$HEAD_IP"' \
      --tool-call-parser glm47 --reasoning-parser glm45 \
      --max-model-len 131072 --gpu-memory-utilization 0.90 \
      --endpoint-file '"$ENDPOINT_FILE"' \
      "${H[@]}"          # H=(--headless) on rank != 0
```

Both parser flags are mandatory, not decorative (F1). This path dies at 30
minutes (F2), which is why it comes second.

---
---

# NOTES

Nothing below is needed to run the commands above.

Companions: `serve-glm52-vllm-gh200.md` (single node, ABANDONED — its §4/§5 still
apply and are restated in D), `serve-gguf-llamacpp-gh200.md` (same model as GGUF,
MEASURED 40 t/s decode / 575 t/s prefill — the incumbent this has to beat),
`scripts/minimax_m3/minimax_m3_multinode_interactive.md` (the verified two-node
launch shape on this cluster, for a 428 GB checkpoint).

## A. The checkpoint, and the memory budget

**The repo changed on 2026-07-28.** The single-node runbook sized everything
against 440.4 GB / 410.1 GiB. From the HF API:

    83 safetensors shards   474.22 GB   =   441.65 GiB

The card breaks it out: **454.29 GB base + 19.91 GB MTP layer**, and
`config.json` now carries `num_nextn_predict_layers: 1`. Re-check before
trusting any table here:

```bash
curl -s "https://huggingface.co/api/models/cyankiwi/GLM-5.2-AWQ-INT4/tree/main?recursive=1" \
  | python3 -c "import json,sys; f=json.load(sys.stdin); \
    print(sum(x['size'] for x in f if x['path'].endswith('.safetensors'))/2**30, 'GiB')"
```

**Download size is not resident size.** The MTP module is `model.layers.78`
(78 layers means indices 0-77, so 78 is the extra one):

    downloaded   474.22 GB  =  441.65 GiB     (all 83 shards)
    weights excl. MTP       =  423.09 GiB     = 52.89 GiB/GPU at 8-way

You download all 83 shards regardless: layer 78 lives entirely in
`model-00083-of-00083.safetensors`, but that shard also holds part of layer 77,
so there is nothing to exclude.

### MEASURED (job 2765627), and the part that does not add up

    Worker_PP0_*  Model loading took 51.29 GiB    (39 layers + embed_tokens)
    Worker_PP1_*  Model loading took 58.0  GiB    (39 layers + norm + lm_head)

Stage 0 lands near the 52.89 GiB arithmetic. **Stage 1 is 6.7 GiB heavier, and
that is not explained by `lm_head`** — embed_tokens and lm_head are the same
shape (154880 x 6144 bf16 = 1.77 GiB, TP-sharded to 0.44 GiB), so they cancel.

The likely cause: **layer 78 is being loaded after all.** Stage 1 logs an extra
MoE init line that stage 0 does not —

    Worker_PP1_TP0  int_wna16.py:295    Using MoEPrepareAndFinalizeNoDPEPModular
    Worker_PP1_TP0  unquantized.py:334  Using MoEPrepareAndFinalizeNoDPEPModular

an *unquantized* MoE alongside the INT4 one, on the last PP stage only, which is
where an MTP module would land. 18.54 GiB / 4 TP ranks = 4.6 GiB, in the right
neighbourhood for a 6.7 GiB delta. So plan against **58.0 GiB**, not 52.89, and
treat "vLLM skips the MTP layer without `--speculative-config`" as unconfirmed —
the evidence here points the other way.

Consequence for the KV budget: the tightest GPU sets the pool.

    usable / GPU at 0.90    86.0 GiB
    resident (stage 1)     -58.0 GiB
                           ---------
    free for KV             28.0 GiB   ->  ~670k tokens at TP=4/PP=2

Still ~5 concurrent full 131k transcripts, so nothing here is binding. If you
want the 6.7 GiB back, rebalance the split — each layer is ~1.35 GiB/GPU, so
`VLLM_PP_LAYER_PARTITION=41,37` roughly evens the two stages at ~55 GiB. Worth
~64k tokens of extra pool; do it only if the pool turns out to matter.

### Why 2 nodes changes the outcome

    2 nodes x 4 GH200 x 95.58 GiB  =  764.6 GiB HBM
    resident weights (excl. MTP)   =  423.1 GiB
                                      ----------
                                      341.5 GiB spare, before KV

| | 1 node (4 GPU) | 2 nodes (8 GPU) |
|---|---|---|
| HBM | 382.3 GiB | 764.6 GiB |
| weights / GPU | 105.8 GiB | **52.9 GiB** |
| free at util 0.90 | **-19.8 GiB** | **+28.0 GiB** MEASURED |
| `--cpu-offload-gb` | forced | **0** |
| pinned host memory | 113-145 GiB | 0 |

Dropping offload to zero deletes, by construction, both walls that ended the
single-node attempt: its §1 forced offload and its §7 unresolved rank-0
pinned-alloc stall (with the unfalsified NUMA hypothesis). It also removes the
UVA offloader from the read path entirely.

### KV pool, bf16 (arithmetic)

MLA latent is 576 (512 `kv_lora` + 64 `qk_rope`), so bf16 costs **1152
B/token/layer**. Under TP the MLA latent is *replicated* across ranks rather
than sharded, so per-GPU cost tracks layers-per-GPU:

| layout | layers / GPU | B/token/GPU | KV pool at 28.0 GiB MEASURED |
|---|---|---|---|
| TP=8, PP=1 | 78 | 89,856 (87.8 KiB) | ~335k tokens |
| **TP=4, PP=2** | 39 | 44,928 (43.9 KiB) | **~670k tokens** |

Plus the DSA indexer cache: 21 `full` indexers x `index_head_dim` 128 =
~2.6 KiB/token model-wide if the index keys are fp8, double if bf16. At 131k
that is 0.3-0.7 GiB. Real, not decisive.

One full 131,072-token sequence costs 5.5 GiB/GPU at TP=4/PP=2, so the pool
holds ~5 concurrent max-length transcripts, or far more real ones.

### Architecture, from `config.json` (confirmed 2026-07-29)

78 layers, hidden 6144, 64 attention heads, 256 routed experts + 1 shared, 8
active. MLA with `kv_lora_rank=512` + `qk_rope_head_dim=64`. DSA sparse
attention (`glm_moe_dsa`, `index_topk=2048`) with **IndexShare**: `indexer_types`
is 21 `full` and 57 `shared`, one real indexer per four layers. 3 dense MLPs then
75 MoE. `max_position_embeddings` = 1,048,576.

Quantization is **compressed-tensors `pack-quantized`**, not classic AWQ despite
the repo name: INT4, `group_size 32`, asymmetric (`symmetric: false`), MSE
observer. The `ignore` list is 2092 modules and covers every attention projection
(`q_a_proj`, `q_b_proj`, `kv_a_proj_with_mqa`, `kv_b_proj`, `o_proj`,
`indexer.wq_b`), so only the MoE expert linears are INT4. That is why 4-bit still
weighs 423 GiB.

## B. Why TP=4 + PP=2, and why MTP is off

The deciding fact is a vLLM limitation, not the hardware: **speculative decoding
is incompatible with pipeline parallelism.** MTP under PP>1 either crashes or
silently diverges from the greedy baseline; the token accounting lives on the
last PP rank only and never reaches the others. Open RFC (vllm#44697), not a
fixed bug, and independently hit in the wild (`bird/GLM-spark`, GLM-5.2 across
3 nodes: *"does not work with PP=3 in this vLLM version due to multiple code
bugs"*).

| layout | fits | MTP | KV / GPU | fabric cost per token | precedent on this cluster |
|---|---|---|---|---|---|
| **TP=4 + PP=2** | yes | no | **670k tok** | 1 hidden state (12 KB) per stage boundary | `scripts/serve/serve_multinode.sbatch` (Kimi-K2.6) |
| TP=8 across nodes | yes | yes | 396k tok | 78 layers x all-reduce over Slingshot | MiniMax-M3 MXFP8, 428 GB, VERIFIED |
| TP=4 + DP=2 + EP | yes | yes | 396k tok | + MoE all-to-all | none |

PP=2 wins on everything except MTP: double the KV pool, and the fabric carries
one 12 KB hidden state per microbatch boundary instead of two all-reduces per
layer for all 78 layers. It is also the layout `serve_multinode.sbatch` already
implements, so there is no new launch machinery to get wrong.

**What giving up MTP costs.** The official recipe runs
`--speculative-config.method mtp --speculative-config.num_speculative_tokens 5`,
GLM-5.2's headline architecture claim is ~20% better MTP acceptance length than
5.1, and the one published GH200 data point is a 43 -> 55 t/s decode gain from an
FP8 MTP-3 graft (dnhkng). A real decode number, deliberately left on the table.
The 19.91 GB module is still downloaded, just never loaded (A). If vllm#44697
lands, revisit — MTP under PP=2 would collapse this table to one row.

78 layers split 39/39 across the two stages. For an uneven split, vLLM takes
`VLLM_PP_LAYER_PARTITION=39,39` as a comma list summing to 78.

Other flag choices in step 5:

- `--gpu-memory-utilization 0.90`, not 0.93: with 28.0 GiB free there is no
  reason to run tight, and profiling headroom is what the single-node attempt
  kept losing.
- `--max-model-len 131072`, not the model's 1M. Raise after the benchmark sizes
  the pool. The repo-wide default is 196608 (`reprocli_serve/config.py`), which
  also fits.
- No `--enable-expert-parallel`: it reshuffles which params live where and adds
  a MoE all-to-all on the fabric. Not a variable you want live during bring-up.

## C. Other GPU counts: 6 fits, 4 does not, 2 is a research project

### 6 GPUs — TP must divide 64, so TP=6 and TP=3 do not exist

vLLM shards attention heads across TP ranks and requires an even split.
GLM-5.2 has `num_attention_heads: 64`, and 64 % 6 = 4, 64 % 3 = 1:

    valid TP:    1, 2, 4, 8
    invalid TP:  3, 6

With 78 layers (78/3 = 26, 78/6 = 13, both even) the surviving 6-GPU layouts:

| layout | weights / GPU | free at 0.90 | layers / GPU | KV pool | 131k seq |
|---|---|---|---|---|---|
| **8 GPU, TP=4 + PP=2** | 58.0 GiB MEASURED | 28.0 GiB | 39 | 670k tok | 5.5 GiB |
| 6 GPU, TP=2 + PP=3 | 70.5 GiB | 15.5 GiB | 26 | 556k tok | 3.7 GiB |
| 6 GPU, TP=1 + PP=6 | 70.5 GiB | 15.5 GiB | 13 | 1112k tok | 1.8 GiB |

Memory is not the problem. The blockers are allocation shape and compute width:

- **No ghx4 node has 6 GPUs**, so you hold two nodes either way. The saving is
  billing (~25% of GPU-hours), not a smaller footprint or a shorter queue.
  Partial-node requests are allowed (`serve_gh200.sbatch` asks for
  `--gpus-per-node=2`), so both 4+2 and 3+3 are allocatable. Neither is good.
- **3+3** is uniform, which is what the native `--nnodes`/`--node-rank`
  rendezvous assumes. But with TP=2 the groups are ranks (0,1), (2,3), (4,5),
  and (2,3) straddles the node boundary — a third of the layers then pay an
  inter-node all-reduce *per layer*, exactly what PP was chosen to avoid.
- **4+2** keeps all TP groups inside a node, which is what you want, but it is
  non-uniform and vLLM's rank-to-GPU assignment is engine-managed rather than
  configurable. Placing it means the Ray backend
  (`--distributed-executor-backend ray`), unverified here.
- **TP=2 halves the per-stage compute width.** Prefill is the entire case for
  the vLLM path over llama.cpp (G), and the incumbent's weakness is precisely
  that it computes on one GPU at a time. TP=4 -> TP=2 attacks the metric this
  exercise exists to measure. A 3-deep pipeline also needs more concurrency
  than a 2-deep one before the bubble amortizes.

Revisit only if the benchmark shows the GPUs compute-underutilized.

### 4 GPUs — closer than the old runbook thought, still short

With the MTP layer non-resident (A), one node needs 105.8 GiB/GPU against 86.0
usable: a **19.8 GiB/GPU** deficit, not the 28-36 the single-node runbook
budgeted. That is below the `--cpu-offload-gb 28` it MEASURED as "tolerable"
(2m31s rank-0 gap) and well below the 36 that stalled. So a single-node retry is
less hopeless than it reads — but it walks straight back into the pinned-alloc
and NUMA regime this runbook exists to escape.

### 2 GPUs — don't

This runbook reads "2xGH200 nodes" as two ghx4 nodes = 8 GPUs. Note that
`serve-laguna-s21-vllm-gh200.md` uses "2xGH200" for two GPUs on one node, so the
vocabulary is overloaded.

On 2 GPUs: 191.2 GiB HBM against 423.1 GiB resident means ~125 GiB of pinned
host memory *per GPU*, deeper into the regime where the single-node attempt
stalled (TP0 stuck in `_maybe_offload_to_cpu` for 15+ min at 36 GiB/GPU). The one
published data point is dnhkng on 2xGH200 + `--cpu-offload-gb 170`: **2.39 t/s**,
rising to 20.31 t/s only after strict local NUMA placement — 8.5x from binding
alone, no binding recipe published, and vLLM has no per-worker NUMA binding (its
TP workers are children of one process, so `srun --cpu-bind` pins them all to the
same node). If 2 GPUs is the real constraint, serve the GGUF through llama.cpp.

## D. Walls carried over from the single-node runbook

Properties of the model and the venv, not of node count. Read that runbook's §4
and §5 in full.

### D1. DeepGEMM / `libnvrtc.so.13` — REQUIRED

GLM-5.2 is `glm_moe_dsa`, every decoder layer builds a DSA `Indexer`, and vLLM
hard-requires DeepGEMM for it with no fallback on Hopper. A missing `.so`
surfaces as a *capability* error, which reads like something is unsupported:

    RuntimeError: Sparse Attention Indexer CUDA op requires DeepGEMM support

It is `nvidia/cu13/lib`. `nvidia/cuda_nvrtc/lib` holds `libnvrtc.so.12`, the
wrong one. Same export as `serve-dsv4flash-vllm-gh200.md`, same reason. Step 4
checks it on both nodes.

### D2. Do NOT pass `--kv-cache-dtype fp8` — two independent reasons

1. It selects the FLASHMLA_SPARSE backend, whose `fp8_ds_mla` layout is 656
   B/token/layer while vLLM's profiling reshape assumes the 576-element latent.
   Startup dies at KV init ~45 min in with `shape '[16, 64, 576]' is invalid for
   input of size 671744` (671744 / (16*64) = 656). Upstream, unfixed:
   vllm-project/recipes#565. MEASURED in the single-node runbook §5: dropping the
   flag moves backend selection to `FLASH_ATTN_MLA_SPARSE` and init proceeds.
   With fp8 KV the candidate list collapses to FLASHMLA_SPARSE alone, so the flag
   removes its own escape route.
2. Past that, vllm#46074: the DSA sparse indexer has an off-by-one in decode
   tensor prep that crashes *concurrent decode* above ~325K `max_model_len`
   (stable at 300K, crashes at 325K/350K). bf16 KV was stable at every tested
   size. Open as of vLLM main, June 2026.

The official recipe *does* use `--kv-cache-dtype fp8`. It targets 8xH200 with a
different backend selection and is wrong for GH200. On 2 nodes there is 341 GiB
spare anyway (A) — nothing to buy.

### D4. FlashInfer mnnvl all-reduce — REQUIRED, and it kills the profiling run

MEASURED, job 2765627: the server got past weight load, past torch.compile
(90-108 s), then died in `profile_cudagraph_memory` with a wall of
`CUBLAS_STATUS_EXECUTION_FAILED` / `CUBLAS_STATUS_INTERNAL_ERROR` /
`illegal memory access` across all 8 workers. **Those are async fallout, not the
cause.** The cause is one line on `Worker_PP0_TP0`:

    RuntimeError: Check failed: (status == cudaSuccess) is false:
      trtllm_mnnvl_allreduce_fusion failed with error code
      an illegal memory access was encountered

with the setup visible earlier in the log:

    compilation.py:312        Enabled custom fusions: allreduce_rms
    symm_mem.py:106  WARNING  SymmMemCommunicator: symmetric memory multicast
                              operations are not supported.
    flashinfer_all_reduce.py  Auto-selected flashinfer allreduce backend: mnnvl
    allreduce_rms_fusion.py   Failed to initialize Flashinfer allreduce workspace.

vLLM fused RMSNorm + all-reduce, FlashInfer picked the `mnnvl` symmetric-memory
all-reduce, this GH200 topology cannot do symmetric-memory multicast, the
workspace init failed — and the *already-compiled* graph called the fused kernel
anyway. Three flags force plain NCCL and remove the fused path:

```bash
export VLLM_ALLREDUCE_USE_SYMM_MEM=0
      --disable-custom-all-reduce
      --compilation-config '{"pass_config":{"fuse_allreduce_rms":false}}'
```

Note `disable_custom_all_reduce=True` was **already** set in the failing run
(vLLM defaults it on for multi-node). It is not sufficient alone —
`fuse_allreduce_rms` is the one that matters.

This is the same wall as `serve-laguna-s21-vllm-gh200.md`, which documents it on
2 GPUs and one node. It is a property of GH200 + FlashInfer, not of this model or
the node count. The repo already knows: `src/reprocli_serve/launch.py:119` force-
disables `fuse_allreduce_rms` for exactly this reason — but only when a
`--compilation-config` is passed through `reprocli_serve`, so raw `vllm serve`
gets no protection. Hence F4.

`VLLM_USE_FLASHINFER_SAMPLER=0` is set alongside preemptively: the log shows
`Using FlashInfer for top-p & top-k sampling`, and both the Laguna and
DeepSeek-V4-Flash runbooks list the FlashInfer sampler as a crash on this
platform (`TopKMaskLogits: invalid resource handle`). It costs nothing at these
batch sizes.

Changing `--compilation-config` changes the config hash, so the poisoned AOT
graph is not reused — no cache clearing needed, but you do pay a fresh compile.

### D3. `CXXABI_1.3.15` — optional

Only silences warning spam from the *standalone* `deep_gemm` wheel; vLLM's
vendored copy is what gates the indexer. If you want it clean:
`module load gcc/14.2.0`, then prepend its libstdc++ dir to `LD_LIBRARY_PATH`.

## E. Storage: `/tmp` is now WRONG

The single-node runbook argued for node-local `/tmp`, correctly, for
**single-node** serving. Two nodes breaks the argument: each node's ranks load
from the path you pass, so `/tmp/GLM-5-2` on node A is invisible to node B.

Use `/work/nvme`, not `/work/hdd` — 474 GB read by 8 ranks is the one workload
where the flash tier earns its keep, and `/work/nvme/bfvr/msalunkhe/models` is
already where most checkpoints here live.

No speed is lost against `/tmp`. vLLM's auto-prefetch stays off either way — the
log says why:
*"Auto-prefetch is disabled because the filesystem (XFS) is not a recognized
network FS (NFS/Lustre) and the checkpoint size exceeds 90% of available RAM
(271.62 GiB)"*. **Both** clauses must pass, and 441.7 > 244.5 fails the RAM
clause on Lustre too.

Do not add `HF_XET_HIGH_PERFORMANCE`, `XET_NUM_CONCURRENT_RANGE_GETS`, or a large
`--max-workers`: `serve-gguf-llamacpp-gh200.md` §4 MEASURED that combination
self-congesting to 5.6 MB/s. At plain defaults (1.33-2.7 GB/s there), 474 GB is
~3-6 minutes.

## F. Landmines in this repo's harness

### F1. `resolve_profile()` silently serves GLM with MiniMax parsers

`src/reprocli_serve/profiles.py` has no GLM entry. `resolve_profile()` falls
through every `is_*` check to `minimax_profile()`, which sets
`tool_call_parser="minimax_m2"` and `reasoning_parser="minimax_m2"`. Nothing
errors. Tool calls just come back wrong. Always pass `--tool-call-parser glm47
--reasoning-parser glm45` explicitly until a `glm52_profile()` exists.

Those names do not match the model version. That is correct, not a typo — they
come from the vLLM GLM-5.2 recipe and are confirmed by the independent
`renning22/glm-5.2-4090` port.

### F2. The head rank times out at 30 minutes

`SERVER_STARTUP_TIMEOUT = 1800` in `src/reprocli_serve/config.py`, hardcoded, no
env override. `wait_until_ready()` raises `TimeoutError` past it. The single-node
bring-up MEASURED **~45 min** to KV cache init (874 s weight load + 1024 s
torch.compile + 170 s warmup). Two nodes with no offload should be faster, but
not obviously under 30 minutes on a cold Inductor cache. Hence raw `vllm serve`
for bring-up (step 5) and the harness only afterwards (step 9).

### F4. `launch.py`'s all-reduce guard only fires when a compilation-config is passed

`_supported_compilation_config()` force-disables `fuse_allreduce_rms` (D4), but
`build_serve_command` only calls it inside `if compilation:` — so a model whose
profile sets no `compilation_config`, launched with no `--compilation-config`,
gets no guard and hits the mnnvl IMA. Every profile except `minimax_m2` is in
that state. Worth making the guard unconditional on GH200.

### F3. `NCCL_SOCKET_IFNAME=hsn` is a bare prefix and it hangs

`scripts/serve/serve_multinode.sbatch` exports the bare prefix `hsn`. The
MiniMax-M3 runbook documents this as a hang: bare `hsn` also matches the
`hsn0.561..` VLAN aliases (public 141.142.x), and mixing those with the private
172.28.x fabric stalls the cross-node socket connect right after `vLLM is using
nccl==...`, with no progress past it. Step 5 pins the four NICs by exact name,
inside the srun payload, so nothing from `~/.bashrc` can leak in.

An empty `IFACE_NAME` in step 3 makes `ip addr show` grab loopback, `HEAD_IP`
silently becomes `127.0.0.1`, the worker never joins, and the launch hangs ~10
min then dies with `4/8 clients joined`. Check the echo.

`TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC=1800` is raised from the usual 1200: the
`shm_broadcast` spam during the ~17 min torch.compile is normal, but a 20-minute
heartbeat sits uncomfortably close to it.

## G. Reading the benchmark

Weight the 8-agent number, not the single-stream one. **PP=2 half-idles the
pipeline at low concurrency** — stage 0 waits while stage 1 works. A single
interactive stream will look bad and is not representative; the sweep's 6-8
concurrent agents are what keep both stages fed. Reject this layout on the
8-agent number or not at all.

**Decode is probably a wash, and MTP is off the table.** llama.cpp MEASURED
40 t/s; dnhkng got 43 t/s on vLLM after NUMA work. The one mechanism that could
have made vLLM decisively win decode was MTP, and PP=2 forecloses it (B). Do not
expect a decode win. If one appears, that is a surprise worth chasing.

**Prefill is the structural case.** llama.cpp gets ~575 t/s because
`--split-mode layer` is pipeline parallelism with one GPU computing at a time
(~48% util). vLLM does real TP, Marlin INT4 kernels, and chunked prefill. Nobody
has published a GLM-5.2 prefill number on 8xGH200. 85k at 575 t/s is ~148 s; at
3x that it is ~50 s.

The counterweight: cold prefill amortizes. An agent pays it once, and turn 2+
hits the prefix cache — *except* that compaction rewrites the transcript (eliding
tool stdouts to placeholders), which diverges the prefix and forces a re-prefill.
How much prefill actually costs therefore depends on the compaction rate, which
is measurable from `repro_events`. Get that number before weighting prefill
heavily.

**So the whole case rests on warm prefill and on concurrency.** With MTP gone, if
the 8-agent throughput and the warm-prefill multiple are not clearly better than
llama.cpp, this path does not pay for itself — it costs two nodes instead of one,
a long startup, three upstream bugs, and a quant whose quality edge over UD-IQ4_XS
is unquantified on both sides.

Watch `cached%` on the agent sim. It should climb toward the 80-95% real sweeps
show; a sag as transcripts grow means the KV pool is evicting, which at 670k
tokens would be surprising and worth chasing.

## H. Open items

- The step-7 table is empty. That is the deliverable, and nothing has reached
  `/health` yet.
- **Is layer 78 (MTP) actually being loaded?** Stage 1 is 6.7 GiB heavier than
  stage 0 and logs an extra *unquantized* MoE init (A). If it is resident, ~4.6
  GiB/GPU is being spent on a module PP=2 can never use, and finding the switch
  to skip it is worth 4.6 GiB of KV pool. Confirm by diffing the loaded weight
  names, not by inference from the memory delta.
- PP stages are imbalanced 51.29 / 58.0 GiB. `VLLM_PP_LAYER_PARTITION=41,37`
  should even them; untested, and worth only ~64k tokens of pool.
- **No `glm52_profile()`** (F1). Until it exists, every harness launch must pass
  `glm47`/`glm45` by hand and a typo serves MiniMax parsers silently.
- **`SERVER_STARTUP_TIMEOUT` is not overridable** (F2). A one-line env read in
  `config.py` would let the harness path work for slow-starting models.
- **`serve_multinode.sbatch` exports the bare `NCCL_SOCKET_IFNAME=hsn`** (F3).
  Worth fixing there, not just working around here.
- **`launch.py`'s `fuse_allreduce_rms` guard is conditional** (F4). It only runs
  when a compilation-config is passed, so most profiles are unprotected against
  the mnnvl IMA that killed job 2765627. Making it unconditional on GH200 is a
  small change that would have saved ~12 minutes here.
- MTP under PP is an open upstream RFC (vllm#44697). If it lands, TP=4+PP=2 wins
  outright and the 19.91 GB module stops being dead weight. Re-check before any
  sweep commits to this brain.
- 6 GPUs (TP=2+PP=3) is memory-viable but needs the Ray backend for a sane 4+2
  placement, unverified here (C).
- `save_sharded_state` to kill the TP read amplification on load
  (`serve-glm52-vllm-gh200.md` §3). Needs one successful load first.
- AWQ-INT4 vs UD-IQ4_XS quality delta is unquantified on both sides.
- The compressed-tensors kernel path (INT4, group 32, asymmetric) on sm90 is
  untested here. If Marlin rejects the asymmetric zero points this fails at load
  with a quant-config error, not at KV init — a fast failure, at least.

## Sources

- [cyankiwi/GLM-5.2-AWQ-INT4](https://huggingface.co/cyankiwi/GLM-5.2-AWQ-INT4) — size, MTP layer, `config.json`
- [vLLM Recipes: zai-org/GLM-5.2](https://recipes.vllm.ai/zai-org/GLM-5.2) — official flags, MTP=5, parsers
- [vllm#46074](https://github.com/vllm-project/vllm/issues/46074) — DSA indexer off-by-one, fp8 KV, ~325K
- [vllm#44697](https://github.com/vllm-project/vllm/issues/44697) — RFC: MTP speculative decoding under PP>1
- [vllm-project/recipes#565](https://github.com/vllm-project/recipes/issues/565) — FLASHMLA_SPARSE + FP8 KV break
- [bird/GLM-spark](https://github.com/bird/GLM-spark) — GLM-5.2 under vLLM PP across nodes; MTP+PP broken
- [renning22/glm-5.2-4090](https://github.com/renning22/glm-5.2-4090) — independent confirmation of `glm47`/`glm45`, 78-layer PP partition
- [vLLM parallelism docs](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/) — TP=GPUs-per-node, PP=nodes; rank placement is engine-managed
- [dnhkng: GH200 benchmarking, GLM-5.2](https://dnhkng.github.io/posts/gh200-benchmarking-part-3-glm52/) — 2xGH200 offload numbers, NUMA 8.5x
