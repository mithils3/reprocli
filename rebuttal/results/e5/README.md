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
