# REFACTOR_PLAN.md — aggressive simplification of reprocli

Phase 0 output. Evidence: 5 exhaustive module maps (usage, repro harness, vllm client,
data/misc, tools), spot-verified zero-caller greps, git history, and live Supabase data
(105 runs / 20,634 events through 2026-07-01 — runs are being produced **today**, so
Phase 2/3 lands between batches and never renames a Supabase column).

**Baseline metrics** (Python only, `__pycache__` excluded):
`src/` 14,529 LOC · `tools/` 2,202 · `tests/` 4,890 · CLI flags: repro 48, vllm-runner 41, serve 33 · deps: 4 (`datasets`, `huggingface_hub`, `openreview-py`, `vllm`).

---

## (a) The real requirements

Reconstructed from scripts/, git churn, and the Supabase run data. Three live paths, in
priority order:

1. **The scored sweep (S6→S7→upload)** — `serve` a brain (`python -m reprocli_serve`
   on ghx4, or OpenRouter) → `python -m reprocli_repro` reproduces a lockfile paper in
   an Apptainer sandbox with metered JIT-SLURM GPU steps → `python
   src/run_arxiv_prompt_vllm.py --mode audit` grades the exact bundle →
   `python -m reprocli_repro.audit_upload` PATCHes the verdict onto the Supabase row.
   Drivers: `scripts/reproduce/repro_audit_one.sh`, `reproduce_easy_minimax_m2.sbatch`.
2. **Live observability** — `supabase_sink`/`live_log`/`run_stats` streaming every run
   to `tools/run_viewer` (heaviest-used table is `repro_events`; tags/activity features
   are genuinely used). Schema is a frozen interface.
3. **Lockfile provenance & maintenance** — `tools/rebuild_splits_from_app.py` (built the
   canonical 2026-06-24 lockfile), `merge_repin_into_splits.py` + `upload_audit_pool_hf.py`
   (the only sanctioned mutation path), `verify_app`'s data layer (`papers.json` is
   app-truth), `split_analysis.py` (edited today), `reprocli_data` pipeline (the only way
   to regenerate the bundle dataset the sweep streams at runtime — dormant, not dead).

Everything else in the repo served the **finished** dataset-construction era
(classification, model trials, recheck, old split builders) and is residue by the
prime directives.

**Never touch:** `data/`, `outputs/`, `notes/`, `prompts/*.txt` content, `rubric_audit.md`,
`tools/run_viewer/supabase_schema.sql` column shapes, `verify_app/public/` (provenance),
the S6→S7 run-dir contract (pinned by `tests/repro/test_audit_bundle.py`), and the
audit-mode CLI exactly as `repro_audit_one.sh` / the easy sbatch invoke it.

---

## (b) Kill list

Verdicts: **KILL** (verified dead — every caller traced), **KILL-C** (dead but removal
touches live files; care needed), **CONFIRM** (see section below; not executed without
your sign-off).

### Whole files / dirs (verified zero callers)

| # | Target | Evidence | ~LOC |
|---|--------|----------|-----:|
| K1 | `src/data/get_premade.py` (KILL) | zero importers; superseded by pipeline index stage (commit 84933dc); docstring references a nonexistent filename | 120 |
| K2 | `src/reprocli_vllm/runtime/rerun.py` + `tests/runtime/test_rerun.py` (KILL) | tests-only importer; advertised `python -m reprocli_vllm.rerun` broken since the move under `runtime/` (cli_args.py:108, docs/cli/run-arxiv.md:74 — fix both); classification-era | 250 |
| K3 | `src/reprocli_data/publish_bundle.py` (KILL) | no script callers; near-duplicate of `build_dataset --stages bundle,upload`; update commands/dataset.md + docs/cli/build-dataset.md | 76 |
| K4 | `tools/build_eval_dev_splits.py` (KILL) | zero references anywhere; superseded same-day by `rebuild_splits_from_app.py` with a *diverging* drop-vs-flip policy — an active trap | 207 |
| K5 | `tools/tier_composition.py` (KILL) | no callers since 06-15; keyword-tagging approach explicitly abandoned by `split_analysis.py`; reads a pre-pool extract, not the lockfile | 130 |
| K6 | `scripts/cluster/delta_scripts.sh` (KILL) | snippets paste-buffer, not runnable (sequential `--pty` sruns); references Delta accounts, not DeltaAI | 60 |
| K7 | `scripts/serve/serve_attach_runner.sh` (KILL) | no script calls it; its 4-line recipe is inlined in every real sbatch | 40 |
| K8 | `docs/apps/v3-viewer.md` + `tools/v3_viewer` refs in `docs/contributing/layout.md` (KILL) | documents a tool that does not exist in the tree; superseded by run_viewer | — |

