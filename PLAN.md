# Code-reduction plan, pass 1 (branch `reduce/pass-1`)

Inputs: eight read-only audits (scratchpad `audit_P1..P8.md`). Ranking = (LOC saved x confidence) / risk.
Excluded automatically: every high-risk item, every public-API removal without zero-caller evidence,
every rewrite in a file without test coverage, docstring compression (documentation is not code),
test-boilerplate removal that changes how tests can be invoked, and consolidations that need a new
shared helper. Operator escape hatches with zero callers but a live effect (`--partition`,
`--apptainer-image`, `--prune-workspace-*`, `--reference`, `--dry-run`, `--prompt-file`,
`--request-workers`, `REPRO_QUEUE_GRACE_HOURS`) are kept on purpose.

Work packages have no file overlap. Cross-partition items run in a sequential package (WP-S) after
the parallel wave. Deleted public symbols are logged in REMOVED.md.

## WP-A  repro core (P1)
Files: `src/reprocli_repro/report/`, `src/reprocli_repro/{loop,cli_args,__main__,prompt_render,inputs,env,reference,budget,transcript}.py`;
tests `tests/repro/test_{report,inputs,env,reference,budget,transcript,loop}.py`.
1. Flatten `report/` package: `git mv src/reprocli_repro/report/report.py src/reprocli_repro/report.py`, delete `report/__init__.py` (pure re-export shim), drop the now-dead `__all__` in report.py. Every importer uses `reprocli_repro.report`, unchanged. (~46)
2. `prompt_render.render_reproduce_prompt`: remove the unused `run_paths` parameter (ruff ARG001) and its TYPE_CHECKING import; update callers and the four `resolve_run_paths` setup lines in test_inputs.py. (~12)
3. `env.env_inner`: inline into its single caller at env.py:60. (~11)
4. `reference.load_bundle` and `reference.arxiv_matches`: inline into their single callers. (~15)
5. `budget.charge()`: zero production callers; delete with `test_budget.py:59-63` and its import. (~14)
6. `report.measurement_schema()`: nullary dict-literal function called once; inline. (~4)
7. `tests/repro/test_transcript.py`: delete `test_sweep_wall_note_empty_value_returns_none` (same falsy branch as the unset test). (~5)

