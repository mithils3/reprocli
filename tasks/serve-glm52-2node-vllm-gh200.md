# Serving GLM-5.2 AWQ-INT4 with vLLM on 2x GH200 NODES (DeltaAI)

`cyankiwi/GLM-5.2-AWQ-INT4` on **two ghx4 nodes = 8 GH200**.
Config: **TP=4 + PP=2, bf16 KV, no MTP, no CPU offload.**

> **STATUS: VERIFIED AND BENCHMARKED (job 2765627, 2026-07-29).** Bring-up in
> **8m47s**, 530,240-token KV pool, no offload. Against the llama.cpp incumbent
> on an 85k transcript: **decode 78.6 vs 40 t/s (2.0x)**, **cold prefill 6,822 vs
> 575 t/s (11.9x)**. Under sweep-shaped load (8 agents x 10 turns): **280.2 t/s
> aggregate, 21.9 turns/min, 85.8% cache share**. This layout is good enough to
> serve on. The open risk is tail latency — p95 ttft reached 20.50 s.

    10:53:41  ranks start          rank=0 gh109 / rank=1 gh113
    11:00:10  stage 0 loaded       51.29 GiB, 316 s
    11:00:42  stage 1 loaded       58.0  GiB, 348 s
    11:01:59  torch.compile done   73 s
    11:02:14  KV cache sized       530,240 tokens (4.05x concurrency at 131k)
    11:02:28  startup complete     8m47s total

Commands first. Everything after `NOTES` is why, and none of it is needed to run
this.

---

# COMMANDS

## 1. Download (once, to shared FS — both nodes must see it)

```bash
hf download cyankiwi/GLM-5.2-AWQ-INT4 \
  --local-dir /work/nvme/bfvr/msalunkhe/models/GLM-5.2-AWQ-INT4
```

474 GB, ~3-6 min. Plain flags only — no `HF_XET_*`, no big `--max-workers` (D).

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
export NCCL_CUMEM_ENABLE=0 NCCL_CUMEM_HOST_ENABLE=0
export NCCL_NET_PLUGIN=none
export OMP_NUM_THREADS=1
export TORCH_NCCL_HEARTBEAT_TIMEOUT_SEC=1800
export TORCH_NCCL_ASYNC_ERROR_HANDLING=1
unset VLLM_HOST_IP MASTER_ADDR MASTER_PORT     # per-node facts; never inherit (E3)
ulimit -l unlimited || true; ulimit -s unlimited || true

export IFACE_NAME=hsn0
mapfile -t NODES < <(scontrol show hostnames "$SLURM_JOB_NODELIST")
HEAD_IP=$(srun --jobid="$SLURM_JOB_ID" --nodes=1 --ntasks=1 --nodelist="${NODES[0]}" \
  bash -lc "ip -o -4 addr show $IFACE_NAME | awk '{split(\$4,a,\"/\"); print a[1]; exit}'")
export HEAD_IP
echo "HEAD_IP=$HEAD_IP"    # must NOT be empty or 127.*
```

**`export HEAD_IP` is load-bearing** — do not stop pasting at the assignment. A
bare `HEAD_IP=$(...)` sets it in your shell only, and srun does not propagate
unexported variables. The launcher falls back to fabric DNS and prints a `note:`
when it does, but do not rely on that.

## 4. Preflight — 2 seconds, saves ~45 minutes

```bash
srun --jobid="$SLURM_JOB_ID" --nodes=2 --ntasks=2 bash -lc \
  'export LD_LIBRARY_PATH=/u/msalunkhe/reprocli/.venv/lib/python3.11/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH
   python -c "import vllm.third_party.deep_gemm; print(\"$(hostname) deep_gemm ok\")"'
