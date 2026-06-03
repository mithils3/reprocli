# reprocli

Utilities for running the NeurIPS arXiv artifact-availability prompt through vLLM and reviewing JSONL outputs.

## Run With Web Verification

The runner uses vLLM tool calling plus a local Python tool loop. The first tool
round searches GitHub for candidate code repositories. Promising candidates are
then verified with the GitHub repository tool, which uses the public GitHub API
and includes root README text when available. Hugging Face verification uses
the public Hugging Face API.
By default it starts one local vLLM OpenAI server, reuses it for every tool round,
lets each paper advance through tool rounds as soon as its own response and tool
calls finish, then shuts the server down when the run finishes.

```bash
python3 src/run_arxiv_prompt_vllm.py \
  --num-prompts 8 \
  --tool-rounds 10 \
  --max-input-tokens 128000 \
  --max-tokens 8192 \
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
python src/run_arxiv_prompt_vllm.py
```

Optional rate-limit helpers:

```bash
export GITHUB_TOKEN=...
export HF_TOKEN=...
```

## Useful Flags

- `--tool-rounds 10`: maximum browse/execute/continue rounds before the final answer.
- `--max-input-tokens 128000`: cap prompt tokens so output has room in context.
- `--max-tokens 8192`: maximum generated tokens per model response.
- `--vllm-cache-dir`: sets `VLLM_CACHE_ROOT`; local model paths default to `<model>/vllm_cache`.
- `--request-workers 8`: number of concurrent request/tool pipelines.
- `--stream-first-response`: print one live response stream while preserving JSONL output.
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

The viewer scans `data/` and `outputs/` for `.jsonl` files. If a response file and matching `*_requests.jsonl` are both present, it pairs them by `custom_id`.
