# Disk-quota hits and queue wait, frontier runs

Read-only check over the 24 rows of rebuttal/results/databook/frontier_cells.csv. Run logs were read on DeltaAI. Nothing was changed there and nothing is committed.

## How queue_wait_minutes is computed

File: scripts/rebuttal/codex_arm/codex_run.py

- Lines 171-172: the bridge keeps `queue_wait_s` (sum of finished waits) and `pending_since` (start of an acquire still waiting).
- Lines 236-243: `_serve` sets `acquiring = self.ctx.session is None` at the start of a run_gpu call. Only an acquire is timed. `pending_since` is set before the call and cleared in the `finally`.
- Lines 247-251: after the call returns, a granted acquire adds `session.started - started`. An acquire that was never granted adds `time.monotonic() - started`, so a request that ends without a grant is counted.
- Line 711: a request still blocked when the run is finalized adds `time.monotonic() - pending_since`.
- Line 712: `queue_wait_minutes = round((queue_wait_s + pending) / 60, 2)`.

So the code does count a request still pending at the stop, both at line 251 (when the call returns) and at line 711 (if it has not returned). Calls that start while a session is already held are not timed as queue wait at all.

## Table

Recomputed = sum over the run's run_gpu calls of (wall time from the FREEZE line to the `run_gpu ok=` line, minus cost_h100h times 60). Pending = the time of an acquire that ended with "could not acquire GPU allocation" (a request still pending at the stop). Total = recomputed + pending. Minutes throughout. The thin arm writes no FREEZE lines and no codex_run.json queue value, so it is shown as n/a. Quota hits are the count of "Disk quota exceeded" in agent.full.log.

| arm | paper | run id tail | quota hits | exit_reason | CSV queue_wait_min | recomputed | pending at stop | total | diff (total minus CSV) |
|---|---|---|---|---|---|---|---|---|---|
| codex-gpt-6-astra | 2505.16927 | 62f1c5 | 0 | natural | 215.51 | 215.5 | 0 | 215.5 | 0.0 |
| codex-gpt-6.1-sol | 2505.16927 | d345e4 | 0 | natural | 621.12 | 618.1 | 0 | 618.1 | -3.0 |
| thin-gpt-6.1-sol | 2505.16927 | eed0ff | 0 | natural | blank | n/a | n/a | n/a | n/a |
| thin-gpt-6.1-sol | 2504.20571 | f42006 | 0 | natural | blank | n/a | n/a | n/a | n/a |
| thin-gpt-6.1-sol | 2506.08898 | 786249 | 0 | natural | blank | n/a | n/a | n/a | n/a |
| codex-gpt-6-astra | 2506.08898 | f7afe8 | 0 | natural | 527.82 | 527.8 | 0 | 527.8 | 0.0 |
| miniswe | 2506.08898 | 014125 | 0 | submitted | blank | n/a | n/a | n/a | n/a |
| codex-gpt-6.1-sol | 2506.08898 | 379147 | 0 | natural | 839.96 | 840.0 | 0 | 840.0 | 0.0 |
| codex-gpt-6.1-sol | 2504.20571 | 91bc6a | 1 | budget_exhausted | 957.67 | 941.0 | 0 | 941.0 | -16.7 |
| thin-gpt-6.1-sol | 2510.21363 | 3603cb | 0 | natural | blank | n/a | n/a | n/a | n/a |
| thin-gpt-6.1-sol | 2504.12463 | d67082 | 0 | natural | blank | n/a | n/a | n/a | n/a |
| thin-gpt-6.1-sol | 2503.02809 | 57a419 | 0 | natural | blank | n/a | n/a | n/a | n/a |
| codex-gpt-6.1-sol | 2504.12463 | cb1fc6 | 0 | natural | 606.01 | 606.0 | 0 | 606.0 | 0.0 |
| codex-gpt-6.1-sol | 2503.14698 | ae78cc | 0 | natural | 562.58 | 562.6 | 0 | 562.6 | 0.0 |
| codex-gpt-6.1-sol | 2505.12677 | 5044c1 | 0 | natural | 562.85 | 562.9 | 0 | 562.9 | 0.0 |
| codex-gpt-6.1-sol | 2412.11979 | fb8412 | 0 | natural | 563.27 | 563.3 | 0 | 563.3 | 0.0 |
| codex-gpt-6.1-sol | 2503.02809 | 918570 | 0 | natural | 680.05 | 680.1 | 0 | 680.1 | 0.0 |
| codex-gpt-6.1-sol | 2511.01463 | effbe6 | 0 | natural | 77.65 | 77.7 | 0 | 77.7 | 0.0 |
| thin-gpt-6.1-sol | 2505.19087 | 095231 | 0 | natural | blank | n/a | n/a | n/a | n/a |
| codex-gpt-6.1-sol | 2506.20671 | c4eacf | 0 | natural | 660.3 | 660.3 | 0 | 660.3 | 0.0 |
| codex-gpt-6.1-sol | 2505.19154 | 8d0463 | 0 | natural | 98.68 | 161.6 | 0 | 161.6 | +62.9 |
| codex-gpt-6.1-sol | 2602.03066 | d3ac33 | 0 | natural | 66.76 | 66.8 | 0 | 66.8 | 0.0 |
| codex-gpt-6-astra | 2505.10475 | a54ff7 | 0 | wall_clock | 536.8 | 834.0 | 1980.0 | 2814.0 | +2277.2 |
| codex-gpt-6-astra | 2510.21363 | 6cef06 | 0 | natural | 3.88 | 3.9 | 0 | 3.9 | 0.0 |