```

Both nodes must print `ok`. If not, fix `LD_LIBRARY_PATH` before launching (C1).

## 5. Launch

One line, **backgrounded**. The per-rank payload lives in
`scripts/serve/glm52_2node.sh` so there is no nested quoting to get wrong:

```bash
mkdir -p logs && srun --jobid="$SLURM_JOB_ID" --nodes=2 --ntasks=2 --ntasks-per-node=1 --gpus-per-task=4 --cpus-per-task=32 bash scripts/serve/glm52_2node.sh > "logs/glm52-2node-${SLURM_JOB_ID}.log" 2>&1 &
export SERVE_PID=$!
tail -f "logs/glm52-2node-${SLURM_JOB_ID}.log"     # Ctrl-C this freely
```

**Do not run it in the foreground.** Piping to `tee` reads more naturally but
leaves `srun` owning the terminal, so the `Ctrl-C` you press to get your prompt
back tears down all 8 workers. MEASURED: that ended the first otherwise-successful
bring-up one second after `Application startup complete`.

Overridable by env on the srun line, no edits needed: `MODEL`, `SERVED_NAME`,
`PORT`, `TP`, `PP`, `NNODES`, `MAX_MODEL_LEN`, `MAX_NUM_SEQS`, `GPU_MEM_UTIL`,
`IFACE`.

The script sets the DeepGEMM `LD_LIBRARY_PATH` (C1), pins the four Slingshot NICs
by exact name (E2), recomputes each node's own fabric IP (E3), forces plain NCCL
(C3), re-runs the deep_gemm check per rank, and adds `--headless` on every rank
but 0.

**`--headless` on every rank but 0 is mandatory.** Only rank 0 runs the API
server and EngineCore. Without it node 1 starts its own and dies at KV init with
`AssertionError: collective_rpc should not be called on follower node` — after
loading all the weights first, so it costs ~7 min to discover.

**Do not add** `--cpu-offload-gb`, `--kv-cache-dtype fp8`, `--speculative-config`,
or `--enable-expert-parallel` (B, C2).
**Do not drop** `--disable-custom-all-reduce`, `fuse_allreduce_rms:false`, or
`VLLM_ALLREDUCE_USE_SYMM_MEM=0`. All three are needed together (C3).

Noise that looks like failure and is not: `shm_broadcast: No available shared
memory broadcast block found in 60 seconds`, the `deep_gemm ... CXXABI_1.3.15`
import warnings (C4), NCCL INIT chatter, and `Using default MoE config` — vLLM
ships no tuned fused-MoE config for `E=256,N=512` on GH200 and falls back to
generic tile sizes. Real but unquantified.

## 6. Health

```bash
curl -fsS "http://${HEAD_IP}:8000/health" && echo "  health: ok"
```

MEASURED sanity lines:

    Worker_PP0_*  Model loading took 51.29 GiB   backend DEEPSEEK_V32_INDEXER   KV free 30.56 GiB
    Worker_PP1_*  Model loading took 58.0  GiB   backend FLASH_ATTN_MLA_SPARSE  KV free 22.88 GiB
    GPU KV cache size: 530,240 tokens

Both backends are correct — the DSA indexer and sparse-MLA attention are separate
specs, and neither is the FLASHMLA_SPARSE that fp8 KV would have forced (C2).

## 7. Benchmark

```bash
# Cold/warm prefill + decode on an ~85k agentic transcript. Start it BEFORE the
# server is up: it polls /health forever and prints elapsed minutes.
python scripts/serve/bench_serve.py \
  --base-url "http://${HEAD_IP}:8000/v1" \
  --model zai-org/GLM-5.2 --scenario both

# Sweep-shaped traffic. THIS is the number that matters — PP=2 is bubble-bound at
# batch 1, so single-stream decode is a floor, not the operating point (F).
python scripts/serve/bench_agent_sim.py \
  --base-url "http://${HEAD_IP}:8000/v1" \
  --model zai-org/GLM-5.2 --agents 8 --turns 10

# Stock random-prompt throughput, for comparability outside this repo.
vllm bench serve --base-url "http://${HEAD_IP}:8000" \
  --model zai-org/GLM-5.2 --dataset-name random \
  --random-input-len 8192 --random-output-len 1024 \
  --num-prompts 64 --max-concurrency 8 --seed 42
