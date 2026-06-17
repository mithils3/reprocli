# Reproduction agent (S6) — implementation plan

Implements **Part III** of [`architecture.md`](architecture.md): the missing
consumer that takes one lockfile row and *actually runs the experiment* on the
cluster under a metered H100-hour budget, emitting the run bundle the auditor
grades.

**Design decisions locked in for this plan:**

- The reproduction agent lives in its **own package and directory**
  (`src/reprocli_repro/`), with its own entry point, CLI, and tool loop.
- **No changes to `reprocli_vllm`** — no `--mode reproduce`, no edit to the
  shared `tool_loop.py`. The classifier/auditor stay untouched.
- The package **imports only stable, mode-agnostic primitives** from
  `reprocli_vllm`; it forks the small loop body on purpose.
- **One paper end-to-end is the driving milestone** (M1 local → M2 audited →
  M3 on real GPU).

---

## What is reused vs. what is new

**Imported (not duplicated)** from `reprocli_vllm`, all mode-agnostic:

- `vllm.client.post_chat_completion_row`, `response_row`
- `vllm.io`: `build_chat_completion_request`, `initial_messages`,
  `normalize_tool_calls`, `response_message`, `tool_result_message`,
  `append_jsonl_row`, `truncate_output_file`
- `runtime.loop_guards` (`repeated_tool_call`, `record_tool_call`,
  `context_budget_exceeded`)
- `runtime.trace_io` (`assistant_message`, `append_trace_row`)
- `runtime.run_health.loop_telemetry`
- `config.config.function_tool` (the tool-schema builder)
- `vllm.server.VllmServer` (only if ever self-hosting the brain)

**New (forked on purpose):**

- The loop body's `append_tool_results` — repro dispatches to repro tools with a
  mutable per-episode **ExecutionContext** (workspace + budget + allocation)
  instead of `execute_tool_call(call, paper=paper)`.
- The **budget guardrail** (bounds *compute*, not tokens/rounds).
- The **post-loop re-execution** that writes the verdict the agent cannot.

---

## Phases

### Phase 0 — Stand up the separate package
- `src/reprocli_repro/__init__.py`, `__main__.py` (`python -m reprocli_repro`),
  `cli_args.py` (its own argparse — not `resolve_mode_settings`).
- `loop.py`: `run_reproduce_loop(...)` — copies the *structure* of
  `run_tool_loop` (two `ThreadPoolExecutor`s, `wait(FIRST_COMPLETED)`,
  `handle_request_done`) but with repro's `append_tool_results(call, ctx)` and
  the budget guardrail. Imports the vLLM client/io primitives.
- `context.py`: `ExecutionContext{arxiv_id, lockfile_row, workspace, budget,
  allocation, evidence}` — per-episode state keyed by `custom_id`, replacing
  `paper=paper`.

**Gate:** `python -m reprocli_repro --help` works; `reprocli_vllm` tests green.

### Phase 1 — Lockfile row → one-paper episode input
- `inputs.py`: load `audit_pool_extracted.jsonl`, select rows; build the opening
  prompt from `agent_task · central_claim · mre_config · match_bar · tier · band
  · budget_h100_hours`.
- `--paper-id <arxiv_id>` (single-paper first-class) plus `--num-prompts` later.
- `prompts/prompt_reproduce.txt` with placeholders; resolve workspace/run-dir
  to `<runs-dir>/<arxiv_id>/<budget>h/<run_id>/` — **the S6→S7 contract the
  existing auditor reads.**

**Gate:** one lockfile row → fully-rendered prompt, no unfilled placeholders.

### Phase 2 — Workspace + reference + evidence (CPU, `--executor local`)
- `workspace.py`: per-paper workspace, `git clone` at pinned commit, **per-paper
  `uv` venv** (never the shared `.venv`).
- `reference.py`: materialize a **read-only `reference/` dir** for the paper from
  the HF bundle row (`Mithilss/neurips-2025-paper-bundles`) — `reference/paper/`
  (LaTeX from `paper_tex_files`) and `reference/supplement/` (every supplement
  file). **Write from `content` bytes, not `text`/`is_text`** — the builder only
  fills `text` for a narrow extension set (`.py` is excluded), but `content`
  holds the raw bytes for every file. No network: bytes come straight from the
  bundle. Emits a `reference/MANIFEST.txt`. This is the agent's reference copy of
  the paper + supplement, separate from the editable code clone.
- `evidence.py`: `commands.log`, `trajectory.jsonl`, `env.lock`, `patches/`.
- `tools/files.py` + `tools/workspace_bash.py`: cwd-confined shell +
  `read_file`/`write_file`/`apply_patch` (path-confinement adapted from
  `run_dir_tools._resolve_within`); `reference/` is readable but not writable.

