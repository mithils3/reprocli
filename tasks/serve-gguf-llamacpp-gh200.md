# Serving GGUF models with llama.cpp on DeltaAI GH200

Runbook for standing up a large GGUF model as an OpenAI-compatible brain on a
4xGH200 node, and for sizing the quant to the hardware. Companion to the vLLM
path (`scripts/serve/serve_gh200.sbatch`, `src/reprocli_serve/profiles.py`),
which remains the default for safetensors models. Use llama.cpp only when a
model ships GGUF-first or is too large to serve in vLLM at acceptable precision.

Written 2026-07-15 from a DeepSeek-V4-Flash and GLM-5.2 bring-up. Numbers marked
MEASURED were observed on job 2659942 (gh046/gh047); everything else is arithmetic.

## 1. The hardware budget

    4x GH200, 97,871 MiB each  =  391,484 MiB  =  382 GiB HBM
    Grace LPDDR per node        =  --mem=440G (what we request)
    /tmp                        =  3.5 TB node-local NVMe (/dev/nvme0n1)

The single number that decides everything: **382 GiB of HBM**. HF publishes
quant sizes in decimal GB; divide by 1.0737 to compare against it.

## 2. Choosing the quant

Rule: **pick the largest quant whose weights fit in ~340 GiB**, leaving ~40 GiB
for KV cache and compute buffers. Do not plan on CPU offload to close a gap.

GLM-5.2 (`unsloth/GLM-5.2-GGUF`), the worked example:

| Quant      | Size   | GiB | Fits 382 GiB? | Verdict |
|------------|--------|-----|---------------|---------|
| UD-Q5_K_XL | 562 GB | 523 | no            | lossless tier, out of reach |
| UD-Q4_K_XL | 467 GB | 435 | no, -53 GiB   | lossless tier, needs offload — see §3 |
| UD-IQ4_XS  | 365 GB | 340 | yes, +42 GiB  | **the pick** |
| UD-IQ3_S   | 309 GB | 288 | yes           | fallback if KV pressure |

Unsloth's KL-divergence benchmarks call `UD-Q4_K_XL` and `UD-Q5_K_XL`
"generally lossless"; they publish no per-quant figure for `UD-IQ4_XS`, so its
quality cost is real but unquantified. Validate it (§7) rather than assume.

DeepSeek-V4-Flash (`unsloth/DeepSeek-V4-Flash-GGUF`) at UD-Q4_K_XL is 155 GB
(144 GiB) and fits trivially, even on 2 GPUs (194 GiB).

## 3. Why not to close the gap with CPU offload

The tempting move is `UD-Q4_K_XL` + `--n-cpu-moe`, spilling experts to Grace
over NVLink-C2C at ~900 GB/s. **It does not work well.** MEASURED on GLM-5.2,
same model, same node, offload vs none:

    UD-Q4_K_XL + -ot "ffn_down_exps.weight=CPU"   ~200 t/s prefill
    UD-IQ4_XS,  pure HBM, no offload              ~575 t/s prefill

A 2.9x prefill win from dropping to a smaller quant that fits. **Fit the quant
to HBM; do not offload to keep a bigger one.** This is the single most important
finding in this runbook.

Prefill batches 2048 tokens, which activates essentially all 256 experts per
layer, so every CPU-resident expert tensor gets computed on Grace. Decode only
touches 8 experts per token; prefill touches all of them. The bottleneck is
Grace's *compute*, not the C2C transfer — which is why the fast link does not
rescue it. A 79k-token prefill costs ~6.6 minutes.

Two further traps if you try anyway:

- **`--n-cpu-moe N` offloads the first N layers, but llama.cpp splits layers
  across GPUs evenly by count.** Cards holding non-offloaded layers get ~19
  layers of full experts (~113 GiB) and OOM. Raising N slides the failing device
  along (device 1 -> device 2) without fixing it. The tell is an *identical*
  allocation byte-count across different N.
- Spread the offload across all layers instead: `-ot "ffn_down_exps\.weight=CPU"`
  moves ~166 GB evenly. Balanced, but still prefill-bound per above.

## 4. Storage: never use node-local /tmp

`/tmp` is node-local XFS. A model downloaded on gh046 is invisible on gh047, and
gone when the allocation ends. This bit us three times in one session.

Use the shared NVMe already referenced by `scripts/serve/serve_gh200.sbatch:35`:

    /work/nvme/bfvr/msalunkhe/models/<model>/