```

### Results (MEASURED 2026-07-29, job 2765627)

85,228-token transcript, 256 tokens out, single stream:

| | llama.cpp IQ4_XS | vLLM TP=4+PP=2 | |
|---|---|---|---|
| decode t/s (1 stream) | 40 | **78.6** | **2.0x** |
| cold prefill t/s | 575 | **6,822** | **11.9x** |
| ttft on 85k, turn 1 | — | **12.49 s** | |
| ttft on 85k, turn 2 | — | **1.32 s** | 9.5x faster |
| warm prefill t/s (effective) | — | 64,512 | 99.9% cached |
| time to `/health` | ~0 | 8m47s | |
| KV pool allocated | — | 530,240 tok | |

8 agents x 10 turns, 3,014-token shared system prompt, 768 tokens out per turn:

| | vLLM TP=4+PP=2 |
|---|---|
| **aggregate output** | **280.2 t/s** (3.6x the single stream) |
| **throughput** | **21.9 turns/min** — 80 turns in 3.7 min |
| **cache share** | **85.8%** (714,304 of 832,121 prompt tokens) |
| per-stream decode | ~44 t/s |
| ttft, mean / worst p95 | 0.89-4.73 s / **20.50 s** |

**Cache share climbs monotonically, 78.0% -> 93.7% across the ten turns.** That
is the healthy signature: transcripts grow, the shared prefix grows with them,
and nothing is being evicted. A 530,240-token pool is not close to binding at
this concurrency.

The per-turn decode column needs care. Under concurrency a request that waits
behind others has its queue time charged to `ttft`, leaving a short decode window
and a per-request rate several times the true one — turn 5 read **199.9 t/s**
against ~44 either side, on the same turn that logged the worst p95 ttft (20.50
s). One such request moves a mean of 8 from 44 to 66. `bench_agent_sim.py` now
reports the **median** for that reason. Quote the aggregate, not the column.

**vLLM wins both halves, and decode is the surprise.** I predicted decode would
be a wash (llama.cpp 40 t/s, dnhkng 43 t/s on 2xGH200 after NUMA work). It is
2x, at 85k of context, with MTP off. Prefill is the rout the shape of the two
engines predicted: 11.9x.

Warm prefill is an *effective* rate — `prompt_tokens / ttft` over all 85,249
tokens, of which 85,184 were cache hits. It is the right agent-facing number
(what a turn actually costs) but not a compute throughput, so do not compare it
to llama.cpp's 575.

**The npp/ntg table's PP and TG columns were not trustworthy in this run.** Every
short-prompt request came back with no first-token timing, so `prefill_tps` fell
to a fabricated `0.0` that then went into the mean, and `decode_tps` divided by a
window that still contained prefill and queueing — which is why B=1 read 48.8 t/s
against the agentic run's 78.6 t/s at 166x the context. `bench_serve.py` now
returns NaN and excludes those instead of averaging in zeros. Only `total t/s`
was sound (it needs just completion counts and batch wall-clock): **182.2 t/s
aggregate at B=8**. Re-run the table to get the per-request columns.

## 8. Stop

```bash
kill "$SERVE_PID"; wait "$SERVE_PID" || true
exit    # also ends the allocation
```

`SERVE_PID`, not the `VLLM_SERVER_PID` the MiniMax-M3 runbook uses: vLLM warns on
every unrecognised `VLLM_*` env var, so that name puts `Unknown vLLM environment
variable detected` at the top of each subsequent launch.

If a relaunch hits `srun: Job step creation temporarily disabled (Requested nodes
are busy)`, the old step still holds the GPUs. Kill the **step**, never the bare
job id:

```bash
squeue -s -j "$SLURM_JOB_ID"
scancel "${SLURM_JOB_ID}.<stepid>"     # .extern is normal, leave it
```

## 9. Through the harness

Startup is 8m47s, comfortably inside the harness's hardcoded 30-minute timeout
(E1), so this path is viable now. Same srun wrapper as step 5, different payload:

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

Both parser flags are mandatory, not decorative (E1). Untested on this model —
`reprocli_serve` must also be made to pass the three all-reduce settings (C3).

---
---

# NOTES

Companions: `serve-glm52-vllm-gh200.md` (single node, ABANDONED),
`serve-gguf-llamacpp-gh200.md` (same model as GGUF, MEASURED 40 t/s decode /
575 t/s prefill — the incumbent this has to beat),
`scripts/minimax_m3/minimax_m3_multinode_interactive.md` (the verified two-node
launch shape on this cluster).

## A. Memory budget

83 shards = 474.22 GB = **441.65 GiB** downloaded, of which **19.91 GB is the MTP
layer** (`model.layers.78`; 78 layers means indices 0-77, so 78 is the extra one).
Re-check before trusting anything here — the repo changed on 2026-07-28:

```bash
curl -s "https://huggingface.co/api/models/cyankiwi/GLM-5.2-AWQ-INT4/tree/main?recursive=1" \
  | python3 -c "import json,sys; f=json.load(sys.stdin); \
    print(sum(x['size'] for x in f if x['path'].endswith('.safetensors'))/2**30, 'GiB')"
