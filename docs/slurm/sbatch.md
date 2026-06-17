# Batch jobs (`scripts/*.sbatch`)

The three SLURM batch scripts in `scripts/` are thin launchers: each sets the same DeltaAI environment block, activates the project venv, then calls the one entry point `src/run_arxiv_prompt_vllm.py` with a different flag set. The Python process embeds its own vLLM server (`vllm/server.py`) and drives the [tool loop](../agent-core/tool-loop.md) over the [paper bundles](../dataset/index.md) — there is no separate `srun` server step inside these scripts. See [Clusters & accounts](clusters.md) for the account/partition table and the `salloc`→`srun` pattern the (designed) reproduction agent uses.

!!! note "One runner, three invocations"
    All three scripts run `python3 src/run_arxiv_prompt_vllm.py …`. What differs is the model, the toolset, the mode, and the I/O paths — the loop body, guardrails, and structured-output finalization are shared (see [architecture](../architecture.md), Part II).

## The shared header

Every script opens with an identical block. The SLURM directives differ only in job name, CPU/GPU/mem/time, and output-file prefix (next section); the env block below is byte-for-byte the same in all three.

| concern | what the header does |
|---|---|
| `set -euo pipefail` | fail fast on any error or unset var |
| caches | `TORCHINDUCTOR_CACHE_DIR`, `TRITON_CACHE_DIR`, `VLLM_CACHE_ROOT` → `/projects/bgnp/msalunkhe/.cache/{torchinductor,triton,vllm}` |
| single-host vLLM | `MASTER_ADDR=127.0.0.1`, `VLLM_HOST_IP=127.0.0.1` |
| NCCL / Torch tuning | `NCCL_CUMEM_ENABLE=0`, `NCCL_NET_PLUGIN` (default `none`), `OMP_NUM_THREADS=1`, `TORCH_NCCL_*` async-error / heartbeat (`1200s`) |
| `PYTHONPATH` | prepends `/u/msalunkhe/reprocli/src` |
| toolchain | `module load python/3.11.9`; `source /u/msalunkhe/reprocli/.venv/bin/activate`; `cd /u/msalunkhe/reprocli/` |
| compiler probe | sets `CXX`/`TORCHINDUCTOR_CXX` to `g++`/`c++` when SLURM leaves `CXX=CC` |
| diagnostics | echoes host + GPU vars, dumps the `CUDA|NCCL|VLLM|SLURM|…` env, runs `nvidia-smi topo -m` |

!!! tip "These paths are operator-specific"
    The header hard-codes one operator's NCSA paths (`/u/msalunkhe/…`, `/projects/bgnp/msalunkhe/…`). Treat the scripts as a template: the env tuning is reusable, the absolute paths are not.

## SLURM directives at a glance

All three target DeltaAI: account `betw-dtai-gh`, partition `ghx4`, one node, `--gpu-bind=none`, `--export=ALL`, and email to `mithils3@illinois.edu` on `BEGIN,END,FAIL`. They diverge on size and walltime:

| script | job name | `--cpus-per-task` | `--gpus-per-node` | `--mem` | `--time` | log prefix |
|---|---|---|---|---|---|---|
| `paper_classification.sbatch` | `reprocli_paper_classification` | 16 | 4 | 256G | 48:00:00 | `slurm-%j` |
| `paper_classification_kimi_k2_6.sbatch` | `reprocli_kimi_k2_6` | 32 | 8 | 512G | 12:00:00 | `slurm-kimi-k2-6-%j` |
| `paper_verification.sbatch` | `reprocli_paper_verification` | 16 | 4 | 256G | 4:00:00 | `slurm-verify-%j` |

The Kimi job is the heavy one — 8 GPUs and 512G — because the model runs at tensor-parallel 8 (below). The other two fit MiniMax on 4 GPUs.

## ✅ `paper_classification.sbatch` — the MiniMax classifier

The stage-1 dataset-construction pass: read each NeurIPS bundle, verify its artifacts via the web/MCP toolset, and emit one MRE record per paper. Uses the default model (`DEFAULT_MODEL = MINIMAX_M2_MODEL`, so `--model` is omitted), which routes through `apply_minimax_profile` in `config/minimax_defaults.py` (TP 4, `minimax_m2` parsers, `trust_remote_code=True`, `temperature=1.0/top_p=0.95/top_k=40`).