Download once, reuse across allocations. Loading from shared storage is slower
than local NVMe but is paid once per job, not once per node.

    hf download unsloth/GLM-5.2-GGUF \
      --include "UD-IQ4_XS/*" \
      --local-dir /work/nvme/bfvr/msalunkhe/models/GLM-5.2-IQ4XS

Do NOT add `HF_XET_HIGH_PERFORMANCE=1`, `XET_NUM_CONCURRENT_RANGE_GETS`, or a
large `--max-workers`. MEASURED: plain defaults hit 1.33-2.7 GB/s; the tuned
combination self-congested to **5.6 MB/s** (18h ETA). `hf_transfer` is dead —
huggingface_hub v1.0+ ignores `HF_HUB_ENABLE_HF_TRANSFER`.

## 5. Building llama.cpp (aarch64 + CUDA)

No prebuilt aarch64 CUDA binaries exist; conda-forge lags. Build from source:

    git clone https://github.com/ggml-org/llama.cpp
    cd llama.cpp
    cmake -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CUDA_ARCHITECTURES="90"      # GH200/H100/H200
    cmake --build build --config Release -j$(nproc)

Builds `llama-server`, `llama-cli`, `llama-bench`, `llama-batched-bench` into
`build/bin/`. Needs `libcurl4-openssl-dev`, or pass `-DLLAMA_CURL=OFF` (we
download with `hf`, so `-hf` support is not needed).

`export PATH` does not survive a new allocation. Put it in `~/.bashrc`:

    echo 'export PATH="$HOME/llama.cpp/build/bin:$PATH"' >> ~/.bashrc

## 6. Launching

Minimal is correct. **Do not add flags speculatively** — a six-flag invocation
hung for 4+ minutes at 100% CPU with only 1.7 GB resident, while the same model
loaded in 5s without them. Suspects were `-sm layer` / `-ts 1,1` (`llama-bench`
failed with the same pair) and `--ctx-size`; never isolated.

    CUDA_VISIBLE_DEVICES=0,1,2,3 nohup llama-server \
      --model /work/nvme/bfvr/msalunkhe/models/GLM-5.2-IQ4XS/UD-IQ4_XS/GLM-5.2-UD-IQ4_XS-00001-of-00009.gguf \
      --alias GLM-5.2-IQ4_XS \
      -ngl 99 \
      -ctk q8_0 -ctv q8_0 \
      --reasoning-preserve \
      --ctx-size 131072 --parallel 1 \
      --cache-reuse 256 \
      --host 127.0.0.1 --port 8080 \
      > /tmp/glm-iq4.log 2>&1 &

Notes on each:

- Point at **shard 1 only**; llama.cpp finds the rest.
- `-ngl 99` puts everything on GPU. Omitting it lets llama.cpp's auto-fitter
  size the split to free VRAM — but the fitter **aborts** if you set `-ngl` or
  any tensor override (`common_fit_params: ... already set by user, abort`).
- **Do not** pass `--split-mode` / `--tensor-split`. llama.cpp already splits
  across all visible GPUs proportional to VRAM, which on 4 identical GH200s is
  the even split you would write by hand.
- `-ctk q8_0 -ctv q8_0` halves KV vs the f16 default, in HBM. Near-lossless.
  MLA-style models (GLM-5.2, DeepSeek-V4) may reject quantized KV — if the
  server dies with a KV-type error, drop these.
- `-nkvo/--no-kv-offload` puts KV in CPU RAM. Avoid: attention touches KV every
  token at every layer, so this reintroduces the §3 bottleneck.
- `--reasoning-preserve` keeps reasoning traces across turns when the chat
  template supports it. The server tells you at startup: `chat template supports
  preserving reasoning, consider enabling it via --reasoning-preserve`. Take the
  hint for any reasoning model used as an agent brain — reasoning models degrade
  when prior reasoning is stripped between turns. Costs context: traces stay in
  the transcript, so budget for it. Watch for the message on every new model.
