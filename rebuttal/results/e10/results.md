# E10 results: the agent's final command chain rerun with two new seeds, no model in the loop

| paper | tier | original agent run | paper target | original measured | seed 1 | seed 2 | outcome |
|---|---|---|---|---|---|---|---|
| 2505.17836 | retrain | muse, score 6 | about 0.05 | 0.0395 | 0.0400 | 0.0393 | misses on both seeds; the measurement repeats within 0.0007 |
| 2510.07501 | retrain | muse, score 6 | -0.20 | -0.2241 | -0.1308 | +0.0566 | misses on both seeds; the measurement moves by 0.28 across seeds, so the original near miss is inside seed noise |
| 2506.10351 | run | dsv4, score 7 | 93.12 | 94.19 | pending | pending | jobs queued on ghx4 |

Metrics: 2505.17836 GoRank mean relative error at 80k steps (job logs e10/logs/*-3550825.log, *-3550826.log); 2510.07501 bias (STATUS.md 2026-11-07 12:35); targets and original values from selection.csv.
Status: 2 of 3 papers finished, and both still miss on both seeds.
