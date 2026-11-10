# Rebuttal data book

Generated at 2026-11-10T01:16:18Z UTC by scripts/rebuttal/build_databook.py. Frontier rows: 42 (grades.jsonl rows with graded_at >= 2026-11-07). Intervals: Wilson score 95%.

## 1. Frontier arms (replies: General, YGTR W1)

Rate: reproduced / graded [Wilson 95%]. Paired diff: arm score minus the best original agent score on the same paper, mean (n); a missing original cell scores 0. spent_h100: thin runs from stats.json, codex and miniswe runs summed from run_gpu lines in agent.full.log. queue_wait_min: codex_run.json, codex runs only.

| arm | planned | graded | reproduced rate | mean score | paired diff (n) | could_not_run |
|---|---|---|---|---|---|---|
| codex-gpt-6.1-sol | 24 | 16 | 2/16 [3.5, 36.0] | 4.44 | -2.25 (n=16) | 6 |
| codex-gpt-6-astra | 8 | 7 | 1/7 [2.6, 51.3] | 3.14 | -3.00 (n=7) | 2 |
| codex-gpt-6.1-sol-nudge | 8 | 0 | - (n=0) | - | - (n=0) | 0 |
| thin-gpt-6.1-sol | 12 | 11 | 4/11 [15.2, 64.6] | 5.45 | -0.82 (n=11) | 3 |
| thin-muse-wonder-1.0 | 12 | 0 | - (n=0) | - | - (n=0) | 0 |
| miniswe | 6 | 3 | 1/3 [6.1, 79.2] | 5.67 | 0.67 (n=3) | 0 |
| thin-gpt-6-astra | not planned | 3 | 1/3 [6.1, 79.2] | 4.33 | -2.33 (n=3) | 1 |
| thin-gpt-6-astra-x86 | not planned | 1 | 0/1 [0.0, 79.3] | 2.00 | -2.00 (n=1) | 1 |
| thin-gpt-6.1-sol-x86 | not planned | 1 | 0/1 [0.0, 79.3] | 7.00 | -1.00 (n=1) | 0 |

Per-run rows (one per grades.jsonl row since 2026-11-07):

