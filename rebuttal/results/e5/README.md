# E5: log integrity for reviewer rqBN

Script: `rebuttal/e5_log_integrity.py` (stdlib, run with Python 3.12 on DeltaAI, nice 19, a few minutes on the login node). Input: `tools/anon_viewer/public/data/index.json` (372 runs) and `/work/nvme/bfvr/msalunkhe/reprocli/agent_runs/`.

Run matching: index run to run dir by `budget_h100`, `tool_rounds_used` = `rounds`, and `spent_h100` within 1e-4, from `stats.json`.

Match rule: a commands.log entry or run_gpu trajectory row must match an agent tool call in `agent.full.log` after whitespace normalization, with the same command, and the same rc (plus cost and remaining for run_gpu rows).

Headline (denominators in brackets):
- Index runs matched to a run dir: 372/372. Run dirs found: 760; not in the index: 388 (225 with stats.json: 68 natural, 111 error, 46 context_budget; 163 without stats.json). Paper says 396 started; not reconciled.
- Agent-issued log entries checked: 45,861 of 49,585 entries (3,724 host-written rows not checked). Passed: 45,673. Explained: 185 (100 refused call with no cost line; 60 remaining within 0.00015 h; 25 first attempt of a retried call, absent from transcript). Unmatched: 3 (see below).
- Write hits: 6,244 segments. Into evidence/ (other files): 6,243 in 360 of 372 runs. Into commands.log, trajectory.jsonl or agent.full.log: 1 (run 2510.25146).
- Log completeness: 65 runs have fewer commands.log headers than agent bash/run_gpu calls (missing 119; 139 calls returned without rc). Code path: `workspace_bash.py:76-77` and `run_gpu.py:145` return without logging. One run (2510.25146) is an overwrite.
- mtimes: commands.log and trajectory.jsonl are at or before run end in 372/372. The evidence/ directory mtime is more than 60 s after run end in 63 runs (23 Jul to Aug, 40 on 2026-10-29). Cause not established.

For a human to judge:
1. `minimax-reimplement-2510.25146`, `agent.full.log:1084`: `write_file` path `/repro/evidence/commands.log`, ok, bytes_written=2106. The file now holds agent markdown and 3 host headers.
2. Unmatched (value, 0.0002 to 0.0003 h, cost equal): `qwen3-retrain-2510.22123` trajectory.jsonl:24; `muse-run-2504.12397` trajectory.jsonl:52; `muse-run-2505.23305` trajectory.jsonl:18.
3. Writes into evidence/ by the agent: `flags_all.tsv.gz`.

Files: per_run.csv, summary.json, unindexed_run_dirs.csv, flags_key.tsv (unmatched, explained, log_short, write_logs), flags_all.tsv.gz (all flags).

## Second check: the database copy of each run (2026-11-11)

Script: `rebuttal/e5_db_integrity.py` (stdlib; reuses the parsers of `e5_log_integrity.py`). Inputs: the `repro_events` rows of the 372 indexed runs, downloaded read-only from the project database on 2026-11-11 (112,184 rows; every run has events and a `repro_runs` row; server insert times run from 2026-07-14 to 2026-08-23), and `evidence/commands.log`, `evidence/trajectory.jsonl` of the same runs copied from the cluster. The harness posts each tool call and its result to the database while the run is going (`supabase_sink.py`), the row time `created_at` is set by the database server, and the sandbox starts with `--cleanenv --no-home` and an allowlist of forwarded variables (`sandbox.py:56`, Hugging Face, cache and proxy variables only), so the agent has no database key.

Match rule: a database `workspace_bash` or `run_gpu` call matches a commands.log entry of the same tool with the same whitespace-normalized command and the same rc. A call's result row is the row at seq + 1.

| Quantity | Count |
| :- | -: |
| Database bash and run_gpu calls | 31,022 |
| matched a commands.log entry on command and rc | 30,739 |
| matched on command, result row never reached the database (best-effort sink) | 51 |
| refused or returned without an rc, so never written to commands.log (156 no GPU allocation, 44 ok without rc, 21 other errors) | 221 |
| in the database and absent from commands.log | 11, all in `minimax-reimplement-2510.25146` |
| rc differs | 0 |
| commands.log entries from bash and run_gpu | 30,869 = 30,739 + 51 + 79 |
| first attempt of a timed-out call the harness retried (rc=?; the database holds the call once) | 79 |
| on disk and absent from the database | 0 |
| run_gpu results with a cost in the database | 12,709 |
| same cost and remaining budget in trajectory.jsonl (within 0.00015 h) | 12,663 |
| GPU release calls matched to a `gpu_release` row on final charge | 43 |
| remaining budget differs by 0.0002 to 0.0003 h (the 3 rows of the first check) | 3 |

Arithmetic: 30,739 + 51 + 221 + 11 = 31,022; 12,663 + 43 + 3 = 12,709.

Time: for the 30,739 matched entries, the time in the commands.log header and the server time of the database result differ by 0.59 s at the median, 1.13 s at the 99th percentile and 8.1 s at most.

The 11 database-only commands are the first 11 commands of the one run whose agent overwrote commands.log with a `write_file` call (found by the first check; auditor score 1, verdict unverifiable). The database still holds them. 368 of 372 runs have no flag other than refused calls and retried attempts; the other 4 are that run and the 3 runs with the remaining-budget difference.

Files in `db_check/`: db_summary.json, db_per_run.csv, db_flags.tsv, db_coverage.csv (events per run in the database).
