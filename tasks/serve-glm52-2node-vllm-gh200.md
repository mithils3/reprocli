# Serving GLM-5.2 AWQ-INT4 with vLLM on 2x GH200 NODES (DeltaAI)

Runbook for `cyankiwi/GLM-5.2-AWQ-INT4` on **two ghx4 nodes = 8 GH200**, and the
retry that `tasks/serve-glm52-vllm-gh200.md` §9 asked for. That runbook is
ABANDONED; this one exists because the variable that killed it was GPU count,
not tuning.

> **STATUS: UNVERIFIED — nothing here has been run.** Every number below is
> either arithmetic from `config.json` + the HF API, or carried over MEASURED
> from a sibling runbook (cited at the point of use). No GLM-5.2 vLLM server has
> ever reached `/health` on this cluster. Treat §7 as the point of the exercise,
> not a formality.

Companions: `serve-glm52-vllm-gh200.md` (single node, abandoned — read its §4/§5,
they still apply), `serve-gguf-llamacpp-gh200.md` (same model as GGUF, MEASURED
40 t/s decode / 575 t/s prefill — the number this path has to beat), and
`scripts/minimax_m3/minimax_m3_multinode_interactive.md` (the verified two-node
launch shape on this cluster, for a 428 GB checkpoint).

---

## 0. The checkpoint changed. Re-measure before sizing anything

The single-node runbook sized everything against **440.4 GB / 410.1 GiB**. That
is stale. From the HF API on 2026-07-29 (`lastModified: 2026-07-28`):

    83 safetensors shards   474.22 GB   =   441.65 GiB

The model card breaks it out: **454.29 GB base + 19.91 GB MTP layer**, and
`config.json` now carries `num_nextn_predict_layers: 1`. The MTP module used to
be absent; it ships in-repo now, which makes §2's layout choice a real fork
rather than a footnote.

Always re-run this before trusting any memory table in this file:

```bash
curl -s "https://huggingface.co/api/models/cyankiwi/GLM-5.2-AWQ-INT4/tree/main?recursive=1" \
  | python3 -c "import json,sys; f=json.load(sys.stdin); \
    print(sum(x['size'] for x in f if x['path'].endswith('.safetensors'))/2**30, 'GiB')"
```

Arch, from `config.json` (all confirmed 2026-07-29): 78 layers, hidden 6144,
64 attention heads, 256 routed experts + 1 shared, 8 active. MLA with
`kv_lora_rank=512` + `qk_rope_head_dim=64`. DSA sparse attention
(`glm_moe_dsa`, `index_topk=2048`) with **IndexShare**: `indexer_types` is 21
`full` and 57 `shared`, i.e. one real indexer per four layers. 3 dense MLPs then
75 MoE. `max_position_embeddings` = 1,048,576.

Quantization is **compressed-tensors `pack-quantized`**, not classic AWQ despite
the repo name: INT4, `group_size 32`, asymmetric (`symmetric: false`), MSE
observer. The `ignore` list is 2092 modules long and covers every attention
projection (`q_a_proj`, `q_b_proj`, `kv_a_proj_with_mqa`, `kv_b_proj`, `o_proj`,
`indexer.wq_b`), so only the MoE expert linears are INT4. That is why 4-bit
still weighs 441 GiB.

---

## 1. The memory budget — `--cpu-offload-gb` goes to ZERO

This is the whole reason to retry.

    2 nodes x 4 GH200 x 95.58 GiB  =  764.6 GiB HBM
    weights, 83 shards             =  441.7 GiB
                                      ----------
                                      323.0 GiB spare, before KV

Against the single-node case, which was 28 GiB short *before* KV cache and so
forced offload:

| | 1 node (4 GPU) | 2 nodes (8 GPU) |
|---|---|---|
| HBM | 382.3 GiB | 764.6 GiB |
| weights / GPU | 110.4 GiB | **55.2 GiB** |
| `--cpu-offload-gb` | 28-36, forced | **0** |
| pinned host memory | 113-145 GiB | 0 |

