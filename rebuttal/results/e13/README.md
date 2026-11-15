# E13: run-to-run agreement for DeepSeek-V4-Flash (16 repeat runs, 9 papers, all three tiers)

Source of the repeats: the repeat batch jobs 3540624 to 3540629 on the GH200 cluster (same harness, same GPU grant and time limits as the runs in the paper). On 2026-11-13 thirteen of their runs had ended with a report, and three more ended on the morning of 2026-11-14 (two at about 05:23, one at 07:05). The run in the paper is the DeepSeek-V4-Flash row of `rebuttal/results/e6/table.csv` (grades at submission).

Grading: each repeat run was graded on 2026-11-13 (the last three on 2026-11-14) with the pinned auditor (`claude-sonnet-5`, frozen eval claims, shipped rubric and prompt, no upload), through a runs root that holds one run per paper (scripts copied from E12; folders `e13_dsv4_repeats`, `e13b_dsv4_repeats`, `e13c_dsv4_repeats`, `e13d_dsv4_repeats`, `e13e_dsv4_repeats` on the cluster). Cost $11.75 ($9.91 for the first 13 and $1.84 for the last three), appended to the spend ledger (item `e13-repeat-grade`).

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
| 2506.20671 | Run | 4, not reproduced | 4, not reproduced | 0.005389, 0.005307 (6.3) |
| 2510.07501 | Retrain | 6, partial | 6, partial | -0.1681, -0.1433 (-0.2) |
| 2510.09485 | Retrain | 9, reproduced | 10, reproduced | 0.668, 0.668 () |

Result: 13 of 16 repeat runs reach the same reproduced verdict as the run in the paper (score of 8 or more). By paper, every repeat agrees with the paper's run on 7 of 9 papers (45% to 94%). The two papers that change are 2503.02809 (7 in the paper, 8 and 9 in the repeats) and 2505.19087 (8 in the paper, 7 and 8 in the repeats), both at Reimplement. 14 of 16 repeat scores are within one point of the paper's score and the largest difference is 2 points.

Pooled with E12 (Muse Spark 1.2, 10 Reimplement pairs, 9 keep their verdict) and the 8 x86 pairs (7 keep their verdict), counting each model and paper once: 23 of 27 keep their verdict (85%, Wilson 68% to 94%). In all four that change, every run scores 7, 8 or 9.

Measured values repeat as well. 2505.17836: 0.0395 in the paper's run, 0.0398 and 0.0399 in the repeats, target 0.05 (the same miss the seed reruns of E10 show). 2506.20671: 0.00539 in the paper's run, 0.00531 and 0.00531 in the repeats, against 6.3. 2510.07501: -0.168 in the paper's run, -0.104 and -0.143 in the repeats, against -0.2. 2503.02809: 40.19, 40.88 and 40.15 against 40.0. 2505.19087: 0.5933, 0.5889 and 0.6020 against 0.60302. On 2505.15201 the paper's run and the repeats report different quantities (67.42, 4.17, 4.16), all graded reproduced.

Limits: 16 runs is the set that had ended by the morning of 2026-11-14, so the papers are the ones whose runs end soonest; two repeats of one paper share the paper's run and are not independent pairs.

## Update 2026-11-14 21:34: a 17th repeat run, on a tenth paper

`3540626-2506.17475-dcee2d` (2506.17475, Reimplement) ended at 20:51 and was graded with the pinned auditor in `e13f_dsv4_repeats` ($0.81; E13 total $12.56 of its $15 limit; Anthropic ledger $169.01 of $230). The auditor gives it 7, partial; the run in the paper scored 5, not reproduced, so the reproduced verdict is the same.

| Paper | Tier | Run in the paper | Repeat run | Measured: paper run, repeat (target) |
| :- | :- | :- | :- | :- |
| 2506.17475 | Reimplement | 5, not reproduced | 7, partial | 10.0, 78.03 (79.01) |

Counts with this run: 14 of 17 repeat runs keep the reproduced verdict of the run in the paper, and every repeat agrees on 8 of 10 papers (80%, Wilson 49% to 94%). Pooled with the 10 Muse Spark 1.2 pairs and the 8 x86 pairs: 24 of 28 model and paper pairs (86%, Wilson 69% to 94%). The four pairs that change are the same four, each with every run at 7, 8 or 9.

The measured value does not repeat on this paper. The paper's run reported 10.0% test accuracy (chance on CIFAR-10) and the repeat reports a mean of 78.03% over 11 seeds, within 5% of the 79.01% target. The auditor still withholds the reproduced verdict, with two medium flags: the agent chose the coefficient learning rate 0.04 from a sweep because it matched the paper's number (the paper states 0.001), and its own full-rank baseline reached 85.57% against the paper's 78.98%. The two scores differ by 2 points, which is the largest difference in the set, now seen on two pairs.

The replies posted on 2026-11-14 and Section 5.2 of the second revised PDF state the counts before this run (16 runs, 7 of 9 papers, 23 of 27 pairs).

## Update 2026-11-15 00:31: an 18th repeat run

`3540629-2510.25146-3bf237` (2510.25146, Reimplement, a second repeat of this paper) ended at 23:56 on 11-14 and was graded in `e13g_dsv4_repeats` ($0.50; E13 total $13.06 of its $15 limit; Anthropic ledger $169.51 of $230). It scores 2, not reproduced, the same as the run in the paper and the first repeat (both 2).

Counts with this run: 15 of 18 repeat runs keep the reproduced verdict of the run in the paper (83%, Wilson 61% to 94%). The paper and pair counts do not move: 8 of 10 papers and 24 of 28 model and paper pairs.

## Update 2026-11-15 04:40: a 19th and a 20th repeat run, on two more papers

`3540625-2506.06991-41fba8` (2506.06991, Retrain) ended at 04:08 and `3540626-2402.04579-967475` (2402.04579, Reimplement) ended at 04:29. Both were graded with the pinned auditor, in `e13h_dsv4_repeats` ($0.71) and `e13i_dsv4_repeats` ($0.82), which brings E13 to $14.60 of its $15 limit and the Anthropic ledger to $171.05 of $230. No further grade fits under the E13 limit.

| Paper | Tier | Run in the paper | Repeat run | Measured: paper run, repeat (target) |
| :- | :- | :- | :- | :- |
| 2506.06991 | Retrain | 6, partial | 6, partial | 0.803, 0.7999 (0.91) |
| 2402.04579 | Reimplement | 4, not reproduced | 7, partial | 0.5248, 0.4764 (direction claim, no point target) |

Counts with these runs: 17 of 20 repeat runs keep the reproduced verdict of the run in the paper (85%, Wilson 64% to 95%), and every repeat agrees on 10 of 12 papers (83%, Wilson 55% to 95%). Pooled with the 10 Muse Spark 1.2 pairs and the 8 x86 pairs: 26 of 30 model and paper pairs (87%, Wilson 70% to 95%). The four pairs that change are the same four, each with every run at 7, 8 or 9.

On 2506.06991 the score, the verdict and the measured value all repeat; the auditor notes one low flag (the released notebook labels gpt-4o-mini files "GPT-4", and the agent used them as the closest released data). On 2402.04579 the scores differ by 3 points (4 and 7), the largest difference in the set, with the same reproduced verdict: the repeat ran 4 of the paper's 100 seeds after wall-time kills and tuned its own solver settings, which the auditor marks with two medium flags.

The replies posted on 2026-11-14 and Section 5.2 of the second revised PDF state the counts at the freeze (16 runs, 7 of 9 papers, 23 of 27 pairs).
