# Serving GLM-5.2 AWQ-INT4 with vLLM on DeltaAI GH200

Runbook for standing up `cyankiwi/GLM-5.2-AWQ-INT4` as an OpenAI-compatible
brain on a 4xGH200 node. Companion to `serve-gguf-llamacpp-gh200.md`, which
serves the same model as GGUF through llama.cpp. The two paths trade off against
each other and the comparison is not settled — see §8.

> **STATUS: ABANDONED 2026-07-15. Use the llama.cpp path.**
>
> The server never reached `/health`. Four walls in one afternoon (§4a, §4b, §5,
> §7), the last of which — an illegal memory access in the model forward — looks
> like `--cpu-offload-gb` simply not working on quantized MoE. The prize was an
> *unmeasured* prefill number (§8) against a llama.cpp path already measured at
> 40 t/s decode / 575 t/s prefill.
>
> Read this before trying again. Everything below is real and was paid for; §9
> says what would have to change to make a retry worth it.

Written 2026-07-15 from a bring-up on gh068/gh151 with vLLM 0.25.1, torch
2.11.0+cu130. Numbers marked MEASURED were observed in that session; everything
else is arithmetic. Sections 1-6 are verified up to the point they describe.

## 1. The hardware budget, and why offload is forced

    4x GH200, 97,871 MiB each  =  382 GiB HBM
    weights, 83 shards          =  440.4 GB  =  410.1 GiB
                                   ------------------------
                                   28 GiB over, before any KV cache

Unlike the GGUF path there is no smaller quant to retreat to: AWQ-INT4 *is* the
4-bit tier. So `--cpu-offload-gb` is not a tuning choice here, it is the only
way the model exists on this node. That makes this runbook the deliberate
exception to `serve-gguf-llamacpp-gh200.md` §3 ("do not offload"), and §8 is
about whether the exception was worth making.

Get the exact size from the API, not the model card:

    curl -s "https://huggingface.co/api/models/cyankiwi/GLM-5.2-AWQ-INT4/tree/main?recursive=1" \
      | python3 -c "import json,sys; f=json.load(sys.stdin); \
        print(sum(x['size'] for x in f if x['path'].endswith('.safetensors'))/2**30, 'GiB')"

Arch (from `config.json`): 78 layers, 256 experts, 8 active, MLA with
`kv_lora_rank=512` + `qk_rope_head_dim=64`, DSA sparse attention (`glm_moe_dsa`,
`index_topk=2048`). 64 attention heads and 256 experts both divide by 4, so TP=4
is fine even though the vLLM recipe says TP=8 (that targets 8xH200 = 1128 GiB).

### Sizing `--cpu-offload-gb`

**It is per GPU, not total.** This is the flag most often misread, and being
wrong by 4x is an instant OOM or an instant waste.

MEASURED at `--cpu-offload-gb 28`: `Model loading took 78.57 GiB memory`. So
total per-GPU parameter bytes ~= 78.57 + 28.31 = 106.9 GiB, and:

    usable at util 0.93        88.9 GiB
    resident weights          -78.6 GiB
                              ---------
    free for KV + buffers      10.3 GiB

KV per token per layer, at 131k context, MLA latent 576 (512 kv_lora + 64 rope):

| KV dtype        | B/token/layer | pool at 131k | verdict |
|-----------------|---------------|--------------|---------|
| `fp8_ds_mla`    | 656           | 6.2 GiB      | fits, but see §5 — it crashes |
| bf16 (default)  | 1152          | 11.0 GiB     | does not fit at offload 28 |

Hence `--cpu-offload-gb 36`: resident drops to ~70.6 GiB, leaving ~18 GiB for an
11.0 GiB bf16 pool plus ~1.2 GiB of DSA indexer cache and activations. But 36
per GPU is 145 GiB of pinned host memory against 271.62 GiB available, and that
is where it stalled (§7). The tradeoff has no verified answer yet.

