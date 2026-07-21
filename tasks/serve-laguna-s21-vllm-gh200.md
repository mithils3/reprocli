# Serve poolside/Laguna-S-2.1-FP8 via vLLM on 2xGH200 (DeltaAI)

Verified working 2026-07-21 on 2x GH200 (one ghx4 node, TP=2), vLLM 0.25.1,
checkpoint `poolside/Laguna-S-2.1-FP8` (118B / 8B-active MoE, agentic-coding
specialist, arch `LagunaForCausalLM`, 112.7 GiB FP8, 256K max context). This is
the roster's coding-specialist rung; the FP8 checkpoint caps at 256K (only the
BF16 repo goes to 1M).

vLLM 0.25.1 already satisfies the recipe (needs 0.25.0+; 0.25.1 for DFlash) and
registers `LagunaForCausalLM` + the `poolside_v1` parsers natively — no bump
needed.

## Download (node-local /tmp, single-node serving)

```bash
hf download poolside/Laguna-S-2.1-FP8 --local-dir /tmp/Langua-S-2.1
```

~121 GB, 3 min at the plain default (~130 MB/s here). /tmp is correct for
single-node serving: local NVMe, dies with the allocation. Re-download on a new
node.

## Environment (all three exports required, every shell)

```bash
source /u/msalunkhe/reprocli/.venv/bin/activate

export VLLM_BLOCKSCALE_FP8_GEMM_FLASHINFER=0   # FlashInfer blockscale FP8 GEMM off
export VLLM_ALLREDUCE_USE_SYMM_MEM=0           # no symmetric-memory (mnnvl) all-reduce
export VLLM_USE_FLASHINFER_SAMPLER=0           # FlashInfer sampler is fragile on this box
```

All three disable FlashInfer paths that crash on GH200 — same class as the
DeepSeek-V4-Flash runbook's `VLLM_USE_FLASHINFER_SAMPLER=0`.

## Serve (TP=2)

```bash
CUDA_VISIBLE_DEVICES=0,1 vllm serve /tmp/Langua-S-2.1 \
  --trust-remote-code \
  --served-model-name poolside/Laguna-S-2.1 \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.93 \
  --max-model-len 262144 \
  --kv-cache-dtype fp8 \
  --disable-custom-all-reduce \
  --compilation-config '{"pass_config":{"fuse_allreduce_rms":false}}' \
  --enable-auto-tool-choice \
  --tool-call-parser poolside_v1 \
  --reasoning-parser poolside_v1 \
  --host 0.0.0.0 --port 8000
```

- Weights load ~56.6 GiB/GPU, leaving ~33 GiB/GPU for KV; fp8 KV halves per-token
  cost (~6 GiB/GPU for a full 256K sequence), so several concurrent 256K
  transcripts fit. Startup: ~62s weight load + ~166s torch.compile.
- `--served-model-name poolside/Laguna-S-2.1` keeps the API model string stable
  regardless of the local dir name (`/tmp/Langua-S-2.1`).

## The wall this dodges: FlashInfer symm-mem all-reduce

Without the two all-reduce flags the server dies at the profiling run with a
misleading `CUBLAS_STATUS_EXECUTION_FAILED (cublasGemmEx ... CUDA_R_16BF)`. That
is async fallout, not the cause. The real crash is:

```
SymmMemCommunicator: symmetric memory multicast operations are not supported.
flashinfer_all_reduce: Auto-selected flashinfer allreduce backend: mnnvl
torch.AcceleratorError: CUDA error: an illegal memory access  (CUDASymmetricMemory dtor)
```

vLLM fused RMSNorm+all-reduce and let FlashInfer pick the `mnnvl` symmetric-memory
all-reduce, which this 2xGH200 topology cannot do. `--disable-custom-all-reduce`
+ `fuse_allreduce_rms:false` + `VLLM_ALLREDUCE_USE_SYMM_MEM=0` force plain NCCL
and remove the fused path. (Fast green/red check: add `--enforce-eager` to skip
compilation; if it serves eager, the compiled fusion was the culprit.)

## Harmless warnings — do NOT chase

`deep_gemm` / `libnvrtc.so.13` / `CXXABI_1.3.15` import failures are benign here.
Unlike GLM-5.2 / V4-Flash, Laguna has no DSA indexer, so vLLM falls back to
`TRITON Fp8 MoE backend` and serves fine without DeepGEMM. Ignore them.

## Sampling (per-request, brain client)

`generation_config.json`: temperature 1.0, top_p 1.0, **top_k 20**, thinking on,
EOS `[2, 24]`, max_new 32768. `top_k 20` is not an OpenAI param, so a plain
OpenAI-compatible client drops it silently and the model runs off-distribution —
plumb it through the repro client via `extra_body={"top_k": 20}` (same class as
the DSV4-Flash `chat_template_kwargs` plumbing).

## Benchmark (once /health binds)

```bash
# sweep-shaped agentic traffic (per-turn ttft/decode/cache-share):
python scripts/serve/bench_agent_sim.py \
  --base-url http://127.0.0.1:8000/v1 \
  --model poolside/Laguna-S-2.1 --agents 8 --turns 10

# stock random-prompt throughput:
vllm bench serve --base-url http://127.0.0.1:8000 \
  --model poolside/Laguna-S-2.1 --dataset-name random \
  --random-input-len 8192 --random-output-len 1024 \
  --num-prompts 64 --max-concurrency 8 --seed 42
```

Watch the cached% column climb toward 80-95% on the agent sim; a sag as
transcripts grow means the KV pool is evicting.

## Deferred: DFlash speculative decode (perf pass)

`generation_config.json` points at `poolside/Laguna-S-2.1-DFlash-FP8`, a 15-token
DFlash draft module. To enable, add:

```bash
  --speculative-config '{"model":"poolside/Laguna-S-2.1-DFlash-FP8","num_speculative_tokens":15}' \
  --moe-backend triton
```

Big decode win but forces the Triton MoE backend (not DeepGEMM). Measure it
against the no-DFlash baseline above before committing it to the sweep.
