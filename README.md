# reprocli

Utilities for running the NeurIPS paper-bundle artifact-availability prompt through vLLM and reviewing JSONL outputs.

## Run With Web Verification

The runner uses vLLM tool calling plus a local Python tool loop. Tool choices
are model-chosen. GitHub discovery and repository inspection use the GitHub MCP
server. Hugging Face discovery and repository details use the Hugging Face MCP
server. Direct URLs from papers or tool results can still be checked with
`fetch_url`.
The paper input is also augmented with artifact candidates from
`data/paperswithcode/arxiv_artifacts.jsonl` when present. These candidates come
from a Papers With Code arXiv-ID scrape and are treated as leads that still need
tool verification.
By default, the vLLM runner reads one-row-per-paper bundles from
`Mithilss/neurips-2025-paper-bundles`
(`https://huggingface.co/datasets/Mithilss/neurips-2025-paper-bundles`), which
include paper LaTeX plus OpenReview supplement manifests and excerpts.
By default it starts one local vLLM OpenAI server, reuses it for every tool round,
lets each paper advance through tool rounds as soon as its own response and tool
calls finish, then shuts the server down when the run finishes.
Raw responses, extracted rows, and optional trace rows are written as JSONL as
each paper fully completes, so output row order follows completion order rather
than dataset order.

```bash
python3 src/run_arxiv_prompt_vllm.py \
  --num-prompts 8 \
  --tool-rounds 10 \
  --max-input-tokens 128000 \
  --max-tokens 8192 \
  --pwc-artifacts /projects/bgnp/msalunkhe/paperswithcode_arxiv_artifacts.jsonl \
  --request-workers 8 \
  --stream-first-response \
  --dataset Mithilss/neurips-2025-paper-bundles \
  --model deepseek-ai/DeepSeek-V4-Flash \
  --model-profile deepseek_v4_flash \
  --reasoning-effort high \
  --vllm-cache-dir /projects/bgnp/msalunkhe/DeepSeek-V4-Flash/vllm_cache
```

`--num-prompts` samples that many papers at random. For a full run, omit it.

```bash
python src/run_arxiv_prompt_vllm.py
```

## Run With OpenAI Batch

The OpenAI runner submits `/v1/responses` requests through the OpenAI Batch API,
then downloads completed results back into the same raw and extracted JSONL
formats used by the rest of the repo.

```bash
OPENAI_API_KEY=... python3 src/run_arxiv_prompt_openai.py \
  --num-prompts 100 \
  --submit-only
```

To resume and download a completed batch:

```bash
OPENAI_API_KEY=... python3 src/run_arxiv_prompt_openai.py \
  --download
```

The submit command records pending batch ids in `outputs/*_batch_ids.jsonl`.
`--download` removes each completed or terminal batch id after saving its files;
still-running batches remain queued for the next run.
Batch requests also set a stable `prompt_cache_key` and `prompt_cache_retention`
of `24h` by default so repeated prompt prefixes can use OpenAI prompt caching.

Optional rate-limit helpers:

```bash
export GITHUB_TOKEN=...
export HF_TOKEN=...
```

The GitHub tools use the remote GitHub MCP server by default. To use another
server, set `GITHUB_MCP_URL` for streamable HTTP or `GITHUB_MCP_COMMAND` for a
local stdio server such as `github-mcp-server stdio`.
The Hugging Face tools use `https://huggingface.co/mcp` by default. To override
that, set `HF_MCP_URL` or `HF_MCP_COMMAND`.

## Papers With Code Artifacts

Scrape Papers With Code by arXiv ID and keep the joined artifact leads under
`data/`:

```bash
python3 src/scrape_paperswithcode_arxiv.py \
  --output data/paperswithcode/arxiv_artifacts.jsonl
```

Upload the scraped JSONL to Hugging Face:

```bash
python3 src/upload_paperswithcode_dataset.py \
  --input data/paperswithcode/arxiv_artifacts.jsonl \
  --repo-id Mithilss/neurips-2025-paperswithcode-artifacts
```

## Paper Bundles With OpenReview Supplements

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

Build a new Hugging Face-ready dataset with one row per `arxiv_id`, grouping
the paper `.tex` files and matched OpenReview supplementary files together.
After a successful build, this uploads to `Mithilss/neurips-2025-paper-bundles`
by default:

```bash
PYTHONPATH=src python3 -m reprocli_data.build_paper_bundle_dataset \
  --output-dir /projects/bgnp/msalunkhe/paper_bundle_dataset \
  --overwrite
```

The bundle columns include `paper_tex_files`, `paper_tex_text`,
`supplement_status`, and `supplement_files`. The builder batches paper rows
before writing Parquet; lower `--batch-size-mb` or `--batch-rows` if a shared
filesystem run is memory constrained. Pass `--no-upload` for a local-only build.

## Useful Flags

- `--tool-rounds 10`: maximum browse/execute/continue rounds before the final answer.
- `--max-input-tokens 128000`: cap prompt tokens so output has room in context.
- `--max-tokens 8192`: maximum generated tokens per model response.
- `--pwc-artifacts data/paperswithcode/arxiv_artifacts.jsonl`: adds
  Papers With Code GitHub, project-page, and Hugging Face candidate links.
- `--vllm-cache-dir`: sets `VLLM_CACHE_ROOT`; local model paths default to `<model>/vllm_cache`.
- `--request-workers 8`: number of concurrent request/tool pipelines.
- `--stream-first-response`: print one live response stream while preserving JSONL output.
- `--save-round-jsonl`: write one `*_trace.jsonl` file with the full message/tool history per paper.
- `--reasoning-effort high`: enables DeepSeek V4 Think High through chat-template kwargs.
- `--model-profile deepseek_v4_flash`: uses the DeepSeek V4 tokenizer, tool parser, reasoning parser, FP8 KV cache, TP=4, and FlashInfer autotune disabled.

## View JSONL Outputs

Start the local viewer:

```bash
python src/view_jsonl_conversations.py --port 8765
```

Open:

```text
http://127.0.0.1:8765
```

The viewer scans `data/` and `outputs/` for `.jsonl` files. It pairs final outputs, `*_trace.jsonl`, `*_extracted.jsonl`, request JSONL, and OpenAI batch input/result files by `custom_id`, then renders a ChatGPT-style transcript with reasoning blocks, tool calls, tool results, extracted JSON, and raw payloads.
