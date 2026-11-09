# Two frontier exits that look odd against their budget use

Read-only check on DeltaAI run directories and the local harness code. Nothing was changed on the cluster or in the repo.

## A. codex-gpt-6.1-sol, 2504.20571, run 91bc6a (exit budget_exhausted at 10.6%)

**Limit hit:** the GPU budget of 8.0 H100-hours (codex_run.json, `budget_h100_hours: 8.0`). The stop fired at 2026-11-08T00:52:55Z.

**Numbers:** the last per-step meter line before the stop read `remaining_h100h=7.0491` at 2026-11-07T17:45:36Z (agent.full.log line 5441), so about 0.95 was spent by then. The databook's spent value of 0.8461 is lower than that and does not match the log, so the CSV spend column is not the meter.

**What happened:** the 4-GPU run released its session at 17:45:42Z. A later run_gpu call, opened at 17:45:57Z, failed at 17:49:29Z with `OSError: [Errno 122] Disk quota exceeded: .../evidence/gpu_step_0019.log` (line 5689). The step-log open sits outside the try block in `src/reprocli_repro/slurm.py` line 273, so the error escaped without releasing the session. Nothing was logged for the next 7 hours. The watchdog in `scripts/rebuttal/codex_arm/codex_run.py` (about lines 395 to 400) keeps charging held wall while a session is held, so the held allocation ran the meter to zero at 00:52:55Z (line 5691: `STOP budget_exhausted`).

**Cause:** harness accounting. A disk-quota error left a GPU session held and billed by wall clock. The agent did not choose a larger allocation for this. The 0.85 to 8.0 gap is unrecorded held wall.

**Table label:** early_stop.md should say "budget exhausted by a leaked held GPU session after a disk-quota error (about 0.95 of 8 H100-h billed by 17:45, rest unrecorded); harness accounting, not spend."

Note: report.json has `agent_assessment: not_reproduced`, while the CSV verdict column reads `reproduced` with score 8.

## B. codex-gpt-6-astra, 2505.10475, run a54ff7 (exit wall_clock at 2.9%)

**Limit hit:** the 48-hour harness wall clock (codex_run.json, `wall_hours: 48.0`). The run started at 2026-11-07T01:05:42Z (line 1) and stopped at 2026-11-09T01:05:43Z (line 1644). The GPU budget was 32 H100-hours with 0.943 spent (CSV `spent_h100` 0.943, 2.9%). Spend is not the comparison for this exit.

**What used the wall clock:** at 2026-11-07T16:06:23Z the agent issued a run_gpu request (`bash scripts/download.sh && bash scripts/eval.sh P8 full 16 && bash scripts/eval.sh P1 full 16`, which the report lists with `--minutes 120`). It never got an allocation. The final line (line 1709) reads `could not acquire GPU allocation: salloc: Job aborted due to signal`, logged at teardown. The request sat in the queue from about 16:06 on 2026-11-07 until the stop, roughly 33 hours.

**The agent's own mistake:** at 16:05:40Z an earlier 30-minute allocation ran the full task and hit `DUE TO TIME LIMIT` (line 1536). That cost 0.50 H100-hours and is the "launcher mistake" in the report. It did not trigger the stop.

**Cause:** the queue, inside the 48-hour harness wall clock. The agent's short-allocation error is real but is not what ended the run.

**Unresolved:** codex_run.json records `queue_wait_minutes: 536.8` (about 9 hours), while the log shows the request pending for about 33 hours. The computation is in `codex_run.py` line 712 (`queue_wait_s` plus `pending`). This needs a check before the rebuttal quotes a queue figure.

**Table label:** early_stop.md should say "wall_clock at 48 h; GPU spend 0.94 of 32 H100-h; the last 33 h were a GPU request stuck in the queue."
