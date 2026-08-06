# Serve DeepSeek-V4-Flash via vLLM on GH200 (DeltaAI)

Verified working 2026-07-16 on 2x GH200 (one ghx4 node, TP=2), vLLM 0.25.1,
checkpoint `deepseek-ai/DeepSeek-V4-Flash` (158B MoE, 13B active, released
natively INT8/FP8, 149 GiB). This IS the lossless config: the unsloth GGUFs
re-quantize this same checkpoint, so there is no reason to use them with vLLM
(whose GGUF loader rejects deepseek* architectures anyway, vllm#13665).

**2026-08-01: sweeps now serve `deepseek-ai/DeepSeek-V4-Flash-0731`**, the
official release that supersedes this preview checkpoint. Everything below still
applies as written (identical `config.json` apart from the DSpark fields,
identical tokenizer, same required exports and flags); swap the model id. Deltas
worth knowing, none of them re-verified on hardware yet:

- Weights grow 148.6 -> 155.4 GiB, so TP=2 puts ~78 GiB on each 96 GB GPU
  instead of ~74 and GPU KV gets that much thinner. If startup fails for want of
  KV blocks, go TP=4 on the full node. The Hub's "158B" (preview) vs "304B"
  (0731) is a counting basis, not a size change: the preview counts fp4 experts
  as the bytes they pack into (141.7B x 2 = the card's 284B logical), 0731 counts
  them logically, and the gap is exactly 12.88B = the DSpark module. Bytes are
  the real footprint.
- 0731 ships a DSpark speculative-decoding module in the same checkpoint,
  enabled with `--speculative-config '{"method":"dspark","num_speculative_tokens":7}'`
  on a vLLM build that registers the method. We leave it off.
- The reasoning-effort ladder was re-cut. In `encoding/encoding_dsv4.py`, 0731's
  `high` is the prompt the preview attached to `max`, and `max` is a new,
  stronger one. `reasoning_effort: "max"` is still the top rung, now more verbose.
- The card adds a `top_p = 0.95` recommendation for agentic scenarios (1.0
  otherwise). Both sweep loops are agentic, so both run 0.95: the auditor via
  `--top-p`, the repro agent via `REPROCLI_TOP_P` (which is otherwise unset, so
  every other brain still defers to its `generation_config`). Preview sweeps ran
  1.0, so sampling is a confound when comparing across the swap.

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
Max is also load-bearing for the ladder: at High Effort the model scores 37,
tying Qwen3.6-27B exactly; Max (+3 -> 40) is what makes it a distinct rung.

Effort is per-request, not a serve flag — the brain client sends:

```python
extra_body={"chat_template_kwargs": {"thinking": True, "reasoning_effort": "max"}}
```

- Plumbed via `REPROCLI_CHAT_TEMPLATE_KWARGS`, pinned in each dsv4 sbatch's
  `CHAT_TEMPLATE_KWARGS_DEFAULT`; the client's `apply_chat_template_kwargs`
  rides it onto every request and never clobbers a per-request override.
- Sampling: temperature 1.0, top_p 0.95 (0731's agentic recommendation; both
  loops here are agentic). The preview's flat 1.0 is a confound across the swap.
- Needs max-model-len >= 393216; the profile's 1M satisfies it with room to spare.
- Budget: Max measured 2.5x average verbosity on the AA index (230M vs 92M
  tokens); size round budgets and wall-clock caps accordingly.

### Max is what fed the 2883229 context deaths — the ceiling is the fix, not the rung

V4's encoder does not drop prior-turn reasoning while tools are in the request
(`encoding_dsv4.py`: `effective_drop_thinking = False` when any message carries
tools), so every round's chain of thought is re-rendered into the next prompt
with no turn-age limit. Under Max's 2.5x verbosity that replay measured 49-72%
of the old 128K input ceiling (median 61%), and 16 of the 27 scored runs in
sweep 2883229 died on `context_budget` — against 1 of 34 for Qwen3.6 and 3 of 34
for MiniMax-M2.7 on the same easy papers. `compact.py` cannot help: it elides
only `role:"tool"` contents and keeps assistant turns verbatim by design, so the
one model whose context is majority reasoning is the one compaction cannot reach.

Effort was briefly dropped to `high` on 2026-08-06 and reverted the same day.
Max stays. The ceiling is what changed: the profile serves the checkpoint's full
1M and the repro agent reads its input ceiling off `/v1/models`, so runs now get
roughly 8x the headroom those deaths happened in.

**If `context_budget` still bites at 1M, the next lever is dropping prior-turn
reasoning from the replay, not lowering the rung.** `conversation_for_round`
(`src/reprocli_repro/transcript.py`) is already the request-only view, so the
full CoT would still reach the logs. Note that this deviates from DeepSeek's
intended agentic format — V4-Flash is designed to see its own reasoning history
in tool loops — so it is a benchmark-design decision, not a silent bug fix.
The same change is already wanted for Laguna (`serve-laguna-s21-vllm-gh200.md`).

**Cross-model caveat:** the `qwen3_27b` and `minimax_m2` sbatches set no thinking
or reasoning kwargs at all, so those brains run their checkpoint defaults while
this one is pinned to its top rung. Effort is matched across every dsv4 sweep but
NOT across the roster, so a DeepSeek-vs-Qwen capability claim carries an unmatched
effort setting on top of the parameter-count gap.

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