- `--cache-reuse 256` salvages KV via shifting when a prompt diverges mid-stream
  (what happens when an agent's transcript is edited, not just appended).
- Prompt caching (`--cache-prompt`) is **on by default**. Agent transcripts are
  append-only, so turn 2+ hits the prefix cache and prefills only the delta.

Expected warnings, all benign:

    Lightning Indexer not supported, set to disabled
      -> DSA sparse attention has no CUDA kernel; falls back to dense. Correct
         but forfeits the long-context speedup. Applies to glm-dsa + deepseek_v4.
    model has unused tensor blk.78.*  -> the NextN/MTP speculative module, ~6 GB
                                        downloaded and never used.
    special_eot_id is not in special_eog_ids -> cosmetic unless generation never
                                                stops; then fix with --override-kv.

## 7. Verifying the quant

Two checks, in order. Fluency survives quant damage long after arithmetic dies,
so check 1 alone is not enough.

    curl -s localhost:8080/v1/chat/completions -H 'Content-Type: application/json' -d '{
      "messages":[{"role":"user","content":"Name the capital of Australia and explain in one sentence why it is not Sydney."}],
      "max_tokens":512, "temperature":1.0, "top_p":1.0}' | jq -r '.choices[0].message.content'
    # want: Canberra, Sydney/Melbourne compromise, 1908

    curl -s localhost:8080/v1/chat/completions -H 'Content-Type: application/json' -d '{
      "messages":[{"role":"user","content":"Write an iterative Python function for the nth Fibonacci number, then state the exact value of fib(30)."}],
      "max_tokens":1024, "temperature":1.0, "top_p":1.0}' | jq -r '.choices[0].message.content'
    # want: fib(30) = 832040

## 8. Benchmarking

`llama-batched-bench` gives the cleanest comparable table (`llama-bench` failed
to load sharded GGUFs in our runs; batched-bench did not):

    CUDA_VISIBLE_DEVICES=0,1,2,3 llama-batched-bench \
      -m <shard-1> -ngl 99 -c 32768 -npp 512 -ntg 128 -npl 1,2,4,8

MEASURED, DeepSeek-V4-Flash UD-Q4_K_XL on 2xGH200, pure HBM:

    B   PP t/s    TG t/s   total t/s
    1   951.5     30.6     135.4
    2  1074.8     35.7     157.6
    4  1086.9     63.9     258.7
    8  1107.6    105.1     380.8

Prefill saturates by B=2; decode scales 3.4x from B=1 to B=8. Use this as the
reference for any new model on this hardware.

MEASURED, GLM-5.2 UD-IQ4_XS on 4xGH200, pure HBM, q8_0 KV, `--parallel 1`:

    prefill   ~575 t/s at 35k ctx, degrading to ~536 t/s by 41k (attention cost)
    decode    ~40 t/s (B=1)
    HBM       80 / 91 / 91 / 85 GiB = ~347 GiB of 382
    GPU util  ~48% average

**Decode is FASTER than DeepSeek-V4-Flash (40 vs 30.6 t/s) despite 2.4x the
weights.** Decode speed tracks *active* params and memory bandwidth, not total
size: GLM-5.2 activates 8 of 256 experts per token. Do not assume a bigger MoE
decodes slower — measure. (Caveat: DeepSeek was benchmarked on 2 GPUs, GLM-5.2
on 4, so this is not a controlled comparison.)

### Why GPU utilization is ~48%, and why that is expected

`--split-mode layer` (the default) is **pipeline parallelism, not tensor
parallelism**. Layers are dealt out sequentially across GPUs, a token flows
through them in order, and only one GPU computes at a time while the rest wait
on activations. `nvitop` shows 100/0/100/0 catching the handoff. Memory
bandwidth at ~11% confirms it: decode should be HBM-bound, so 11% means waiting,
not reading.

Levers, in order of expected value:

- `--parallel N` + concurrent requests. Batching fills the pipeline bubbles.
  This is why DeepSeek's aggregate scaled 3.4x to B=8 while per-stream decode
  barely moved. If sweeps run several agents at once, low per-GPU util is
  irrelevant — aggregate is what you bill.
- `-sm row` shards tensors so all GPUs work every layer. Trades communication
  for parallelism; does not always win. Measure.
- Accept it. llama.cpp is not a tensor-parallel engine. `serve_gh200.sbatch`'s
  vLLM path does real TP and would use this hardware better — llama.cpp is the
  right tool only when GGUF is the only checkpoint that fits.

For a **realistic agentic profile** (~80-90k input, cached prefix), size the KV:
`-c` must cover `npl * (npp + ntg)`, so 90k x 2 sequences needs `-c 200000`.

    -c 200000 -npp 90000 -ntg 1024 -npl 1,2

But note `-npp 90000` measures a **cold** prefill, which a real agent pays once
per run. Turn 2+ hits the prompt cache. To measure that, POST the same prefix
twice with `cache_prompt:true` and compare `.timings.prompt_n` — it should
collapse from ~79k to a few hundred. That second number is what an agent turn
actually costs.

## 9. Adding a future model

