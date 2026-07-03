# ReproBench — system architecture

End to end: how the dataset is built, how papers are reproduced, and how those
reproductions are graded. The whole system turns on **one lockfile** (the
band-selected audit pool) and **two live LLM agent roles** arranged around it — the
**reproduction agent** (S6) and the **auditor** (S7) — with a shared **serving
layer** both brains attach to by URL. The auditor is a *mode* of one shared
tool-calling core (`run_tool_loop` in `reprocli_vllm`); the reproduction agent lives
in its **own package** (`src/reprocli_repro/`) and *forks* that loop's structure,
reusing only mode-agnostic primitives. The lockfile itself was built upstream by an
earlier classifier pass (S1–S5) and is consumed as a published, frozen input.

```
  LOCKFILE ──► REPRODUCTION agent (JIT srun) ──► run bundle ──► AUDITOR agent
  (the data)      (actually run the MRE)          (evidence)     (grade 0–5)
     S5                    S6 ✅                                      S7
```

Both brains reason on an already-served vLLM endpoint (`reprocli_serve`), resolved
purely by base URL; neither self-hosts a model.

> Verified against: `reprocli_repro/` (`cli_args.py`, `cli_resolve.py`, `loop.py`,
> `context.py`, `inputs.py`, `dataset.py`, `prompt_render.py`, `workspace.py`,
> `reference.py`, `evidence.py`, `budget.py`, `cluster.py`, `slurm.py`,
> `sandbox.py`, `dispatch.py`, `postgrest.py`,
> `tools/workspace_bash.py`, `tools/files.py`, `tools/run_gpu.py`),
> `reprocli_vllm/` (`run_arxiv_prompt_vllm.py`, `config/cli_args.py`,
> `config/config.py`, `runtime/tool_loop.py`, `runtime/loop_guards.py`,
> `runtime/run_health.py`, `vllm/io.py`, `schema/output.py`, `schema/audit.py`,
> `tools/run_dir_tools.py`, `tools/web_fetch.py`, `audit/audit.py`,
> `audit/select_pool.py`), `reprocli_serve/`, `prompts/prompt_reproduce.txt`.
> Status legend: ✅ live.

## 0. The whole system (Mermaid)

```mermaid
flowchart TD
  classDef lock fill:#fde68a,stroke:#b45309,stroke-width:2px,color:#000;
  classDef llm  fill:#dbeafe,stroke:#1d4ed8,color:#000;
  classDef gpu  fill:#dcfce7,stroke:#15803d,color:#000;

  A["NeurIPS 2025 arXiv LaTeX bundles + OpenReview supplements"]
  CL["classifier pass (S1–S5, historical)<br/>verify artifacts → MRE record<br/>built the lockfile upstream"]:::llm
  POST1["normalize_score_and_tier · web_verification · h100 audit"]
  SEL["audit/select_pool.py · band-stratified, cheapest-first"]
  LOCK["THE LOCKFILE — Mithilss/reprobench-splits (~100 rows)<br/>central_claim · mre_config · match_target · agent_task · tier · band · budget"]:::lock
  RA["① REPRODUCTION agent ✅<br/>own package (reprocli_repro), forked loop<br/>URL brain (reprocli_serve) + run_gpu → JIT salloc per step"]:::llm
  GPU["fresh salloc per step (DeltaAI ghx4 — the only profile)<br/>mandatory Apptainer sandbox · released the instant the step exits"]:::gpu
  BUN["run bundle  agent_runs/&lt;paper&gt;/&lt;budget&gt;h/&lt;run&gt;/<br/>workspace/ · reference/ · evidence/ · report.json ✅"]
  AU["② AUDITOR agent ✅<br/>run_tool_loop · run-dir tools (list/read/bash/write_run_file)<br/>grade 0–5 + cheat_flags"]:::llm
  POST2["finalize_audit_row · anti-cheat cap → verdict"]

  A --> CL --> POST1 --> SEL --> LOCK
  LOCK -->|"agent_task · match_target"| RA
  RA <-->|"run_gpu = one JIT salloc … srun (no pre-held alloc)"| GPU
  RA --> BUN
  LOCK -->|"central_claim · match_target (verbatim)"| AU
  BUN -->|"runs_dir"| AU --> POST2

  class LOCK lock;
```

Through-line for all three roles: **the model reports evidence, the code computes
every consequential label** (tier at classification; score, verdict, run-health at
audit). No agent ever grades itself — the reproduction agent runs the experiment and
**reports** what it measured; the *auditor* is the role that renders the
reproduction verdict.

---

# Part I — Dataset construction (S1–S5, historical provenance)