Dropping offload to zero deletes, by construction, the two walls that ended the
single-node attempt: §1's forced offload and §7's unresolved rank-0 pinned-alloc
stall (with its unfalsified NUMA hypothesis). It also deletes the UVA offloader
from the read path entirely, so §3's `Loading weights took 874.06 s` should
improve for reasons other than sharding.

At `--gpu-memory-utilization 0.90`:

    usable / GPU        86.0 GiB
    resident weights   -55.2 GiB
                       ---------
    free for KV        30.8 GiB

### KV pool, bf16 (arithmetic)

MLA latent is 576 (512 `kv_lora` + 64 `qk_rope`), so bf16 costs **1152
B/token/layer**. Per-GPU cost depends on how many layers land on that GPU, and
under TP the MLA latent is *replicated* across ranks rather than sharded:

| layout | layers / GPU | B/token/GPU | KV pool at 30.8 GiB |
|---|---|---|---|
| TP=8, PP=1 | 78 | 89,856 (87.8 KiB) | **~368k tokens** |
| TP=4, PP=2 | 39 | 44,928 (43.9 KiB) | **~736k tokens** |

Add the DSA indexer cache: 21 `full` indexers x `index_head_dim` 128 =
~2.6 KiB/token model-wide if the index keys are fp8, double that if bf16. At
131k context that is 0.3-0.7 GiB. Real, not decisive.

For scale: one full 131,072-token sequence costs 5.5 GiB/GPU at TP=4/PP=2, so
the pool holds ~5 concurrent max-length transcripts, or far more real ones.

---

## 2. Layout: the choice is MTP vs. KV pool, and only measurement settles it

Three layouts fit. They are not equivalent, and the deciding factor is a vLLM
limitation, not the hardware.