1. **Size it (§2).** Get exact bytes from
   `https://huggingface.co/api/models/<repo>/tree/main/<QUANT>` — do not trust
   the model card's rounded table. Pick the largest quant under ~340 GiB.
2. **Read the arch config** (`num_hidden_layers`, `n_routed_experts`,
   `num_experts_per_tok`, `first_k_dense_replace`, `moe_intermediate_size`) from
   `https://huggingface.co/<base-repo>/raw/main/config.json`. Per-layer expert
   bytes at 4-bit ~= `n_experts * 3 * hidden * moe_intermediate * 0.5625`. This
   is how you predict fit and offload sizing before downloading 400 GB.
3. **Download to `/work/nvme/...`** (§4), plain flags.
4. **Launch minimal** (§6), add flags only with a measured reason.
5. **Verify** (§7), then **benchmark** (§8) against the DeepSeek table.
6. Check for a `Lightning Indexer`-style kernel gap — new architectures often
   run correct-but-dense in llama.cpp for months after release.

### sbatch template

Adapt `scripts/serve/serve_gh200.sbatch`. The llama.cpp path is much simpler
than the vLLM one — no profile, no parsers, no compilation config:

    #SBATCH -J reprocli_serve_gguf
    #SBATCH -A betw-dtai-gh
    #SBATCH -p ghx4
    #SBATCH --nodes=1
    #SBATCH --ntasks=1
    #SBATCH --cpus-per-task=64
    #SBATCH --gpus-per-node=4        # 4, not 2: 340 GiB needs all four
    #SBATCH --gpu-bind=none
    #SBATCH --mem=440G
    #SBATCH --time=24:00:00
    #SBATCH -o slurm-serve-gguf-%j.out

    set -euo pipefail
    export PATH="$HOME/llama.cpp/build/bin:$PATH"
    MODEL_DIR=/work/nvme/bfvr/msalunkhe/models/GLM-5.2-IQ4XS
    SHARD=$MODEL_DIR/UD-IQ4_XS/GLM-5.2-UD-IQ4_XS-00001-of-00009.gguf
    ENDPOINT_FILE=/work/nvme/bfvr/msalunkhe/endpoints/glm52.json

    llama-server --model "$SHARD" --alias GLM-5.2 \
      -ngl 99 -ctk q8_0 -ctv q8_0 --reasoning-preserve \
      --ctx-size 131072 --parallel 8 --cache-reuse 256 \
      --host 0.0.0.0 --port 8080 &

    # publish the endpoint the way serve_gh200.sbatch does, so consumers on other
    # nodes can find it: bind 0.0.0.0, discover a routable hsn0..hsn3 fabric IP,
    # write {"base_url": "http://<hsn-ip>:8080/v1"} once /health is green.

Differences from the vLLM sbatch that matter:

- `--gpus-per-node=4` (the vLLM MiniMax profile uses 2).
- `--mem=440G` — needed only if you offload; 220G is fine for pure-HBM serving.
- No `module load python` / venv — `llama-server` is a static-ish binary.
- None of the NCCL/torch env block applies; llama.cpp does its own multi-GPU.
- `--parallel N` sets concurrent slots (vLLM's `--max-num-seqs`). Context is
  split N ways, and **the prompt cache is per-slot** — concurrent agents sharing
  a slot evict each other's prefix. Match N to concurrent conversations.
- `--host 0.0.0.0` to be reachable off-node; `127.0.0.1` only for local tests.

## 10. Open items

- Decode t/s under expert offload was never measured (we cancelled at 36%
  prefill). If someone revisits offload, that is the missing number — though §3
  makes the case moot.
- `-sm row` was never measured against the default layer split. If single-stream
  decode matters more than aggregate, that is the first thing to try.
- No batched/concurrent numbers for GLM-5.2 — only `--parallel 1`. Run
  `llama-batched-bench -npl 1,2,4,8` to get the aggregate curve that actually
  matters for sweeps.
- Quant validation (§7) not run against UD-IQ4_XS. Its quality delta vs the
  "lossless" UD-Q4_K_XL remains unquantified.
- The 6-flag server hang (§6) was never root-caused. If it recurs, bisect:
  `--ctx-size` first, then `--flash-attn`, then `-sm`/`-ts`.
- llama.cpp is not wired into `reprocli_serve`. Today it is a manual endpoint;
  a consumer points at `http://<host>:8080/v1`. If GGUF serving becomes routine,
  a `Profile`-equivalent belongs in `src/reprocli_serve/`.
