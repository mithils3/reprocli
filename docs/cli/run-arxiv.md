# `run_arxiv_prompt_vllm.py` — flag reference

The entry point `src/run_arxiv_prompt_vllm.py` runs the **auditor**: it grades
one agent reproduction attempt per paper against the rubric. `audit` is the only
mode. Every flag below is defined in `config/cli_args.py` (`parse_args`);
model-shaped defaults are filled in afterward by `config/minimax_defaults.py`
(`apply_model_defaults`), and the audit prompt/output/tool defaults by
`resolve_mode_settings`. See [the architecture overview](../architecture.md) for
where the auditor sits in the pipeline.

The runner is **URL-only**: it attaches to an already-served brain and never
self-hosts a model. Serve one with [`reprocli_serve`](../slurm/serve.md) and
point the runner at it via `--vllm-server-url`, `$REPROCLI_SERVER_URL`, or a
`$REPROCLI_ENDPOINT_FILE`. With no endpoint the runner exits with an error.

!!! note "How to read the defaults"
    Argparse `default=` values come from `config/cli_args.py` (most string/path
    constants live in `config/config.py`). Flags marked **profile** below have a
    literal argparse default of `None` and are resolved by `apply_model_defaults`
    in `config/minimax_defaults.py` based on `--model`. Flags marked **mode** are
    resolved by `resolve_mode_settings` from the `AUDIT_*` constants.

---

## Mode

`--mode` accepts a single choice, `audit`, and defaults to it. There is no
`classification` or `reproduce` choice on this entry point — dataset construction
and the reproduction agent are separate surfaces (see
[the reproduction agent](../modes/reproduction.md)).

| Flag | Type | Default | Help |
| --- | --- | --- | --- |
| `--mode` | choice `{audit}` | `audit` | Grades an agent reproduction attempt against the rubric (the only mode). |

The auditor reads each paper's `central_claim` plus that paper's run directory
and grades 0–5 with read-only-then-scriptable run-dir tools scoped to
`<runs-dir>/<arxiv_id>` (`AUDIT_TOOLS`): `list_run_files`, `read_run_file`,
`bash`, and `write_run_file` (path-confined to the run dir). See
[the auditor mode](../modes/auditor.md) and
[run-dir tools](../tools/run-dir-tools.md) for the flow.

---

## Brain endpoint

Where the model runs. The runner posts chat-completions to an existing server;
it launches nothing. `resolve_server_url` checks `--vllm-server-url`, then
`$REPROCLI_SERVER_URL`, then the `base_url` in the file named by
`$REPROCLI_ENDPOINT_FILE` (the JSON [`reprocli_serve`](../slurm/serve.md)
publishes). If all three are empty it raises `SystemExit` pointing at
`reprocli_serve`.

| Flag | Type | Default | Help |
| --- | --- | --- | --- |
| `--model` | str | `MiniMaxAI/MiniMax-M2.7` (`DEFAULT_MODEL`) | Model id sent in requests; also selects the sampling/token profile (`apply_model_defaults`). |
| `--vllm-server-url` | str | `None` | Base URL of the served brain. Falls back to `$REPROCLI_SERVER_URL` / `$REPROCLI_ENDPOINT_FILE`. Required (via one of those sources). |
| `--served-model-name` | str | `None` | Model id to send when attached to a server. Defaults to the id the server advertises at `/v1/models` (also reads `$REPROCLI_SERVED_MODEL`). |

---

## Input

Which papers to grade and where their run directories live. The paper list **is**
the claims pool (`load_mre_records`); `--runs-dir` supplies one run directory per
paper.

| Flag | Type | Default | Help |
| --- | --- | --- | --- |
| `--claims` | path | `AUDIT_CLAIMS_DEFAULT` | Audit-pool rows carrying the `central_claim` per paper, injected into the audit prompt. A local JSONL path or an `hf://datasets/<owner>/<name>/<file>` reference. |
| `--runs-dir` | path | `AUDIT_RUNS_DIR_DEFAULT` | Root of the agent reproduction runs; the auditor reads one run dir per paper at `<runs-dir>/<arxiv_id>` via the run-dir tools. |
| `--paper-ids-file` | path | `None` | Grade only the arXiv ids listed in this file (one per line). |
| `--num-prompts` | int | `None` (all papers) | Cap the number of papers processed. Must be ≥ 1. |
| `--prompt-file` | path | `AUDIT_PROMPT_FILE` (**mode**) | Audit prompt template; must contain `{CENTRAL_CLAIM}`. |

