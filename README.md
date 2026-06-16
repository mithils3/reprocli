# reprocli

Utilities for running the NeurIPS paper-bundle artifact-availability prompt
through MiniMax M2 or Kimi K2.6 on vLLM.

## Run Classification

The active production path is `scripts/paper_classification.sbatch`. The runner
launches through `srun` inside the batch allocation, starts one local vLLM
server, drives a Python tool loop, and writes raw, extracted, and optional trace
JSONL rows as papers complete.

Use `scripts/paper_classification_kimi_k2_6.sbatch` to try
`moonshotai/Kimi-K2.6` with `kimi_k2` tool/reasoning parsers, 8-way tensor
parallelism, trust-remote-code, and `--mm-encoder-tp-mode data`.
Use `--vllm-server-url` when a vLLM OpenAI-compatible server is already running
and the classifier should attach to it instead of launching its own local
server.

The tool surface is:

- GitHub MCP tools for repository, code, issue, pull request, commit, file, and
  tree evidence.
- Hugging Face MCP tools for Hub search, repository details, README/card
  evidence, and file trees.
- `fetch_url` for direct project, documentation, paper, dataset, and file URLs.
- `paper_bundle_file_contents` for text files listed in the current paper's
  bundled OpenReview supplement manifest.

Canonical command:

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

Kimi K2.6 trial command:

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

Attach to an already-running multi-node Kimi server:

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

If the server was launched without a served model alias, set `--model` to the
exact model name printed by vLLM at startup, such as
`/work/hdd/bfvr/msalunkhe/models/`.

`--num-prompts` samples that many papers at random. Omit it to process the full
dataset.

Optional credentials and MCP overrides:

```bash
export GITHUB_TOKEN=...
export HF_TOKEN=...
```

The GitHub tools use the remote GitHub MCP server by default. To use another
server, set `GITHUB_MCP_URL` for streamable HTTP or `GITHUB_MCP_COMMAND` for a
local stdio server such as `github-mcp-server stdio`.
The Hugging Face tools use `https://huggingface.co/mcp` by default. To override
that, set `HF_MCP_URL` or `HF_MCP_COMMAND`.

## Dataset Pipeline

One command builds the paper-bundle dataset end to end: arXiv ids and titles
come pre-matched from the
[`ai-conferences/NeurIPS2025`](https://huggingface.co/datasets/ai-conferences/NeurIPS2025)
dataset (papers without an arxiv id are dropped — no fuzzy title matching),
arXiv e-print sources and OpenReview supplements are downloaded, and a
one-row-per-paper Parquet dataset is written:

```bash
PYTHONPATH=src python3 -m reprocli_data.build_dataset --data-dir data --workers 8
```

Smoke test (5 papers into a scratch dir):

```bash
PYTHONPATH=src python3 -m reprocli_data.build_dataset \
  --limit 5 --data-dir data/smoke --workers 2 --allow-failures
```

Stages run in order `index,sources,supplements,bundle[,upload]` and are
resume-friendly (already-downloaded papers are skipped). Use `--stages` to run
a subset, `--force` to refetch/replace, and `--upload` to push the bundle to
`Mithilss/neurips-2025-paper-bundles`:

```bash
PYTHONPATH=src python3 -m reprocli_data.build_dataset --stages bundle --force
PYTHONPATH=src python3 -m reprocli_data.build_dataset --stages upload
```

Once sources and supplements are downloaded, rebuild the Parquet bundle and
push it to the Hub in one step (replaces any existing bundle output):

```bash
PYTHONPATH=src python3 -m reprocli_data.publish_bundle --data-dir data
```

Supplements are matched to OpenReview notes by the forum id from `paper_url`
(never by title). Optional env vars: `OPENREVIEW_USERNAME`/`OPENREVIEW_PASSWORD`
for OpenReview, `HF_TOKEN` for upload.

Bundle columns: `arxiv_id`, `title`, `openreview_id`, `arxiv_id_source`,
`paper_source_url`, `paper_status`, `paper_tex_files`, `paper_tex_text`,
`supplement_source_url`, `supplement_status`, `supplement_files`. The builder
batches paper rows before writing Parquet; lower `--batch-size-mb` or
`--batch-rows` if a shared filesystem run is memory constrained.

The intermediate file-level dataset (`Mithilss/neurips-2025-arxiv-latex-sources`)
is no longer produced; bundles are built directly from the extracted source
directories under `<data-dir>/arxiv_sources/`.

## Useful Flags

