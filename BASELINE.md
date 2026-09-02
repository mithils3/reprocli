# Code-reduction baseline (branch `reduce/pass-1`, 2026-09-02, from `repro-next` @ ca64fbe)

## Test suite

Command: `PYTHONPATH=src python3 -m pytest tests -q`

| state | result |
|---|---|
| on `repro-next` @ ca64fbe | 539 passed, 1 failed, 1 skipped |
| after pinning the date-dependent Sonnet-5 pricing assertion (intro rate expired 2026-08-31) | 540 passed, 1 skipped |

The one failure was `tests/claude/test_claude_agent.py::PricingTests::test_each_tier_is_priced_from_its_own_base`,
which asserted the introductory Sonnet-5 price against today's date. Fixed by asserting the post-2026-08-31
rate; no source change. Baseline to hold: **540 passed, 1 skipped, 0 failed**.

Lint: `ruff check src tools` (rules E9, F) is clean.

## LOC (git-tracked `.py .sh .sbatch .js .html .css`; code = non-blank, non-comment)

| partition | files | physical | code |
|---|---|---|---|
| scripts/cluster | 1 | 126 | 70 |
| scripts/reproduce | 22 | 6862 | 4571 |
| scripts/serve | 7 | 1038 | 749 |
| src/reprocli_claude | 3 | 688 | 594 |
| src/reprocli_data | 9 | 1498 | 1311 |
| src/reprocli_openai | 2 | 338 | 286 |
| src/reprocli_repro | 39 | 7007 | 5706 |
| src/reprocli_serve | 9 | 1130 | 848 |
| src/reprocli_vllm | 32 | 3604 | 3010 |
| src/run_arxiv_prompt_vllm.py | 1 | 109 | 87 |
| tests/ (all) | 61 | 7027 | 5503 |
| tools/anon_viewer | 27 | 8127 | 6890 |
| tools/run_viewer | 39 | 5233 | 4634 |
| tools/verify_app | 10 | 2982 | 2575 |
| tools/*.py (5 standalone) | 5 | 814 | 688 |
| **TOTAL** | 267 | 46583 | 37522 |

Python only: 172 files, 27261 physical, 22156 code.
src/ 11842 code · tests/ 5503 code · tools/ 4363 code · scripts/ 448 code.

## Cyclomatic complexity (radon 6.0.1, src + tools/*.py + scripts/serve/*.py)

730 blocks, average complexity A (4.17). Blocks graded C or worse (CC ≥ 11):

| function | CC |
|---|---|
| reprocli_vllm/audit/select_pool.py write_outputs | 19 |
| reprocli_vllm/runtime/tool_loop.py run_tool_loop | 18 |
| reprocli_repro/loop.py run_reproduce_loop | 16 |
| reprocli_repro/audit_upload.py main | 16 |
| reprocli_data/build_dataset.py main | 13 |
| reprocli_data/pipeline/index.py read_index_csv | 13 |
| reprocli_repro/loop.py handle_request_done | 13 |
| reprocli_serve/launch.py build_serve_command | 12 |
| reprocli_serve/launch.py _supported_compilation_config | 12 |
| reprocli_vllm/vllm/client.py downgrade_response_format_on_reject | 12 |
| reprocli_vllm/tools/run_dir_tools.py _walk | 12 |
| reprocli_claude/__main__.py main | 12 |
| reprocli_repro/compact.py elide_compact | 12 |
| (9 more at CC 11) | 11 |

Full per-block dump: scratchpad `cc_baseline.json`; per-file LOC: scratchpad `loc_baseline.json`.

## Repo map and partitions

Entry points (all referenced from sbatch scripts, README, or `.claude/skills`):
`python -m reprocli_repro`, `reprocli_repro.audit_upload`, `reprocli_repro.metrics_beacon`,
`python -m reprocli_serve`, `python src/run_arxiv_prompt_vllm.py`, `reprocli_vllm.audit.select_pool`,
`reprocli_claude`, `reprocli_data.build_dataset`, `tools/run_viewer/setup_db.py`,
`tools/verify_app/build_data.py`, `tools/verify_app/fetch_arxiv_meta.py`.

Callers outside `src/` that must count as references: `tests/`, `tools/`, `scripts/`, `.claude/skills/analyze-sweep/*.py`,
sbatch scripts under `scripts/reproduce`, and the three deployed web apps.

| # | partition | paths | code LOC | tests |
|---|---|---|---|---|
| P1 | repro core | `src/reprocli_repro/{__init__,__main__,cli_args,loop,context,inputs,budget,compact,dataset,env,evidence,prompt_render,reference,transcript,workspace}.py`, `src/reprocli_repro/report/` | ~2200 | tests/repro/test_{budget,compact,context,env,evidence,finalize,inputs,loop,output,reference,report,transcript,workspace}.py, tests/smoke |
| P2 | repro infra | `src/reprocli_repro/{sandbox,slurm,cluster,gpu_session,gpu_usage,cleanup,live_log,metrics_beacon,run_beacon,event_sink,supabase_sink,postgrest,audit_upload,batch_runs}.py` | ~2500 | tests/repro/test_{sandbox,slurm,cluster,gpu_session,gpu_usage,live_log,metrics_beacon,supabase_sink,postgrest,audit_bundle,batch_runs,guardrails}.py |
| P3 | repro tools | `src/reprocli_repro/tools/` | ~1100 | tests/repro/test_{tools,tools_plan_bash,partitions,run_gpu,run_gpu_dispatch}.py |
| P4 | vllm runner | `src/reprocli_vllm/`, `src/run_arxiv_prompt_vllm.py` | ~3100 | tests/{vllm,runtime,schema,audit,tools} |
| P5 | serve + claude + openai | `src/reprocli_serve/`, `src/reprocli_claude/`, `src/reprocli_openai/` | ~1700 | tests/serve, tests/claude |
| P6 | data + standalone tools | `src/reprocli_data/`, `tools/*.py`, `tools/verify_app/*.py`, `tools/run_viewer/setup_db.py`, `tools/anon_viewer/*.py`, `scripts/serve/*.py` | ~2900 | none (only provably-dead removals) |
| P7 | tests | `tests/` | 5503 | duplicates / tests of deleted code only |
| P8 | web apps | `tools/run_viewer/public`, `tools/verify_app/public`, `tools/anon_viewer/public` | ~13000 | none, deployed; provably-dead only |

Out of scope for edits: `scripts/reproduce/*.sbatch` (sweep launchers of record, no test coverage,
launched by hand on the cluster), `.claude/`, `paper_latex/`, `notes/`, `data/`, `outputs/`.