## 2. Download

    hf download cyankiwi/GLM-5.2-AWQ-INT4 --local-dir /tmp/GLM-5-2

Plain flags. Do NOT add `HF_XET_HIGH_PERFORMANCE`, `XET_NUM_CONCURRENT_RANGE_GETS`
or a large `--max-workers` — `serve-gguf-llamacpp-gh200.md` §4 measured that
combination self-congesting to 5.6 MB/s. At the 1.33-2.7 GB/s plain defaults
hit, 440 GB is ~3-6 minutes.

## 3. Storage: `/tmp` is CORRECT here

This inverts the GGUF runbook's §4. For **single-node serving**, node-local
`/tmp` is the right choice:

- It is local NVMe. Faster than `/work/nvme`, no network hop.
- vLLM's auto-prefetch would not turn on either way. The log says why:
  `Auto-prefetch is disabled because the filesystem (XFS) is not a recognized
  network FS (NFS/Lustre) and the checkpoint size (410.12 GiB) exceeds 90% of
  available RAM (271.62 GiB).` **Both** clauses must pass. On Lustre the RAM
  check still fails (410.1 > 244.5), so moving to `/work/nvme` buys nothing and
  costs throughput.

The GGUF runbook's "never use /tmp" stands for its own reasons — the copy dies
with the allocation and is invisible to other nodes. Those are persistence
arguments, not speed arguments. Re-download on a new node; it is 3-6 minutes.

MEASURED: `Loading weights took 874.06 seconds` from /tmp. That is 480 MiB/s per
rank, which looks bad until you account for TP: every rank reads the whole
checkpoint and keeps its 1/4 slice, so real traffic is ~1.6 TiB in 874s =
**~1.9 GiB/s aggregate**, partly overlapped with dequant. The documented fix for
the 4x amplification is a sharded checkpoint (`save_sharded_state`), after which
load time stays flat regardless of TP. Needs one successful load first.

## 4. The environment — three walls, ~45 min each

The environment is load-bearing and survives neither a new shell nor a new node
allocation. Startup is ~15 min of weight loading plus ~17 min of torch.compile
*before* anything touches the indexer or the KV cache, so every one of these
costs most of an hour to discover.

### 4a. `libnvrtc.so.13` — the DeepGEMM wall

GLM-5.2 is `glm_moe_dsa`, so every decoder layer builds a DSA `Indexer`, and
vLLM hard-requires DeepGEMM for it. Symptom:

    RuntimeError: Sparse Attention Indexer CUDA op requires DeepGEMM support
                  in the current vLLM environment.

