# Queue forecast for the rebuttal GPU runs, 2026-11-09

Cutoff: Sunday 2026-11-15 18:00 Central. Snapshot taken Monday 2026-11-09 01:02 CST on the cluster.
Times below are cluster time (CST).

## 1. Queue wait by day (no-shell jobs, partition ghx4, user msalunkhe)

Source: `sacct -u msalunkhe -S 2026-11-06 -X --name no-shell`, rows with a Start time. Wait = Start minus Submit. Days are the Submit day. The 2 jobs for 11-09 are a partial day.

| Submit day | Started jobs | Median wait | 90th percentile wait | Longest wait |
|---|---|---|---|---|
| 11-06 | 123 | 5.1 min | 487.5 min (8.1 h) | 3112 min (51.9 h) |
| 11-07 | 87 | 235.2 min (3.9 h) | 1602 min (26.7 h) | 2635 min (43.9 h) |
| 11-08 | 91 | 7.3 min | 232.8 min (3.9 h) | 1082 min (18.0 h) |
| 11-09 (partial) | 2 | 15.3 min | 16.9 min | 17.2 min |
| All four days | 303 | 9.9 min | 625.6 min (10.4 h) | 3112 min |

Count of jobs still pending now: 40. Oldest pending job is 3548889, submitted 11-07 05:08:05 and still pending with reason Priority. Its wait so far is 43.9 h, which is already past the median and the 90th percentile of every day above.

The sacct table also shows 276 jobs cancelled by user 91115 and 49 timeouts. Cancelled jobs with a Start time are counted as started above.

## 2. Batch jobs still to run

Source: `squeue -u msalunkhe -h -o '%i %j %T %M %l %S'`, read at 01:02 CST.

| Job | Name | State | Elapsed | Time limit | Expected start (%S) | Experiment (inferred) |
|---|---|---|---|---|---|---|
| 3540624 | repro_easy_dsv4 | RUNNING | 4:18:28 | 2-00:00:00 | started 11-08 20:43:41 | Repeat runs |
| 3540786 | repro_medium_qwen3 | RUNNING | 4:21:26 | 2-00:00:00 | started 11-08 20:40:43 | E8 rerun |
| 3540625 | repro_medium_dsv4 | PENDING | 0:00 | 2-00:00:00 | 11-10 01:31:01 | Repeat runs |
| 3540626 | repro_hard_dsv4 | PENDING | 0:00 | 2-00:00:00 | 11-10 01:31:01 | Repeat runs |
| 3540627 | repro_easy_dsv4 | PENDING | 0:00 | 2-00:00:00 | 11-10 01:31:01 | Repeat runs |
| 3540628 | repro_medium_dsv4 | PENDING | 0:00 | 2-00:00:00 | 11-10 01:31:01 | Repeat runs |
| 3540629 | repro_hard_dsv4 | PENDING | 0:00 | 2-00:00:00 | 11-10 01:31:01 | Repeat runs |
| 3540630 | repro_easy_dsv4 | PENDING | 0:00 | 2-00:00:00 | 11-10 01:31:01 | Repeat runs |
| 3540631 | repro_medium_dsv4 | PENDING | 0:00 | 2-00:00:00 | 11-10 01:31:01 | Repeat runs |
| 3540632 | repro_hard_dsv4 | PENDING | 0:00 | 2-00:00:00 | 11-10 01:31:01 | Repeat runs |
| 3540633 | repro_medium_minimax | PENDING | 0:00 | 2-00:00:00 | 11-10 01:31:01 | E8 rerun |
| 3540787 | repro_hard_qwen3 | PENDING | 0:00 | 2-00:00:00 | 11-10 01:31:01 | E8 rerun |
| 3558022 | e10-2506.10351-s1 | PENDING | 0:00 | 2:50:00 | 11-10 01:31:01 | E10 seeds |
| 3558023 | e10-2506.10351-s2 | PENDING | 0:00 | 2:50:00 | 11-10 01:31:01 | E10 seeds |

The experiment column is inferred from job names and from the schedule in rebuttal/PLAN.md (lines 164 to 177 and 223). Only 3540624 and 3540786 are confirmed by that schedule.