### Dead functions / constants / branches (KILL)

| # | Target | Evidence |
|---|--------|----------|
| K9 | `workspace.resolve_and_prepare` | zero callers (grep-verified) |
| K10 | `evidence.write_env_lock` + the empty `env.lock` touch at init (KILL-C) | zero callers; the advertised "resolved environment" evidence file is always empty — check the audit prompt/rubric doesn't reference `env.lock` before removing the touch |
| K11 | `supabase_sink.GOOD_EXIT` | defined, never read |
| K12 | `tools/files.py` `_resolve(writable=False)` branch | "retained for callers that only inspect paths" — none exist |
| K13 | `tools/__init__.REPRO_TOOLS` module constant | live path uses `build_repro_tools`; port the one test to it |
| K14 | `vllm/io.py:42,45` `or WEB_TOOLS` / `or FINAL_RESPONSE_FORMAT` | both arg namespaces always set these; the fallback silently hands the wrong toolset — make missing attrs raise |
| K15 | `compaction` `soft_limit_chars` param | guardrails always passes 0; branch exercised only by tests — hardcode |
| K16 | `supabase_sink`/`audit_sink` `import requests` try/except double transport (KILL-C) | one canonical transport: urllib (already the retry.py path); `requests` isn't in requirements.txt |

### Dead flags (KILL-C — each removal also deletes its backing code and docs rows)

- **`reprocli_repro/cli_args.py`** (~24 of 48 `add_argument`s never non-default in any
  script/doc/test): `--num-prompts`, `--seed` (+ the random-sampling path in
  `inputs.select_episode_rows`), `--prompt-file`, `--bundle-dataset`, `--build-venv`,
  `--no-build-venv`, `--venv-python` (+ the upfront-venv path in `workspace.py` — agents
  build their own venvs in-sandbox), `--scratch-root` + `Cluster.scratch_root` (field
  never read — "Phase 7" never landed), `--modules` + `Cluster.modules` (help text admits
  inert), `--model`, `--request-workers`, `--trace-output`, all six `--microcompact*` /
  `--summarize-*` knobs (hardcode as constants), `--hw`.
- **`reprocli_vllm/config/cli_args.py`**: `--structured-outputs-backend`,
  `--tokenizer-mode`, `--block-size`, `--hf-path-in-repo`, `--hf-private`,
  `--hf-upload-every`, `--max-repeated-tool-calls`, `--rubric-file` (hardcode
  `rubric_audit.md`), `--vllm-cache-dir` (dies with the embedded server, C2).
- Keep even though rarely varied: `--tool-rounds`, `--budget-h100-hours`, `--lockfile`,
  `--split`, `--paper-id`, `--run-id`, endpoint/model flags, `--output`,
  `--save-round-jsonl`, `--runs-dir`, `--no-reference`, `--partition`, audit-side
  `--max-input-tokens`/`--max-tokens`/`--max-model-len`/`--trace-output` (all
  evidenced in real invocations).

### Stale-text sweep (KILL — misleads operators today)

`cli_resolve.py` still sends "(Phase 0 placeholder operating prompt)" **on every live
run**; `cluster.py` docstring describes the opposite of the held-session design;
`run_dir_tools.py` / `audit/inputs.py` claim the auditor tools are "read-only"
(write_run_file + bash exist); `__main__.py` end message says Phase 5 is pending;
`run_reproduce_minimax_m2.md` §5 says Phases 5–6 "not yet wired" (they shipped);
`commands/classification.md` calls classification "the active production path";
`loop.py`'s fork comment cites a drifted `tool_loop.py:122`.

---

## CONFIRM WITH ME (executed only on your explicit approval)

> **Decisions 2026-07-01:** plan approved. C1, C2, C3, C4, C7 **approved**.
> C5 **declined** — the GPT-5.5 recheck trio stays. C6 **declined** — the dev15
> sweep scripts stay and no unified sweep driver is built; migration step 13 is dropped.