```

MEASURED resident, against 86.0 GiB usable per GPU at util 0.90:

| | weights | free for KV |
|---|---|---|
| stage 0 (39 layers + embed) | 51.29 GiB | 30.56 GiB |
| stage 1 (39 layers + norm + lm_head) | **58.0 GiB** | **22.88 GiB** |

Two nodes is what makes this work: 8 x 95.58 = 764.6 GiB HBM against ~423 GiB of
resident weights, so `--cpu-offload-gb` is **0**. That deletes both walls that
killed the single-node attempt (forced offload, and its unresolved rank-0
pinned-alloc stall). One node would need 105.8 GiB/GPU against 86.0 usable.

**Stage 1 is 6.7 GiB heavier and it should not be.** `embed_tokens` and `lm_head`
are the same shape, so they cancel. Stage 1 logs an extra *unquantized* MoE init
that stage 0 does not (`unquantized.py:334` alongside `int_wna16.py:295`), on the
last PP stage only, which is where an MTP module would land. 18.54 GiB / 4 ranks
= 4.6 GiB, the right neighbourhood. So **layer 78 is probably resident despite no
`--speculative-config`** — unconfirmed, and worth confirming by diffing loaded
weight names rather than inferring from a memory delta.

The pool is sized off the tightest GPU, so that 6.7 GiB costs KV directly. Each
layer is ~1.35 GiB/GPU, so `VLLM_PP_LAYER_PARTITION=41,37` should even the stages
at ~55 GiB and buy ~60k tokens (+11%). Untested. Not binding: 530,240 tokens is
already ~4 concurrent full 131k transcripts.

MLA latent is 576 (512 `kv_lora` + 64 `qk_rope`) = 1152 B/token/layer at bf16,
and TP *replicates* it rather than sharding, so per-GPU cost tracks layers/GPU:
TP=4+PP=2 gives 39 layers x 1152 = 43.9 KiB/token/GPU. TP=8+PP=1 would double it.

Architecture, from `config.json`: 78 layers, hidden 6144, 64 attention heads, 256
routed experts + 1 shared (8 active), DSA sparse attention (`glm_moe_dsa`,
`index_topk=2048`) with IndexShare — 21 `full` + 57 `shared` indexers. Quant is
compressed-tensors **`pack-quantized`**, not classic AWQ despite the repo name:
INT4, group 32, asymmetric, with a 2092-entry `ignore` list covering every
attention projection. Only the MoE expert linears are INT4, which is why 4-bit
still weighs 423 GiB.

## B. Why TP=4 + PP=2, and why MTP is off

**Speculative decoding is incompatible with pipeline parallelism** (vllm#44697,
an open RFC, not a fixed bug; independently hit by `bird/GLM-spark` on GLM-5.2
across 3 nodes). That single fact decides the layout.

| layout | fits | MTP | KV/GPU | fabric cost | precedent here |
|---|---|---|---|---|---|
| **TP=4 + PP=2** | yes | no | **530k tok** | 1 hidden state (12 KB) per stage boundary | `serve_multinode.sbatch` (Kimi-K2.6) |
| TP=8 across nodes | yes | yes | ~265k tok | 78 layers x all-reduce over Slingshot | MiniMax-M3, VERIFIED |
| TP=4 + DP=2 + EP | yes | yes | ~265k tok | + MoE all-to-all | none |

PP=2 wins on everything except MTP. What that costs: the official recipe runs
MTP-5, GLM-5.2's headline claim is ~20% better acceptance length than 5.1, and
the one published GH200 data point is 43 -> 55 t/s from an FP8 MTP-3 graft
(dnhkng). A real decode gain, deliberately left on the table. If vllm#44697 lands,
this table collapses to one row.

Other choices: `--gpu-memory-utilization 0.90` not 0.93 (no reason to run tight
with 23-30 GiB free); `--max-model-len 131072` not the model's 1M (raise after
the benchmark sizes the pool); no `--enable-expert-parallel` (reshuffles param
placement and adds a MoE all-to-all on the fabric — not a live variable during
bring-up).

**6 GPUs: no.** TP must divide `num_attention_heads` = 64, so TP=3 and TP=6 do
not exist; only TP=2+PP=3 or TP=1+PP=6 survive. Memory is fine (70.5 GiB/GPU).
The blockers: no ghx4 node has 6 GPUs so you hold two nodes anyway (the saving is
~25% of billed GPU-hours, nothing else); 3+3 straddles a TP group across the
fabric, reintroducing per-layer inter-node all-reduce; 4+2 keeps TP groups
node-local but is non-uniform and needs the Ray backend; and TP=2 halves the
per-stage compute width, which attacks prefill — the entire case for vLLM over
llama.cpp (F). Revisit only if the benchmark shows the GPUs underutilized.

## C. Walls carried over from the single-node runbook

### C1. DeepGEMM / `libnvrtc.so.13` — REQUIRED

Every decoder layer builds a DSA `Indexer`, and vLLM hard-requires DeepGEMM for
it with no Hopper fallback. A missing `.so` surfaces as a *capability* error:

    RuntimeError: Sparse Attention Indexer CUDA op requires DeepGEMM support

It is `nvidia/cu13/lib`. `nvidia/cuda_nvrtc/lib` holds `libnvrtc.so.12`, the
wrong one. Step 4 checks both nodes.

### C2. Do NOT pass `--kv-cache-dtype fp8` — two independent reasons

1. It selects FLASHMLA_SPARSE, whose `fp8_ds_mla` layout is 656 B/token/layer
   while vLLM's profiling reshape assumes the 576-element latent. Dies at KV init
   ~45 min in with `shape '[16, 64, 576]' is invalid for input of size 671744`
   (671744 / (16*64) = 656). Unfixed: vllm-project/recipes#565. With fp8 KV the
   candidate list collapses to FLASHMLA_SPARSE alone, so the flag removes its own
   escape route.
2. vllm#46074: the DSA indexer has an off-by-one in decode tensor prep that
   crashes *concurrent decode* above ~325K `max_model_len`. bf16 KV was stable at
   every tested size.

The official recipe does use fp8 KV. It targets 8xH200 with different backend
selection. On 2 nodes there is nothing to buy anyway.

### C3. FlashInfer mnnvl all-reduce — three flags, all REQUIRED

MEASURED: the server got past weight load and torch.compile, then died in
`profile_cudagraph_memory` with a wall of `CUBLAS_STATUS_EXECUTION_FAILED` /
`illegal memory access` across all 8 workers. **Those are async fallout.** The
cause is one line on `Worker_PP0_TP0`:

    RuntimeError: trtllm_mnnvl_allreduce_fusion failed with error code
      an illegal memory access was encountered

vLLM fused RMSNorm + all-reduce, FlashInfer picked the `mnnvl` symmetric-memory
all-reduce, this topology cannot do symmetric-memory multicast, workspace init
failed — and the already-compiled graph called the fused kernel anyway.

```bash
export VLLM_ALLREDUCE_USE_SYMM_MEM=0
      --disable-custom-all-reduce
      --compilation-config '{"pass_config":{"fuse_allreduce_rms":false}}'