!!! tip "Audit defaults come from `config/config.py`"
    The argparse default for `--claims`, `--runs-dir`, `--prompt-file`,
    `--output`, and `--extracted-output` is literal `None`; `resolve_mode_settings`
    then substitutes the `AUDIT_*` constants. The rubric is fixed to
    `AUDIT_RUBRIC_FILE` (`rubric_audit.md`) — it is **not** a CLI flag. Pass an
    explicit value to override the others.

See [the lockfile](../selection/lockfile.md) for what `--claims` rows carry and
[run-dir tools](../tools/run-dir-tools.md) for what the auditor sees under
`--runs-dir`.

---

## Generation & sampling

Token budgets and sampling. Sampling params (`--temperature`, `--top-p`,
`--top-k`) and `--max-model-len` are **profile** defaults — `None` until
`apply_model_defaults` fills them from `--model`.

| Flag | Type | Default | Help |
| --- | --- | --- | --- |
| `--max-tokens` | int | `8192` | Max output tokens per request. |
| `--max-input-tokens` | int | `128000` | Max input tokens admitted into the conversation. Must be ≥ 1. |
| `--max-model-len` | int | **profile**: `196608` (`MAX_MODEL_LEN`) | Model context length; bounds the context-fit check. |
| `--temperature` | float | **profile**: `1.0` | Sampling temperature. |
| `--top-p` | float | **profile**: `0.95` | Nucleus sampling cutoff. |
| `--top-k` | int | **profile**: MiniMax `40`, Kimi unset | Top-k cutoff. If set, must be ≥ 1. |

!!! warning "Context-fit check"
    `parse_args` enforces `--max-input-tokens + --max-tokens <= --max-model-len`
    and errors out otherwise. Because `--max-model-len` is a profile default,
    lowering it can make the default token budgets invalid.

---

## Tool-loop budgets

How long the auditor keeps calling run-dir tools before the forced final-answer
turn (`runtime/tool_loop.py`). The audit mode sets `use_tools = True`.

| Flag | Type | Default | Help |
| --- | --- | --- | --- |
| `--tool-rounds` | int | `10` | Max tool-calling rounds before the final-answer turn. Must be ≥ 1. |
| `--request-workers` | int | `8` | Concurrent papers in flight; clamped to `min(workers, len(papers))`. Must be ≥ 1. |

The repeated-call cutoff is fixed to `MAX_REPEATED_TOOL_CALLS`
(`resolve_mode_settings`) and is not a CLI flag. See [the tool loop](../agent-core/tool-loop.md)
and [the guardrails](../agent-core/guardrails.md) for how these budgets are spent.

---

## Output sinks

Where verdicts, extracted records, and traces are written. `--output` /
`--extracted-output` are `None` at parse time and resolved to the `AUDIT_*`
constants.

| Flag | Type | Default | Help |
| --- | --- | --- | --- |
| `--output` | path | `AUDIT_DEFAULT_OUTPUT` (**mode**) | Raw per-paper verdict JSONL. |
| `--extracted-output` | path | `AUDIT_DEFAULT_EXTRACTED` (**mode**) | Parsed/structured verdict records JSONL. |
| `--trace-output` | path | `None` → `trace_output_path(--output)` | Per-round tool-call trace JSONL. Derived from `--output` when unset (`runtime/trace_io.py`). |
| `--save-round-jsonl` | flag | off | Write per-round intermediate JSONL during the loop (`runtime/tool_loop.py`). |
| `--stream-first-response` | flag | off | Stream the first response of the first paper to stderr (round 0 only). |

---

## Validation rules

`parse_args` rejects the run (via `parser.error`) when any of these fail:

- `--tool-rounds` ≥ 1
- `--num-prompts` ≥ 1 (when provided)
- `--request-workers` ≥ 1
- `--max-input-tokens` ≥ 1
- `--top-k` ≥ 1 (when provided)
- `--max-input-tokens + --max-tokens` ≤ `--max-model-len`

!!! example "Audit a batch of agent runs"
    ```bash
    python3 src/run_arxiv_prompt_vllm.py \
      --mode audit \
      --vllm-server-url "$SERVER_URL" \
      --claims hf://datasets/Mithilss/neurips-2025-audit-pool/audit_pool_extracted.jsonl \
      --runs-dir <runs-dir> \
      --output outputs/v5/audit.jsonl \
      --extracted-output outputs/v5/audit_extracted.jsonl
    ```

---

## See also

- [Serving (`reprocli_serve`)](../slurm/serve.md) — stand up the brain the runner attaches to.
- [The lockfile](../selection/lockfile.md) — what `--claims` rows carry.
- [Auditor mode](../modes/auditor.md) — what the audit pass computes.
- [Run-dir tools](../tools/run-dir-tools.md) — the auditor's toolset over `--runs-dir`.
- [The tool loop](../agent-core/tool-loop.md) and [structured output](../agent-core/structured-output.md).