Two stages produced the lockfile that the two live consumers (reproduction, audit)
read. The classifier pass that emitted the MRE records is **no longer a runnable
mode** — the lockfile is now consumed as a published, frozen input — but the
provenance below explains where each field came from.

## I.1 Pipeline (ASCII)

```
STAGE 1 — DATASET CONSTRUCTION  (classifier pass — how the lockfile was built)
   NeurIPS 2025 arXiv LaTeX bundles
        │  load_bundle_papers()  →  Paper(tex_files)
        ▼
   paper bundle text ──► vLLM + tool loop ──► artifact / link verification
        ▼
   ONE MRE record per paper   (output_schema.FINAL_JSON_SCHEMA)
     ├ central_claim, claim_evidence, paper_kind
     ├ mre_config     — smallest experiment that tests the claim
     ├ match_target   — {config, metric, value, scope, match_bar_kind}  ◄ coherent anchor pinned here
     ├ agent_task     — what the repro agent is told to do
     ├ verified_links, signals   (code / data / weights)
     └ h100_estimate  (compute cost)
        ▼  normalize_score_and_tier · web_verification · h100 audit
   <run>_extracted.jsonl   (every classified paper)

STAGE 2 — POOL SELECTION  (audit/select_pool.py)                            ✅
   keep if  verified  AND  tier ∈ {Easy, Medium, Hard}  AND  audited H100 ≤ 192 hr
   band-stratified Easy/Medium/Hard · bands 0-8/8-32/32-96/96-192 · cheapest-first
   per-tier band weights 5/7/8/5 per 25 selected (largest-remainder to --total)
        ▼
   audit_pool_extracted.jsonl  →  published as Mithilss/neurips-2025-audit-pool
   ◄══ THE LOCKFILE (~200 rows)
   each row = claim + mre_config + match_target + agent_task + tier + cost
```

## I.2 The `match_target` through-line

The pinned success bar is a **coherent anchor tuple** —
`match_target = {config, metric, value, scope, match_bar_kind}` — set once and
reused, so every agent is judged against the same ruler instead of one the auditor
re-infers each run. The classifier pins a tuple where running `config` and
measuring `metric` over `scope` can actually yield `value` (a string, so it
tolerates `"2.37x"`, `"76.5%"`, `"8.56 kB"`, or a range). The **coherence
invariant** (config↔value, config↔scope) is enforced at classification time
(commit `327d497`): four earlier runs failed at an *incoherent anchor*, not the
tolerance — MagCache pinned `K=1` against a `2.37×` value `K=1` can't reach; AIPW
pinned an ImageNet-only `config` against a 19-benchmark-average `value`. Deriving
the bar later only relocated the incoherent claim, so it is now pinned — and
audited — upstream.

```
Stage 1 classifier PINS the tuple  →  lockfile CARRIES it
   →  Auditor ADOPTS it verbatim, filling only op/tolerance from match_bar_kind
```

Only `match_bar_kind` is pinned; **`op` and `tolerance` are not**. The auditor fills
them from one shared kind→default mapping (`rubric_audit.md` C1), so every run's
verdict applies the same ruler by construction:

| `match_bar_kind` | what counts as a match | op / tolerance (DERIVED from the kind, not pinned) |
|---|---|---|
| `point_estimate` | land near `value` | `op=abs_rel_within`, tolerance = rubric default (±5 %) |
| `threshold` | clear a floor/ceiling | `op=">="` / `"<="`, tolerance null |
| `direction` | beat a baseline (no tolerance band) | `op="measured_method > measured_baseline"`, tolerance null |
| `magnitude` | the *size* of a delta is the target | tolerance applies to the delta |
| `none` | no checkable scalar/relation (theory/position) | no scalar comparison |

Legacy rows that predate the tuple (no `match_target`) fall back to the auditor
*deriving* the bar from the claim + reported numbers, per the same rubric C1.

> The reproduction prompt renders `match_target` as an explicit **Pinned success bar**
> block (`config · metric · value · scope`, plus a plain-language reading of
> `match_bar_kind`), so the agent aims at the same structured anchor the auditor scores
> against. `op`/`tolerance` stay auditor-side — the agent is shown the *shape* of the bar
> ("reproduce a value close to the target", "beat the baseline", …), never a numeric
> tolerance it could game. The `mre_config`/`agent_task` prose still restate the value
> inline as before; the auditor keys off the same structured tuple verbatim.

---

# Part II — The single agent core

There is **one agent core** (`run_tool_loop`, `reprocli_vllm/runtime/tool_loop.py`).
The **auditor** is its one live mode (`resolve_mode_settings` fills the audit prompt,
toolset, and output schema); `--mode` accepts only `audit`. (The classifier that
built the lockfile was historically a second mode of this same core, which is why
the runtime still generalizes over prompt/toolset/schema.) The reproduction agent
(Part III) is a **separate package that forks this loop's structure** — same skeleton
(two thread pools, `wait(FIRST_COMPLETED)`, `handle_request_done`), but its own
driver, guardrails, and tool dispatch, importing only mode-agnostic primitives from
`reprocli_vllm` (the vLLM client/io, `loop_guards`, `trace_io`, `function_tool`).

