# Pending no-shell GPU jobs on DeltaAI (read-only check, 2026-11-08 21:10 CST)

Scope: 36 pending jobs, all on account betw-dtai-gh, partition ghx4. Submit times are CST from squeue. Limits are squeue %l.

Method: a run's launcher is the `salloc --no-shell` process that holds its pending job. Each such process was matched to a job by account, time limit and start time (ps lstart equals squeue SubmitTime). Its parent (codex_run.py or the reprocli_repro harness) was matched to a run dir through /proc/<pid>/fd, or through the --run-id argument for harness runs. Login nodes checked: gh-login01 and gh-login03.

Limits of the check: the harness logs `session_jobid` only after a grant, so no log ties a pending job id to a run. 25 jobs have no live launcher and no recoverable run identity. Their run is UNKNOWN, and the launcher is gone.

| Job id | Submit (CST) | Time limit | Run id | Paper | Class | Evidence |
|---|---|---|---|---|---|---|
| 3549889 | 11-07 10:00:26 | 6:00:00 | codex-gpt-6-astra-20261107T140243Z-9f613b | 2504.20571 | ALIVE | salloc pid 1658088 (gh-login03), parent codex_run 3523507 holds the run's codex_events.jsonl |
| 3549918 | 11-07 10:07:07 | 4:00:00 | codex-gpt-6.1-sol-20261107T113825Z-cb72b0 | 2510.21363 | ALIVE | salloc 1752290 (gh-login03), parent codex_run 1350084 holds the run |
| 3554694 | 11-08 06:18:48 | 12:00:00 | codex-gpt-6.1-sol-nudge-20261107T183141Z-91ce2a | 2505.10475 | ALIVE | salloc 338245 (gh-login01), parent codex_run 16588 holds the run |
| 3554778 | 11-08 06:37:53 | 1-00:00:00 | codex-gpt-6.1-sol-nudge-20261107T183141Z-907bb1 | 2506.08898 | ALIVE | salloc 622247 (gh-login01), parent codex_run 16596 holds the run |
| 3554859 | 11-08 07:15:07 | 7:30:00 | codex-gpt-6.1-sol-20261108T005328Z-9d3d35 | 2502.05795 | ALIVE | salloc 3440815 (gh-login03), parent codex_run 2175881 holds the run |
| 3556164 | 11-08 14:05:53 | 1-00:00:00 | core-a-2506.08898-87d1e2 | 2506.08898 | ALIVE | salloc 3933494 (gh-login01), parent harness pid 240206 (--run-id) |
| 3556797 | 11-08 16:12:56 | 2:00:00 | core-a-2504.20571-855aa5 | 2504.20571 | ALIVE | salloc 3387181 (gh-login01), parent harness pid 239881 (--run-id) |
| 3557462 | 11-08 18:10:32 | 2:00:00 | core-a-2505.10475-4e617a | 2505.10475 | ALIVE | salloc 1474657 (gh-login01), parent harness pid 255872 (--run-id) |
| 3558124 | 11-08 20:05:59 | 6:00:00 | core-a-2505.16927-f60e76 | 2505.16927 | ALIVE | salloc 3580621 (gh-login01, 4 GPUs), parent harness pid 238382 (--run-id) |
| 3558569 | 11-08 21:01:08 | 7:00:00 | codex-gpt-6.1-sol-20261108T013802Z-fed396 | 2505.10475 | ALIVE | salloc 1693378 (gh-login03, 4 GPUs), parent codex_run 3198855 holds the run |
| 3558570 | 11-08 21:01:20 | 7:40:00 | codex-gpt-6-astra-20261109T024706Z-5280d9 | 2502.05795 | ALIVE | salloc 1697533 (gh-login03), parent codex_run 1396183 holds the run |
| 3548889 | 11-07 05:08:05 | 7:30:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | no live salloc on either login node; no run id in Slurm or logs |
| 3549067 | 11-07 06:05:53 | 1-00:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3549890 | 11-07 10:00:38 | 2:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3550917 | 11-07 14:13:36 | 2:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3550974 | 11-07 14:37:37 | 2:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3552546 | 11-07 20:38:04 | 7:30:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3552947 | 11-07 22:10:30 | 2:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3554593 | 11-08 05:58:58 | 3:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3554610 | 11-08 06:05:59 | 6:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3554702 | 11-08 06:21:58 | 15:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3554947 | 11-08 07:39:33 | 10:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3554996 | 11-08 07:50:56 | 6:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3555040 | 11-08 07:59:58 | 2:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3555067 | 11-08 08:03:53 | 2:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3555077 | 11-08 08:07:36 | 4:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3555113 | 11-08 08:10:28 | 2:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3555265 | 11-08 09:11:04 | 1:40:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3555273 | 11-08 09:18:12 | 1:30:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3555283 | 11-08 09:23:24 | 1:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3555340 | 11-08 09:38:10 | 3:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3556208 | 11-08 14:17:13 | 2:30:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3557426 | 11-08 18:00:03 | 2:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3557447 | 11-08 18:03:52 | 2:00:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3557722 | 11-08 18:51:04 | 1:40:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |
| 3558595 | 11-08 21:04:49 | 30:00 | UNKNOWN | UNKNOWN | UNKNOWN (launcher gone) | same |

## Counts

| Class | Jobs |
|---|---|
| ALIVE | 11 |
| FINISHED | 0 |
| VOID | 0 |
| DEAD | 0 |
| UNKNOWN (launcher gone) | 25 |

FINISHED, VOID and DEAD could not be assigned: no job maps to a run dir with a report.json or VOID file, and the 25 orphans have no run identity to test.

## Correction, 2026-11-08 21:35 CST (main session)

The check above looked for launchers only on gh-login01 and gh-login03. gh-login02 holds 11 more live `salloc --no-shell` launchers, and three new requests come from compute nodes gh076 and gh083 (the E8 rerun and repeat-run harnesses). Matching each pending job's SubmitTime to a live launcher's start time (within 3 s) on all four login nodes gives 22 live, 3 from compute nodes (3558624, 3558625, 3558630, kept), and 13 orphans whose AllocNode is a login node with no live salloc:

3548889 3549067 3549890 3550917 3550974 3552546 3552947 3554610 3555040 3555067 3555113 3555265 3555340

They were submitted 11-07 05:08 to 11-08 09:38 with limits of 1:40 to 24:00, are older than every live request, so Slurm would start them first, and nothing would attach to them once granted. Cancelling them needs Mithil's approval (the permission check blocked an scancel).
