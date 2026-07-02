# Repository layout & conventions

This page is the map for contributors and future agents: where each piece of ReproBench lives and the rules that keep it that way. The repo is organized around the [system architecture](../architecture.md) — a lockfile that a reproduction agent and an auditor read, with the model served separately — so the package boundaries follow those surfaces, not arbitrary feature folders. Read this before adding a module; it tells you which package something belongs in and which file it should *not* outgrow.

## The one rule that shapes every file

!!! warning "300-line hand-written source limit"
    From `CLAUDE.md` and `AGENTS.md`:

    - Keep hand-written source files **under 300 lines**; `*.txt` and `*.md` files may exceed 300 lines.
    - Split code into focused modules **before** a file crosses that limit.
    - Generated data, paper text dumps, binary artifacts, and model outputs are **exempt**.

This is why every package is a set of small subpackages rather than a few large files, and why the largest source modules sit right under the cap. When a module approaches the limit, factor the cohesive part out into a sibling module — this is why `reprocli_repro/inputs.py` split into `inputs.py` + `dataset.py` + `prompt_render.py`, and why Supabase transport was consolidated into a single `postgrest.py`.

## Top-level tree

```text
reprocli/
├── src/
│   ├── run_arxiv_prompt_vllm.py     ✅ auditor entry point — main() for `--mode audit`
│   ├── reprocli_vllm/               ✅ the auditor core + dataset-construction post-processing
│   ├── reprocli_repro/              ✅ the S6 reproduction agent (`python -m reprocli_repro`)
│   ├── reprocli_serve/              ✅ the vLLM chat-completions server the brains attach to
│   ├── reprocli_data/               ✅ dataset build/publish pipeline
│   └── reprocli_openai/             ✅ gpt-5.5 recheck of Hard no-code rows
├── tools/                           ✅ review apps + analysis scripts (not an importable pkg)
│   ├── verify_app/                  ✅ audit-pool verdict review app
│   ├── run_viewer/                  ✅ static run/audit viewer
│   ├── plot_audit_pool.py · upload_audit_pool_hf.py · rebuild_splits_from_app.py · …
├── scripts/                         ✅ SLURM launchers — serve/ · reproduce/ · cluster/ · minimax_m3/
├── tests/                           ✅ pytest, mirrors the source subpackages
├── docs/                            this MkDocs Material site
├── prompts/                         prompt_reproduce.txt · prompt_audit.txt · prompt.txt · …
├── rubric_audit.md                  audit rubric (hardcoded auditor input)
├── data/ · outputs/                 generated datasets, run bundles, model outputs
└── CLAUDE.md · AGENTS.md · README.md · mkdocs.yml · requirements.txt
```

!!! note "Import root"
    `src/` is on `PYTHONPATH` (the sbatch scripts set `export PYTHONPATH=…/src`), so packages import as `reprocli_vllm.*`, `reprocli_repro.*`, `reprocli_serve.*`, `reprocli_data.*`, `reprocli_openai.*`. The auditor runs as `python3 src/run_arxiv_prompt_vllm.py`; the reproduction agent as `python -m reprocli_repro`; the server as `python -m reprocli_serve`; the data/recheck tools as `python -m reprocli_data.build_dataset` / `python -m reprocli_openai.recheck`.

## Where things live

| Path | Role | Read more |
|---|---|---|
| `src/run_arxiv_prompt_vllm.py` | `main()` — parses args and runs the auditor loop (`--mode audit`, the only mode) | [run-arxiv CLI](../cli/run-arxiv.md) |
| `src/reprocli_vllm/` | The auditor tool loop + the dataset-construction schema/selection/H100 code | [agent core](../agent-core/index.md), [auditor](../modes/auditor.md) |
| `src/reprocli_repro/` | The S6 reproduction agent — its own forked loop, budget meter, JIT-SLURM substrate | [reproduction mode](../modes/reproduction.md), architecture §III |
| `src/reprocli_serve/` | The vLLM server the reproduction/audit brains attach to by URL | [serving](../slurm/serve.md) |
| `src/reprocli_data/` | Build & publish the NeurIPS-2025 paper bundle dataset | [build-dataset CLI](../cli/build-dataset.md), [dataset](../dataset/index.md) |
| `src/reprocli_openai/` | Re-check Hard-tier no-code rows on gpt-5.5 (Responses API) | [architecture](../architecture.md) |
| `tools/verify_app/`, `tools/run_viewer/` | Browser apps to review audit-pool verdicts and runs | [verify app](../apps/verify-app.md) |
| `tools/*.py` | Pool plots, HF upload of the lockfile, split rebuilds | [select-pool](../selection/select-pool.md) |
| `scripts/**/*.sbatch`, `*.md` | SLURM launch + interactive multi-node notes | [clusters](../slurm/clusters.md), [sbatch](../slurm/sbatch.md) |
| `tests/` | pytest suite, one subpackage per source subpackage | [testing](testing.md) |

