# reprocli

Utilities for running the NeurIPS arXiv artifact-availability prompt through vLLM and reviewing JSONL outputs.

## Run With Web Verification

The runner uses vLLM tool calling plus a local Python tool loop. Search uses DuckDuckGo HTML, so no Brave/Tavily key is required. GitHub and Hugging Face checks use their public APIs.
By default it starts one local vLLM OpenAI server, reuses it for every tool round,
lets each paper advance through tool rounds as soon as its own response and tool
calls finish, then shuts the server down when the run finishes.

```bash
python3 src/run_arxiv_prompt_vllm.py \
  --num-prompts 1 \
  --tool-rounds 4 \
  --max-input-tokens 128000 \
  --max-tokens 32768 \
  --no-compile \
  --enforce-eager \
  --request-workers 10 \
  --stream-first-response \
  --dataset /projects/bgnp/msalunkhe/datasets \
  --model /projects/bgnp/msalunkhe/MiniMax-M2.7
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

If you already started vLLM on the node, reuse it instead of starting a second
server:

```bash
python3 src/run_arxiv_prompt_vllm.py \
  --vllm-server-url http://127.0.0.1:8000 \
  --tool-rounds 4
```

## Quick One-Shot Test

Use this when you only want to test prompt formatting or vLLM startup, without web tools.

```bash
python src/run_arxiv_prompt_vllm.py \
  --num-prompts 1 \
  --tool-rounds 0 \
  --no-compile \
  --enforce-eager
```

## Useful Flags

- `--tool-rounds 4`: maximum browse/execute/continue rounds before the final answer.
- `--max-input-tokens 128000`: cap prompt tokens so output has room in context.
- `--max-tokens 32768`: maximum generated tokens per model response.
- `--batch-backend server`: default; start or reuse one persistent vLLM server.
- `--batch-backend run-batch`: old behavior; starts a new vLLM batch process per round.
- `--vllm-server-url`: use an already-running OpenAI-compatible vLLM server.
- `--request-workers 10`: number of concurrent request/tool pipelines for server mode.
- `--stream-first-response`: print one live response stream while preserving JSONL output.
- `--first-tool-choice required`: forces the first model pass to call a verification tool.
- `--tool-timeout 20`: timeout for each HTTP request made by a tool.
- `--tool-max-chars 8000`: cap each tool result before feeding it back to the model.
- `--no-compile`: passes vLLM compilation mode 0 for faster debug startup.
- `--enforce-eager`: disables CUDAGraphs as well; useful for smoke tests.
- `--disable-web-tools`: old one-shot behavior with no tools attached.

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
