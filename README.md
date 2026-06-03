# reprocli

Utilities for running the NeurIPS arXiv artifact-availability prompt through vLLM and reviewing JSONL outputs.

## Run With Web Verification

The runner uses vLLM tool calling plus a local Python tool loop. Search uses DuckDuckGo HTML, so no Brave/Tavily key is required. GitHub and Hugging Face checks use their public APIs.
By default it starts one local vLLM OpenAI server, reuses it for every tool round,
lets each paper advance through tool rounds as soon as its own response and tool
calls finish, then shuts the server down when the run finishes.

```bash
python3 src/run_arxiv_prompt_vllm.py \
  --num-prompts 8 \
  --tool-rounds 8 \
  --max-input-tokens 128000 \
  --max-tokens 32768 \
  --request-workers 8 \
  --stream-first-response \
  --dataset /projects/bgnp/msalunkhe/datasets \
  --model /projects/bgnp/msalunkhe/MiniMax-M2.7 \
  --vllm-cache-dir /projects/bgnp/msalunkhe/MiniMax-M2.7/vllm_cache \
  --trust-remote-code \
  --compilation-config '{"mode":3,"pass_config":{"fuse_minimax_qk_norm":true}}'
```

For a larger run, omit `--num-prompts`.

```bash
python src/run_arxiv_prompt_vllm.py --tool-rounds 4
```

Optional rate-limit helpers:

```bash
export GITHUB_TOKEN=...
export HF_TOKEN=...
```

## Useful Flags

- `--tool-rounds 4`: maximum browse/execute/continue rounds before the final answer.
- `--max-input-tokens 128000`: cap prompt tokens so output has room in context.
- `--max-tokens 32768`: maximum generated tokens per model response.
- `--vllm-cache-dir`: sets `VLLM_CACHE_ROOT`; local model paths default to `<model>/vllm_cache`.
- `--request-workers 8`: number of concurrent request/tool pipelines.
- `--stream-first-response`: print one live response stream while preserving JSONL output.
- `--trust-remote-code`: pass through to vLLM for MiniMax.
- `--compilation-config`: pass the vLLM compilation JSON directly.

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