| # | Item | Recommendation | The ambiguity |
|---|------|----------------|----------------|
| C1 | **Classification mode + MCP stack** (~2,300 LOC): `mcp_client`, `github_mcp`, `huggingface_mcp`, `huggingface_tree`, `mcp_results`, `paper_bundle` tool, `papers/bundles.py`, `papers/supplements.py`, `WEB_TOOLS`/`WEB_SYSTEM_MESSAGE` in config.py, classification mode in `run_arxiv_prompt_vllm.py`, `scripts/{minimax_m2,minimax_m3}/paper_classification*.sbatch`, `commands/classification.md`, their tests | **Delete.** Lockfile is frozen; nothing on the sweep path touches MCP; the repro agent imports only `fetch_url_tool`/`parse_tool_arguments` (moved out first, R2). Tag `pre-refactor` makes re-classification a checkout away | You may want to re-classify a swapped-in paper before ICLR; that flow would need a git-tag resurrection |
| C2 | **Embedded vLLM server**: `vllm/server.py`, `vllm/cache.py`, the serve-flag half of `minimax_defaults.py`, embedded-fallback branch in `endpoint.py` | **Delete.** Only caller with no `--vllm-server-url` is the Kimi trial sbatch (itself C4). Kills the documented byte-for-byte serve-flag duplication with `reprocli_serve/profiles.py` — one source of truth. Breaking: no-URL becomes dry-run (repro) / hard error (runner) instead of a silent local boot | It's README-documented default behavior |
| C3 | **`delta-h200` cluster profile** + override flags `--account`/`--gpus-per-node` + uncalibrated a100/b200/h200 `HW_MULTIPLIER` entries | **Delete; hardcode deltaai/GH200.** No script targets it | Any plan to run on Delta H200 (or another cluster) before the sweep finishes? |
| C4 | **`scripts/kimi_k2_6/`** (sbatch + runbook) | **Delete.** Kimi wasn't selected as brain; sbatch header requests 8 GPUs/node on a 4-GPU partition (never ran as written) | Provenance-only value |
| C5 | **GPT-5.5 recheck trio** (~800 LOC): `src/reprocli_openai/recheck.py`, `tools/verify_app/publish_openai_recheck.py`, `report_openai_recheck.py` | **Delete.** One-shot complete, results baked into papers.json → lockfile; its `OUT_DIR` already points at a nonexistent directory, so a rerun would silently restart from zero anyway | A future paper swap into Hard/no-code could want a recheck — app is the truth source regardless |
| C6 | **Sweep-driver consolidation**: generalize `reproduce_easy_minimax_m2.sbatch` (already TIER-parameterized, RESUME, paired audit) into the single sweep driver; delete `reproduce_dev15_minimax_m2.sbatch` + `run_dev15.sh` (~80% duplicated loop, both missing the audit stage) | **Do it** — this is the highest-value structural change and it's *your* active tooling | Timing: runs in flight today; also confirms dev sweeps should go through the paired-audit path |
| C7 | Repro-side sampling flags `--temperature`/`--top-p`/`--top-k` (never set; serve profiles own sampling) | **Delete, hardcode defaults** | Cross-model sweeps might someday want per-run sampling |

---

## (c) Target architecture

**Minimal-motion, not clean-slate**: the sweep is imminent and producing data today; the
current `reprocli_repro` layering (cluster/sandbox/slurm/gpu_session verified clean and
non-overlapping) is *right*. The wrongness is (1) residue mass, (2) the repro agent
depending on classifier grab-bags, (3) three copies of Supabase HTTP plumbing.

```
src/
  reprocli_vllm/            # shrinks to the shared agent substrate + auditor
    vllm/                   #   client, endpoint, retry, io      — the ONLY network seam to the brain
    runtime/                #   tool_loop (auditor loop), loop_guards, run_health, trace_io,
                            #   live_events, audit_sink, audit_rows, mre_records
    audit/                  #   audit, h100, inputs, select_pool  — Stage-7 + selection provenance
    schema/                 #   output, audit
    tools/                  #   run_dir_tools (auditor), shared: web_fetch (fetch_url moved out of
                            #   web_tools), result_limits, http_utils
    config/                 #   config.py SPLIT: shared budgets/function_tool stay; audit prompt
                            #   stays; classifier prose dies with C1. cli_args slims per kill list
  reprocli_repro/           # unchanged layout; slimmed cli_args/cli_resolve; supabase_rows +
    ...                     #   supabase_sink + audit_upload share ONE postgrest.py helper
    postgrest.py            #   NEW (~60 LOC): headers/_request/now_iso used by all three sinks
  reprocli_serve/           # unchanged — profiles.py becomes the single source of serve flags (C2)
  reprocli_data/            # unchanged minus publish_bundle.py — dormant regeneration tooling
  run_arxiv_prompt_vllm.py  # audit-first entry point (classification mode dies with C1)
tools/                      # run_viewer + verify_app data layer + the 3 lockfile tools + analysis
scripts/                    # serve/ + reproduce/ (one sweep driver + repro_audit_one.sh) + cluster/
```

