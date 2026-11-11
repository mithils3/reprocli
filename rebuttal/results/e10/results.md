# E10 results: the agent's final command chain rerun with two new seeds, no model in the loop

| paper | tier | original agent run | paper target | original measured | seed 1 | seed 2 | outcome |
|---|---|---|---|---|---|---|---|
| 2505.17836 | retrain | muse, score 6 | about 0.05 | 0.0395 | 0.0400 | 0.0393 | misses on both seeds; the measurement repeats within 0.0007 |
| 2510.07501 | retrain | muse, score 6 | -0.20 | -0.2241 | -0.1308 | +0.0566 | misses on both seeds; the measurement moves by 0.28 across seeds, so the original near miss is inside seed noise |
| 2506.10351 | run | dsv4, score 7 | 93.12 | 94.19 | 93.65 | 94.15 | both seeds within 0.54 points of the original (94.19 - 93.65); all three values are inside 5% of the target, and the run's partial grade came from a protocol deviation the agent disclosed |

Metrics: 2505.17836 GoRank mean relative error at 80k steps (job logs e10/logs/*-3550825.log, *-3550826.log); 2510.07501 bias (STATUS.md 2026-11-07 12:35); targets and original values from selection.csv.
Status: 3 of 3 papers finished. The 2 Retrain papers still miss on both seeds; on the Run paper the agent's value repeats. 2506.10351 metric: test accuracy on EPN-612 (job logs e10/logs/e10-2506.10351-s1-3558022.log, e10-2506.10351-s2-3558023.log, test_results.json test_acc 0.93646 and 0.94154).