| arm | model | paper | budget | run_id | score | verdict | reproduced | orig tier | dsv4 | minimax | muse | qwen3 | orig best | diff | agent_assessment | exit_reason | queue_wait_min | budget_h100 | spent_h100 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| codex-gpt-6-astra | gpt-6-astra | 2505.16927 | 32h | codex-gpt-6-astra-20261107T101517Z-62f1c5 | 1 | unverifiable | False | reimplement | 4 | 0 | 4 | 4 | 4 | -3 | could_not_run | natural | 215.51 | 32.0 | 0.039 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2505.16927 | 32h | codex-gpt-6.1-sol-20261107T010540Z-d345e4 | 1 | unverifiable | False | reimplement | 4 | 0 | 4 | 4 | 4 | -3 | could_not_run | natural | 621.12 | 32.0 | 0.0546 |
| thin-gpt-6.1-sol | gpt-6.1-sol | 2505.16927 | 32h | core-a-2505.16927-eed0ff | 1 | unverifiable | False | reimplement | 4 | 0 | 4 | 4 | 4 | -3 | could_not_run | natural |  | 32.0 | 0.0669 |
| thin-gpt-6.1-sol | gpt-6.1-sol | 2504.20571 | 8h | core-a-2504.20571-f42006 | 8 | reproduced | True | run | 8 | 6 | 7 | 8 | 8 | 0 | not_reproduced | natural |  | 8.0 | 1.2537 |
| thin-gpt-6.1-sol | gpt-6.1-sol | 2506.08898 | 32h | core-a-2506.08898-786249 | 4 | not_reproduced | False | retrain | 7 | 0 | 8 | 0 | 8 | -4 | partial | natural |  | 32.0 | 0.1768 |
| codex-gpt-6-astra | gpt-6-astra | 2506.08898 | 32h | codex-gpt-6-astra-20261107T010540Z-f7afe8 | 2 | not_reproduced | False | retrain | 7 | 0 | 8 | 0 | 8 | -6 | partial | natural | 527.82 | 32.0 | 0.1745 |
| miniswe | miniswe | 2506.08898 | 32h | miniswe-2506.08898-20261107T014125 | 6 | partial | False | retrain | 7 | 0 | 8 | 0 | 8 | -2 | partial | submitted |  | 32.0 | 0.2864 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2506.08898 | 32h | codex-gpt-6.1-sol-20261107T010540Z-379147 | 4 | not_reproduced | False | retrain | 7 | 0 | 8 | 0 | 8 | -4 | partial | natural | 839.96 | 32.0 | 0.6146 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2504.20571 | 8h | codex-gpt-6.1-sol-20261107T010540Z-91bc6a | 8 | reproduced | True | run | 8 | 6 | 7 | 8 | 8 | 0 | not_reproduced | budget_exhausted | 957.67 | 8.0 | 0.8461 |
| thin-gpt-6.1-sol | gpt-6.1-sol | 2510.21363 | 8h | core-a-2510.21363-3603cb | 7 | partial | False | retrain | 8 | 8 | 7 | 4 | 8 | -1 | partial | natural |  | 8.0 | 6.9633 |
| thin-gpt-6.1-sol | gpt-6.1-sol | 2504.12463 | 96h | core-a-2504.12463-d67082 | 2 | not_reproduced | False | retrain | 4 | 2 | 2 | 4 | 4 | -2 | could_not_run | natural |  | 96.0 | 0.3065 |
| thin-gpt-6.1-sol | gpt-6.1-sol | 2503.02809 | 8h | core-a-2503.02809-57a419 | 8 | reproduced | True | reimplement | 7 | 0 | 8 | 8 | 8 | 0 | partial | natural |  | 8.0 | 0.1195 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2504.12463 | 96h | codex-gpt-6.1-sol-20261108T013715Z-cb1fc6 | 2 | not_reproduced | False | retrain | 4 | 2 | 2 | 4 | 4 | -2 | could_not_run | natural | 606.01 | 96.0 | 0.1981 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2503.14698 | 96h | codex-gpt-6.1-sol-20261108T023042Z-ae78cc | 2 | not_reproduced | False | reimplement | 1 | 2 | 1 | 1 | 2 | 0 | could_not_run | natural | 562.58 | 96.0 | 0.0308 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2505.12677 | 8h | codex-gpt-6.1-sol-20261108T023043Z-5044c1 | 6 | partial | False | reimplement | 6 | 8 | 0 | 4 | 8 | -2 | not_reproduced | natural | 562.85 | 8.0 | 0.2565 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2412.11979 | 32h | codex-gpt-6.1-sol-20261108T023042Z-fb8412 | 2 | not_reproduced | False | run | 8 | 0 | 7 | 4 | 8 | -6 | could_not_run | natural | 563.27 | 32.0 | 0.3779 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2503.02809 | 8h | codex-gpt-6.1-sol-20261108T013715Z-918570 | 7 | partial | False | reimplement | 7 | 0 | 8 | 8 | 8 | -1 | partial | natural | 680.05 | 8.0 | 0.0538 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2511.01463 | 32h | codex-gpt-6.1-sol-20261108T122023Z-effbe6 | 2 | not_reproduced | False | reimplement | 5 | 0 | 2 | 2 | 5 | -3 | could_not_run | natural | 77.65 | 32.0 | 0.0692 |
| thin-gpt-6.1-sol | gpt-6.1-sol | 2505.19087 | 8h | core-a-2505.19087-095231 | 7 | partial | False | reimplement | 8 | 8 | 8 | 8 | 8 | -1 | partial | natural |  | 8.0 | 0.2642 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2506.20671 | 8h | codex-gpt-6.1-sol-20261108T023042Z-c4eacf | 2 | not_reproduced | False | run | 4 | 2 | 3 | 2 | 4 | -2 | could_not_run | natural | 660.3 | 8.0 | 0.1694 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2505.19154 | 8h | codex-gpt-6.1-sol-20261108T120002Z-8d0463 | 6 | partial | False | run | 6 | 2 | 6 | 0 | 6 | 0 | not_reproduced | natural | 98.68 | 8.0 | 0.5736 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2602.03066 | 8h | codex-gpt-6.1-sol-20261108T152418Z-d3ac33 | 7 | partial | False | reimplement | 8 | 6 | 9 | 7 | 9 | -2 | partial | natural | 66.76 | 8.0 | 0.119 |
| codex-gpt-6-astra | gpt-6-astra | 2505.10475 | 32h | codex-gpt-6-astra-20261107T010540Z-a54ff7 | 3 | not_reproduced | False | run | 0 | 0 | 0 | 3 | 3 | 0 | partial | wall_clock | 536.8 | 32.0 | 0.943 |
| codex-gpt-6-astra | gpt-6-astra | 2510.21363 | 8h | codex-gpt-6-astra-20261109T010623Z-6cef06 | 4 | not_reproduced | False | retrain | 8 | 8 | 7 | 4 | 8 | -4 | not_reproduced | natural | 3.88 | 8.0 | 0.3946 |
| thin-gpt-6.1-sol | gpt-6.1-sol | 2502.05795 | 8h | core-a-2502.05795-3948fe | 8 | reproduced | True | run | 8 | 4 | 9 | 4 | 9 | -1 | not_reproduced | natural |  | 8.0 | 6.6985 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2505.19087 | 8h | codex-gpt-6.1-sol-20261108T013802Z-809986 | 8 | reproduced | True | reimplement | 8 | 8 | 8 | 8 | 8 | 0 | partial | natural | 1471.58 | 8.0 | 0.1675 |
| codex-gpt-6-astra | gpt-6-astra | 2505.19087 | 8h | codex-gpt-6-astra-20261109T014602Z-6d6831 | 8 | reproduced | True | reimplement | 8 | 8 | 8 | 8 | 8 | 0 | partial | natural | 42.38 | 8.0 | 0.2117 |
| thin-gpt-6.1-sol | gpt-6.1-sol | 2503.14698 | 96h | core-a-2503.14698-a56492 | 1 | unverifiable | False | reimplement | 1 | 2 | 1 | 1 | 2 | -1 | could_not_run | natural |  | 96.0 | 0.0027 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2505.18809 | 8h | codex-gpt-6.1-sol-20261108T134632Z-1f75b8 | 4 | not_reproduced | False | run | 8 | 0 | 7 | 8 | 8 | -4 | not_reproduced | natural | 882.82 | 8.0 | 1.0917 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2510.21363 | 8h | codex-gpt-6.1-sol-20261107T113825Z-cb72b0 | 7 | partial | False | retrain | 8 | 8 | 7 | 4 | 8 | -1 | not_reproduced | natural | 2400.14 | 8.0 | 4.2234 |
| miniswe | miniswe | 2505.10475 | 32h | miniswe-2505.10475-20261107T014125 | 8 | reproduced | True | run | 0 | 0 | 0 | 3 | 3 | 5 | reproduced | submitted |  | 32.0 | 13.2684 |
| thin-gpt-6.1-sol | gpt-6.1-sol | 2506.20671 | 8h | core-a-2506.20671-85c5e2 | 8 | reproduced | True | run | 4 | 2 | 3 | 2 | 4 | 4 | partial | natural |  | 8.0 | 1.1006 |
| thin-gpt-6.1-sol | gpt-6.1-sol | 2506.06991 | 8h | core-a-2506.06991-4ace48 | 6 | partial | False | retrain | 6 | 4 | 6 | 0 | 6 | 0 | not_reproduced | natural |  | 8.0 | 1.1026 |
| codex-gpt-6-astra | gpt-6-astra | 2504.20571 | 8h | codex-gpt-6-astra-20261107T140243Z-9f613b | 2 | not_reproduced | False | run | 8 | 6 | 7 | 8 | 8 | -6 | partial | wall_clock | 2850.4 | 8.0 | 0.4061 |
| codex-gpt-6-astra | gpt-6-astra | 2504.12463 | 96h | codex-gpt-6-astra-20261109T140330Z-235c24 | 2 | not_reproduced | False | retrain | 4 | 2 | 2 | 4 | 4 | -2 | could_not_run | natural | 11.73 | 96.0 | 0.1663 |
| thin-gpt-6-astra | gpt-6-astra | 2505.16927 | 32h | astra-a-2505.16927-50c745 | 1 | unverifiable | False | reimplement | 4 | 0 | 4 | 4 | 4 | -3 | could_not_run | natural |  | 32.0 | 0 |
| thin-gpt-6-astra | gpt-6-astra | 2506.08898 | 32h | astra-a-2506.08898-d3db7c | 4 | not_reproduced | False | retrain | 7 | 0 | 8 | 0 | 8 | -4 | partial | natural |  | 32.0 | 0 |
| thin-gpt-6-astra-x86 | gpt-6-astra-x86 | 2505.16927 | 32h | astra-x86-2505.16927-8dbd30 | 2 | not_reproduced | False | reimplement | 4 | 0 | 4 | 4 | 4 | -2 | could_not_run | natural |  | 32.0 | 0 |
| thin-gpt-6-astra | gpt-6-astra | 2504.20571 | 8h | astra-a-2504.20571-9686ac | 8 | reproduced | True | run | 8 | 6 | 7 | 8 | 8 | 0 | partial | natural |  | 8.0 | 0 |
| thin-gpt-6.1-sol-x86 | gpt-6.1-sol-x86 | 2505.19087 | 8h | x86-a-2505.19087-ec4293 | 7 | partial | False | reimplement | 8 | 8 | 8 | 8 | 8 | -1 | partial | natural |  | 8.0 | 0 |
| miniswe | miniswe | 2505.16927 | 32h | miniswe-2505.16927-20261107T152720 | 3 | not_reproduced | False | reimplement | 4 | 0 | 4 | 4 | 4 | -1 | not_reproduced | submitted |  | 32.0 | 1.8036 |
| codex-gpt-6.1-sol | gpt-6.1-sol | 2502.05795 | 8h | codex-gpt-6.1-sol-20261108T005328Z-9d3d35 | 3 | not_reproduced | False | run | 8 | 4 | 9 | 4 | 9 | -6 | partial | wall_clock | 2863.72 | 8.0 | 0.2002 |