Salient flags:

```bash
python3 src/run_arxiv_prompt_vllm.py \
  --tool-rounds 12 \
  --max-input-tokens 128000 --max-tokens 8192 \
  --request-workers 32 \
  --stream-first-response \
  --dataset Mithilss/neurips-2025-paper-bundles \
  --vllm-cache-dir /projects/bgnp/msalunkhe/MiniMax-M2.7/vllm_cache \
  --distributed-executor-backend mp \
  --output outputs/neurips_2025_minimax_m2_trial.jsonl \
  --extracted-output outputs/neurips_2025_minimax_m2_trial_extracted.jsonl \
  --save-round-jsonl \
  --max-model-len 196608 \
  --compilation-config '{"mode":3,"pass_config":{"fuse_minimax_qk_norm":true}}' \
  --hf-repo Mithilss/neurips-2025-results
```

| flag | effect |
|---|---|
| (no `--mode`) | defaults to `classification` (`config/cli_args.py`); loads bundle papers with `tex_files`, prompt template `prompts/prompt.txt`, `{PAPER_TEXT}` placeholder |
| (no `--num-prompts`) | runs the **full** dataset (`select_papers` returns all papers) |
| `--request-workers 32` | up to 32 episodes in flight against the embedded server |
| `--compilation-config` | explicit override of the per-model default (`{"cudagraph_mode":"PIECEWISE"}`); enables the `fuse_minimax_qk_norm` pass |
| `--hf-repo` | incremental + final upload of run outputs to the Hub (`hf_run_uploader`) |

The classifier's tools, schema, and post-processing are documented on [the classifier page](../modes/classifier.md).

## ✅ `paper_classification_kimi_k2_6.sbatch` — Kimi K2.6 classifier

Same classification job, swapped onto Moonshot **Kimi K2.6** on 8 GPUs. Passing `--model` to a local Kimi checkpoint makes `apply_model_defaults` route through `apply_kimi_defaults` (`config/minimax_defaults.py`): TP 8, the `kimi_k2` tool-call + reasoning parsers, `mm_encoder_tp_mode="data"`, and `trust_remote_code=True`. The script also sets several of these explicitly so the intent is legible:

```bash
python3 src/run_arxiv_prompt_vllm.py \
  --model /work/hdd/bfvr/msalunkhe/models/ \
  --num-prompts 500 \
  --tool-rounds 12 \
  --max-input-tokens 128000 --max-tokens 8192 \
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
  --tool-call-parser kimi_k2 --reasoning-parser kimi_k2 \
  --mm-encoder-tp-mode data
```

| difference vs. MiniMax | why |
|---|---|
| `--model /work/hdd/bfvr/msalunkhe/models/` | local Kimi K2.6 checkpoint; `is_kimi_k2_6` detects it via path suffix or `config.json` `architectures` (`KimiK25…`) |
| `--tensor-parallel-size 8` | the model is sharded across all 8 GPUs (`--gpus-per-node=8`) |
| `--tool-call-parser kimi_k2` / `--reasoning-parser kimi_k2` | Kimi's native tool-call and reasoning grammars |
| `--mm-encoder-tp-mode data` | multimodal-encoder TP placement Kimi expects (forwarded to vLLM verbatim) |
| `--num-prompts 500` | random subset of 500 papers (`random.sample`), not the full set |
| `--request-workers 16` | half the MiniMax concurrency — the 8-way model is heavier per request |
| no `--compilation-config` | Kimi runs without the MiniMax fusion pass |

!!! note "`trust-remote-code` is a default, not a flag here"
    Neither classifier script passes `--trust-remote-code` on the command line. `apply_minimax_profile` / `apply_kimi_defaults` set `args.trust_remote_code = True`, and `VllmServer.__enter__` appends `--trust-remote-code` to the vLLM command when that attribute is truthy. Both model families load with remote code enabled.

## 🚧 `paper_verification.sbatch` — stale audit-pass launcher

This script was the launcher for an earlier **deterministic verification-target curator** (`--mode verification`, MRE-only, tools-off — one schema-forced generation per paper from its MRE record, no bundle and no tool loop). Its in-file comment still describes that design.

