# Serve DeepSeek-V4-Flash via vLLM on GH200 (DeltaAI)

Verified working 2026-07-16 on 2x GH200 (one ghx4 node, TP=2), vLLM 0.25.1,
checkpoint `deepseek-ai/DeepSeek-V4-Flash` (158B MoE, 13B active, released
natively INT8/FP8, 149 GiB). This IS the lossless config: the unsloth GGUFs
re-quantize this same checkpoint, so there is no reason to use them with vLLM
(whose GGUF loader rejects deepseek* architectures anyway, vllm#13665).

## Environment (both exports required, every shell)

```bash
source /u/msalunkhe/reprocli/.venv/bin/activate

# 1. DeepGEMM needs libnvrtc.so.13. Without this the server dies with
#    "Sparse Attention Indexer CUDA op requires DeepGEMM support" -- V4's
#    Lightning Indexer has no non-DeepGEMM fallback. The standalone deep_gemm
#    wheel is separately broken (needs CXXABI_1.3.15 > spack gcc-runtime 13.2);
#    ignore that warning, vLLM's vendored copy is the one that matters.
export LD_LIBRARY_PATH=/u/msalunkhe/reprocli/.venv/lib/python3.11/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH

# 2. FlashInfer's top-k/top-p sampling kernel crashes the profile run on this
#    platform (TopKMaskLogits: invalid resource handle). Native torch sampler
#    instead; negligible cost at our batch sizes.
export VLLM_USE_FLASHINFER_SAMPLER=0
```

## Serve (TP=2)

```bash
vllm serve deepseek-ai/DeepSeek-V4-Flash \
  --tensor-parallel-size 2 \
  --served-model-name deepseek-ai/DeepSeek-V4-Flash \
  --gpu-memory-utilization 0.95 \
  --kv-cache-dtype fp8 \
  --kv-offloading-size 100 \
  --port 8000
```

- `--kv-cache-dtype fp8` is REQUIRED, not a tradeoff: V4's fp8_ds_mla KV
  layout asserts on anything else ("only supports fp8 kv-cache, got auto").
- `--kv-offloading-size 100` = 100 GiB CPU prefix-cache tier (total across TP
  ranks, native OffloadingConnector) in Grace LPDDR over NVLink-C2C. Weights
  take 74 GiB of each 96 GB GPU, so GPU KV is thin; this tier is what keeps
  multi-agent transcripts from thrashing. Node has 440G allocated, so up to
  ~200 is safe.
- No `--max-model-len`: model default is 1M and the startup KV check passed
  at TP=2. If a future config trips "max seq len is larger than ... KV cache",
  set `--max-model-len` just under the capacity the error reports.
- First request after startup stalls while DeepGEMM JIT-compiles kernels.

## Reasoning effort (sweep requirement)

AA's Intelligence Index 40 for V4 Flash is the **Reasoning, Max Effort** variant.
The roster ladder cites that number, so eval-100 sweeps MUST run Think Max or the
capability axis is confounded (same trap as MiniMax AWQ-reported-as-upstream).

Effort is per-request, not a serve flag — the brain client must send:

```python
extra_body={"chat_template_kwargs": {"thinking": True, "reasoning_effort": "max"}}
```

- Sampling: temperature 1.0, top_p 1.0 (DeepSeek's Think Max recommendation).
- Think Max needs max-model-len >= 393216; the default 1M above satisfies it.
- NOT yet plumbed: no `chat_template_kwargs` support exists in the repro client.
  Add a per-model request-kwargs field to the sweep profile before this sweep.
- Budget warning: Max Effort measured 2.5x average verbosity on the AA index
  (230M vs 92M tokens); size round budgets and wall-clock caps accordingly.

## Benchmark

```bash
# sweep-shaped traffic (per-turn ttft/decode/cache-share table):
python scripts/serve/bench_agent_sim.py \
  --base-url http://127.0.0.1:8000/v1 \
  --model deepseek-ai/DeepSeek-V4-Flash --agents 8 --turns 10

# stock random-prompt sweep:
vllm bench serve --base-url http://127.0.0.1:8000 \
  --model deepseek-ai/DeepSeek-V4-Flash --dataset-name random \
  --random-input-len 8192 --random-output-len 1024 \
  --num-prompts 64 --max-concurrency 8 --seed 42
```

Watch the cached% column: append-only transcripts should climb toward the
80-95% cache share real sweeps show; a sag as transcripts grow means the GPU
prefix cache is evicting and the CPU tier isn't absorbing it.

## Known good/bad flags

| flag | verdict |
|---|---|
| `--kv-cache-dtype fp8` | required (fp8_ds_mla assert) |
| `VLLM_USE_FLASHINFER_SAMPLER=0` | required (FlashInfer sampler crash) |
| `LD_LIBRARY_PATH` += nvidia/cu13/lib | required (DeepGEMM/nvrtc) |
| `--kv-offloading-size 100` | working; total GiB across ranks |
| TP=2, gpu-mem-util 0.95 | working; 74 GiB weights + ~17 GiB KV per GPU |

Shutdown prints a harmless `tilelang/lib/libcudart_stub.so: undefined symbol:
cudaDeviceReset` traceback (tilelang ships a stub libcudart that shadows the
real one in the cleanup path). If "invalid resource handle" errors ever appear
OUTSIDE the sampler, suspect that stub shadowing first.
