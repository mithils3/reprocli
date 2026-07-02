# Refactor Report — repro-next, 2026-07-01 → 2026-07-02

Aggressive residue-removal refactor of the reprocli codebase, executed as 47 commits
(`pre-refactor` tag `791bc4f` → `f0ea062`), net **−5,213 lines** (2,166 insertions,
7,379 deletions across 134 files). Every commit left the test suite green; the three
live surfaces — S6 reproduction agent, S7 auditor, `reprocli_serve` — were verified
after every batch.

## Before / after

| Metric | Before | After | Δ |
|---|---|---|---|
| `src/` Python LOC | 14,529 | 12,116 | −2,413 (−17%) |
| `tools/` Python LOC | 2,202 | 1,833 | −369 |
| `tests/` Python LOC | 4,890 | 4,704 | −186 (net of new tests) |
| repro CLI flags (`add_argument`) | 48 | 21 | −27 |
| vLLM runner CLI flags | 41 | 22 | −19 |
| serve CLI flags | 33 | 33 | 0 (protected) |
| Test results | 354 passed / 1 skipped | 340 passed / 1 skipped | every removed test exercised deleted code; added 6 CLI smoke tests, 7 postgrest tests, 1 gpu_session test |
| Ruff findings | 1 (F401) | 0 | lint fully clean |
| Source/test files over the 300-line rule | 2 (`inputs.py` 383, `reference.py` 310) | 0 | plus 2 oversized test files split |
| Dependencies | 4 | 4 | all still genuinely consumed (`datasets`, `huggingface_hub`, `openreview-py`, `vllm`) |

## What was deleted (kill list, executed)

**Era residue — classification/construction pipeline (Batches A, C):**
- Classification mode of `run_arxiv_prompt_vllm.py` — **audit is the only mode**
  (`--mode` kept for script compatibility, `choices=("audit",)`).
- The entire MCP tool stack: `mcp_client`, `github_mcp`, `huggingface_mcp`,
  `huggingface_tree`, `mcp_results`, `paper_bundle`, `papers/bundles`,
  `papers/supplements` (~1,100 LOC, classifier-only). `web_tools.py` stripped to the
  auditor dispatch; `fetch_url` moved to `tools/web_fetch.py`.
- HF run uploader (`hf_upload.py`, `--hf-*` flags); `OUTPUT_WRITE_LOCK` relocated to
  its only consumer (`tool_loop.py`).
- Construction-era CLIs: `reference.py` bulk-materialize CLI (+`commands/reference.md`),
  `data/get_premade.py`, `reprocli_data/publish_bundle.py`, `runtime/rerun.py`,
  `tools/build_eval_dev_splits.py`, `tools/tier_composition.py`.
- Scripts: `scripts/kimi_k2_6/`, classification + repin sbatches,
  `delta_scripts.sh`, `serve_attach_runner.sh`. (Standalone provenance tools
  `merge_repin_into_splits.py` and `upload_audit_pool_hf.py` were kept.)

**Embedded vLLM server (Batch D):** `vllm/server.py` + `vllm/cache.py` deleted. The
runner is **URL-only**: no endpoint URL → hard error pointing at `reprocli_serve`; the
repro harness without a URL is dry-run only. `reprocli_serve/profiles.py` is the single
source of serve profiles (the duplicated serve half of `minimax_defaults.py` died;
what remains sets only client-side request fields).

**Dead flags (Batches B, C, D, E):**
- repro: `--temperature --top-p --top-k --max-tokens --max-input-tokens
  --max-model-len --request-workers --trace-output --microcompact* --summarize-*
  --num-prompts --seed --prompt-file --bundle-dataset --build-venv --venv-python
  --cluster --account --gpus-per-node --hw --scratch-root --modules`.
  Attributes still consumed internally are named constants in `cli_resolve.py`
  (same values as the old defaults). `--partition` and `--apptainer-image` kept.
  **deltaai is the only cluster profile** (delta-h200 deleted).
- runner: `--dataset --hf-repo --hf-path-in-repo --hf-private --hf-upload-every
  --structured-outputs-backend --tokenizer-mode --block-size --max-repeated-tool-calls
  --rubric-file --tensor-parallel-size --kv-cache-dtype --distributed-executor-backend
  --compilation-config --mm-encoder-tp-mode --vllm-cache-dir --gpu-memory-utilization
  --tool-call-parser --reasoning-parser` (`--rubric-file` hardcoded to
  `rubric_audit.md`; the serve-side flags of the same names are untouched).