## `src/reprocli_vllm/` — the auditor core ✅

`run_tool_loop` (`runtime/tool_loop.py`) drives the **auditor** (`run_arxiv_prompt_vllm.py --mode audit`, the only mode): read one agent reproduction run directory with the path-confined run-dir tools and emit a 0–5 verdict. The same package still owns the dataset-construction post-processing — the classifier's output schema and the pool-selection / H100-audit code that built the lockfile — so those subpackages stay here even though classification is no longer a runnable mode.

| Subpackage | What's in it | Key modules |
|---|---|---|
| `config/` | CLI args, defaults, audit-mode resolution, placeholders | `cli_args.py`, `config.py`, `minimax_defaults.py` |
| `papers/` | Load arXiv LaTeX bundles + OpenReview supplements into `Paper` | `papers.py` |
| `runtime/` | The tool loop, guardrails, run-health, audit rows/sink, live events, trace I/O | `tool_loop.py`, `loop_guards.py`, `run_health.py`, `audit_rows.py`, `audit_sink.py`, `live_events.py`, `mre_records.py`, `trace_io.py` |
| `tools/` | The auditor's run-dir tools + shared dispatch + `fetch_url` | `run_dir_tools.py`, `web_tools.py`, `web_fetch.py`, `http_utils.py`, `result_limits.py` |
| `schema/` | Structured-output schemas | `audit.py` (auditor), `output.py` (dataset-construction classifier) |
| `audit/` | Auditor post-processing + pool selection (the lockfile) | `audit.py`, `select_pool.py`, `h100.py`, `inputs.py` |
| `vllm/` | Chat-completions client + I/O against an already-served endpoint | `client.py`, `io.py`, `endpoint.py`, `retry.py` |

!!! tip "Which subpackage does new code go in?"
    Loop mechanics and budgets → `runtime/`. A new run-dir tool the auditor can call → `tools/` (and register it in `AUDIT_TOOLS`). A change to what the model must *emit* → `schema/`. Anything that turns model evidence into a computed label (score, verdict, selection) → `audit/`. Talking to the model server → `vllm/`.

!!! note "URL-only server"
    `reprocli_vllm` does **not** self-host a model. The auditor attaches to a server that `reprocli_serve` stands up, resolving the URL from `--vllm-server-url` / `$REPROCLI_SERVER_URL` / `$REPROCLI_ENDPOINT_FILE`; with no endpoint it exits with an error.

See the [tool loop](../agent-core/tool-loop.md), [guardrails](../agent-core/guardrails.md), and [structured output](../agent-core/structured-output.md) pages for how `runtime/`, `loop_guards.py`, and `schema/` fit together, and the [auditor](../modes/auditor.md) mode page for the live role.

## `src/reprocli_repro/` — the reproduction agent ✅

The S6 execution agent runs as `python -m reprocli_repro`. It is its **own package with a forked `run_tool_loop`** (it imports only mode-agnostic primitives from `reprocli_vllm`), takes one lockfile row, and actually runs the experiment on DeltaAI under a metered H100-hour budget — every GPU step is a just-in-time `salloc`/`srun` inside a **mandatory Apptainer sandbox**. It emits the run bundle (`report.json` + `evidence/`) the auditor grades.