- **Single agent, not multi-agent.** One model, one conversation per item, one
  fixed toolset. Parallelism is *across items* (N independent episodes), never
  within one episode.
- **ReAct-style, `tool_choice="auto"`.** The model decides whether/which tool to
  call; the loop never scripts a tool sequence — it enforces budgets and harvests
  results.
- **Bounded autonomy.** Every episode provably terminates: a round cap, a
  repeat-call cap, and a context budget each force a final answer.
- **Trust-but-verify.** The LLM proposes; deterministic code decides every
  consequential label.

## II.1 Runtime (ASCII)

```
                          run_arxiv_prompt_vllm.main()
                          parse_args → resolve_mode_settings (audit prompt/tools/schema)
                                      │
        ┌─────────────────────────────┼──────────────────────────────────────────┐
        ▼                             ▼                                            ▼
 ┌──────────────┐          ┌──────────────────────┐                     ┌──────────────────┐
 │ INPUT LOADER │          │  MODEL SERVER (vLLM)  │                     │   OUTPUT SINKS    │
 │ audit:       │          │  OpenAI /v1/chat      │                     │  raw .jsonl       │
 │  claim +     │          │  completions          │                     │  extracted .jsonl │
 │  run_dir     │          │  URL-ONLY:             │                    │  trace .jsonl opt │
 │  manifest    │          │  --vllm-server-url /   │                    └────────▲─────────┘
 │              │          │  $REPROCLI_ENDPOINT_…  │                             │ OUTPUT_WRITE_LOCK
 │              │          │  (reprocli_serve)      │                             │
 └──────┬───────┘          └───────────▲───────────┘                             │
        │ initial_messages             │ HTTP (stateless completions)            │
        │ [system, user]               │  no endpoint → hard error (never self-hosts)
        ▼                              │                                         │
 ┌───────────────────────────────────────────────────────────────────────────────────────┐
 │ ORCHESTRATOR — run_tool_loop  (runtime/tool_loop.py)                                    │
 │   conversations{id → [messages]}    ← per-episode memory lives HERE, not the server     │
 │   two ThreadPoolExecutors:  requests pool → vLLM   ·   tools pool → tool layer           │
 │   event loop: wait(request_futures ∪ tool_futures, FIRST_COMPLETED)                      │
 │   GUARDRAILS (runtime/loop_guards.py): repeated_call_cutoff · round_limit · context_budget │
 └───────────────┬───────────────────────────────────────────────────────┬─────────────────┘
                 │ tool_calls present                                     │ tools OFF (final pass)
                 ▼                                                        ▼
 ┌─────────────────────────────────────┐                  ┌──────────────────────────────────┐
 │ TOOL EXECUTION LAYER (run_dir_tools) │                  │ STRUCTURED-OUTPUT FINALIZATION     │
 │  retry-once on transient + truncate  │                  │ response_format = json_schema      │
 │  audit run-dir tools, path-confined: │                  │  audit → AUDIT_RESPONSE_FORMAT     │
 │  list_run_files · read_run_file ·    │                  └────────────────┬─────────────────┘
 │  bash · write_run_file               │                                   ▼
 └─────────────────────────────────────┘                  ┌──────────────────────────────────┐
        results appended → next round                     │ POST-PROCESSING (run_health/audit) │
                                                          │  LLM proposes · CODE decides label │
                                                          └──────────────────────────────────┘
```

## II.2 One episode — the state machine

`handle_request_done` is the transition function. Two phases: a *free
tool-exploration* phase (tools on, `tool_choice=auto`) then exactly one *forced
structured-output* phase (tools removed, `response_format=json_schema`) — which is
why the final JSON parses reliably.

```
 round 0:  request WITH tools  ([system, user-prompt])
    │
    ▼ request completes
 tools enabled?
   ├─ YES + tool_calls → repeated? → exit repeated_call_cutoff → force final
   │                   → round+1 ≥ tool_rounds? → exit round_limit
   │                   → append_tool_results (run every call) → next round
   ├─ YES, no tool_calls → re-issue ONE tools-off pass → schema-forced JSON
   └─ NO (final pass)   → record telemetry+exit_reason → write rows
    │ next request: include_tools = not force_final AND next_round < tool_rounds
    └─                              AND not context_budget_exceeded   → loop
```

