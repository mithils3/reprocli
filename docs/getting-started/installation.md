# Installation

ReproBench (`reprocli`) is a source checkout, not a packaged install: there is no
`pyproject.toml` or `setup.py`. You create a Python environment, install the
deps in `requirements.txt`, and run the entry points with `PYTHONPATH=src` so the
`reprocli_repro`, `reprocli_vllm`, `reprocli_serve`, `reprocli_data`, and
`reprocli_openai` packages resolve. This page covers the environment, the
dependency set (including the vLLM nightly extra index), and the environment
variables the tool layer reads.

!!! note "What needs a GPU"
    The reproduction (`reprocli_repro`) and auditor (`run_arxiv_prompt_vllm.py
    --mode audit`) agents are **URL-only brains**: they attach to a vLLM
    chat-completions server you stand up with `reprocli_serve` and never launch a
    model themselves. Serving the brain needs CUDA GPUs; the reproduction agent's
    orchestrator and the auditor themselves are CPU work (the reproduction agent's
    `run_gpu` tool JIT-allocates GH200s only for the experiment steps). See
    [the architecture overview](../architecture.md) for the split and
    [Quickstart](quickstart.md) for first commands.

## 1. Python environment

The cluster jobs target **Python 3.11** (`module load python/3.11.9` in
`scripts/**/*.sbatch`). Create an isolated environment with `uv`:

```bash
# from the repo root
uv venv --python 3.11 .venv
source .venv/bin/activate
```

!!! tip "uv is the project standard"
    The reproduction agent (`reprocli_repro`) provisions a **per-paper `uv` venv**
    rather than a shared one, per [the architecture doc](../architecture.md).
    Using `uv` here keeps the local dev environment consistent with that intent.
    Plain `python -m venv` + `pip` works too.

## 2. Install dependencies

All runtime deps live in `requirements.txt`:

```text
--extra-index-url https://wheels.vllm.ai/nightly

datasets
huggingface_hub
openreview-py
vllm
```

Install them:

```bash
uv pip install -r requirements.txt
```

!!! warning "The vLLM nightly extra index is load-bearing"
    The first line, `--extra-index-url https://wheels.vllm.ai/nightly`, pins
    `vllm` to the **nightly wheel channel**. The Kimi K2.6 / MiniMax M2 paths use
    parsers and flags (`kimi_k2` tool/reasoning parsers,
    `--mm-encoder-tp-mode data`) that may not be in a stable vLLM release. Keep
    the `--extra-index-url` line when you reinstall, or `pip` will resolve `vllm`
    from PyPI and you may get an older build.

| Package | Why it is needed |
|---|---|
| `vllm` | the OpenAI-compatible model server stood up by `reprocli_serve` |
| `datasets` | loads the lockfile / paper-bundle datasets and writes/reads JSONL results |
| `huggingface_hub` | model, lockfile, and paper-bundle downloads |
| `openreview-py` | dataset build only — fetches OpenReview supplements |

## 3. Run with `PYTHONPATH=src`

There is no install step that puts the packages on `sys.path`, so every
invocation prepends `src/`. The three live entry points are the reproduction
agent (`python -m reprocli_repro`), the auditor
(`src/run_arxiv_prompt_vllm.py --mode audit`, its only mode), and the model
server (`python -m reprocli_serve`); `scripts/**/*.sbatch` set
`export PYTHONPATH=.../reprocli/src` for exactly this.

```bash
# reproduction agent (S6)
PYTHONPATH=src python3 -m reprocli_repro --help

# auditor (S7) — audit is the only mode
PYTHONPATH=src python3 src/run_arxiv_prompt_vllm.py --help

# model server the two brains attach to
PYTHONPATH=src python3 -m reprocli_serve --help

# dataset builder (module form)
PYTHONPATH=src python3 -m reprocli_data.build_dataset --help
```

The default model is `MiniMaxAI/MiniMax-M2.7` (`DEFAULT_MODEL` in
`config/config.py`). See [`run-arxiv`](../cli/run-arxiv.md) and
[`build-dataset`](../cli/build-dataset.md) for the full flag sets, and
[Quickstart](quickstart.md) for ready-to-run commands.

!!! example "Attach the auditor to an existing server"
    ```bash
    PYTHONPATH=src python3 src/run_arxiv_prompt_vllm.py --mode audit \
      --vllm-server-url "http://${HEAD_IP}:8000" \
      --runs-dir /work/nvme/bfvr/msalunkhe/reprocli/agent_runs
    ```
    With no `--vllm-server-url` (and no `$REPROCLI_SERVER_URL` /
    `$REPROCLI_ENDPOINT_FILE`) the runner exits with an error — it does not
    self-host a model (`vllm/endpoint.py`).

## 4. Credentials & environment variables

Neither agent needs GitHub or Hugging Face MCP credentials — the auditor explores
a run directory with path-confined run-dir tools, and the reproduction agent works
in its own workspace. The variables that matter:

### Endpoint resolution (both brains)

Both the reproduction agent and the auditor resolve their vLLM endpoint from, in
order, `--vllm-server-url`, then `$REPROCLI_SERVER_URL`, then the JSON file named
by `$REPROCLI_ENDPOINT_FILE` (published by `reprocli_serve`); with none set they
error out (`vllm/endpoint.py`). The served model name comes from
`--served-model-name` / `$REPROCLI_SERVED_MODEL`, else the id the server
advertises. A hosted OpenAI-compatible endpoint (e.g. OpenRouter) is authenticated
with `$REPROCLI_API_KEY` / `$OPENROUTER_API_KEY` (and `$REPROCLI_OPENROUTER_PROVIDER`
to pin a provider).

### Environment variable reference

| Variable | Purpose | Default |
|---|---|---|
| `REPROCLI_SERVER_URL` | Base URL of the served brain (used when `--vllm-server-url` is omitted) | _unset_ |
| `REPROCLI_ENDPOINT_FILE` | Path to the endpoint JSON `reprocli_serve` publishes | _unset_ |
| `REPROCLI_SERVED_MODEL` | Model id to send in requests when attached to a server | _unset_ (server-advertised id) |
| `REPROCLI_API_KEY` / `OPENROUTER_API_KEY` | Bearer token for a hosted OpenAI-compatible endpoint | _unset_ |
| `HF_TOKEN` | Hugging Face token for pulling the lockfile / paper-bundle datasets (and the dataset builder's `upload` stage) | _unset_ (public reads work anonymously) |
| `REPRO_WORK_ROOT` | Root of the reproduction agent's run bundles + outputs (NVMe scratch) | `/work/nvme/bfvr/msalunkhe/reprocli` |
| `REPRO_APPTAINER_SIF` | Base `.sif` backing the mandatory Apptainer sandbox for `run_gpu` steps | the `deltaai` profile default |
| `OPENREVIEW_USERNAME` / `OPENREVIEW_PASSWORD` | OpenReview login for the dataset builder's supplement stage | _unset_ (anonymous) |
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` | Optional: push audit verdicts + run stats to Supabase (`reprocli_repro.audit_upload`) | _unset_ (upload skipped) |

## Next steps

- [Quickstart](quickstart.md) — first reproduction and audit runs.
- [Concepts](concepts.md) — the lockfile and the agent roles.
- [Serving (reprocli_serve)](../slurm/serve.md) — stand up the brain both agents attach to.
- [SLURM clusters](../slurm/clusters.md) and [sbatch](../slurm/sbatch.md) — running on DeltaAI.