Misleading: nothing is missing, it just will not load. vLLM checks whether
DeepGEMM *imports*, not whether it works (vllm-project/vllm#35021), so a missing
`.so` surfaces as a capability error. torch is `2.11.0+cu130`, and the vendored
`vllm.third_party.deep_gemm` wants CUDA 13's NVRTC, which ships in the venv but
is not on the loader path:

    export LD_LIBRARY_PATH=/u/msalunkhe/reprocli/.venv/lib/python3.11/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH

**`nvidia/cuda_nvrtc/lib` holds `libnvrtc.so.12` — the wrong one.** It is
`nvidia/cu13/lib`. If absent entirely: `uv pip install nvidia-cuda-nvrtc-cu13`.

GH200 is sm90, so DeepGEMM is supported. On sm80 (A100) this is a dead end with
no fallback — see vllm-project/vllm#35021 and the TRITON_MLA_SPARSE workaround
in https://gist.github.com/timinar/c8d2eca4e2ea7d11db57a1e6e62d06a2.

### 4b. `CXXABI_1.3.15` — the standalone deep_gemm wall

    ImportError: /sw/spack/.../gcc-runtime/13.2.1-.../libstdc++.so.6:
      version `CXXABI_1.3.15' not found (required by deep_gemm/_C...so)

`CXXABI_1.3.15` ships with GCC 14; the spack python module drags in
`gcc-runtime/13.2.1`, which tops out at 1.3.14, and its lib dir wins on
`LD_LIBRARY_PATH`. Cray's `gcc-native/14` is loaded by default and does **not**
reorder it. The spack module does:

    module load gcc/14.2.0
    export LD_LIBRARY_PATH="$(dirname $(gcc -print-file-name=libstdc++.so.6)):$LD_LIBRARY_PATH"

Optional — the bundled DeepGEMM satisfies vLLM on its own, so 4a alone unblocks
the indexer. This only silences the warning spam and gives vLLM its preferred
build. libstdc++ is ABI-backward-compatible, so a newer one is safe under the
gcc-13-built python.

### 4c. Verify before burning a launch

    python -c "import vllm.third_party.deep_gemm; print('bundled ok')"   # this one gates the indexer
    python -c "import deep_gemm; print('standalone ok')"                 # nice to have

Either printing `ok` clears §4a. Two seconds, versus 45 minutes.

## 5. What NOT to add: `--kv-cache-dtype fp8`

It selects the FLASHMLA_SPARSE backend, whose `fp8_ds_mla` layout is 656
B/token/layer, while vLLM's profiling reshape assumes the 576-element MLA
latent. Startup dies at KV init, ~45 min in:

    RuntimeError: shape '[16, 64, 576]' is invalid for input of size 671744

The arithmetic identifies it exactly: `671744 / (16*64) = 656`. Known upstream,
no maintainer fix — https://github.com/vllm-project/recipes/issues/565
("FLASHMLA_SPARSE backend breaks with FP8 KV Cache when running GLM-5.2 via
official recipe/image"). There is nothing to switch to; FLASHMLA_SPARSE is the
only sparse-MLA backend on Hopper.

MEASURED: dropping the flag changes backend selection to
`FLASH_ATTN_MLA_SPARSE out of potential backends: ['FLASH_ATTN_MLA_SPARSE',
'FLASHMLA_SPARSE']` and init proceeds past KV. **With fp8 KV the candidate list
collapses to FLASHMLA_SPARSE alone** — the flag removes its own escape route.

Cost: bf16 KV is ~2x the pool (§1), which is what `--cpu-offload-gb 36` pays for.
Do not re-add this flag to claw the memory back.

## 6. Launching

    module load gcc/14.2.0
    source /u/msalunkhe/reprocli/.venv/bin/activate
    export LD_LIBRARY_PATH=/u/msalunkhe/reprocli/.venv/lib/python3.11/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH
    export TORCHINDUCTOR_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/torchinductor
    export TRITON_CACHE_DIR=/work/nvme/bfvr/msalunkhe/.cache/triton
    export VLLM_CACHE_ROOT=/work/nvme/bfvr/msalunkhe/.cache/vllm
    export SAFETENSORS_FAST_GPU=1 CUDA_MODULE_LOADING=LAZY CUDA_DEVICE_ORDER=PCI_BUS_ID
    export VLLM_HOST_IP=127.0.0.1 MASTER_ADDR=127.0.0.1
    export NCCL_CUMEM_ENABLE=0 NCCL_CUMEM_HOST_ENABLE=0 OMP_NUM_THREADS=1

    python -c "import vllm.third_party.deep_gemm" || { echo "fix LD_LIBRARY_PATH first"; exit 1; }

    CUDA_VISIBLE_DEVICES=0,1,2,3 vllm serve /tmp/GLM-5-2/ \
      --served-model-name zai-org/GLM-5.2 \
      --tensor-parallel-size 4 \
      --cpu-offload-gb 36 \
      --max-model-len 131072 \
      --max-num-seqs 8 \
      --gpu-memory-utilization 0.93 \
      --tool-call-parser glm47 \
      --reasoning-parser glm45 \
      --enable-auto-tool-choice \
      --trust-remote-code \
      --host 0.0.0.0 --port 8000

Notes on the non-obvious flags:

- `glm47` (tool) / `glm45` (reasoning) come from the vLLM GLM-5.2 recipe. They
  do not match the model name. That is correct, not a typo.
- `--enable-expert-parallel` left OFF. It reshuffles which params are resident
  vs offloaded, which is not a variable you want live during bring-up.
- `--cpu-offload-gb` is **per GPU**. 36 means 145 GiB of pinned host memory.
- No `--speculative-config mtp`. The recipe's 5-token MTP is for the FP8
  checkpoint; the AWQ repo's MTP module is untested here.
- `--mem=440G` in sbatch. The offloaded weights are pinned, so unlike the pure-HBM
  llama.cpp path this request is real.

### Expected startup timeline

MEASURED end to end, 12:58:01 -> 13:43:09 = **~45 min**:

    +0:00   engine init
    +2:15   three ranks log "Total CPU offloaded parameters"
    +5:40   rank 0 logs the same, 2m31s after the others (see §7)
    +5:45   "Loading safetensors checkpoint shards: 0%"
    +20:20  "Loading weights took 874.06 seconds"
    +23:07  "Model loading took 78.57 GiB memory and 1253.13 seconds"
    +40:13  "torch.compile took 1024.34 s in total"
    +43:03  "Initial profiling/warmup run took 169.57 s"
    +45:08  KV cache init

Two log lines look like failures and are not:

- `shm_broadcast: No available shared memory broadcast block found in 60 seconds`
  repeating for half an hour. It tells you itself: *"this typically happens when
  some processes are... doing some time-consuming work (e.g. compilation)."*
- The rank-0 offload gap (§7).

Changing any flag that alters the config hash — `--kv-cache-dtype` included —
invalidates `torch_compile_cache/<hash>/` and buys another ~17 min compile.

## 7. UNRESOLVED: rank 0 stalls in pinned allocation

MEASURED, `--cpu-offload-gb 28`: TP1/2/3 logged `Total CPU offloaded parameters:
28.31` within the same second; TP0 logged it **2m31s later**, then loading began
4s after that. Tolerable.

MEASURED, `--cpu-offload-gb 36`: TP2/3/1 logged `36.27` across 8 seconds. TP0 had
not logged **15+ minutes later**. py-spy on TP0:

    Thread (active): "MainThread"
        __torch_function__ (torch/utils/_device.py:116)
        _maybe_offload_to_cpu (vllm/model_executor/offloader/uva.py:97)
        wrap_modules (vllm/model_executor/offloader/uva.py:56)
        make_layers (vllm/model_executor/models/utils.py:711)

So it is **active in a tensor factory under the UVA offloader**, not deadlocked,
not blocked on NCCL, not blocked on IO. It is allocating pinned host memory and
that is what is slow. `py-spy dump --pid <TP0 pid>` is the tool; use it before
theorizing.

Two candidate explanations, neither confirmed:

- **Pinned-memory pressure.** 4 x 36.27 = 145 GiB pinned against 271.62 GiB
  available, while four ranks also want page cache for a 410 GiB checkpoint.
  28 -> 36 is +32 GiB pinned and is the only thing that changed between the
  tolerable case and the stall. Test by reverting to 28.
- **NUMA.** Each Grace is local to exactly one Hopper. If rank 0's pinned buffer
  lands on the wrong Grace, both the allocation and every subsequent UVA read
  cross the inter-module fabric instead of the local 900 GB/s C2C.
  https://dnhkng.github.io/posts/gh200-benchmarking-part-3-glm52/ MEASURED
  **8.5x** (2.39 -> 20.31 tok/s) from strict local NUMA placement alone, on
  2xGH200 + GLM-5.2 + `--cpu-offload-gb 170`. It publishes no binding recipe.
  Diagnose with `numactl --hardware` and `numastat -p <TP0 pid>`.

**vLLM has no per-worker NUMA binding.** Its TP workers are children of one
process, so `srun --cpu-bind` pins all four to the *same* node, which is worse
than letting them float. If NUMA is the answer, this needs a real harness.

Next attempt should shrink the problem rather than tune placement:

    --cpu-offload-gb 28 --max-model-len 65536

113 GiB pinned instead of 145, and it fits by the numbers: 78.57 GiB resident,
10.3 GiB free, bf16 KV at 64k ~= 5.5 GiB + ~0.6 GiB indexer. If TP0 still stalls
at 28, offload size was not the variable and it is NUMA.

## 8. Benchmarking, and the question this path has to answer

    python scripts/serve/bench_serve.py --model zai-org/GLM-5.2

It polls `/health` until the server binds, then reports cold prefill, warm
(prefix-cached) prefill, and decode on an ~85k-token agentic transcript, plus an
npp/ntg/npl table shaped like `serve-gguf-llamacpp-gh200.md` §8 so the two paths
are directly comparable.

**Decode is probably a wash.** llama.cpp IQ4_XS MEASURED 40 t/s; the dnhkng blog
got 43 t/s on vLLM after its NUMA work. Nothing here is worth 45 min of startup.

**Prefill is the whole case for this path.** llama.cpp gets only ~575 t/s, and
`serve-gguf-llamacpp-gh200.md` §8 explains why structurally: `--split-mode layer`
is pipeline parallelism, one GPU computing at a time, ~48% util. vLLM does real
TP across all four, plus Marlin INT4 kernels and chunked prefill. Nobody has
published a GLM-5.2 prefill number on 4xGH200 with offload. 85k at 550 t/s is
~155s; at 3x that it is ~50s.

The counterweight: cold prefill is amortized — `serve-gguf-llamacpp-gh200.md` §8
notes an agent pays it once per run, and turn 2+ hits the prefix cache. Over a
multi-hour repro run 155s is noise. **Except** compaction rewrites the transcript
(eliding tool stdouts to placeholders), which diverges the prefix and forces a
re-prefill; and llama.cpp's prompt cache is per-slot, so concurrent sweep agents
evict each other. How much prefill actually costs therefore depends on the
compaction rate, which is measurable from `repro_events`.

So the decision rule: **if vLLM's warm prefill is not several-fold better than
llama.cpp's, this path does not pay for itself** — it costs 45-min startups, two
upstream bugs, an unresolved NUMA stall, and a quant whose quality edge over
IQ4_XS is itself unquantified.

## 9. Open items

- The server has never reached `/health`. Everything past §7 is unverified.
- The §7 stall. Revert to `--cpu-offload-gb 28` first (isolates pinned pressure
  from NUMA), then `numastat -p`.
- No prefill/decode numbers on this path at all. That is the §8 question and the
  only reason to keep going.
- AWQ-INT4 vs UD-IQ4_XS quality delta is unquantified on both sides. Neither
  runbook can tell you whether the better quant is worth anything here.
- `save_sharded_state` to kill the 4x TP read amplification (§3). Needs one
  successful load.
- MTP speculative decode (recipe: 5 draft tokens) untested against the AWQ repo.
  The blog got 43 -> 55 tok/s from an FP8 MTP-3 graft, so there is real headroom.
- vLLM's `--cpu-offload-gb` offloads params in load order, not by tensor type,
  so it spills whole early layers rather than targeting experts the way
  llama.cpp's `-ot "ffn_down_exps\.weight=CPU"` could. Whether an expert-targeted
  offload would beat it is unknown; RFC vllm-project/vllm#38256 ("Incremental MoE
  Expert Offloading") is the upstream work to watch.
- Not wired into `reprocli_serve`. This is a manual endpoint; a `Profile`
  equivalent belongs in `src/reprocli_serve/profiles.py` if it becomes routine.