Exit reasons (`natural · round_limit · repeated_call_cutoff · context_budget`)
roll into `verification_status` (`verified · incomplete · degraded`). The
reproduction agent's forked loop adds a fifth exit reason, `budget_exhausted`
(Part III.4).

## II.3 The one live mode: audit

`--mode` accepts only `audit`. The table below contrasts the live auditor with the
historical classifier that built the lockfile (kept for context — it is no longer a
runnable mode).

| | **Auditor** (`--mode audit`) ✅ live | **Classifier** (historical, built the lockfile) |
|---|---|---|
| Job | Grade one agent's reproduction run against the rubric | Read a paper, *verify* artifacts, emit one MRE record |
| Input | `{CENTRAL_CLAIM}` + `{RUBRIC}` + run-dir manifest | `{PAPER_TEXT}` (bundle LaTeX + supplement) |
| Tools | `list_run_files`, `read_run_file`, `bash`, `write_run_file` | web/artifact-verification tools |
| Tool scope | Path-confined to `<runs-dir>/<arxiv_id>`; read-write (`write_run_file` lets it drop a scoring script and run it under `bash`) | open-web evidence |
| Final schema | `AUDIT_RESPONSE_FORMAT` (0–5 score, cheat_flags, citations) | `FINAL_RESPONSE_FORMAT` (signals, match_target, h100) |
| Code decides | anti-cheat cap (high flag → 0), verdict, run-health | tier, web_verification rollup, h100 audit |

The reproduction agent (Part III) is the other live role, but **not** a mode of this
core — it is its own package with a forked loop.

## II.4 Statelessness & concurrency

The vLLM server is a pure completion endpoint — **all conversation memory is the
orchestrator's `conversations` dict**. The runner is **URL-only**: it attaches to an
already-served endpoint (`--vllm-server-url` / `$REPROCLI_SERVER_URL` /
`$REPROCLI_ENDPOINT_FILE`, published by `reprocli_serve`) and never self-hosts a
model. That statelessness is exactly the property Part III exploits: the
reproduction agent's *brain* is the same served model while its *hands*
(`run_gpu`/`srun`) live elsewhere. Up to `--request-workers` episodes run at once; request and tool pools
are separate so a slow tool never blocks a model response; rows are appended as
each item finishes under `OUTPUT_WRITE_LOCK`.

---

# Part III — The reproduction agent (S6) ✅

The reproduction agent is live in its own package (`src/reprocli_repro/`), invoked as
`python -m reprocli_repro`. Given **one lockfile row** (`agent_task`, `central_claim`,
`mre_config`, `match_target`, `tier`, `selection_band`, `audited_h100_hours`), it is an
agent that *actually runs the experiment* on the cluster under a metered
H100-hour budget and emits the run bundle the auditor grades. It is the same
`run_tool_loop` skeleton, **forked** into its own driver, whose toolset executes
real commands — the heavy ones via a just-in-time `salloc`/`srun` inside a
**mandatory Apptainer sandbox**.

What it comprises: the forked tool loop (`loop.py`), the per-episode
`ExecutionContext` (`context.py`), the `summarize-compact` context tier (`summarize.py`),
the input pipeline that turns one lockfile row into a rendered prompt + run directory
(`inputs.py` + `dataset.py` + `prompt_render.py`), the per-paper workspace /
read-only reference / durable evidence setup (`workspace.py`, `reference.py`,
`evidence.py`), the H100-equivalent budget meter (`budget.py`), the DeltaAI cluster
profile (`cluster.py`), the JIT `salloc`/`srun` step builder and Apptainer sandbox
(`slurm.py`, `sandbox.py`), the workspace-confined CPU tools
(`tools/workspace_bash.py`, `tools/files.py`), and the metered `run_gpu` tool
(`tools/run_gpu.py`) wired through `dispatch.execute_repro_tool_call` by
`build_repro_tools()`. The forced final pass writes a structured `report.json` — what
the agent ran and measured, cited into `evidence/`. There is **no** harness
re-execution and **no** agent-written verdict; the auditor owns the verdict. See
[`reproduction-agent-plan.md`](reproduction-agent-plan.md) for the historical design
record.

## III.1 The core design decision: decouple orchestration from GPU — via JIT allocation

The agent's *thinking* (LLM calls, file edits, dependency installs, reading
results) is cheap CPU work; only the experiment itself needs a GPU. Renting a GPU
for the whole episode while the LLM reasons would burn the H100 budget on idle
time. The original design held one GPU allocation open for the whole budget
window; the **built** design goes further — **just-in-time (JIT) allocation**:

- **Orchestrator** runs on a **login or CPU allocation** — long-lived, cheap, and
  **never holds a GPU**. It holds the agent loop, the budget meter, evidence
  capture, the bundle writer, and **all** CPU work (clone, `uv venv`, install,
  edit, inspect).