- Plus function-level kills: venv machinery in `workspace.py`, random-sampling branch
  in episode selection, unreachable io.py fallbacks, dead `requests` transport
  branches, orphan helpers (`GOOD_EXIT`, `REPRO_TOOLS`, `write_env_lock`, …).

## Structural changes (Phase 3)

- **`src/reprocli_repro/postgrest.py`** (68 lines): the one urllib PostgREST transport
  behind `supabase_sink`, `audit_upload`, and `audit_sink` — payloads, URLs, headers,
  and per-caller retry behavior byte-identical; the dead `requests` branches removed.
- **`inputs.py` split** 365 → 142 lines (+ `dataset.py`, `prompt_render.py`).
- **`slurm._require_target`** raises `SlurmConfigError` instead of `SystemExit`
  (surfaced as a clean acquire failure — the old `BaseException` escaped the tool
  dispatch's `except Exception`).
- `live_log` uses a public `call_arguments` accessor; duplicate `bounded()` helpers
  deduped; oversized test modules split (`test_run_gpu_dispatch.py`,
  `test_tools_plan_bash.py`).
- Docs modernized site-wide against the current code (architecture, quickstart, CLI
  references regenerated from the real argparse, source-tree map, 0 broken internal
  links, mkdocs builds clean). `reproduction-agent-plan.md` is now a banner-marked
  historical page.

## Breaking changes

1. Every flag listed above is gone; invocations passing them now fail at parse time.
   All live scripts/runbooks in-repo were updated and the exact sbatch/audit
   invocations were smoke-tested, but any *external* wrapper passing deleted flags
   (e.g. `--cluster deltaai`, `--no-build-venv`) must drop them.
2. `run_arxiv_prompt_vllm.py` without an endpoint URL now exits with an error instead
   of starting an embedded vLLM server.
3. Classification mode no longer exists; `--mode` accepts only `audit`.
4. Sampling parameters (temperature 1.0, top_p 0.95, top_k 40, max_tokens 8192,
   max_input_tokens 128000) and compaction thresholds are fixed constants on the repro
   side — changing them now means editing `cli_resolve.py`.
5. In audit mode a hallucinated non-audit tool call (e.g. `fetch_url`) returns an
   unknown-tool error instead of silently executing a classifier-era handler.
6. The repro operating prompt no longer contains "(Phase 0 placeholder operating
   prompt; …)" — a model-facing string change.
7. `python -m reprocli_vllm.runtime.rerun` and the bulk
   `python -m reprocli_repro.reference` CLIs are gone.

## Deliberately kept

- The GPT-5.5 recheck trio (C5 declined) and the dev15 sweep scripts with no unified
  driver (C6 declined).
- The two decoupled loop skeletons (`reprocli_repro/loop.py` vs
  `runtime/tool_loop.py`) — accepted debt, now documented as a diverged fork.
- The endpoint-file JSON writer/reader duplication between serve and clients.
- Supabase schema, payload shapes, and the S6→S7 run-dir contract — frozen live
  interfaces, byte-identical.
- `prompts/*.txt` untouched.

## Verification performed

- Full suite + ruff after every one of the 47 commits (enforced per batch).
- End-to-end offline dry-run: `python -m reprocli_repro --paper-id 2502.06067 --split
  dev --no-reference` — lockfile fetch, tier/band/budget resolution, run-dir setup,
  prompt render, clean "dry run: no brain attached" exit.
- `run_arxiv_prompt_vllm.py --help` + a dry argparse of the exact `--mode audit` argv
  used by `repro_audit_one.sh`; `python -m reprocli_serve --help`; smoke tests mirror
  all three live invocations.
- mkdocs site builds with zero broken internal links.

**Remaining validation (needs DeltaAI GPU time):** one real paper through
repro → audit → `audit_upload` on the dev split. The runbook
(`scripts/reproduce/run_reproduce_minimax_m2.md`) is updated for the new CLI.

**Flagged for a decision:** `prompt_render.py` still renders the literal
`(classifier verification: …)` label inside the live reproduction prompt — text sent
to the model, so it was left alone; rewording it is a prompt change, not a refactor.