**Core data types** (unchanged, made explicit): lockfile row → `EpisodeInput` →
`ExecutionContext` (workspace/budget/session/evidence/sandbox) → `report.json`
(REPORT_JSON_SCHEMA) → audit verdict row (AUDIT_RESPONSE_FORMAT) → Supabase
`repro_runs`/`repro_events` rows (frozen schema).

**I/O at the edges:** brain HTTP only via `vllm/client.py`+`retry.py`; Supabase only via
the sinks (now one shared postgrest helper); SLURM/subprocess only via `slurm.py`+
`env.exec_argv`; HF only via `inputs.py`/`reference.py`/`mre_records.py`. Pure center:
budget, compaction, rows builders, report validation, audit finalize, run_stats.

**Deliberate duplication kept** (documented, not accidental): the endpoint-file JSON
contract has an independent writer (`reprocli_serve/endpoint.py`) and reader
(`reprocli_vllm/vllm/endpoint.py`) — that's the two-halves decoupling contract. The two
loop skeletons (`loop.py` fork of `tool_loop.py`) stay — unifying them pre-sweep is
risk without payoff; recorded as accepted debt with the fork comment fixed.

**Bug fixed in passing** (correctness, not feature): `slurm._require_target` raises
`SystemExit`, which escapes the dispatcher's `except Exception` and can unwind the whole
multi-episode loop from inside a tool thread → raise a normal exception instead.

**300-line rule**: `inputs.py` 383 → under 300 after the sampling path dies (else split
run-dir resolution out); `reference.py` 310 → under 300 after its construction-era CLI
half dies.

## (d) Migration order

Each step = one commit, repo green (`PYTHONPATH=src python -m pytest tests/` + smoke).

**Phase 1 — safety net** (no kill-list tests):
1. Smoke script: repro dry-run (`python -m reprocli_repro --paper-id <dev id> --no-reference`
   renders a prompt offline), audit-mode argparse smoke, `repro_audit_one.sh -h` paths.
2. Record commands: tests `PYTHONPATH=src python -m pytest tests/`; lint `ruff check src tools`
   (new dev-only config, zero runtime deps); no typechecker (not adding one).

**Phase 2 — slash** (order: independent → dependent):
3. K1–K8 whole files, one commit each. 4. K9–K16 dead functions/branches.
5. Repro dead flags + backing code (inputs sampling path, workspace venv path, cluster
   dead fields). 6. Runner dead flags. 7. Stale-text sweep. 8. C-items as approved,
   biggest first (C1 → C2 → C5 → C3/C4/C7). 9. Purge newly unreachable tests/docs/deps
   (`openreview-py` stays — pipeline; `datasets`/`huggingface_hub`/`vllm` stay).

**Phase 3 — redesign:**
10. Move `fetch_url_tool`/`parse_tool_arguments` out of the `web_tools` grab-bag (R2 —
    precondition for C1). 11. Split `config.py` concerns. 12. `postgrest.py` shared
    helper; kill the requests/urllib double transport; export `live_log` args accessor
    (no more `_arguments` private reach). 13. C6 single sweep driver. 14. SystemExit fix.
15. 300-line fixes (`inputs.py`, `reference.py`). 16. `bounded()`/`_bounded` dedupe.

**Phase 4 — verify & report:** full suite + dry-run + one real paper through
repro→audit→upload on dev; README/docs updated to the new surface (incl. deleting flag
reference rows); `REFACTOR_REPORT.md` with before/after metrics and every breaking change.

**Expected removal:** ~4,000–4,500 LOC of `src/`+`tools/` Python (~25%) plus their tests,
~30 CLI flags, 2 script dirs — more if all CONFIRM items are approved.

## Breaking changes (all intentional, none silent)

- Removed CLI flags per kill list (repro + runner); removed `python -m
  reprocli_data.publish_bundle` (use `build_dataset --stages bundle,upload --force`).
- If C1: `--mode classification` removed; `run_arxiv_prompt_vllm.py` becomes the auditor
  entry point. If C2: no embedded server — a brain URL is required (repro stays dry-run
  capable). If C3: single hardcoded cluster profile. If C6: dev sweeps run through the
  unified paired-audit driver.
- Resurrection point: git tag `pre-refactor` before Phase 2 starts.