| Area | Modules |
|---|---|
| Entry + CLI | `__main__.py`, `cli_args.py`, `cli_resolve.py` |
| Loop + state | `loop.py`, `context.py`, `guardrails.py`, `compaction.py`, `transcript.py`, `dispatch.py`, `finalize.py` |
| Inputs | `inputs.py`, `dataset.py`, `prompt_render.py`, `reference.py` |
| Workspace + evidence | `workspace.py`, `evidence.py`, `env.py`, `live_log.py`, `run_stats.py`, `summarize.py` |
| Budget + GPU substrate | `budget.py`, `cluster.py`, `slurm.py`, `sandbox.py`, `gpu_session.py` |
| Report bundle | `report/schema.py`, `report/validate.py` |
| Persistence | `postgrest.py`, `supabase_rows.py`, `supabase_sink.py`, `audit_upload.py` |
| Tools | `tools/workspace_bash.py`, `tools/files.py`, `tools/fetch.py`, `tools/partitions.py`, `tools/run_gpu.py` (+ `run_gpu_schema.py`, `run_gpu_notes.py`), `tools/output.py`, `tools/plan.py`, `tools/patch/` |

!!! note "One cluster profile"
    `cluster.py` carries a single built-in profile, `deltaai`. The two per-run overrides are `--partition` and `--apptainer-image`; there is no `--cluster`/`--account`/`--gpus-per-node`/`--hw`/`--scratch-root`/`--modules` surface. The agent picks a partition per allocation via the `list_partitions` tool.

## `src/reprocli_serve/` — the model server ✅

`python -m reprocli_serve` stands up a vLLM chat-completions server other nodes can reach and **publishes an endpoint JSON** the reproduction agent and auditor read. `profiles.py` is the single source of truth for per-model serve profiles (tensor/pipeline parallelism, tool-call/reasoning parsers, etc.); `args.py` layers CLI overrides on top. Other modules: `launch.py` (build+run the `vllm serve` command), `endpoint.py` (publish the URL), `network.py` (fabric-IP discovery), `wait.py` (health wait), `config.py`.

## `src/reprocli_data/` — dataset pipeline ✅

Builds the one-row-per-paper bundle. `build_dataset.py` is the CLI; the `pipeline/` subpackage holds the five stages (`index → sources → supplements → bundle → upload`), again split to stay under the line limit.

| Module | Stage / role |
|---|---|
| `build_dataset.py` | CLI dispatcher over the five stages |
| `pipeline/index.py` | Snapshot pre-matched arXiv ids from the NeurIPS2025 dataset |
| `pipeline/sources.py` | Download + extract arXiv e-print packages |
| `pipeline/supplements.py`, `attachments.py` | OpenReview supplementary material |
| `pipeline/bundle.py` | Assemble the Parquet bundle |
| `pipeline/output.py`, `common.py` | Shared paths, filenames, writers |

Details on each stage and the emitted schema live in [dataset stages](../dataset/stages.md) and the [bundle schema](../dataset/bundle-schema.md).

## `src/reprocli_openai/` — recheck ✅

`recheck.py` re-checks the audit-pool's Hard-tier no-code rows on gpt-5.5 using the synchronous OpenAI Responses API (the Batch queue was too slow), with web search and strict structured outputs. It reuses `reprocli_vllm.config` placeholders, appends raw responses to `results_raw.jsonl` for resume, and is invoked as `python -m reprocli_openai.recheck` (`--status` for progress).

## `tools/` and `scripts/`

`tools/` is **not** an importable package — it holds standalone review apps and analysis scripts:

- `verify_app/` — review audit-pool verdicts (see [verify app](../apps/verify-app.md)).
- `run_viewer/` — a static viewer for reproduction runs and audits.
- `plot_audit_pool.py`, `upload_audit_pool_hf.py`, `rebuild_splits_from_app.py`, `merge_repin_into_splits.py`, `split_analysis.py` — pool analysis + publishing/rebuilding the [lockfile](../selection/lockfile.md).

`scripts/` holds the SLURM substrate, grouped into folders: `serve/` (the `reprocli_serve` central-server launchers), `reproduce/` (the reproduction-agent orchestrator launchers), `minimax_m3/`, and `cluster/`. See [clusters](../slurm/clusters.md), [sbatch](../slurm/sbatch.md), and [serving](../slurm/serve.md).

## `tests/`

The suite mirrors the source subpackages — one test directory per area — so a change in `audit/` lands tests in `tests/audit/`, a change in `reprocli_repro` lands them in `tests/repro/`, and so on (`tests/{audit,repro,runtime,schema,serve,smoke,tools,vllm}/`). Keep that mapping when you add modules. See [testing](testing.md).
