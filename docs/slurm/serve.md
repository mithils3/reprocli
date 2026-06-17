# Serving: the central vLLM server (`reprocli_serve`)

reprocli splits into two halves that couple only through a published URL:

- the **CC half** — the provider-agnostic agent brains (classifier, auditor,
  reproduction). Like Codex, Claude Code, or opencode, they run no model
  themselves; they only POST chat-completions to a base URL (see
  [the reproduction agent's note](../modes/reproduction.md#tools-the-reproduction-agent-gets)
  and [the agent core](../architecture.md#part-ii-the-single-agent-core)).
- the **serving half** — `src/reprocli_serve/`. It boots a vLLM server on a GPU
  node, binds `0.0.0.0`, discovers the routable fabric IP, and publishes the URL
  so any other Delta / DeltaAI node can attach.

Both live in this repo but stay decoupled: `reprocli_serve` must not import the
agent packages, and the agents reach it only by URL. That is the same split the
[clusters page](clusters.md) describes (serving is a GPU allocation; the agent
loop is cheap CPU work) made concrete: **one server, many consumers, provider
swap = URL change.**

## Stand up the server

On DeltaAI (1× 4×GH200 node, tensor-parallel 4), from the repo root:

```bash
sbatch scripts/serve_gh200.sbatch          # MiniMax-M2.7, publishes endpoint JSON
# multi-node (Kimi-K2.6, TP=4 + PP=N):
sbatch --nodes=2 scripts/serve_multinode.sbatch
```

The launcher writes `vllm_endpoint.json` (to a shared path) once `/health` is
green, and removes it on exit:

```json
{ "base_url": "http://141.142.249.0:8000", "served_model_name": "MiniMaxAI/MiniMax-M2.7", ... }
```

## Attach a consumer (three equivalent ways)

The runner resolves its endpoint in this order, falling back to the **embedded**
local server if none is set (so default behavior is unchanged):

| how | what to set |
|---|---|
| explicit flag | `--vllm-server-url http://<ip>:8000` |
| env URL | `export REPROCLI_SERVER_URL=http://<ip>:8000` |
| env file | `export REPROCLI_ENDPOINT_FILE=/.../vllm_endpoint.json` |

```bash
python3 src/run_arxiv_prompt_vllm.py \
  --vllm-server-url "$(jq -r .base_url /projects/bgnp/msalunkhe/endpoints/minimax_m2.json)" \
  --model MiniMaxAI/MiniMax-M2.7 --num-prompts 2
```

The resolver lives in `reprocli_vllm/vllm/endpoint.py` (CC half); the publish side
is `reprocli_serve/endpoint.py` (serving half). The two halves couple **only**
through this JSON contract — neither imports the other.

## Dataset production with the serve paradigm

`scripts/paper_classification.sbatch` runs the stage-1 classifier on a single node
this way: step 1 starts the central server, step 2 attaches the runner by URL.
The dataset outputs are unchanged from the older embedded-server form; the only
difference is that the model is now a swappable service rather than a process
bolted into the runner (so changing providers is a server-step / URL change).

## DeltaAI networking notes

From the [NCSA DeltaAI docs](https://docs.ncsa.illinois.edu/systems/deltaai/en/latest/user-guide/architecture.html):

- **4 GH200 GPUs/node** → `--tensor-parallel-size 4` fits one node.
- **HPE/Cray Slingshot 11**, four NICs per node: interfaces `hsn0`–`hsn3`. The
  launcher publishes the first `hsn` with an IP (preferring `hsn0`); for
  multi-node NCCL data use the prefix `NCCL_SOCKET_IFNAME=hsn` (all four).
- Partitions: `ghx4` (48 h) and `ghx4-interactive` (≤4 nodes, 2 h).
- An empty fabric-interface name makes `ip addr show` pick loopback and publishes
  `127.0.0.1` — reachable only from the serving node. The launcher refuses to
  publish loopback for exactly this reason.