**Speculative decoding is incompatible with pipeline parallelism in vLLM.** MTP
under PP>1 either crashes or silently diverges from the greedy baseline; the
token accounting lives on the last PP rank only and never reaches the others.
This is tracked as an open RFC (vllm#44697), not a fixed bug, and it was
independently hit in the wild (`bird/GLM-spark`, GLM-5.2 across 3 nodes: *"does
not work with PP=3 in this vLLM version due to multiple code bugs"*).

So:

| layout | fits | MTP | KV / GPU | fabric cost per token | precedent on this cluster |
|---|---|---|---|---|---|
| **TP=4 + PP=2** | yes | **no** | 736k tok | 1 hidden state (12 KB) at the stage boundary | `scripts/serve/serve_multinode.sbatch` (Kimi-K2.6) |
| **TP=8 across nodes** | yes | **yes** | 368k tok | 78 layers x all-reduce over Slingshot | MiniMax-M3 MXFP8, 428 GB, VERIFIED |
| TP=4 + DP=2 + EP | yes | yes | 368k tok | + MoE all-to-all | none; skip for bring-up |

MTP is not a rounding error here. The official vLLM recipe runs
`--speculative-config.method mtp --speculative-config.num_speculative_tokens 5`,
GLM-5.2's headline architecture claim is a ~20% improvement in MTP acceptance
length over 5.1, and this repo ships the 19.91 GB MTP module. Under PP=2 that
module is dead weight on disk.

Against that, TP=8 puts 78 layers' worth of all-reduce on the Slingshot fabric
instead of NVLink. DeltaAI has 4x 200GbE per node; the MiniMax-M3 runbook shows
this works for a similar-size MoE, but "works" is not "is free".

**Bring up TP=4 + PP=2 first** (§6). It is the layout the existing multi-node
sbatch already implements, it has the largest KV pool, and it puts almost
nothing on the fabric — the fewest ways to fail while you are still finding out
whether the model serves at all. Then run §7's A/B against TP=8 + MTP=5. The
answer is a measurement, and nobody has published it.

One caveat to carry into the A/B: PP=2 half-idles the pipeline at low
concurrency. A single interactive stream will look bad; the sweep's 6-8
concurrent agents are what keep both stages fed. Benchmark at sweep concurrency,
not at batch 1, or you will reject PP for the wrong reason.

---

## 3. What carries over unchanged from the single-node runbook

Read `serve-glm52-vllm-gh200.md` §4 and §5 in full. Both walls are properties of
the model and the venv, not of the node count.

### 3a. DeepGEMM / `libnvrtc.so.13` — REQUIRED (that runbook's §4a)

GLM-5.2 is `glm_moe_dsa`, every decoder layer builds a DSA `Indexer`, and vLLM
hard-requires DeepGEMM for it with no fallback on Hopper. Missing `.so` surfaces
as a *capability* error, which reads like something is unsupported:

    RuntimeError: Sparse Attention Indexer CUDA op requires DeepGEMM support

```bash
export LD_LIBRARY_PATH=/u/msalunkhe/reprocli/.venv/lib/python3.11/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH
```

It is `nvidia/cu13/lib`. `nvidia/cuda_nvrtc/lib` holds `libnvrtc.so.12`, the
wrong one. Same export as `serve-dsv4flash-vllm-gh200.md`, same reason.

**Verify on both nodes before burning a launch** — two seconds against ~45
minutes:

```bash
srun --jobid="$SLURM_JOB_ID" --nodes=2 --ntasks=2 bash -lc \
  'python -c "import vllm.third_party.deep_gemm; print(\"$(hostname) bundled ok\")"'
```

### 3b. Do NOT pass `--kv-cache-dtype fp8` — now two independent reasons

1. It selects the FLASHMLA_SPARSE backend, whose `fp8_ds_mla` layout is 656
   B/token/layer while vLLM's profiling reshape assumes the 576-element latent.
   Startup dies at KV init ~45 min in with `shape '[16, 64, 576]' is invalid for
   input of size 671744` (671744 / (16*64) = 656). Upstream, unfixed:
   vllm-project/recipes#565. MEASURED in the single-node runbook §5: dropping the
   flag moves backend selection to `FLASH_ATTN_MLA_SPARSE` and init proceeds.
   With fp8 KV the candidate list collapses to FLASHMLA_SPARSE alone, so the flag
   removes its own escape route.
2. Even past that, vllm#46074: the DSA sparse indexer has an off-by-one in decode
   tensor prep that crashes *concurrent decode* above ~325K `max_model_len`
   (stable at 300K, crashes at 325K/350K). bf16 KV was stable at every tested
   size. Open as of vLLM main, June 2026.

The official recipe *does* use `--kv-cache-dtype fp8`. It targets 8xH200 with a
different backend selection, and it is wrong for GH200. On 2 nodes you have
322 GiB spare anyway (§1) — there is nothing to buy.

### 3c. `CXXABI_1.3.15` — optional (that runbook's §4b)

Only silences warning spam from the *standalone* `deep_gemm` wheel; vLLM's
vendored copy is what gates the indexer. If you want it clean:
`module load gcc/14.2.0` then prepend its libstdc++ dir to `LD_LIBRARY_PATH`.

---

## 4. Storage: `/tmp` is now WRONG (this inverts §3 of the single-node runbook)

That runbook argued for node-local `/tmp`, correctly, for **single-node**
serving. Two nodes breaks the argument: each node's ranks load weights from the
path you pass, so `/tmp/GLM-5-2` on node A is invisible to node B, and you would
be paying the download twice and racing two allocations.

Use the shared filesystem, same place the other large checkpoints live:

```bash
hf download cyankiwi/GLM-5.2-AWQ-INT4 \
  --local-dir /work/hdd/bfvr/msalunkhe/models/GLM-5.2-AWQ-INT4
```

Plain flags only. Do NOT add `HF_XET_HIGH_PERFORMANCE`,
`XET_NUM_CONCURRENT_RANGE_GETS`, or a large `--max-workers` —
`serve-gguf-llamacpp-gh200.md` §4 MEASURED that combination self-congesting to
5.6 MB/s. At the plain defaults (1.33-2.7 GB/s there), 474 GB is ~3-6 minutes.

You lose nothing by not using `/tmp`: vLLM's auto-prefetch stays off either way.
The log says why — *"Auto-prefetch is disabled because the filesystem (XFS) is
not a recognized network FS (NFS/Lustre) and the checkpoint size exceeds 90% of
available RAM (271.62 GiB)"*. **Both** clauses must pass, and 441.7 > 244.5
fails the RAM clause on Lustre too.

---

## 5. Two landmines specific to launching through this repo

### 5a. `resolve_profile()` silently serves GLM with MiniMax parsers

`src/reprocli_serve/profiles.py` has no GLM entry. `resolve_profile()` falls
through every `is_*` check to `minimax_profile()`, which sets
`tool_call_parser="minimax_m2"` and `reasoning_parser="minimax_m2"`. Nothing
errors. Tool calls just come back wrong.

**Always pass both explicitly** until a `glm52_profile()` exists:

```
--tool-call-parser glm47 --reasoning-parser glm45
```

Those names do not match the model version. That is correct, not a typo — they
come from the vLLM GLM-5.2 recipe and are confirmed by the independent
`renning22/glm-5.2-4090` port.

### 5b. The head rank times out at 30 minutes

`SERVER_STARTUP_TIMEOUT = 1800` in `src/reprocli_serve/config.py`, hardcoded,
no env override. `wait_until_ready()` raises `TimeoutError` past it. The
single-node bring-up MEASURED **~45 min** to KV cache init (874 s weight load +
1024 s torch.compile + 170 s warmup). Two nodes with no offload should be
faster, but not obviously under 30 minutes on a cold Inductor cache.

So: **bring up with raw `vllm serve`** (§6), which has no such deadline, and
switch to `python -m reprocli_serve` only once you have measured startup and the
compile cache is warm. `scripts/serve/bench_serve.py` polls `/health` forever by
default and is the right thing to watch with.

### 5c. `NCCL_SOCKET_IFNAME=hsn` is a bare prefix and it hangs

`scripts/serve/serve_multinode.sbatch` currently exports the bare prefix `hsn`.
The MiniMax-M3 runbook documents this as a hang: a bare `hsn` also matches the
`hsn0.561..` VLAN aliases (public 141.142.x), and mixing those with the private
172.28.x fabric stalls the cross-node socket connect right after `vLLM is using
nccl==...`, with no progress past it. Pin the four NICs by exact name, inside
the srun payload so nothing from `~/.bashrc` can leak in:

```bash
export NCCL_SOCKET_IFNAME=hsn0,hsn1,hsn2,hsn3
export GLOO_SOCKET_IFNAME=hsn0
```

---

## 6. Bring-up: interactive, TP=4 + PP=2

Modeled on `scripts/minimax_m3/minimax_m3_multinode_interactive.md`, which is
the verified two-node shape on this cluster.

### 6.1 Allocate

```bash
salloc --account=betw-dtai-gh --partition=ghx4-interactive \
  --nodes=2 --ntasks-per-node=1 --gpus-per-node=4 \
  --cpus-per-task=32 --mem=440G --time=02:00:00
```

`--mem=440G` is no longer load-bearing for pinned weights (§1) but still buys
page cache for a 474 GB checkpoint.

### 6.2 Shell prep, then discover the head IP

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

An empty `IFACE_NAME` makes `ip addr show` grab loopback, `HEAD_IP` silently
becomes `127.0.0.1`, the worker never joins, and the launch hangs ~10 min then
dies with `4/8 clients joined`. Check the echo.

`TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC=1800` is raised from the usual 1200: the
`shm_broadcast: No available shared memory broadcast block found in 60 seconds`
spam during the ~17 min torch.compile is normal (the message says so itself),
but a 20-minute heartbeat is uncomfortably close to it.

### 6.3 Launch

```bash
mkdir -p logs
MODEL=/work/hdd/bfvr/msalunkhe/models/GLM-5.2-AWQ-INT4

srun --jobid="$SLURM_JOB_ID" --nodes=2 --ntasks=2 --ntasks-per-node=1 \
  --gpus-per-task=4 --cpus-per-task=32 bash -lc '
    module load python/3.11.9
    source /u/msalunkhe/reprocli/.venv/bin/activate
    export LD_LIBRARY_PATH=/u/msalunkhe/reprocli/.venv/lib/python3.11/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH
    export NCCL_SOCKET_IFNAME=hsn0,hsn1,hsn2,hsn3
    export GLOO_SOCKET_IFNAME=hsn0
    export VLLM_HOST_IP="$(ip -o -4 addr show hsn0 | awk "{split(\$4,a,\"/\"); print a[1]; exit}")"
    python -c "import vllm.third_party.deep_gemm" || { echo "FIX LD_LIBRARY_PATH"; exit 1; }
    vllm serve '"$MODEL"' \
      --served-model-name zai-org/GLM-5.2 \
      --tensor-parallel-size 4 \
      --pipeline-parallel-size 2 \
      --nnodes 2 --node-rank "$SLURM_PROCID" --master-addr '"$HEAD_IP"' \
      --max-model-len 131072 \
      --max-num-seqs 16 \
      --gpu-memory-utilization 0.90 \
      --tool-call-parser glm47 \
      --reasoning-parser glm45 \
      --enable-auto-tool-choice \
      --enable-prompt-tokens-details \
      --trust-remote-code \
      --host 0.0.0.0 --port 8000
  ' >"logs/glm52-2node-${SLURM_JOB_ID}.log" 2>&1 &
export VLLM_SERVER_PID=$!
tail -f "logs/glm52-2node-${SLURM_JOB_ID}.log"
```

Notes on the non-obvious choices:

- **No `--cpu-offload-gb`.** That is the entire point (§1). If you find yourself
  adding it back, the layout is wrong, not the flag.
- **No `--kv-cache-dtype fp8`** (§3b). Two independent upstream bugs.
- **No `--speculative-config`.** MTP is incompatible with PP>1 (§2). Adding it
  here is the single most likely way to get a silently-wrong server rather than
  a crash.
- **No `--enable-expert-parallel`.** It reshuffles which params live where and
  adds a MoE all-to-all on the fabric. Not a variable you want live during
  bring-up.
- `--gpu-memory-utilization 0.90`, not 0.93: with 30.8 GiB free there is no
  reason to run tight, and profiling headroom is what the single-node attempt
  kept losing.
- `--max-model-len 131072`, not the model's 1M. Raise it after §7 measures the
  pool. Note the repo-wide default is 196608 (`reprocli_serve/config.py`), which
  also fits.
- 78 layers split 39/39 across the two PP stages. If you ever need an uneven
  split (e.g. to make room for the head/embedding on stage 0), vLLM takes
  `VLLM_PP_LAYER_PARTITION=39,39` as a comma list summing to 78.

Health, once the log shows the API binding:

```bash
curl -fsS "http://${HEAD_IP}:8000/health" && echo "  health: ok"
```

### 6.4 The TP=8 + MTP arm

Same allocation, same env. Swap the parallelism and add the draft config:

```bash
      --tensor-parallel-size 8 \
      --speculative-config.method mtp \
      --speculative-config.num_speculative_tokens 5 \
```

and drop `--pipeline-parallel-size`. Everything else is unchanged. Two things to
watch: the KV pool halves (§1), and MTP acceptance is only worth having if it
survives the fabric all-reduce cost — which is exactly the §7 A/B.

---

## 7. Benchmark — this is the deliverable

The single-node path died with **zero** performance numbers. Producing them is
the reason to spend two nodes. Run all three, on both layouts.

```bash
# 1. Cold/warm prefill + decode on an ~85k agentic transcript, plus the
#    npp/ntg/npl table shaped to match serve-gguf-llamacpp-gh200.md section 8.
python scripts/serve/bench_serve.py \
  --base-url "http://${HEAD_IP}:8000/v1" \
  --model zai-org/GLM-5.2 --scenario both

# 2. Sweep-shaped traffic: N concurrent agents, append-only transcripts.
#    This is the one that reflects real wall-clock, and the one PP=2 needs
#    (a single stream will under-report it, section 2).
python scripts/serve/bench_agent_sim.py \
  --base-url "http://${HEAD_IP}:8000/v1" \
  --model zai-org/GLM-5.2 --agents 8 --turns 10

# 3. Stock random-prompt throughput, for comparability outside this repo.
vllm bench serve --base-url "http://${HEAD_IP}:8000" \
  --model zai-org/GLM-5.2 --dataset-name random \
  --random-input-len 8192 --random-output-len 1024 \
  --num-prompts 64 --max-concurrency 8 --seed 42
```

`bench_serve.py` waits on `/health` forever by default and prints elapsed
minutes, so start it *before* the server is up and it doubles as the startup
timer (§5b).

### Record this table

| | llama.cpp IQ4_XS | vLLM TP=4+PP=2 | vLLM TP=8+MTP=5 |
|---|---|---|---|
| decode t/s (1 stream) | **40** MEASURED | | |
| decode t/s (8 agents) | — | | |
| cold prefill t/s | **575** MEASURED | | |
| warm prefill t/s | — | | |
| cached share, 8 agents x 10 turns | — | | |
| time to `/health` | ~0 | | |
| MTP acceptance length | n/a | n/a | |

The llama.cpp column is MEASURED in `serve-gguf-llamacpp-gh200.md` §8 on one
node. It is the incumbent and it costs no startup.

### The decision rule

`serve-glm52-vllm-gh200.md` §8 set it, and it still holds with one amendment.

**Decode is probably a wash.** llama.cpp MEASURED 40 t/s; the dnhkng blog got
43 t/s on vLLM after NUMA work. Nothing there is worth a long startup — *unless*
MTP lands, which is the new variable: the recipe's 5 draft tokens plus GLM-5.2's
claimed +20% acceptance length is the only mechanism on the table that could
make vLLM decisively win decode. The blog measured 43 -> 55 t/s from an FP8
MTP-3 graft. That is why §6.4 exists.

**Prefill is the structural case.** llama.cpp gets ~575 t/s because
`--split-mode layer` is pipeline parallelism with one GPU computing at a time
(~48% util). vLLM does real TP, Marlin INT4 kernels, and chunked prefill. Nobody
has published a GLM-5.2 prefill number on 8xGH200. 85k at 575 t/s is ~148 s; at
3x that it is ~50 s.

The counterweight: cold prefill amortizes. An agent pays it once, and turn 2+
hits the prefix cache — *except* that compaction rewrites the transcript (eliding
tool stdouts to placeholders), which diverges the prefix and forces a
re-prefill. So how much prefill actually costs depends on the compaction rate,
which is measurable from `repro_events`. Get that number before weighting
prefill heavily.

**So: if neither the warm-prefill multiple nor MTP-assisted decode is
several-fold better than llama.cpp, this path does not pay for itself** — it
costs two nodes instead of one, a long startup, three upstream bugs, and a quant
whose quality edge over UD-IQ4_XS is unquantified on both sides.

Watch `cached%` on the agent sim. It should climb toward the 80-95% real sweeps
show; a sag as transcripts grow means the KV pool is evicting, which at 736k
tokens (§1) would be surprising and worth chasing.

---

## 8. If you meant 2 GH200 *GPUs*, not 2 nodes

This runbook reads "2xGH200 nodes" as **two ghx4 nodes = 8 GPUs**. Note that
`serve-laguna-s21-vllm-gh200.md` uses "2xGH200" for two GPUs on one node, so the
vocabulary is genuinely overloaded here.

On 2 GPUs the arithmetic is unkind: 191.2 GiB HBM against 441.7 GiB of weights
means ~125 GiB of pinned host memory *per GPU*, which is deeper into exactly the
regime where the single-node attempt stalled (§7 there: TP0 stuck in
`_maybe_offload_to_cpu` for 15+ minutes at 36 GiB/GPU). The one published data
point is the dnhkng blog on 2xGH200 + `--cpu-offload-gb 170`: **2.39 t/s**,
rising to 20.31 t/s only after strict local NUMA placement — 8.5x from binding
alone, with no binding recipe published, and vLLM has no per-worker NUMA binding
(its TP workers are children of one process, so `srun --cpu-bind` pins them all
to the same node).

That is a research project, not a bring-up. If 2 GPUs is the real constraint,
serve the GGUF through llama.cpp instead.

---

## 9. Open items

- Nothing in this file has been executed. §1's offload-to-zero claim is
  arithmetic; the first run either confirms it at KV-cache init or does not.
- The §7 table is empty. That is the deliverable.
- **No `glm52_profile()` in `src/reprocli_serve/profiles.py`** (§5a). Until it
  exists, every launch through the harness must pass `glm47`/`glm45` by hand and
  a typo serves MiniMax parsers silently.
- **`SERVER_STARTUP_TIMEOUT` is not overridable** (§5b). A one-line env read in
  `config.py` would let the harness path work for slow-starting models.
- **`serve_multinode.sbatch` exports the bare `NCCL_SOCKET_IFNAME=hsn`** (§5c),
  which the M3 runbook documents as a hang. Worth fixing there, not just
  working around here.
- MTP under PP is an open upstream RFC (vllm#44697). If it lands, the §2 table
  collapses to one row and TP=4+PP=2 wins outright.
- `save_sharded_state` to kill the TP read amplification on load
  (`serve-glm52-vllm-gh200.md` §3). Needs one successful load first.
- AWQ-INT4 vs UD-IQ4_XS quality delta is unquantified on both sides. Neither
  runbook can tell you whether the better quant buys anything.
- The compressed-tensors kernel path (INT4, group 32, asymmetric) on sm90 is
  untested here. If Marlin rejects the asymmetric zero points, this fails at
  load with a quant-config error, not at KV init — a fast failure, at least.

---

## Sources

- [cyankiwi/GLM-5.2-AWQ-INT4](https://huggingface.co/cyankiwi/GLM-5.2-AWQ-INT4) — size, MTP layer, `config.json`
- [vLLM Recipes: zai-org/GLM-5.2](https://recipes.vllm.ai/zai-org/GLM-5.2) — official flags, MTP=5, parsers
- [vllm#46074](https://github.com/vllm-project/vllm/issues/46074) — DSA indexer off-by-one, fp8 KV, ~325K
- [vllm#44697](https://github.com/vllm-project/vllm/issues/44697) — RFC: MTP speculative decoding under PP>1
- [vllm-project/recipes#565](https://github.com/vllm-project/recipes/issues/565) — FLASHMLA_SPARSE + FP8 KV break
- [bird/GLM-spark](https://github.com/bird/GLM-spark) — GLM-5.2 under vLLM PP across nodes; MTP+PP broken
- [renning22/glm-5.2-4090](https://github.com/renning22/glm-5.2-4090) — independent confirmation of `glm47`/`glm45`, 78-layer PP partition
- [dnhkng: GH200 benchmarking, GLM-5.2](https://dnhkng.github.io/posts/gh200-benchmarking-part-3-glm52/) — 2xGH200 offload numbers, NUMA 8.5x