## 2. Static results (final)

| item | reply slot | number | source file | status |
|---|---|---|---|---|
| E5 agent log entries checked | rqBN | 45,861 of 49,585 | rebuttal/results/e5/summary.json | final |
| E5 log entries unmatched | rqBN | 3 | rebuttal/results/e5/summary.json | final |
| E5 log entries explained | rqBN | 185 | rebuttal/results/e5/summary.json | final |
| E5 runs with a write into evidence/ | rqBN | 360 of 372 | rebuttal/results/e5/summary.json | final |
| E5 runs with late evidence/ mtime | rqBN | 63 of 372 | rebuttal/results/e5/summary.json | final |
| E5 run dirs not in index | rqBN | 388 of 760 | rebuttal/results/e5/summary.json | final |
| E6 reproduced cells at 5% (index) | tolerance | 73 of 400 | rebuttal/results/e6/summary.json | final |
| E6 reproduced point estimates | tolerance | 51 of 73 | rebuttal/results/e6/summary.json | final |
| E6 best agent at 5%, run tier | tolerance | dsv4 14/34 = 41.2% [26.4, 57.8] | rebuttal/results/e6/summary.json | final |
| E6 best agent at 5%, retrain tier | tolerance | dsv4/muse 9/33 = 27.3% [15.1, 44.2] | rebuttal/results/e6/summary.json | final |
| E6 best agent at 5%, reimplement tier | tolerance | muse 5/33 = 15.2% [6.7, 30.9] | rebuttal/results/e6/summary.json | final |
| E7 v3: all four step-3 questions yes | rqBN | 55 of 100 [45.2, 64.4] | rebuttal/results/e7/summary.json | final |
| E7 rescore: reproduced cells, paper targets to corrected targets | rqBN | 73 to 71 of 400 | rebuttal/results/e7/rescore_summary.md | final |
| E7 rescore: cells that flip reproduced on correction | rqBN | 2 of 40 | rebuttal/results/e7/rescore_summary.md | final |
| E8 reproduced cells, reproduction check | YGTR Q3 | 73 of 400 | rebuttal/results/e8/summary.json | final |
| E8 best agent, environment runs removed, run | YGTR Q3 | dsv4 14/34 = 41.2% [26.4, 57.8] | rebuttal/results/e8/summary.json | final |
| E8 best agent, environment runs removed, retrain | YGTR Q3 | muse 9/32 = 28.1% [15.6, 45.4] | rebuttal/results/e8/summary.json | final |
| E8 best agent, environment runs removed, reimplement | YGTR Q3 | muse 5/32 = 15.6% [6.9, 31.8] | rebuttal/results/e8/summary.json | final |
| E8 empty cells | YGTR Q3 | 28 | rebuttal/results/e8/summary.json | final |
| E8 build-dependency runs | YGTR Q3 | 24 | rebuttal/results/e8/summary.json | final |
| E8 empty-cell trace, classes A/B/C/D | YGTR Q3 | A 2, B 16, C 0, D 4 (of 22) | rebuttal/results/e8/empty_cells_traced.csv | final |
| E9 run runs scanned of runs in index | YGTR Q2 | 127 of 129 | rebuttal/results/e9/summary.json | final |
| E9 run runs with a primary-source hit | YGTR Q2 | 117 of 127 scanned | rebuttal/results/e9/summary.json | final |
| E9 run reproduced runs with a hit | YGTR Q2 | 28 of 31 (reproduced rows, e6 table) | rebuttal/results/e9/summary.json and rebuttal/results/e6/table.csv | final |
| E9 retrain runs scanned of runs in index | YGTR Q2 | 118 of 118 | rebuttal/results/e9/summary.json | final |
| E9 retrain runs with a primary-source hit | YGTR Q2 | 62 of 118 scanned | rebuttal/results/e9/summary.json | final |
| E9 retrain reproduced runs with a hit | YGTR Q2 | 13 of 29 (reproduced rows, e6 table) | rebuttal/results/e9/summary.json and rebuttal/results/e6/table.csv | final |
| E9 reimplement runs scanned of runs in index | YGTR Q2 | 123 of 125 | rebuttal/results/e9/summary.json | final |
| E9 reimplement runs with a primary-source hit | YGTR Q2 | 75 of 123 scanned | rebuttal/results/e9/summary.json | final |
| E9 reimplement reproduced runs with a hit | YGTR Q2 | 3 of 13 (reproduced rows, e6 table) | rebuttal/results/e9/summary.json and rebuttal/results/e6/table.csv | final |

