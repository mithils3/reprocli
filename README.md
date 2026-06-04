# reprocli

Utilities for running the NeurIPS arXiv artifact-availability prompt through
DeepSeek on vLLM and reviewing JSONL outputs.

## Setup

Install the Python environment used by your cluster or local vLLM setup, then run
commands from the repository root. The package-style data scripts expect
`PYTHONPATH=src` unless the project is installed as a package.

```bash
export PYTHONPATH=src
export GITHUB_TOKEN=...
export HF_TOKEN=...
```

The GitHub tools use the remote GitHub MCP server by default. To use another
server, set `GITHUB_MCP_URL` for streamable HTTP or `GITHUB_MCP_COMMAND` for a
local stdio server such as `github-mcp-server stdio`. Set
`GITHUB_MCP_TOOLSETS` if you want a different GitHub MCP toolset list.

The Hugging Face tools use `https://huggingface.co/mcp` by default. To override
that, set `HF_MCP_URL` or `HF_MCP_COMMAND`.

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
By default it starts one local vLLM OpenAI server, reuses it for every tool round,
lets each paper advance through tool rounds as soon as its own response and tool
calls finish, then shuts the server down when the run finishes.

```bash
PYTHONPATH=src python3 src/run_arxiv_prompt_vllm.py \
  --num-prompts 8 \
  --tool-rounds 10 \
  --max-input-tokens 128000 \
  --max-tokens 8192 \
  --pwc-artifacts Mithilss/neurips-2025-paperswithcode-artifacts \
  --request-workers 8 \
  --stream-first-response \
  --dataset /projects/bgnp/msalunkhe/datasets \
  --model deepseek-ai/DeepSeek-V4-Flash \
  --model-profile deepseek_v4_flash \
  --reasoning-effort high \
  --vllm-cache-dir /projects/bgnp/msalunkhe/DeepSeek-V4-Flash/vllm_cache
```

For a larger run, omit `--num-prompts`.

```bash
PYTHONPATH=src python3 src/run_arxiv_prompt_vllm.py
```

## Tool Behavior

Tool choice is automatic. The model is not forced to call a particular tool
first, but it must verify artifact claims before final JSON.

GitHub repository, code, issue, pull request, commit, tree, and file inspection
go through the GitHub MCP server. GitHub code search supports quoted phrases,
`OR`, `NOT`, and search qualifiers, with a 256-character query limit. The prompt
therefore allows compact GitHub code-search batching when it fits, and otherwise
asks for separate alias searches. Promising repos should be checked with
`github_repo`, then README/docs/config/script files should be read with
`github_file_contents`.

Hugging Face models, datasets, Spaces, papers, Hub search, and repo details go
through the Hugging Face MCP server. HF search is treated as semantic or
natural-language search, so the prompt does not assume boolean `OR` semantics.

## Papers With Code Artifacts

Scrape Papers With Code by arXiv ID and keep the joined artifact leads under
`data/`:

```bash
PYTHONPATH=src python3 -m reprocli_data.scrape_paperswithcode_arxiv \
  --output data/paperswithcode/arxiv_artifacts.jsonl
```

Upload the scraped JSONL to Hugging Face:

```bash
PYTHONPATH=src python3 -m reprocli_data.upload_paperswithcode_dataset \
  --input data/paperswithcode/arxiv_artifacts.jsonl \
  --repo-id Mithilss/neurips-2025-paperswithcode-artifacts
```

Other data utilities live under `src/reprocli_data/`:

```bash
PYTHONPATH=src python3 -m reprocli_data.fetch_neurips_2025_arxiv
PYTHONPATH=src python3 -m reprocli_data.download_arxiv_sources
PYTHONPATH=src python3 -m reprocli_data.build_arxiv_sources_parquet
```

## Useful Flags

- `--tool-rounds 10`: maximum browse/execute/continue rounds before the final answer.
- `--max-input-tokens 128000`: cap prompt tokens so output has room in context.
- `--max-tokens 8192`: maximum generated tokens per model response.
- `--pwc-artifacts data/paperswithcode/arxiv_artifacts.jsonl`: adds
  Papers With Code GitHub, project-page, and Hugging Face candidate links.
- `--vllm-cache-dir`: sets `VLLM_CACHE_ROOT`; local model paths default to `<model>/vllm_cache`.
- `--request-workers 8`: number of concurrent request/tool pipelines.
- `--stream-first-response`: print one live response stream while preserving JSONL output.
- `--reasoning-effort high`: enables DeepSeek V4 Think High through chat-template kwargs.
- `--model-profile deepseek_v4_flash`: uses the DeepSeek V4 tokenizer, tool parser, reasoning parser, FP8 KV cache, TP=4, and FlashInfer autotune disabled.

## View JSONL Outputs

Start the local viewer:

```bash
PYTHONPATH=src python3 src/view_jsonl_conversations.py --port 8765
```

Open:

```text
http://127.0.0.1:8765
```

The viewer scans `data/` and `outputs/` for `.jsonl` files. If a response file and matching `*_requests.jsonl` are both present, it pairs them by `custom_id`.
