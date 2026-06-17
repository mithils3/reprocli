# Classification / audit runs (vLLM)

Run the agent core over paper bundles on vLLM. The runner launches through
`srun` inside a batch allocation, starts one local vLLM server (or attaches to an
existing one), drives the Python tool loop, and writes raw, extracted, and
optional trace JSONL rows as papers complete.

The active production path is `scripts/paper_classification.sbatch`. Use
`scripts/paper_classification_kimi_k2_6.sbatch` for `moonshotai/Kimi-K2.6` with
`kimi_k2` tool/reasoning parsers, 8-way tensor parallelism, trust-remote-code,
and `--mm-encoder-tp-mode data`.

## Tool surface

- GitHub MCP tools for repository, code, issue, pull request, commit, file, and
  tree evidence.
- Hugging Face MCP tools for Hub search, repository details, README/card
  evidence, and file trees.
- `fetch_url` for direct project, documentation, paper, dataset, and file URLs.
- `paper_bundle_file_contents` for text files listed in the current paper's
  bundled OpenReview supplement manifest.

## Canonical command (MiniMax M2)

```bash
python3 src/run_arxiv_prompt_vllm.py \
  --num-prompts 500 \
  --tool-rounds 12 \
  --max-input-tokens 128000 \
  --max-tokens 8192 \
  --request-workers 16 \
  --stream-first-response \
  --dataset Mithilss/neurips-2025-paper-bundles \
  --vllm-cache-dir /projects/bgnp/msalunkhe/MiniMax-M2.7/vllm_cache \
  --distributed-executor-backend mp \
  --output outputs/neurips_2025_minimax_m2_trial.jsonl \
  --extracted-output outputs/neurips_2025_minimax_m2_trial_extracted.jsonl \
  --save-round-jsonl \
  --max-model-len 196608 \
  --compilation-config '{"cudagraph_mode":"PIECEWISE"}'
```

## Kimi K2.6 trial

```bash
python3 src/run_arxiv_prompt_vllm.py \
  --model moonshotai/Kimi-K2.6 \
  --num-prompts 500 \
  --tool-rounds 12 \
  --max-input-tokens 128000 \
  --max-tokens 8192 \
  --request-workers 16 \
  --stream-first-response \
  --dataset Mithilss/neurips-2025-paper-bundles \
  --vllm-cache-dir /projects/bgnp/msalunkhe/Kimi-K2.6/vllm_cache \
  --distributed-executor-backend mp \
  --output outputs/neurips_2025_kimi_k2_6_trial.jsonl \
  --extracted-output outputs/neurips_2025_kimi_k2_6_trial_extracted.jsonl \
  --save-round-jsonl \
  --max-model-len 196608 \
  --tensor-parallel-size 8 \
  --tool-call-parser kimi_k2 \
  --reasoning-parser kimi_k2 \
  --mm-encoder-tp-mode data
```

## Attach to an already-running multi-node Kimi server

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

Use `--vllm-server-url` when a vLLM OpenAI-compatible server is already running
and the classifier should attach to it instead of launching its own local
server. If the server was launched without a served model alias, set `--model`
to the exact model name printed by vLLM at startup, such as
`/work/hdd/bfvr/msalunkhe/models/`.

Instead of the flag, you can export `REPROCLI_SERVER_URL=http://<ip>:8000` or
`REPROCLI_ENDPOINT_FILE=/path/to/vllm_endpoint.json` (the file published by the
`reprocli-serve` sibling repo); the runner resolves the URL from any of the
three, and falls back to its embedded local server when none is set. This is the
recommended path for standing up one shared server many nodes attach to — see the
[serving page](../docs/slurm/serve.md).

`--num-prompts` samples that many papers at random. Omit it to process the full
dataset.

## Credentials and MCP overrides

```bash
export GITHUB_TOKEN=...
export HF_TOKEN=...
```

The GitHub tools use the remote GitHub MCP server by default. To use another
server, set `GITHUB_MCP_URL` for streamable HTTP or `GITHUB_MCP_COMMAND` for a
local stdio server such as `github-mcp-server stdio`. The Hugging Face tools use
`https://huggingface.co/mcp` by default; override with `HF_MCP_URL` or
`HF_MCP_COMMAND`.
