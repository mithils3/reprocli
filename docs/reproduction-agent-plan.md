# Reproduction agent (S6) — historical design document

!!! note "Superseded by the implementation"
    This page was the phase-by-phase construction roadmap for the S6 reproduction
    agent. That agent has since been **built** (its design shifted in the building),
    so this roadmap is kept only as a historical record. For how the reproduction
    agent actually works today, read **[the architecture overview](architecture.md)**
    and **[the reproduction mode page](modes/reproduction.md)**.

## What shipped

The reproduction agent is a live surface — `python -m reprocli_repro` — living in
its own package (`src/reprocli_repro/`). Given one lockfile row it runs that paper's
experiment on the cluster under a metered H100-hour budget and writes the run bundle
the auditor grades. The pieces that shipped:

- A **forked tool loop** (`loop.py`) — the `run_tool_loop` skeleton reimplemented
  with its own driver, per-episode `ExecutionContext`, and dispatch, importing only
  mode-agnostic primitives from `reprocli_vllm`.
- A **URL-only brain**: the agent's reasoning runs on an already-served
  OpenAI-compatible endpoint resolved from `--vllm-server-url` /
  `$REPROCLI_SERVER_URL` / `$REPROCLI_ENDPOINT_FILE` (published by
  [`reprocli_serve`](slurm/serve.md)). It never self-hosts a model.
- A **compute-budget meter** (`budget.py`) that bounds H100-equivalent hours, plus
  **summarize-compact** context management (`summarize.py`).
- **JIT SLURM GPU steps** (`slurm.py`): every `run_gpu` call opens one fresh
  `salloc`, runs the command inside a **mandatory Apptainer sandbox** (`sandbox.py`),
  and releases the allocation the instant the step exits. **DeltaAI is the only
  cluster profile** (`cluster.py`).
- A **run bundle** (`workspace/` · `reference/` · `evidence/` · `report.json`) that
  is the S6→S7 contract the existing auditor reads with no auditor changes. The
  agent writes an account of its run, never a verdict — the auditor renders the
  verdict.

See [`architecture.md`](architecture.md) for the current, authoritative description.
