# Reproduction agent (`--mode reproduce`) 🚧

The reproduction agent is the **missing consumer** of the lockfile: given one
lockfile row it *actually runs the experiment* on the cluster under a metered
H100-hour budget, then emits the run bundle the auditor grades. It is the same
`run_tool_loop` skeleton as the [classifier](classifier.md) and
[auditor](auditor.md), with an execution toolset bolted on. This page summarizes
**Part III** of the [system architecture](../architecture.md) — read that for the
full spec.

!!! warning "Status: 🚧 designed, not yet wired"
    Nothing below is built. There is no `src/reprocli_repro/` package and no
    `--mode reproduce` yet. This is the single open edge (S6) that turns
    classifier-plus-auditor into an end-to-end benchmark. See
    [Part V of the architecture](../architecture.md#part-v-status-the-one-remaining-handoff).

## Where it sits in the pipeline

The reproduction agent is **S6**, fed by the lockfile and feeding the auditor:

```text
CLASSIFIER ──► LOCKFILE ──► REPRODUCTION agent (srun) ──► run bundle ──► AUDITOR
   (S1)        (the data)          (S6 🚧)                 (evidence)      (S7)
```

Its input is **one lockfile row** (`audit_pool_extracted.jsonl`) carrying
`agent_task`, `central_claim`, `mre_config`, `match_bar`, `tier`, `band`, and
`budget_h100_hours`. See [the lockfile](../selection/lockfile.md) for the row
schema and [select-pool](../selection/select-pool.md) for how rows are chosen.

## The core decision: decouple orchestration from GPU

The agent's *thinking* — LLM calls, file edits, dependency installs, reading
results — is cheap CPU work; only the experiment itself needs a GPU. Renting a GPU
for the whole episode while the LLM reasons would burn the H100 budget on idle
time. So the design physically splits the two:

| layer | runs on | holds |
|---|---|---|
| **Orchestrator** | login or CPU allocation (long-lived, cheap, no GPU) | the agent loop, the budget meter, evidence capture, the bundle writer |
| **GPU work** | a GPU allocation held open for the budget window | nothing but `srun` steps that do real experiment work |

**The allocation is the budget container; each `run_gpu` tool call is one `srun`
step inside it.** This reuses the repo's existing split — `salloc` holds the
nodes, `srun --jobid=$SLURM_JOB_ID --nodes=1 --ntasks=1 … bash -lc '…'` runs each
step — documented on the [SLURM clusters](../slurm/clusters.md) and
[sbatch](../slurm/sbatch.md) pages.

This works because the vLLM server is a **pure completion endpoint** — all
conversation memory lives in the orchestrator's `conversations` dict, not the
server (Part II.4). The agent's *brain* can be any served model while its *hands*
(`srun`) live in a different allocation.

```mermaid
flowchart TD
  classDef cpu fill:#dbeafe,stroke:#1d4ed8,color:#000;
  classDef gpu fill:#dcfce7,stroke:#15803d,color:#000;

  LOCK["LOCKFILE ROW<br/>agent_task · central_claim · mre_config<br/>match_bar · tier · band · budget_h100"]
  ORCH["ORCHESTRATOR (login / CPU — NO GPU)<br/>run_tool_loop core · budget meter · evidence<br/>tools: workspace_bash · run_gpu · read/write/apply_patch · write_repro_yaml/submit"]:::cpu
  GPU["GPU ALLOCATION (held for the budget window)<br/>srun --jobid=$ALLOC bash -lc 'cd workspace && cmd'<br/>per-paper NVMe workspace · per-paper uv venv"]:::gpu
  HAR["HARNESS RE-EXECUTION<br/>final srun runs repro.yaml's scoring entrypoint FRESH<br/>apply match_bar → result.json"]
  AU["AUDITOR (--mode audit)"]

  LOCK -->|agent_task| ORCH
  ORCH <-->|"run_gpu = srun --jobid=$ALLOC …"| GPU
  ORCH -->|"budget exhausted OR agent writes repro.yaml"| HAR
  HAR -->|"run bundle runs/&lt;paper&gt;/&lt;budget&gt;h/&lt;run&gt;/"| AU
```

## Tools the reproduction agent gets

The toolset swaps in through the same `resolve_mode_settings` seam used by the
other modes (a new `--mode reproduce`); the loop body, guardrails, structured-output
finalization, and trace capture are unchanged from Part II.

| tool | runs where | role |
|---|---|---|
| `workspace_bash` | orchestrator / CPU `srun` step | clone the repo at a pinned commit, create the per-paper `uv` venv, install deps, edit files, inspect data — anything that does not need a GPU |
| `run_gpu` | `srun --jobid=$ALLOC` into the GPU allocation | the experiment: training/eval/scoring. Wraps the command, captures out/err/exit, **meters** `gpus × wallclock × hw_multiplier`, enforces a per-step timeout and the **remaining** budget |
| `read_file` / `write_file` / `apply_patch` | orchestrator (workspace-confined) | structured edits; `apply_patch` feeds `patches/author_code.diff` (R11 integrity) |
| `write_repro_yaml` + `submit` | orchestrator | the submission contract: the scoring entrypoint command + where the metric lands. `submit` ends the episode |

!!! note "The brain is provider-agnostic"
    The agent's reasoning runs on **any OpenAI-compatible `/v1/chat/completions`
    server, chosen purely by base URL**. The existing `--vllm-server-url` +
    `build_chat_completion_request` → `post_chat_completion_row` path already speaks
    that protocol, so the brain is swapped by changing the URL — a cluster vLLM
    server or any other gateway — with no provider-specific code in the harness. If
    that endpoint is itself a cluster vLLM server, it is its own allocation, never
    the one metered against the paper's H100 budget.

## The budget meter (the new guardrail)

Where the classifier/auditor [guardrails](../agent-core/guardrails.md) bound
*tokens and rounds*, the reproduction agent's hard guardrail bounds *compute*.
`run_gpu` is wrapped so it refuses once the budget is spent, forcing the agent
toward submission:

```text
remaining = budget_h100_hours − Σ(step.gpus × step.wallclock_h × hw_multiplier)
if remaining ≤ 0:  run_gpu refuses → forces the agent toward write_repro_yaml/submit
```

`hw_multiplier` comes from the H100-equivalence table (report-format R9), so a
GH200 step and an H200 step are both charged in **H100-equivalent hours** — see
[the H100 budget model](../selection/h100-budget.md). Every step appends a
`trajectory.jsonl` row (`{t, h100_hours_consumed, measured, note}`) so
`budget_at_first_pass` is reconstructable.

## The verdict is harness-written, not agent-written

The agent's last act is `repro.yaml` (the submission contract) — **it never writes
`result.json`.** The harness then re-executes the scoring entrypoint *fresh* in a
final `srun` step (CORE-Bench style), parses the metric, applies the lockfile's
`match_bar`, and writes `result.json`:

| `status` | meaning | counts in the success curve as |
|---|---|---|
| `reproduced` | ≥1 in-tolerance measurement within budget | success |
| `out_of_tolerance` | a measurement exists; best is outside tolerance | failure (measured) |
| `no_result` | no valid measurement before budget/termination | failure (unmeasured) |
| `invalid_run` | harness/infra fault | excluded, rerun |

An agent claim that contradicts the harness measurement is recorded as an
`integrity.flag`, **not silently resolved** — the same trust-but-verify posture as
the other modes, applied to execution. The full bundle layout (`report.json`,
checklist R1–R12, failure taxonomy E1–E8, `evidence/`) is the report-format spec;
this page pins only the execution architecture around it. The bundle lands at
`runs/<paper_id>/<budget>h/<run_id>/` for the [auditor](auditor.md) to grade.

!!! example "The run bundle the auditor reads"
    ```text
    runs/<paper_id>/<budget>h/<run_id>/
      result.json     # harness-written verdict (status/measured/within_tolerance/…)
      report.json     # report-format spec (R1–R12 checklist, E1–E8 taxonomy)
      repro.yaml      # the agent's submission contract (scoring entrypoint)
      evidence/       # commands.log · trajectory.jsonl · env.lock · patches/
    ```

## Proposed module layout 🚧

Part III.6 proposes splitting execution out of `reprocli_vllm` (classifier +
auditor) into a new `reprocli_repro` package, which also closes the standing TODO
to separate classification/audit from the harness and keeps every module under the
[300-line rule](../contributing/layout.md):

```text
src/reprocli_repro/                 # the S6 execution agent (mode = reproduce)
  __init__.py
  cli_args.py        # --mode reproduce wiring; reuses resolve_mode_settings seam
  slurm.py           # salloc/srun wrappers, allocation lifecycle, node discovery
  budget.py          # H100-equiv meter + hw_multiplier table (R9)
  workspace.py       # per-paper workspace + uv venv + pinned-commit clone
  evidence.py        # commands.log / trajectory.jsonl / env.lock / patches capture
  tools/
    workspace_bash.py
    run_gpu.py       # the srun-dispatching tool
src/reprocli/report/                # the bundle layer (also feeds the auditor)
  schema.py · validate.py · render.py   # report.json/result.json schema + report.md
  reexecute.py       # harness re-runs repro.yaml → result.json (CORE-Bench style)
```

!!! warning "Sandboxing is a prerequisite at scale"
    The reproduction agent's `run_gpu` / `workspace_bash` run real shell commands.
    Like the auditor's `bash`, they are fine for running our own agents locally, but
    container/seccomp isolation is the prerequisite before running **untrusted paper
    code** at scale. A per-paper `uv` venv already isolates dependency installs so
    one paper's install cannot poison another's.

## See also

- [System architecture, Part III](../architecture.md#part-iii-the-reproduction-agent-s6-designed-not-yet-wired) — the full design this page summarizes
- [The shared agent core](../agent-core/index.md) and [tool loop](../agent-core/tool-loop.md) — the `run_tool_loop` skeleton all three modes reuse
- [SLURM clusters](../slurm/clusters.md) and [sbatch jobs](../slurm/sbatch.md) — the allocation → `srun` step substrate `run_gpu` builds on
- [The lockfile](../selection/lockfile.md) and [H100 budget model](../selection/h100-budget.md) — the input row and the unit the budget meter charges in