!!! warning "This script is out of date — do not run it as-is"
    The verification mode it invokes was **removed** when the curator was replaced by the LLM reproduction auditor (commit `f98dc43`, "Replace deterministic verification curator with LLM reproduction auditor"). The current runner does **not** accept the flags this script passes:

    - `--mode verification` — `config/cli_args.py` now only allows `choices=("classification", "audit")`.
    - `--mre-records hf://…/audit_pool_extracted.jsonl` — no such argument exists; the auditor reads claims via `--claims` instead.
    - `--prompt-file prompt_verification.txt` — that prompt file was deleted (the live audit prompt is `prompts/prompt_audit.txt`).

    Running it today fails at `parse_args`. The audit pass it represents is now the **auditor mode** (`--mode audit`), documented on [the auditor page](../modes/auditor.md).

The audit pass it stood in for is now driven like this (a corrected, minimal invocation — verify exact paths against `config/cli_args.py` defaults before use):

```bash
python3 src/run_arxiv_prompt_vllm.py \
  --mode audit \
  --claims hf://datasets/Mithilss/neurips-2025-audit-pool/audit_pool_extracted.jsonl \
  --runs-dir <runs-dir> \
  --output outputs/v5/audit.jsonl \
  --extracted-output outputs/v5/audit_extracted.jsonl
```

`--mode audit` reads each paper's `central_claim` from the audit pool plus the agent's run directory at `<runs-dir>/<arxiv_id>` with read-only run-dir tools, and grades 0–5 against `rubric_audit.md` ([run-dir tools](../tools/run-dir-tools.md), [auditor](../modes/auditor.md)). The SLURM header and walltime in the stale script (4h, 4 GPUs, 256G) are still a reasonable shape for an audit pass; only the Python invocation needs to be rewritten.

## How the runner launches vLLM and drives the loop

None of these scripts starts vLLM with `srun`. The Python entry point launches the server **inside the same job step** as a subprocess and then loops in-process:

```mermaid
flowchart TD
  S["sbatch step (1 node, N GPUs)"] --> R["run_arxiv_prompt_vllm.main()"]
  R --> P["parse_args → apply_model_defaults<br/>resolve_mode_settings (prompt/tools/schema)"]
  P --> L["load papers + build prompts"]
  L --> V["VllmServer.__enter__()<br/>subprocess: vllm.entrypoints.openai.api_server<br/>--tensor-parallel-size --tool-call-parser …<br/>poll /health until ready"]
  V --> T["run_tool_loop(args, papers, prompts, base_url)<br/>HTTP /v1/chat/completions · tool rounds · forced JSON"]
  T --> O["write raw + extracted jsonl<br/>optional HF upload"]
  V -.->|__exit__ terminates server| O
```

Concretely (`run_arxiv_prompt_vllm.py`):

1. `parse_args()` applies the per-model profile and `resolve_mode_settings` (mode picks prompt, tools, output schema).
2. Papers/prompts are loaded — bundle LaTeX for classification, claim + run dir for audit.
3. Unless `--vllm-server-url` is given, `with VllmServer(args) as server_url:` spawns `python -m vllm.entrypoints.openai.api_server` on `127.0.0.1:<free-port>` with `--enable-auto-tool-choice` and the resolved TP / parser / `--max-model-len` / `--mm-encoder-tp-mode` / `--trust-remote-code` flags, then polls `/health` until ready (`vllm/server.py`).
4. `run_tool_loop(...)` drives episodes over the OpenAI-compatible endpoint (`runtime/tool_loop.py`); the server is stateless, so all conversation memory lives in the orchestrator.
5. On exit, `VllmServer.__exit__` terminates the subprocess; rows are flushed and, if `--hf-repo` is set, uploaded.

!!! note "Attaching to an external server"
    These scripts always use the embedded server. The same runner can attach to an already-running multi-node vLLM via `--vllm-server-url` (e.g. the interactive Kimi serving in `scripts/kimi_k2_6_multinode_interactive.md`); see [architecture](../architecture.md) II.4 and [Clusters & accounts](clusters.md).

## See also

- [Clusters & accounts](clusters.md) — account/partition table, `salloc`→`srun` allocation pattern.
- [Classifier mode](../modes/classifier.md) · [Auditor mode](../modes/auditor.md) — what each pass actually computes.
- [The tool loop](../agent-core/tool-loop.md) — the shared agent core these jobs invoke.
- [Run a paper](../cli/run-arxiv.md) — the `run_arxiv_prompt_vllm.py` CLI in full.