## 3. E10 re-execution

Source: /work/nvme/bfvr/msalunkhe/rebuttal/e10/state.json job ids; sacct -X -n -P -j <ids> -o JobID,JobName%24,State,Elapsed. Pending until COMPLETED.

| job | name | state | elapsed | status |
|---|---|---|---|---|
| 3540342 | e10-2510.07501-s1 | COMPLETED | 00:06:00 | final |
| 3544919 | e10-2510.07501-s2 | COMPLETED | 00:03:11 | final |
| 3544920 | e10-2505.17836-s1 | FAILED | 00:02:04 | pending |
| 3550322 | e10-2505.17836-s1 | FAILED | 00:00:06 | pending |
| 3544921 | e10-2505.17836-s2 | FAILED | 00:01:56 | pending |
| 3550323 | e10-2505.17836-s2 | FAILED | 00:00:05 | pending |
| 3544922 | e10-2506.10351-s1 | FAILED | 00:02:14 | pending |
| 3558022 | e10-2506.10351-s1 | PENDING | 00:00:00 | pending |
| 3544923 | e10-2506.10351-s2 | FAILED | 00:03:07 | pending |
| 3558023 | e10-2506.10351-s2 | PENDING | 00:00:00 | pending |

## 4. Repeat and rerun jobs (YGTR Q3, W2)