Slurm's expected start for every pending job is 11-10 01:31, about 24.5 h from the snapshot. No measured runtime exists for these jobs. The running jobs have 4.3 h elapsed, so the time limit (48 h) is used as the upper bound on compute.

## 3. Frontier runs (per-run wall time)

Sources: rebuttal/results/frontier/run_usage.csv (11 finished runs) and rebuttal/results/databook/frontier_cells.csv (24 cells, 16 with a queue wait).

- Median GPU calls per finished run: 5 (11 runs, values from 0 to 18).
- Median queue wait per run: 563 min (16 cells, longest 958 min). The CSV value is already the run total (quota_and_queue.md, line 712), so it is not multiplied by the call count again.
- Median compute per run: 40 min (wall_minutes, 11 runs).

Worked example for one frontier run at the median: 5 sessions, each waiting about 113 min (563 / 5), gives 563 min of queue. Add 40 min of compute, for 603 min, about 10.0 h per run. A run started at 01:00 on 11-09 ends near 11:00 on 11-09.

The number of frontier runs still to launch is not in the brief, so the total cannot be stated. If the runs go one after another, total time is the number of runs times 10 h.

## 4. Expected finish per experiment

Method: the median wait is the pooled median (9.9 min). The 90th percentile is the pooled value (625.6 min, 10.4 h). Pending jobs have already waited longer than both, so each one is taken to start now (median case) or at the 10.4 h mark from now (p90 case). The Slurm estimate (11-10 01:31) is also shown. Each batch job is taken to run its full 48 h time limit, which is the worst case. Each E10 job is taken to run 2:50.

Cutoff check: a 48 h job must start by 11-13 18:00 to finish by the cutoff. A 2:50 job must start by 11-15 15:10.

- **Repeat runs (9 jobs, 1 running, 8 pending):** median case, finish by 11-11 01:00. p90 case (start 11-09 11:25), finish by 11-11 11:25. Slurm estimate (start 11-10 01:31), finish by 11-12 01:31. All before cutoff.
- **E8 reruns (3 jobs, 1 running, 2 pending):** median case, the running job ends by 11-10 20:40, and the pending pair by 11-11 01:00. p90 case, by 11-11 11:25. Slurm estimate, by 11-12 01:31. All before cutoff.
- **E10 seeds (2 jobs, pending):** median case, finish by 11-09 04:00. p90 case, by 11-09 14:15. Slurm estimate, by 11-10 04:21. All before cutoff.
- **Frontier (per run, about 10 h):** median case, one run finishes by 11-09 11:00. Longest observed (958 min wait plus 40 min compute, 16.6 h), by 11-09 17:40. Total depends on the number of runs still to launch.

## Risk

On the measured waits, each experiment clears the cutoff, provided its jobs can run alongside each other. If only 2 of the 8 repeat jobs can run at a time, they need about 8 days and would miss. A pending 48 h job misses only if it has not started by 11-13 18:00, that is about 65 h from now. The oldest pending job has waited 44 h, and the longest measured wait was 52 h. A job would have to wait about 21 h longer than the longest wait seen so far to miss.

The most exposed item is the 8 repeat-run jobs, since 8 jobs would run in sequence only if the queue allows one at a time. Only 2 jobs are running now. If concurrency stays at 2, the 8 repeat jobs at 48 h each would need about 8 days in 2 slots, which would miss the cutoff. This depends on the per-user concurrency limit, which was not checked.

Note, 01:10 on 11-09 (main session): the pooled median counts only sessions that started, so it understates the wait for the ones still pending; six sessions inside job 3540786 had waited 1 h 46 min to 3 h 41 min at 01:00. All 52 pending jobs show reason (Priority), with no per-user job or GPU limit on the betw-dtai-gh association, and Slurm's expected start for 3540625, 3540787 and 3558022 is 2026-11-10 01:31. The repeat runs have a 2-day limit, so if they start then they finish by 11-12 01:31 at the latest, which is too late to fill the T29u W1 slot for a Thursday morning post unless they end early, and in time for the 11-16 results update.
