# Frontier arm forecast, 2026-11-09 (read only)

Snapshot taken Mon 2026-11-09 02:41 CST. Deadline for stopping runs: Sun 2026-11-15 18:00 CST, which is 9,559 minutes away. Nothing was cancelled, submitted or changed. Not committed.

## Table

| Arm | Planned | Graded (frontier_cells.csv) | Finished, not in CSV | In progress | Stalled (no report, idle over 3 h, no live process) | Not started | Est. finish, parallel runs | Est. finish, serial steps | Before 11-15 18:00 |
|---|---|---|---|---|---|---|---|---|---|
| codex gpt-6.1-sol (Codex CLI) | 24 | 12 | 3 | 3 | 5 | 1 | 11-13 12:44 | 11-20 14:24 | yes (parallel) / no (serial) |
| codex gpt-6-astra (Codex CLI) | 8 | 4 | 1 | 2 | 0 | 1 | 11-12 15:31 | 11-13 12:44 | yes / yes |
| thin gpt-6.1-sol | 12 | 7 | 2 | 0 | 3 | 0 | 11-13 12:44 | 11-22 08:50 | yes (parallel) / no (serial) |
| miniswe muse-wonder-1.0 | 6 | 1 | 0 | 2 | 3 | 0 | 11-13 12:44 | 11-27 05:29 | yes (parallel) / no (serial) |
| nudge gpt-6.1-sol (continue prompt) | 8 | 0 | 2 | 0 | 2 | 6 | 11-13 12:44 | 12-06 22:47 | yes (parallel) / no (serial) |

Notes on the table:

- Graded counts come from the 24 rows of `rebuttal/results/databook/frontier_cells.csv`. That file has 12 codex gpt-6.1-sol rows, 4 astra, 7 thin and 1 miniswe. None is labeled nudge, so the nudge arm has 0 graded rows.
- "Finished, not in CSV" means the run has a report.json but no CSV row yet. For nudge, the two papers (2505.10475, 2506.08898) also appear in the stalled column, because their newest attempt is idle and an older attempt finished.
- In progress means a live codex_run.py process or a file changed in the last 3 hours. Live processes found: 2502.05795 (codex sol, pid 2175881; codex astra, pid 1396183), 2505.10475 (codex sol, pid 3198855), 2504.20571 (codex astra, pid 3523507). The astra run on 2504.20571 has had no file change for 40 hours, so it is likely stuck.
- Miniswe in progress: 2505.10475 and 2505.16927 (changed in the last hour). Its step count is unreliable, see below.
- Papers planned for each arm: codex sol and thin use the 12 core and 12 extension papers in `rebuttal/subset.json`. Astra, miniswe and nudge use the first 8, 6 and 8 core papers. The brief gave the thin count as 12, the nudge count as 8 and the astra count as 8; the miniswe count of 6 comes from `rebuttal/PLAN.md` (E2).
- One graded CSV row (2602.03066, codex sol) sits in the extension list, so all 12 codex sol graded rows are in the planned set.

## Arithmetic

Queue wait: `squeue` reports elapsed time 0:00 for PENDING jobs, so the wait was measured as time since submit (`%V`). The 41 PENDING no-shell jobs have a median age of 628.3 minutes. The RUNNING no-shell job (3560952) started at 02:38.

Cost per GPU step: 628.3 + 8 = 636.3 minutes, about 10.6 hours.

Steps per finished run, from the run logs (`run_gpu ok=` lines in agent.full.log for Codex, `⏺ run_gpu` lines for thin and miniswe):
- Codex sol, 12 graded: 2, 3, 4, 6, 8, 9, 11, 14, 17, 23, 23, 28. Median (9 + 11) / 2 = 10.
- Astra, 4 graded: 2, 6, 10, 12. Median (6 + 10) / 2 = 8.
- Thin, 7 graded: 4, 7, 8, 10, 16, 17, 30. Median 10.
- Miniswe and nudge have no graded run, so the codex median of 10 is used.

Remaining steps per run: a run with no more steps than the median keeps 1 step. A run that has done more than the median keeps 1 step, because its length is unknown. A stalled or not-started run gets the median minus its steps done, or the full median. Finished runs need 0.

Worked example, codex sol: 26 remaining steps in total, the largest single run needs 10. Serial bound: 26 × 636.3 = 16,544 minutes = 275.7 hours, which is 11.5 days, so the finish is 11-09 02:41 plus 11.5 days, 11-20 14:24. Parallel bound: 10 × 636.3 = 6,363 minutes = 106 hours, so the finish is 11-13 12:44. The same method gives the other rows.

## Caveats

- The wait is a floor. The jobs have waited 628 minutes so far and are still pending, so a longer wait would push every estimate later.
- The stalled runs (no live process, no file change for over 3 hours) may never resume without a relaunch. The table counts them as remaining work at the median cost.
- Miniswe on 2505.10475 logs 258 `⏺ run_gpu` lines, far above the others. The count may include mentions in the text, so its remaining steps were set to 1.
- Thin and miniswe step counts use `⏺ run_gpu` lines, which count tool calls and may also count mentions in the text. Codex counts use `run_gpu ok=`.
- Harness wall time and Codex's own compaction are not in the estimate.