Source: sacct -X -n -P -j <12 ids> -o JobID,JobName%24,State,Elapsed,Start. Not graded here.

| job | name | state | elapsed | start | status |
|---|---|---|---|---|---|
| 3540624 | repro_easy_dsv4 | RUNNING | 22:32:37 | 2026-11-08T20:43:41 | pending |
| 3540625 | repro_medium_dsv4 | PENDING | 00:00:00 | Unknown | pending |
| 3540626 | repro_hard_dsv4 | PENDING | 00:00:00 | Unknown | pending |
| 3540627 | repro_easy_dsv4 | PENDING | 00:00:00 | Unknown | pending |
| 3540628 | repro_medium_dsv4 | PENDING | 00:00:00 | Unknown | pending |
| 3540629 | repro_hard_dsv4 | PENDING | 00:00:00 | Unknown | pending |
| 3540630 | repro_easy_dsv4 | PENDING | 00:00:00 | Unknown | pending |
| 3540631 | repro_medium_dsv4 | PENDING | 00:00:00 | Unknown | pending |
| 3540632 | repro_hard_dsv4 | PENDING | 00:00:00 | Unknown | pending |
| 3540633 | repro_medium_minimax | PENDING | 00:00:00 | Unknown | pending |
| 3540786 | repro_medium_qwen3 | RUNNING | 22:35:35 | 2026-11-08T20:40:43 | pending |
| 3540787 | repro_hard_qwen3 | PENDING | 00:00:00 | Unknown | pending |
