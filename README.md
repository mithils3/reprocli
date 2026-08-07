# reprocli

The harness behind **RECLAIM**, a benchmark that asks whether an agent can
reproduce a published paper's headline claim starting from the artifacts the
authors actually released, graded against the execution evidence the run
produces rather than the agent's own account of it.

The repo holds the whole loop: the dataset pipeline that builds paper bundles
from NeurIPS 2025 + arXiv + OpenReview, the selection/audit machinery that
carves the frozen lockfile, the S6 reproduction agent that runs one paper's
experiment on the cluster, the S7 auditor that grades that run against the
rubric, the vLLM serving layer both attach to by URL, two static web apps for
human verification and run inspection, and the paper itself
(`paper_latex/`, ICLR 2027).

## Status (2026-08-07)

- **Dataset frozen 2026-07-13.** The benchmark is published as the HF dataset
  `Mithilss/reprobench-splits`: split `test` = the 100-paper eval set
  (34/33/33 across the Easy/Medium/Hard artifact tiers, band-stratified by
  compute), split `validation` = the disjoint 14-paper dev set. There is no
  `train` split. The lockfile is the *audited selection* (each paper's central
  claim, pinned `match_target` success bar, artifact signals, compute band,
  audited H100 hours) — it is not a per-paper recipe.
- **Audit rubric frozen 2026-07-16** (`rubric_audit.md`). Post-freeze runs all
  grade against that exact text; the coarse `blocked` verdict is gone and score
  band 3 now means "right experiment, killed by resources before a valid
  number". `rubric_audit_v2.md` is a superseded design record, kept for
  provenance. Scores from before the rubric freeze are not comparable across it.
- **Sweeps are running** across a model roster served on DeltaAI GH200 nodes
  (MiniMax-M2.7 / M3, Qwen3.6-27B, GLM-5.2, DeepSeek-V4-Flash-0731,
  Laguna-S21) plus OpenRouter-hosted brains, one sbatch per model per tier under
  `scripts/reproduce/`. Headline numbers are re-audited with a **pinned
  Sonnet-5 auditor** (`reprocli_claude`) so cross-model comparisons are not
  confounded by self-grading.
- **Two findings drive the paper**: the *availability cliff* (reproduction rate
  collapses as the released artifact stack thins) and the *self-claim gap*
  (most runs that claim a reproduction do not survive a provenance audit of
  their evidence).
- 518 tests pass (`PYTHONPATH=src python3 -m pytest tests -q`).

## Layout

| Path | What it owns |
| --- | --- |
| `src/reprocli_data/` | Dataset pipeline: arXiv e-print sources + OpenReview supplements → one-row-per-paper Parquet bundle. |
| `src/reprocli_vllm/` | Auditor core — audit prompt/rubric assembly, run-dir tools, tool loop, verdict schema + deterministic scoring, H100 band ladder, audit-pool selection. |
| `src/run_arxiv_prompt_vllm.py` | S7 auditor entry point (`--mode audit`), URL-only vLLM/OpenAI-compatible client. |
| `src/reprocli_repro/` | S6 reproduction agent — episode loop, Apptainer sandbox, JIT GPU sessions + compute metering, evidence bundle, report schema, Supabase telemetry. |
| `src/reprocli_claude/` | The same S7 auditor on the Anthropic Messages API, for prompt caching, adaptive thinking, and a schema-bound final turn. This is the pinned grader. |
| `src/reprocli_openai/` | gpt-5.5 web-search re-check of the audit pool's no-code Hard tier. |
| `src/reprocli_serve/` | vLLM launcher: per-model serve profiles, launch flags, health wait, endpoint publication. |
| `scripts/serve/`, `scripts/reproduce/` | sbatch jobs — serve a brain; run a tier's papers through the paired S6→S7 flow. |
| `tools/verify_app/` | Static app for human verification of the classifier's artifact verdicts (Supabase-backed). |
| `tools/run_viewer/` | Static run viewer — live sweep telemetry, transcripts, audits, batch/analysis pages. |
| `tasks/` | Runbooks for serving each model and for the H100 recompute pass. |
| `prompts/`, `rubric_audit.md` | Frozen prompt templates and the frozen audit rubric. |
| `paper_latex/` | The ICLR 2027 submission. |

## The two halves: brains and serving

The code splits into halves that talk only over a published URL:

- **Brains (agent half)** — `reprocli_repro`, `run_arxiv_prompt_vllm.py`, and
  `reprocli_vllm`. These are **URL-only, provider-agnostic clients**: like Codex
  or Claude Code they host no model, they only make chat-completions requests to
  a base URL. There is no embedded in-process server.
- **Serving** — `src/reprocli_serve/` boots vLLM on a GPU node (e.g. 4×GH200,
  TP=4), binds `0.0.0.0`, and publishes its URL for any other Delta/DeltaAI node
  to attach to. `reprocli_serve/profiles.py` is the single source of truth for
  per-model launch flags (parsers, KV dtype, compilation config, context length).

Point a runner at a server with `--vllm-server-url`, `$REPROCLI_SERVER_URL`, or
`$REPROCLI_ENDPOINT_FILE` — so swapping the model is a URL change. With no
endpoint configured the reproduction agent renders prompts as a dry run and the
auditor exits with an error; neither self-hosts a model.

When the base URL is OpenRouter, set `$REPROCLI_OPENROUTER_PROVIDER` to a
provider slug (e.g. `deepseek`) to pin every request to that upstream with
fallbacks off, so a cache-read-dominated run is billed at that provider's own
cache pricing instead of being silently routed to a pricier host. A
comma-separated list sets a preference order (still no fallback beyond the
list). Unset → OpenRouter's default routing, and a no-op against a local vLLM.

## Running the benchmark

**1. Serve a brain** (on a GPU node):

```bash
sbatch scripts/serve/serve_gh200.sbatch          # single node, TP=4
sbatch scripts/serve/serve_multinode.sbatch      # TP=4 + PP=2 across two nodes
# or directly:
PYTHONPATH=src python3 -m reprocli_serve --model <hf-id-or-path> --port 8000
```

**2. Reproduce one paper** (S6). The agent reads the paper's locked target from
the lockfile, works in a per-paper Apptainer sandbox, allocates GPUs just in
time, and meters spend against a per-episode H100-hour ceiling derived from the
paper's compute band:

```bash
PYTHONPATH=src python3 -m reprocli_repro \
  --paper-id 2505.18513 --split dev \
  --vllm-server-url http://<host>:8000/v1
```

The run bundle lands at `<runs-dir>/<arxiv_id>/<budget>h/<run_id>/` with
`report.json`, `evidence/`, and `stats.json`. That directory is the S6→S7
contract.

**3. Audit that run** (S7), grading the bundle against the frozen rubric and the
paper's pinned success bar:

```bash
PYTHONPATH=src python3 src/run_arxiv_prompt_vllm.py --mode audit \
  --claims hf://datasets/Mithilss/reprobench-splits/eval_100.jsonl \
  --runs-dir <runs-dir> --vllm-server-url http://<host>:8000/v1
```

**Paired, one command.** `scripts/reproduce/repro_audit_one.sh <paper-id> [split]`
pins a run id, reproduces, grades *that exact bundle* (never
`<runs-dir>/<id>`, which mixes past attempts), and patches the verdict onto the
run's `repro_runs` row.

**A whole tier** is one sbatch, which serves the brain and then walks every paper
in the tier through the paired flow:

```bash
sbatch scripts/reproduce/dsv4_flash/easy_dsv4_flash.sbatch
```

**Re-audit a finished sweep with the pinned grader:**

```bash
PYTHONPATH=src python3 -m reprocli_claude --batch slurm-2687371 \
  --runs-dir <runs-dir> --upload
```

Needs `ANTHROPIC_API_KEY`; `--batch`/`--upload` also need `SUPABASE_URL` +
`SUPABASE_SERVICE_KEY`.

## Dataset pipeline

`commands/dataset.md` has the copy-paste reference. In short:

```bash
PYTHONPATH=src python3 -m reprocli_data.build_dataset --data-dir data --workers 8
```

Stages run `index,sources,supplements,bundle[,upload]` and are resume-friendly.
Downstream of the bundle, `reprocli_vllm.audit.select_pool` carves the
band-stratified audit pool, `tools/verify_app/` collects the human verdicts on
it, and `tools/rebuild_splits_from_app.py` rebuilds eval-100 + dev from those
verdicts. `tools/split_analysis.py` prints the composition tables and
`tools/plot_audit_pool.py` the figures.

## Development

```bash
PYTHONPATH=src python3 -m pytest tests -q     # 518 tests, no GPU or network needed
ruff check .
```

Project rules live in `CLAUDE.md`: files are sized by cohesion (~500 lines fine,
~800 acceptable for one coherent concern), and a file is split when it mixes
concerns, not to hit a number.
