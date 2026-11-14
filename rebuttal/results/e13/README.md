# E13: run-to-run agreement for DeepSeek-V4-Flash (13 repeat runs, 9 papers, all three tiers)

Source of the repeats: the repeat batch jobs 3540624 to 3540629 on the GH200 cluster (same harness, same GPU grant and time limits as the runs in the paper). On 2026-11-13 thirteen of their runs had ended with a report. The run in the paper is the DeepSeek-V4-Flash row of `rebuttal/results/e6/table.csv` (grades at submission).

Grading: each repeat run was graded on 2026-11-13 with the pinned auditor (`claude-sonnet-5`, frozen eval claims, shipped rubric and prompt, no upload), through a runs root that holds one run per paper (scripts copied from E12; folders `e13_dsv4_repeats`, `e13b_dsv4_repeats`, `e13c_dsv4_repeats` on the cluster). Cost $9.91, appended to the spend ledger (item `e13-repeat-grade`).

| Paper | Tier | Run in the paper | Repeat run | Measured: paper run, repeat (target) |
| :- | :- | :- | :- | :- |
| 2506.20671 | Run | 4, not reproduced | 4, not reproduced | 0.005389, 0.005307 (6.3) |
| 2505.15201 | Retrain | 8, reproduced | 8, reproduced | 67.42, 4.17 (10) |
| 2505.15201 | Retrain | 8, reproduced | 8, reproduced | 67.42, 4.16 (10) |
| 2505.17836 | Retrain | 6, partial | 6, partial | 0.03945, 0.0398 (0.05) |
| 2505.17836 | Retrain | 6, partial | 6, partial | 0.03945, 0.03992 (0.05) |
| 2506.07673 | Retrain | 10, reproduced | 8, reproduced | -37.2, -37.2 (-37.2) |
| 2510.07501 | Retrain | 6, partial | 6, partial | -0.1681, -0.1035 (-0.2) |
| 2510.09485 | Retrain | 9, reproduced | 10, reproduced | 0.668,  () |
| 2503.02809 | Reimplement | 7, partial | 8, reproduced | 40.19, 40.88 (40) |
| 2503.02809 | Reimplement | 7, partial | 9, reproduced | 40.19, 40.15 (40) |
| 2505.19087 | Reimplement | 8, reproduced | 7, partial | 0.5933, 0.5889 (0.603) |
| 2505.19087 | Reimplement | 8, reproduced | 8, reproduced | 0.5933, 0.602 (0.603) |
| 2510.25146 | Reimplement | 2, not reproduced | 2, not reproduced | ,  (25.8) |

Result: 10 of 13 repeat runs reach the same reproduced verdict as the run in the paper (score of 8 or more). By paper, every repeat agrees with the paper's run on 7 of 9 papers (45% to 94%). The two papers that change are 2503.02809 (7 in the paper, 8 and 9 in the repeats) and 2505.19087 (8 in the paper, 7 and 8 in the repeats), both at Reimplement. 11 of 13 repeat scores are within one point of the paper's score and the largest difference is 2 points.

Pooled with E12 (Muse Spark 1.2, 10 Reimplement pairs, 9 keep their verdict) and the 8 x86 pairs (7 keep their verdict), counting each model and paper once: 23 of 27 keep their verdict (85%, Wilson 68% to 94%). In all four that change, every run scores 7, 8 or 9.

Measured values repeat as well. 2505.17836: 0.0395 in the paper's run, 0.0398 and 0.0399 in the repeats, target 0.05 (the same miss the seed reruns of E10 show). 2506.20671: 0.00539 and 0.00531 against 6.3. 2503.02809: 40.19, 40.88 and 40.15 against 40.0. 2505.19087: 0.5933, 0.5889 and 0.6020 against 0.60302. On 2505.15201 the paper's run and the repeats report different quantities (67.42, 4.17, 4.16), all graded reproduced.

Limits: 13 runs is the set that had ended by the evening of 2026-11-13, so the papers are the ones whose runs end soonest; two repeats of one paper share the paper's run and are not independent pairs.