## WP-B  repro infra (P2)
Files: `src/reprocli_repro/{batch_runs,slurm,cluster,gpu_session,metrics_beacon}.py`;
tests `tests/repro/test_{batch_runs,slurm,cluster,gpu_session,metrics_beacon,sandbox,audit_bundle}.py`.
1. `batch_runs.py`: delete the `python -m reprocli_repro.batch_runs` CLI (`resolve_bundles`, `parse_args`, `main`, lines ~152-211, plus the argparse/os/sys imports and the usage example at docstring lines 14-15; keep the docstring's first paragraph, the paper cites it). `reprocli_claude` imports only `Run, fetch_runs, select_runs, bundle_for, newest_bundle`. Delete `test_resolve_splits_present_from_missing`. Log in REMOVED.md. (~71)
2. `slurm.SessionHandle.command`: write-only field, delete the field and its two writers. (~8)
3. `cluster.cluster_names()`: zero non-test callers; delete, rewrite `test_cluster.py:61` to `assertEqual(set(defaults), {"deltaai"})`, drop the import and `test_default_is_a_known_name`. (~11)
4. `metrics_beacon.Beacon.failed`: write-only counter (lines 197, 230-233, 270); delete. (~6)
5. `gpu_session._acquire_error`: inline into its single caller. (~5)
6. `tests/repro/test_sandbox.py`: delete `ExecArgvIntegrationTests` (its two halves are `test_env.py` tests on the same branch). (~13)
7. `tests/repro/test_metrics_beacon.py`: replace the copied `_ctx` with an import from `tests.repro.test_gpu_session` (the repo already uses cross-test imports in tests/claude), keeping the `budget_hours` default. (~15)
8. `tests/repro/test_audit_bundle.py`: replace the hand-copied `run_dir_for` with `from run_arxiv_prompt_vllm import run_dir_for` so the test asserts the real function. (~5)

## WP-C  repro tools (P3)
Files: `src/reprocli_repro/tools/{__init__,fetch,files}.py`; tests `tests/repro/test_{run_gpu,run_gpu_dispatch,tools,tools_plan_bash}.py`.
1. Merge `test_run_gpu_dispatch.py` into `test_run_gpu.py` (its first 48 lines are a byte-identical copy of the helpers); delete the dispatch file. (~48)
2. Merge `test_tools_plan_bash.py` into `test_tools.py` (identical `_ctx` and imports); delete the plan_bash file. (~18)
3. `tools/fetch.py`: fold the schema into `tools/__init__.py` and register the handler as `lambda arguments, _ctx: fetch_url_tool(arguments)`; delete fetch.py. Tool name and arguments unchanged. (~20)
4. `tools/__init__.py`: `_DEFAULT_GPUS_PER_NODE` import-time `resolve_cluster()` is only a default no caller uses; make `gpus_per_node` required and drop the `DEFAULT_CLUSTER, resolve_cluster` import. (~5)
5. `files.py`: inline `locate_by_suffix`, `_display_path`, `_roots` into their single callers. (~19)

## WP-D  vllm runner (P4)
Files: `src/reprocli_vllm/**`, `src/run_arxiv_prompt_vllm.py`; tests `tests/{vllm,runtime,schema,audit,tools}/`.
Do NOT edit `tests/smoke/`, `tests/repro/`, or anything under `src/reprocli_repro`, `src/reprocli_claude`.
1. Delete the SSE streaming client: `client.py:227-346` (`stream_chat_completion`, `post_streaming_chat_completion`, `StreamedResponseBuilder`), the `stream` parameter of `post_chat_completion_row`, `tool_loop.py:83,90`, the `--stream-first-response` flag in `config/cli_args.py`, and `test_streamed_body_is_stripped_too`. Log the flag in REMOVED.md. (~143)
2. Delete the classifier-era finalizer: `run_health.finalize_extracted_row`, `verification_status`, `signal_verification_states`, `without_score`, `UNVERIFIED_SIGNAL_STATES`, `INCOMPLETE`, `WEB_VERIFICATION_ALIAS` (inline `DEGRADED` into `degraded_row`), the `else` branch in `io.extracted_response` (leave the `mode` parameter in the signature for now; WP-S drops it), `h100.audit_h100_fields`, `legacy_audit_fields`, `basis_text`, and the tests pinning them in `test_run_health.py:39-110` and `test_h100_audit.py:38-72`. KEEP `h100.recomputed_hours` and `arithmetic_mismatch` (named as the reference implementation in tasks/h100-recompute-eval100.md) and everything in `schema/output.py`. Migrate `test_tool_loop_outputs.py:24` to `mode="audit"`. (~230)
3. `--min-p`: no such flag exists; delete the `min_p` guard in `io.py:43-44`, the `args.min_p = getattr(...)` line in `config/cli_args.py:130`, and `test_min_p_included_only_when_set`. (~14)
4. `config.FINAL_NO_TOOLS_MESSAGE`: only a default argument that every caller overrides; delete it and make `final_message` required in the three tool_loop functions. (~11)
5. `--num-prompts` / `select_papers` / `import random` in `run_arxiv_prompt_vllm.py` and `config/cli_args.py`: zero callers; delete. Log in REMOVED.md. (~11)
6. `endpoint.py`: the `timeout` parameter threaded through four fetchers is never supplied; use the constant. `cli_value` on `resolve_api_key`/`auth_headers` is never non-None outside tests; delete with its test lines. (~13)
7. `config/cli_args.argparse_path`: replace with `type=Path`. (~3)
8. `trace_io.trace_row`: inline into `append_trace_row`. (~6)
9. `tool_loop.py:38,42`: `request_model = model_id or args.model` can never fall through; use `model_id`. (~3)
10. `tests/audit/test_audit.py`: delete `test_score_2_is_not_reproduced` (same fall-through band as score 5, weaker asserts). (~5)

## WP-E  serve + claude + openai (P5)
Files: `src/reprocli_serve/{args,launch,profiles,endpoint}.py`, `src/reprocli_claude/{agent,__main__}.py`, `src/reprocli_openai/recheck.py`; tests `tests/serve/test_launch.py`, `tests/claude/`.
1. `recheck.py`: delete the runner half (`run`, `client`, `status`, `main`, `call_with_retry`, `retry_after_seconds`, `request_kwargs`, `paper_texts_from_trace`, `TRACE`, `OUT_DIR`, `PROMPT_FILE`, `PAPER_START/END`, `MODEL`, `WORKERS`, `MAX_RETRIES`, `FINAL_JSON_SCHEMA` import). Keep the JSONL/extraction library the verify_app tools import (`iter_jsonl`, `write_jsonl`, `raw_rows`, `completed_raw_rows`, `parse_result`, `collect`, `output_text`, `hard_no_code_ids`, `add_recheck_args`, `wait_for_recheck`, `collect_recheck`, `POOL`, `RAW_NAME`). Verify each kept name with grep over tools/. Log the `python -m reprocli_openai.recheck` entry point in REMOVED.md. (~135)
2. `reprocli_serve`: delete the five `--data-parallel-*` flags and `_dataparallel_flags()`; delete `--tokenizer-mode`, `--structured-outputs-backend`, `--vllm-bin` (use the literal `"vllm"`). Log in REMOVED.md. (~34)
3. `profiles.Profile.extra`: unused field; delete with the `field` import. (~3)
4. `endpoint.remove_endpoint`: `FileNotFoundError` is an `OSError`; keep one except. (~3)
5. `reprocli_claude/agent.py`: delete `AuditResult.paper_id` (never read) and the `claude-opus-4-7/4-6` PRICES entries (identical to the fallback). (~7)
6. `reprocli_claude/__main__.py`: inline `_open_sink`; drop the always-true `if on_event:` guard. (~8)
7. `tests/serve/test_launch.py`: delete `PassthroughTests.test_extra_args_are_appended_verbatim` (byte-identical assertion to the MegaMoe probe test). (~4)

## WP-G  deployed web apps (P8), provably dead only
Files: `tools/anon_viewer/public/{viewer,overview,styles,anon,theme}.css`, `tools/anon_viewer/public/{strip,runcard,charts,data,render,verdict}.js`, `tools/run_viewer/public/{overview,estimates,auditlens,freeze}.js`.
Apply audit_P8.md rows 1-30 (every class token verified absent from the same app's .js and index.html). Skip rows 31-32. Re-verify each token with the grep in the audit before deleting. (~170)

## WP-S  sequential, after the parallel wave
1. `ExecutionContext.allocation`: write-only field (context.py, gpu_session.py writers, assertions in test_context/test_run_gpu/test_gpu_session). (~11)
2. `slurm.build_srun`/`run_in_session`: unused `cluster` parameter; update `tools/run_gpu.py:153` and tests. (~14)
3. `cluster.from_args`: two-getattr passthrough imported under the callee's name; `cli_args.py` calls `resolve_cluster` directly. (~18)
4. Drop the now-unused `mode` parameter of `io.extracted_response` and its arguments in `tool_loop.py` and `reprocli_claude/__main__.py:174`. (~4)
5. Delete `args.min_p = None` in `reprocli_repro/cli_args.py`. (~1)
6. P6: delete `export.NARRATIVE` (anon_viewer), the duplicate `import requests` in `verify_app/build_data.py`, merge the two `pipeline.supplements` imports in `build_dataset.py`, drop the unused `out_dir` parameter of `merge_repin_into_splits._download_base`. (~7)

## Deliberately skipped (remaining opportunities, judged too risky or out of bounds)
- P1: the single-episode fan-out in `loop.py` (~150, rewrite of the live sweep driver); `--prune-workspace-*`, `--reference`, `--apptainer-image`, `--partition` (operator knobs); `env.lock` touch (on-disk run-dir layout).
- P2: `cleanup.py` accounting and traversal (untested, log loss); `sandbox` probe/which caches (test seams); `live_log`/`supabase_sink`/`audit_sink` row-builder merge (needs a shared base); `--dry-run` on audit_upload (untested).
- P3: `REPRO_QUEUE_GRACE_HOURS`, `output.tail` window (edge-case behavior), docstring compression (~115 lines of incident records), `known_cluster_defaults`.
- P4: `tool_loop`/`transcript` helper merge (different `CONTEXT_BUDGET_NOTE` per side, a trap), `web_tools` dispatcher merge, `papers` subpackage, `build_audit_prompt` collapse (pins the S6->S7 contract), parametrizing `test_audit.py`.
- P5: `_Flag` coalescing table, `config.json` profile fallback (real feature for unnamed local paths), `SPLIT_CLAIMS` aliases, the white-box `EventWriteTests` (different seam from `test_audit_sink`).
- P6/P8: Supabase transport dedup across five tools (needs a paged helper), `scrub.py` window helpers (untested rewrite), `verify_app`/`run_viewer` CSS (clean).
- P7: `sys.path.insert` boilerplate in 49 test files (~91; would drop direct `python3 tests/x.py` runs), `_fake_post` capture block x6 (new helper), `good_report()` fixture (load-bearing paths).