- **GPU work** is provisioned **per step**: each `run_gpu` tool call opens **one
  fresh `salloc`** sized for that step and **releases it the instant the command
  exits**. Nothing is pre-held; there is no `--allocation-jobid` and no
  pre-held-allocation mode. So idle GPU time is never charged — the budget is spent
  only on real compute.

This splits two kinds of decision cleanly:

- **Operator-set (the DeltaAI cluster profile — the agent's *entitlements*):** the
  account, default partition, node hardware (`hw`), and GPUs-per-node are pinned by
  the single built-in `deltaai` profile (`cluster.py`). The only per-run overrides
  are `--partition` (pick a different queue on the same account) and
  `--apptainer-image` (swap the base `.sif`). The agent can only allocate on the
  account the profile grants it.
- **Model-set (per `run_gpu` call):** `gpus` and a wallclock cap `minutes`. These
  size the JIT allocation and are exactly what the meter charges.

**Accepted tradeoff:** a JIT step may sit in the SLURM queue, adding latency on a
busy cluster. That is the price of an unattended pipeline that charges only real
compute and never squats on idle GPUs.

Every GPU step runs through a JIT `salloc` on the cluster profile the agent is
entitled to — there is **no** off-cluster "local" executor. A real reproduction
needs a real GPU, so `run_gpu` always provisions one rather than offering a
plain-subprocess fallback that could never reproduce anything.

## III.2 Runtime (ASCII)

```
                    LOCKFILE ROW  (one paper × budget cell)
   agent_task · central_claim · mre_config · match_target · tier · selection_band · audited_h100_hours
            (source: Mithilss/reprobench-splits — HF dataset, hf:// file, or local .jsonl)
                              │  inputs.prepare_episodes → render prompt + resolve run dir
                              ▼
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │ ORCHESTRATOR  (login / CPU allocation — cheap, long-lived, NEVER holds a GPU)      │
 │  run_reproduce_loop  (loop.py — forked run_tool_loop skeleton)                      │
 │  reproduction LLM  → any OpenAI-compatible /v1/chat/completions endpoint,           │
 │      resolved from --vllm-server-url / $REPROCLI_SERVER_URL / $REPROCLI_ENDPOINT_FILE│
 │      (published by reprocli_serve). The repro agent never self-hosts a model.       │
 │                                                                                    │
 │  budget meter   H100-equiv = Σ gpus × elapsed_h × hw_multiplier[hw]  (budget.py)   │
 │  context mgmt   summarize-compact (brain-call summary) → hard context cutoff        │
 │  evidence rec.  → commands.log · trajectory.jsonl · env.lock · patches/             │
 │                                                                                    │
 │  TOOLS (workspace-confined CPU tools + the metered run_gpu, via build_repro_tools)│
 │   workspace_bash → cwd-confined shell  (git clone, uv venv, edit, inspect)         │
 │   read_file / write_file / apply_patch  (read: workspace+reference+evidence;       │
 │                                          write: workspace+evidence only)            │
 │   fetch_url      → read-only fetch of a public http(s) URL                          │
 │   list_partitions → read-only sinfo of the cluster's partitions                    │
 │   run_gpu        → one JIT salloc per step ─────────────────────────────┐  ✅      │
 └──────────────────────────────────────────────────────────────────────────│────────┘
        no pre-held allocation — a fresh salloc opens here, per step          │
                              │                                               ▼  salloc … srun
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │ JIT GPU STEP  (slurm.py — released the instant the command exits)                  │
 │  salloc -A <acct> -p <part> --nodes=1 --gpus=<k> --time=<min> \                     │
 │    srun --ntasks=1 apptainer exec --nv … <sif> bash -lc 'cd <workspace> && <cmd>'   │
 │  per-paper workspace · per-paper uv venv · --time is the budget pre-authorization   │
 │  every step: capture stdout/stderr/exit + elapsed×gpus → meter + trajectory.jsonl   │
 └──────────────────────────────────────────────────────────────────────────────────┘
                              │ budget exhausted OR agent finishes → forced final pass
                              ▼
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │ FINAL REPORT  (report.json — the agent's own account, NOT a verdict)              │
 │  forced final pass (tools off) emits report.json: what was run, the metric       │
 │  value(s) observed, and citations into evidence/. The agent never grades itself —│
 │  it states what it measured; the AUDITOR decides whether it reproduced.          │
 └──────────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
   run bundle  outputs/repro/agent_runs/<arxiv_id>/<budget>h/<run_id>/  →  Part II auditor
```

The run directory is resolved by `inputs.resolve_run_paths` to
`<runs-dir>/<arxiv_id>/<budget>h/<run_id>/` (default runs-dir
`outputs/repro/agent_runs`; `<run_id>` is a fresh time+random id so re-runs of one
paper never collide). Inside it: `workspace/` (rw — the editable clone + the
per-paper `uv` venv), `reference/` (ro — the paper LaTeX + every supplement file,
materialized from `Mithilss/neurips-2025-paper-bundles`), and `evidence/`. This is
the S6→S7 contract the existing auditor reads (it walks `<runs-dir>/<arxiv_id>`).

## III.3 Tools the reproduction agent gets

| tool | runs where | role |
|---|---|---|
| `workspace_bash` | orchestrator CPU subprocess, cwd = `workspace/` | clone the repo at a pinned commit, create the per-paper `uv` venv, install deps, edit, inspect — anything that does not need a GPU. Every command is appended to `evidence/commands.log` |
| `read_file` / `write_file` / `apply_patch` | orchestrator (path-confined) | reads span `workspace`/`reference`/`evidence`; writes only `workspace`/`evidence` (the `reference/` copy is never writable). `apply_patch` runs `git apply` and saves the diff verbatim under `evidence/patches/` |
| `fetch_url` | orchestrator (`tools/fetch.py`, read-only) | fetch a public http(s) URL (docs, a wheel index, a raw file) as text — no write, no GPU |
| `list_partitions` | orchestrator (`sinfo`, read-only) | enumerates the cluster's partitions (node pools) — idle/total nodes, walltime, GPU gres — plus the built-in default, so the model can pick a `partition` for `run_gpu` instead of the profile's default |
| `run_gpu` | one JIT `salloc … srun` per call, inside the Apptainer sandbox | the experiment: training/eval/scoring. Wraps the command, captures out/err/exit, **meters** `gpus × elapsed × hw_multiplier`, enforces a per-step timeout and the **remaining** budget. Optional `partition` (from `list_partitions`) overrides the profile default for that allocation; the profile pins only the default |

`build_repro_tools()` assembles the CPU tools and the `run_gpu` tool and wires them
through `dispatch.execute_repro_tool_call` against the per-episode
`ExecutionContext`, so the loop runs a paper episode end-to-end: every GPU step
JIT-`salloc`s on the `deltaai` profile inside the mandatory Apptainer sandbox. The
loop body, guardrails, summarize-compact, structured-output finalization, and trace
capture are all in place.

**The brain is provider-agnostic.** The agent's reasoning runs on **any
OpenAI-compatible `/v1/chat/completions` server, chosen purely by base URL**. The
runner resolves it from `--vllm-server-url`, else `$REPROCLI_SERVER_URL`, else the
endpoint file `reprocli_serve` publishes (`$REPROCLI_ENDPOINT_FILE`). The reused
`build_chat_completion_request` → `post_chat_completion_row` path already speaks
that protocol, so the brain is swapped by changing the URL — no provider-specific
code in the harness, and the agent never self-hosts a model.

## III.4 The budget meter (the new guardrail)

Where the classifier/auditor guardrails bound *tokens and rounds*, the
reproduction agent's hard guardrail bounds *compute* (`budget.py` +
`loop.apply_guardrails`):