Quota hits: one run in 24 has a hit, 91bc6a (2504.20571). Its first hit is agent.full.log line 5689, `[2026-11-07T17:49:29Z] run_gpu ok=False ... error=OSError: [Errno 122] Disk quota exceeded: '.../evidence/gpu_step_0019.log'`. Its exit_reason is budget_exhausted.

## Worked example: a54ff7 (2505.10475, codex-gpt-6-astra)

The log has no "Pending job allocation" or "Granted job allocation" lines. Those strings appear in no run log. The only salloc line is the final abort, agent.full.log line 1709. So the wait was rebuilt from the bridge timeline: each FREEZE line (start of a run_gpu call) and the matching `run_gpu ok=` line (end of the call).

The pending request is the call that began at FREEZE on 2026-11-07 16:06:23Z (line 1643). It ended at 2026-11-09 01:06:21Z (line 1709) with "could not acquire GPU allocation: salloc: Job aborted due to signal". From 16:06:23 on 11-07 to 01:06:21 on 11-09 is 32 h 59 min 58 s, which is 1980.0 minutes. That is the pending time, and it is not in the CSV.

The granted calls sum to 834.0 minutes over 9 calls. The largest is the call from 10:36:29 to 15:33:41 on 11-07 (lines 1410 to 1412). It ran for 297.2 minutes and charged 0.0001 GPU-hours, which is about 0 minutes. Its command was a sinfo probe. Without that call, the granted sum is 834.0 minus 297.2, which is 536.8. That matches the CSV exactly, so the CSV leaves out both this 297.2-minute call and the 1980.0-minute pending request.

By the code at lines 249-251 and 711, the pending request should be counted (about 1980 minutes), so the CSV value disagrees with the repo code for this run. The likely reasons are that codex_run.json was written by another copy of the harness, or that the stop path skipped the count. The log does not settle which. Total with the pending request is 2814.0 minutes against a CSV value of 536.8.

## Notes

- Differences above 60 minutes: a54ff7 (+2277.2 with the pending request, +297.2 without it) and 8d0463 (+62.9). For 8d0463 the extra time is one call from 14:07 to 15:15 on 11-08 (67.7 minutes, 4.8 minutes charged). The CSV appears to leave it out, probably because the session was already held at that call's start, which the code does not time as queue wait. I did not confirm the session state for that call.
- The recomputation counts every call, while the code counts only calls that start with no session. The two agree on the other 15 codex rows within 17 minutes.
- The thin rows have no queue value in the CSV and no FREEZE lines, so they are not checked here.