```

`disable_custom_all_reduce=True` was **already** set in the failing run (vLLM
defaults it on for multi-node). It is not sufficient alone — `fuse_allreduce_rms`
is the one that matters. Same wall as `serve-laguna-s21-vllm-gh200.md`, which
hits it on 2 GPUs and one node: a property of GH200 + FlashInfer, not of this
model or the node count.

`VLLM_USE_FLASHINFER_SAMPLER=0` rides along preemptively — both the Laguna and
DeepSeek-V4-Flash runbooks list the FlashInfer sampler as a crash on this platform
(`TopKMaskLogits: invalid resource handle`). Costs nothing at these batch sizes.

### C4. `CXXABI_1.3.15` — cosmetic

Only silences warning spam from the *standalone* `deep_gemm` wheel; vLLM's
vendored copy is what gates the indexer. To clean it: `module load gcc/14.2.0`,
then prepend its libstdc++ dir to `LD_LIBRARY_PATH`.

## D. Storage

`/tmp` is wrong here — each node's ranks load from the path you pass, so
`/tmp/GLM-5-2` on node A is invisible to node B. Use `/work/nvme`, not
`/work/hdd`: 474 GB read by 8 ranks is the one workload where the flash tier
earns its keep.

No speed is lost against `/tmp`. Auto-prefetch stays off either way — MEASURED:
`Filesystem type for checkpoints: LUSTRE. Checkpoint size: 441.65 GiB. Available
RAM: 425.66 GiB` -> `exceeds 90% of available RAM. Skipping auto-prefetch.`

Do not add `HF_XET_HIGH_PERFORMANCE`, `XET_NUM_CONCURRENT_RANGE_GETS`, or a large
`--max-workers`: `serve-gguf-llamacpp-gh200.md` §4 MEASURED that combination
self-congesting to 5.6 MB/s. At plain defaults, 474 GB is ~3-6 minutes.

## E. Landmines in this repo's harness

- **E1. `resolve_profile()` silently serves GLM with MiniMax parsers.**
  `profiles.py` has no GLM entry, so it falls through every `is_*` check to
  `minimax_profile()`. Nothing errors; tool calls just come back wrong. Always
  pass `--tool-call-parser glm47 --reasoning-parser glm45` explicitly. Those names
  do not match the model version and that is correct — they come from the vLLM
  GLM-5.2 recipe, confirmed independently by `renning22/glm-5.2-4090`.
  `SERVER_STARTUP_TIMEOUT = 1800` in `config.py` is hardcoded with no env
  override; 8m47s clears it, but a cold Inductor cache on a bigger model would not.
- **E2. `NCCL_SOCKET_IFNAME=hsn` is a bare prefix and it hangs.**
  `serve_multinode.sbatch` exports it. Bare `hsn` also matches the `hsn0.561..`
  VLAN aliases (public 141.142.x); mixing those with the private 172.28.x fabric
  stalls the cross-node connect right after `vLLM is using nccl==...`. Step 5 pins
  the four NICs by exact name inside the srun payload so nothing from `~/.bashrc`
  can leak in. Relatedly, an empty `IFACE_NAME` in step 3 makes `ip addr show`
  grab loopback, `HEAD_IP` silently becomes `127.0.0.1`, and the launch hangs
  ~10 min then dies with `4/8 clients joined`. Check the echo.
- **E3. A stale `VLLM_HOST_IP` breaks the engine.** MEASURED: with it left
  exported in the login shell, rank 0 logged `master_addr=172.28.81.240,
  mq_connect_ip=172.28.80.7 (local)` then `zmq.error.ZMQError: Cannot assign
  requested address`. `master_addr` was right; the ZMQ socket had nothing to bind.
  It must be **each node's own** fabric address, so it can never be inherited —
  the launcher recomputes it unconditionally and unsets `MASTER_ADDR`/`MASTER_PORT`
  (`serve_gh200.sbatch` pins `MASTER_ADDR=127.0.0.1`, which would fight
  `--master-addr`).
- **E4. `launch.py`'s all-reduce guard is conditional.**
  `_supported_compilation_config()` force-disables `fuse_allreduce_rms` (C3), but
  `build_serve_command` only calls it inside `if compilation:`. Every profile
  except `minimax_m2` sets no `compilation_config`, so every one of them is
  unprotected against the mnnvl IMA. Making it unconditional on GH200 would have
  saved ~12 minutes here.

## F. Reading the benchmark

**Prefill was the predicted win and it landed: 11.9x.** llama.cpp gets ~575 t/s
because `--split-mode layer` is pipeline parallelism with one GPU computing at a
time (~48% util). vLLM does real TP, Marlin INT4 kernels, and chunked prefill.
85k costs 148 s there and 12.5 s here.

**Decode was predicted to be a wash and was not: 78.6 vs 40 t/s.** The prediction
rested on two arguments that both look wrong now. First, MTP: the one mechanism
that could have made vLLM decisively win decode is foreclosed by PP=2 (B), and
decode doubled anyway — so MTP would be gravy, not the deciding factor. Second,
PP bubbles: a single sequence is strictly sequential across the two stages, so
batch-1 decode should half-idle the pipeline, and 78.6 t/s says that idle costs
less than the per-stage work saved. DSA is the likely reason the 85k context is
not a drag at all — `index_topk=2048` caps attended tokens regardless of
transcript length, so decode cost is roughly flat in context.

Both arguments were about *ceilings*, and the floor turned out to be high enough
that neither bound. Treat that as a caution about the reasoning, not just a happy
result.

**Under sweep-shaped load it holds up: 280.2 t/s aggregate, 3.6x the single
stream.** Single-stream decode really was a floor, as expected — per-stream drops
to ~44 t/s under 8-way concurrency while the aggregate more than triples. That is
continuous batching doing its job, and it is the number the sweep actually sees.

**Prefix caching behaves.** 85.8% overall, climbing 78.0% -> 93.7% as transcripts
grow, squarely in the 80-95% band real sweeps show. Nothing evicts at 530k
tokens. So the 11.9x cold-prefill win is worth less than it looks — an agent pays
it once and every later turn hits cache (12.49 s -> 1.32 s ttft) — but that is
the good case, not a caveat.

The real caveat is compaction: it rewrites the transcript and diverges the
prefix, forcing a re-prefill that this sim never triggers. How much prefill costs
in production therefore depends on the compaction rate, measurable from
`repro_events`. Get that number before sizing the prefill win.

**Watch tail latency, not throughput.** p95 ttft hit **20.50 s** on turn 5 while
the mean was 4.26 s. Head-of-line blocking under 8-way concurrency is the one
number here that got worse, and it is invisible in the aggregate. If the sweep
runs more than 8 concurrent agents, measure this before raising `--max-num-seqs`
above 16.

**Verdict: this path pays for itself.** Two nodes instead of one, an 8m47s
startup, and three upstream bugs, against 2x single-stream decode, 11.9x cold
prefill, and 280 t/s aggregate under load. The remaining unknown is quality — the
AWQ-INT4 vs UD-IQ4_XS delta is unquantified on both sides, and no throughput
number settles it.

## G. Open items

- **p95 ttft of 20.50 s under 8 agents** is the one bad number. Head-of-line
  blocking, invisible in the aggregate. Characterise it before running more than
  8 concurrent agents or raising `--max-num-seqs`.
- **Re-run the npp/ntg table** now that `bench_serve.py` excludes untimed
  requests instead of averaging in zeros. Its PP/TG columns were unusable.
- **Compaction re-prefill is unmeasured.** The agent sim is append-only, so it
  never diverges a prefix; production does. Pull the compaction rate from
  `repro_events` to size what prefill actually costs.
- **Why did no short-prompt request record a first token?** The agentic path
  (same `stream_once`) timed fine at 85k. The fix stops it corrupting the mean
  but does not explain it. Suspects, in order: a reasoning/tool-call delta shape
  the parser only emits for short prompts, or the threaded `stream_many` path.
  `--scenario agentic --input-tokens 512 --output-tokens 128` isolates it —
  same short prompt, no threads.
- Is layer 78 (MTP) actually resident (A)? If so, ~4.6 GiB/GPU is spent on a
  module PP=2 can never use. Confirm by diffing loaded weight names.
- PP stages imbalanced 51.29 / 58.0 GiB. `VLLM_PP_LAYER_PARTITION=41,37` should
  even them; untested, worth ~+11% pool.
- No `glm52_profile()` (E1); `SERVER_STARTUP_TIMEOUT` not overridable;
  `serve_multinode.sbatch` bare `hsn` (E2); `launch.py` conditional guard (E4).
  All four are small fixes in this repo, not upstream.
- MTP under PP is an open upstream RFC (vllm#44697). Re-check before any sweep
  commits to this brain.
- No tuned fused-MoE config for `E=256,N=512` on GH200; running generic tiles.
- `save_sharded_state` would kill the TP read amplification on load. Now possible
  — it needed one successful load first.
- AWQ-INT4 vs UD-IQ4_XS quality delta is unquantified on both sides.

## Sources

- [cyankiwi/GLM-5.2-AWQ-INT4](https://huggingface.co/cyankiwi/GLM-5.2-AWQ-INT4) — size, MTP layer, `config.json`
- [vLLM Recipes: zai-org/GLM-5.2](https://recipes.vllm.ai/zai-org/GLM-5.2) — official flags, MTP=5, parsers
- [vllm#46074](https://github.com/vllm-project/vllm/issues/46074) — DSA indexer off-by-one, fp8 KV, ~325K
- [vllm#44697](https://github.com/vllm-project/vllm/issues/44697) — RFC: MTP speculative decoding under PP>1
- [vllm-project/recipes#565](https://github.com/vllm-project/recipes/issues/565) — FLASHMLA_SPARSE + FP8 KV break
- [bird/GLM-spark](https://github.com/bird/GLM-spark) — GLM-5.2 under vLLM PP across nodes; MTP+PP broken
- [renning22/glm-5.2-4090](https://github.com/renning22/glm-5.2-4090) — independent confirmation of `glm47`/`glm45`
- [vLLM parallelism docs](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/) — TP=GPUs-per-node, PP=nodes
- [dnhkng: GH200 benchmarking, GLM-5.2](https://dnhkng.github.io/posts/gh200-benchmarking-part-3-glm52/) — 2xGH200 offload numbers, NUMA 8.5x