```
cost(step)  = gpus × elapsed_hours × hw_multiplier[hw]          # charged on ACTUAL elapsed
worst(step) = gpus × (minutes / 60) × hw_multiplier[hw]         # pre-authorization (the --time cap)
affordable  = not budget.exhausted() AND worst ≤ budget.remaining()
if not affordable:  run_gpu refuses BEFORE launching → forces the agent to finish + report
```

SLURM bills only the run, never the queue wait, so the meter is fed elapsed *run*
time. `--time=<minutes>` is the worst-case ceiling SLURM hard-kills at, so a step
can be refused before it ever launches. `hw_multiplier` (`budget.HW_MULTIPLIER`)
reduces every part to H100-equivalent hours: Hopper-class parts (`h100`/`h200`/
`gh200`) start at ~1.0 because they share the compute die; non-Hopper entries
(`a100`≈0.5, `b200`≈2.2) are placeholders to be calibrated empirically. Every step
appends a `trajectory.jsonl` row so `budget_at_first_pass` is reconstructable.
Budget exhaustion sets `exit_reason="budget_exhausted"` and force-finals via the
same mechanism as `repeated_call_cutoff`.

## III.5 Context management — summarize-compact

Tool stdout stays **verbatim** in the conversation. Once the prompt crosses a soft
threshold (a fraction of the input-token budget), `summarize.py` makes one brain
call that rewrites the old span into a structured summary (keeping the recent turns
verbatim) so the loop keeps going; only if summarization itself fails past the real
ceiling does the loop fall back to the hard context-budget cutoff. A cheaper
`microcompact` tier that replaced stale tool results with `[elided N chars]`
placeholders was removed after the 07-03 batch: agents re-ran discovery commands
and whole GPU evals because results they needed had been elided out from under
them — the "evidence is the durable store" rationale did not hold in practice.

