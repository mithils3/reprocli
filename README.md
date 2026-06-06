# reprocli

Utilities for running the NeurIPS paper-bundle artifact-availability prompt
through MiniMax M2 on vLLM.

## Run Classification

The active production path is `scripts/paper_classification.sbatch`. The runner
starts one local vLLM server, drives a Python tool loop, and writes raw,
extracted, and optional trace JSONL rows as papers complete.

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
  --output outputs/neurips_2025_minimax_m2_trial.jsonl \
  --extracted-output outputs/neurips_2025_minimax_m2_trial_extracted.jsonl \
  --save-round-jsonl \
  --max-model-len 196608
```

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

## Paper Bundles

Download and extract OpenReview supplementary material for papers present in the
arXiv source dataset:

```bash
PYTHONPATH=src python3 -m reprocli_data.download_openreview_supplements \
  --dataset Mithilss/neurips-2025-arxiv-latex-sources \
  --output-dir /projects/bgnp/msalunkhe/openreview_supplements \
  --workers 16 \
  --delay 0.75 \
  --allow-failures
```

Build a Hugging Face-ready dataset with one row per `arxiv_id`, grouping the
paper `.tex` files and matched OpenReview supplementary files together. After a
successful build, this uploads to `Mithilss/neurips-2025-paper-bundles` by
default:

```bash
PYTHONPATH=src python3 -m reprocli_data.build_paper_bundle_dataset \
  --output-dir /projects/bgnp/msalunkhe/paper_bundle_dataset \
  --overwrite
```

The bundle columns include `paper_tex_files`, `paper_tex_text`,
`supplement_status`, and `supplement_files`. The builder batches paper rows
before writing Parquet; lower `--batch-size-mb` or `--batch-rows` if a shared
filesystem run is memory constrained. Pass `--no-upload` for a local-only build.

## arXiv Sources

The bundle builder starts from the arXiv-source corpus. To rebuild that corpus:

```bash
PYTHONPATH=src python3 -m reprocli_data.download_arxiv_sources
PYTHONPATH=src python3 -m reprocli_data.build_arxiv_sources_parquet
```

## Useful Flags

- `--tool-rounds 12`: maximum tool-use rounds before the final answer.
- `--max-input-tokens 128000`: cap prompt tokens so output has room in context.
- `--max-tokens 8192`: maximum generated tokens per model response.
- `--request-workers 16`: number of concurrent request/tool pipelines.
- `--stream-first-response`: print one live response stream while preserving JSONL output.
- `--save-round-jsonl`: write one `*_trace.jsonl` file with the full message/tool history per paper.
- `--vllm-cache-dir`: sets `VLLM_CACHE_ROOT`; local model paths default to `<model>/vllm_cache`.
