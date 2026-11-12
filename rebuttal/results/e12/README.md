# E12: run-to-run agreement from an existing second run (Muse Spark 1.2, 10 Reimplement papers)

Source of the pairs: the project database (`repro_runs`, read 2026-11-11). On 2026-08-20 Muse Spark 1.2 was started twice on the Reimplement papers with the same 8 H100-hour budget: an early batch (`muse_spark Hard 20260820T132822Z`) and the batch of record (`muse_spark Hard 20260820T205201Z`, the runs in the paper). 10 runs of the early batch ended naturally. They had only a self-grade. No other cell has two complete runs after the dataset freeze (the 91 other repeated cells are Qwen3.6-27B and MiniMax-M2.7 runs from before 2026-07-13).

Grading: each of the 10 early-batch runs was graded on 2026-11-11 with the pinned auditor (`claude-sonnet-5`, frozen eval claims, shipped rubric and prompt, no upload), one paper at a time through a runs root that holds only that run. Cost $7.90 (`spend_e12.jsonl` on the cluster, appended to the ledger). Outputs on the cluster: `/work/nvme/bfvr/msalunkhe/rebuttal/e12_repeats/`.

| Paper | Run in the paper | Second run |
| :- | :- | :- |
| 2402.04579 | 0, disqualified | 4, not reproduced |
| 2503.02809 | 8, reproduced | 7, partial |
| 2505.12677 | 0, disqualified | 6, partial |
| 2505.19087 | 8, reproduced | 8, reproduced |
| 2505.22860 | 9, reproduced | 8, reproduced |
| 2505.24452 | 8, reproduced | 8, reproduced |
| 2509.16950 | 0, disqualified | 0, disqualified |
| 2510.25146 | 2, not reproduced | 0, disqualified |
| 2512.02339 | 4, not reproduced | 5, not reproduced |
| 2602.03066 | 9, reproduced | 8, reproduced |

Reproduced verdict (score 8 or more) the same in 9 of 10 pairs: 4 reproduced in both, 5 in neither, 1 split (8 against 7). Wilson 95% interval for 9/10: 60% to 98%. Five-way verdict the same in 6 of 10. Absolute score difference: 4, 1, 6, 0, 1, 0, 0, 2, 1, 1; within one point in 7 of 10; mean 1.6. The two large differences are pairs where the run in the paper carries a high-severity flag (score set to 0) and the second run does not.

Limits: one agent and one tier; the early batch holds only the runs that had ended before the relaunch, which favours shorter runs; the harness commit of 2026-08-20 (855f111, closes stdin for agent steps) lies between the two batches.

Files: e12_grades.csv, muse_pairs.csv (run ids, start times, rounds and spend of both runs).