## III.6 The agent reports; the auditor renders the verdict

The reproduction agent's last act is its **report** — a structured account of what
it ran, the metric value(s) it observed, and citations into `evidence/`. It writes
**no verdict**: there is no `repro.yaml` submission contract and **no post-loop
harness re-execution**. Everything after the report belongs to the **auditor**
(Part II, S7), the separate LLM-as-a-judge that already reads the run bundle and
grades it. This keeps the "no agent grades itself" through-line intact — the
report's author and its grader are different roles — while removing a deterministic
re-run that only duplicated what the auditor already does.

What the auditor owns, once the report + evidence land:

- **Re-execution, if it wants it.** The auditor can recompute a metric from a saved
  artifact by `write_run_file`-ing a scoring script and running it under `bash`
  (`run_dir_tools.py`) — so a fresh measurement is the *judge's* call against the
  evidence, not a step the harness forces on every run.
- **The pinned ruler.** It adopts the lockfile's `match_target` verbatim (§I.2) and
  fills `op`/`tolerance` from the one shared `match_bar_kind`→default table
  (`rubric_audit.md` C1).
- **The verdict.** The 0–5 score → `reproduced` / `partial` / `not_reproduced` /
  `unverifiable`, with the deterministic anti-cheat cap, exactly as in
  [the auditor](modes/auditor.md). There is no second, harness-authored verdict to
  reconcile.

Trust-but-verify is unchanged, only relocated: a claim in the report that
contradicts the evidence the auditor recomputes becomes a `cheat_flag`, and a run
whose realized config/scope drifts from the pinned `config`/`scope` is graded down
rather than taken on faith. The repro agent states what it measured; the auditor
decides whether it reproduced.

## III.7 Module layout (`src/reprocli_repro/`)

```
src/reprocli_repro/                 # the S6 execution agent — its own package, forked loop
  __init__.py · __main__.py         # entry point: prepares episodes + drives the full loop
  cli_args.py · cli_resolve.py      # its own argparse (NOT resolve_mode_settings): run selection,
                                    #   workspace, cluster (--partition/--apptainer-image), endpoint,
                                    #   loop limits, outputs — plus default/validation resolution
  loop.py                           # run_reproduce_loop — forked run_tool_loop skeleton
  context.py                        # ExecutionContext + Budget (per-episode mutable state)
  inputs.py · dataset.py · prompt_render.py   # lockfile row → rendered prompt + RunPaths (S6→S7 contract)
  workspace.py                      # per-paper workspace + empty per-paper uv venv
  reference.py                      # read-only reference/ from the HF paper-bundle dataset (library half)
  evidence.py                       # commands.log / trajectory.jsonl / env.lock / patches/
  budget.py                         # H100-equiv meter + hw_multiplier table
  cluster.py                        # the single deltaai profile (+ --partition/--apptainer-image overrides)
  slurm.py · sandbox.py             # JIT salloc/srun GPU-step builder + the mandatory Apptainer wrap
  transcript.py                     # conversation shaping + incremental JSONL output
  postgrest.py                      # consolidated Supabase (PostgREST) transport
  dispatch.py                       # execute_repro_tool_call seam — routes build_repro_tools()
  tools/
    workspace_bash.py               # cwd-confined shell
    files.py                        # read_file / write_file / apply_patch
    fetch.py                        # read-only fetch_url
    partitions.py                   # list_partitions — sinfo pools + the profile default
    run_gpu.py                      # the JIT-dispatching metered GPU tool
  report/                           # report schema + bundle writer → report.json
                                    #   (the agent's cited account of the run; the auditor grades it)
```

Keeping repro in its own package (rather than a third `--mode`) leaves the
`reprocli_vllm` audit core untouched and keeps every module under the 300-line rule.
The only thing repro borrows is import-level primitives.

---

# Part IV — The SLURM execution substrate

How GPU work is actually managed in this repo. Two distinct patterns coexist: the
**serving job** (`reprocli_serve`) pre-holds one GPU allocation for the whole batch
job and serves a vLLM endpoint; the reproduction agent allocates **just-in-time, per
step** (Part III). Both build on the same `salloc`/`srun` primitives, and the two
brains (reproduction, audit) reach the serving job over its published URL.

## IV.1 Clusters & accounts