**Gate (offline):** one paper's repo clones, venv builds, `reference/` is
materialized with paper LaTeX + all supplement files (incl. `.py` from `content`
bytes), an edit applies, evidence files written, path-escape rejected.

Bundle facts (verified): public HF dataset, 136 shards, ~3,400 papers; each row
carries `paper_tex_text`/`paper_tex_files` and `supplement_files[*].content`
(raw bytes for binary + text). The local `data/paper_bundle_dataset` parquet is a
stale older schema — pull from HF.

### Phase 3 — Budget meter + SLURM substrate
- `budget.py`: `hw_multiplier` table (R9), `consume()`, `remaining()` — pure.
- `slurm.py`: `srun --jobid=$ALLOC … bash -lc 'cd <ws> && <cmd>'`; **assume a
  pre-held allocation** via `--allocation-jobid` (decouple orchestration from
  GPU). `--executor {local,srun}`.
- Budget guardrail in `loop.py`: `run_gpu` refuses at `remaining() <= 0`;
  exhaustion sets `exit_reason="budget_exhausted"` and force-finals (same
  mechanism as `repeated_call_cutoff`).

**Gate:** budget math tests (GH200 vs H200 both in H100-equiv); local-executor
loop spends fake budget and force-finals at zero.

### Phase 4 — Toolset assembled → **Milestone M1: 1 paper through the loop (local)**
- `tools/run_gpu.py`: wraps `slurm`/local, meters `gpus × wallclock ×
  hw_multiplier`, per-step timeout + remaining-budget enforcement, appends
  trajectory row.
- `tools/__init__.py`: `REPRO_TOOLS` + handler dispatch wired into `loop.py`.

**Gate / M1:** `python -m reprocli_repro --paper-id <id> --executor local`
drives the chosen paper: clone → edit → "run GPU" → spend budget → stop, with a
populated evidence dir.

### Phase 5 — Submission contract + harness re-execution → `result.json`
- `write_repro_yaml` + `submit` tools (final structured output is the *contract*,
  not a verdict).
- `report/reexecute.py`: after the loop, one fresh `srun`/local step runs
  `repro.yaml`'s scoring entrypoint clean, parses the metric, applies the
  lockfile `match_bar`, writes `result.json {status, measured, within_tolerance,
  budget_at_first_pass, integrity.flags}`. Orchestrated in `__main__`, **after**
  the loop — the loop stays verdict-free.

**Gate:** the four statuses produce correct `result.json` on a fake scoring
script; an agent claim contradicting the measurement becomes an `integrity.flag`.

### Phase 6 — Bundle → **Milestone M2: auditor grades the 1-paper bundle**
- `report/schema.py` + `report/validate.py`; write `result.json · report.json ·
  repro.yaml · evidence/` to `<runs-dir>/<arxiv_id>`.

**Gate / M2:** run the **existing** `reprocli_vllm` auditor (`--mode audit
--runs-dir <same root>`) over the one paper's bundle — grades with zero changes.

### Phase 7 — **Milestone M3: same paper on real GPU (`--executor srun`)**
- `scripts/paper_reproduce.sbatch` (+ DeltaAI variant): hold the allocation,
  standard env block, attach the brain via `--vllm-server-url`, run
  `--executor srun --allocation-jobid $SLURM_JOB_ID --paper-id <id>`.

**Gate / M3:** the one paper reproduced end-to-end on the cluster; budget meter
stops it; auditor grades the real bundle.

### Phase 8 — Hardening (post-M3)
Sandboxing `run_gpu`/`workspace_bash` before untrusted code at scale;
`invalid_run` retry into a fresh `<run_id>`; agent-owned `salloc` (v1 assumes a
pre-held allocation).

---

## Module layout (self-contained, all under the 300-line rule)

```
src/reprocli_repro/
  __init__.py · __main__.py · cli_args.py
  loop.py · context.py · inputs.py · budget.py · slurm.py · workspace.py · reference.py · evidence.py
  tools/__init__.py · tools/workspace_bash.py · tools/run_gpu.py · tools/files.py
  report/schema.py · report/validate.py · report/reexecute.py
prompts/prompt_reproduce.txt · scripts/paper_reproduce.sbatch
```

The only thing repro borrows from `reprocli_vllm` is import-level primitives;
behavior, CLI, and the loop are its own. The path to first signal is **M1**
(Phase 0→4, all offline on one paper).
</content>
</invoke>