| cluster | account / partition | hardware | used for |
|---|---|---|---|
| **DeltaAI** (NCSA) | `-A betw-dtai-gh -p ghx4` | GH200, 4 GPU/node | the reproduction agent's JIT profile (`deltaai`, the only profile) and GPU serving jobs |
| **Delta** (NCSA) | `-A bfvr-delta-cpu -p cpu-interactive` | CPU | model downloads, CPU orchestration (the reproduction agent's login/CPU host) |
| **Delta** (NCSA) | `-A bfvr-delta-gpu -p gpuH200x8-interactive` | H200 ×8/node | interactive + multi-node model serving |

The reproduction agent's `cluster.py` encodes a **single** built-in profile,
`deltaai`, carrying the account, default partition, `hw`, and GPUs-per-node. The only
per-run overrides are `--partition` (a different queue on the same account) and
`--apptainer-image` (the base `.sif`).

## IV.2 Two allocation patterns

```bash
# A. Serving job — PRE-HELD allocation (one sbatch job holds the nodes for the server's life):
salloc -A betw-dtai-gh -p ghx4 --nodes=1 --gpus-per-node=4 --time=<window>
srun --jobid=$SLURM_JOB_ID --nodes=1 --ntasks=1 python -m reprocli_serve --model <id>  # publishes a URL

# B. Reproduction agent — JIT allocation (a fresh salloc PER run_gpu step, then released):
#    every step runs inside the mandatory Apptainer sandbox (sandbox.py); CUDA/torch come
#    from the NGC .sif, so there is no host `module load`.
salloc -A betw-dtai-gh -p ghx4 --nodes=1 --gpus=<k> --time=<minutes> \
       srun --ntasks=1 apptainer exec --nv --cleanenv --no-home <sif> bash -lc 'cd <workspace> && <command>'
```

Pattern A is the serving shape (`reprocli_serve`): the allocation lives for the
server's lifetime and other nodes attach to the published endpoint by URL. Pattern B
is the reproduction agent's `slurm.py`: the agent owns and releases each allocation,
so it holds no GPU while reasoning or installing.

Pattern B (the reproduction agent) runs every step inside the **mandatory Apptainer
sandbox** (`sandbox.py`): the NGC
PyTorch `.sif` is the read-only root, so CUDA + a GPU-ready `torch` come from the image
(no host `module load`), and writes are confined to the per-paper workspace/evidence,
`/tmp`, and the package caches. The agent layers a **per-paper `uv` venv** (with
`--system-site-packages`, to reuse the image's torch) on top — never the shared `.venv` —
so one paper's dependency install can never poison another's.

## IV.3 Why this maps cleanly onto the agent core

The chat-completions server is stateless (Part II.4), so the reproduction agent
attaches its brain to any already-running **OpenAI-compatible endpoint by base
URL** and spends **zero** GPU budget on reasoning — GPUs are touched only by JIT
`run_gpu` steps that do real experiment work. Orchestration (CPU) and GPU steps are
physically separate allocations, and the GPU allocation exists only for the
lifetime of one step. (If the brain endpoint is itself a cluster vLLM server, it is
its own long-lived allocation — never one metered against the paper's H100 budget.)

---

# Part V — Status

| stage | component | status |
|---|---|---|
| S1–S5 | Classifier pass → MRE records → `audit/select_pool.py` → lockfile (HF dataset) | historical — built the lockfile now consumed as a frozen input |
| S6 | **Reproduction agent (`python -m reprocli_repro`, JIT srun) → run bundle** | ✅ live — forked loop, budget meter, JIT-SLURM substrate + Apptainer sandbox, evidence store, toolset + `run_gpu`, `report.json` bundle. Every GPU step JIT-`salloc`s on the `deltaai` profile |
| S7 | Auditor agent (`--mode audit`) + anti-cheat cap | ✅ live |

The reproduction agent runs a paper end-to-end: `__main__` prepares each episode,
`dispatch.execute_repro_tool_call` routes `build_repro_tools()` against the
per-episode `ExecutionContext`, every `run_gpu` step JIT-`salloc`s on the `deltaai`
profile inside the mandatory Apptainer sandbox, and the forced final pass writes
`report.json`. The existing auditor grades that bundle with **zero changes**
(`--mode audit --runs-dir <same root>`; gated by `tests/repro/test_audit_bundle.py`).

### Notes

- The auditor re-scores artifacts (recompute a metric from a saved output) by
  `write_run_file`-ing a scoring script and running it under `bash`
  (`run_dir_tools.py`); there is no dedicated interpreter tool.
- Every reproduction GPU step runs inside the **mandatory Apptainer sandbox**
  (`sandbox.py`, `slurm.py`): the base `.sif` is a read-only root, writes are
  confined to the per-paper workspace/evidence, and `--apptainer-image` swaps the
  image. Tighter credential-split and offline-prefetch hardening for untrusted paper
  code layers onto that same wrap.
