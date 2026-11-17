# Second-round answers for Reviewer T29u (2026-11-16; prepared, not posted)

### If asked: repeats cover one agent and tier; how chosen?

The 10 Muse Spark 1.2 papers are the Reimplement papers on which a second run, started the same day with the same budget, had finished. They include all 5 Reimplement papers that Muse Spark 1.2 reproduces, and 4 of the 5 are reproduced again.

| Agent | Papers | Keep the reproduced verdict |
| :- | :- | -: |
| Muse Spark 1.2 | 10 Reimplement | 9 |
| DeepSeek-V4-Flash | 1 Run, 6 Retrain, 5 Reimplement | 1, 6 and 3 |
| gpt-6.1-sol and gpt-6-astra | 8 pairs | 7 |
| All | 30 pairs | $\frac{26}{30}$ = 87% [70%, 95%] |

The DeepSeek-V4-Flash row holds every repeat run of that agent that finished, 20 runs of which 17 keep the verdict (Section 5.2 reports the first 16). In each of the four pairs that change, every run scores 7, 8 or 9 out of 10.

Source: rebuttal/results/e12/README.md (9 of 10; 5 at 8 or more, 4 again); rebuttal/results/e13/README.md (20 runs, 17 keep; 10 of 12; 26 of 30); paper.txt 563. The four changed pairs: Muse Spark 1.2 and DeepSeek-V4-Flash on 2503.02809, DeepSeek-V4-Flash on 2505.19087 (e12, e13 READMEs), gpt-6-astra on 2505.19087 (7 and 8, rebuttal/results/databook/frontier_cells.csv).
Caution: only 4 of the 12 DeepSeek-V4-Flash papers are in subset.json, so no stratified draw is claimed; 18 of 38 opened repeats stopped ungraded (STATUS.md:135); e12 says completion "favours shorter runs". Since 2026-11-17 nine more repeat runs have finished and are ungraded (5 of DeepSeek-V4-Flash at Retrain, 4 of Qwen3.6-27B at Reimplement; STATUS.md, 11-17 09:45), so "every repeat run of that agent that finished" must become "every repeat run graded by 11-15" unless they are graded first, and three of them self-report a verdict that differs from the paper run.

### If asked: who is right on the 28 split runs?

Each run has one human grade, so we describe the 28 runs by their two scores. In 18 of them the scores are a 7 and an 8, and in 22 the lower score is a 6 or a 7. Of the 9 runs that only the LLM auditor accepts, the human gave a 7 to seven and a 5 to two. The tier result is the same under either grader (Table 13):

| Reproduced cells | Run (of 136) | Retrain (of 132) | Reimplement (of 132) |
| :- | -: | -: | -: |
| Human grade | 35 = 26% | 32 = 24% | 16 = 12% |
| LLM auditor | 31 = 23% | 29 = 22% | 13 = 10% |

When the LLM auditor graded 38 runs a second time, no reproduced verdict changed and the mean absolute score difference was 0.39 points out of 10.

Source: rebuttal/results/e4/matrix_0_10.csv (7 and 8: 11 + 7; lower score 6 or 7: 15 + 7; human 5: 2); paper.txt Table 13; rebuttal/results/e7/rescore_summary.md (38, 0, 0.39).
Caution: no second human grade or per-run label exists, so no causes are given; the 38 runs come from the corrected-target papers; Table 13 uses submitted grades.

### If asked: do results hold on the 55 targets?

The 92 counts the value question alone, and 55 targets pass all four questions (Table 15). The reproduction rate on those 55 is close to the rate on the other 45, at $\frac{36}{220}$ = 16% against $\frac{34}{180}$ = 19% of cells. By tier, the best agent reproduces:

| Targets | Run | Retrain | Reimplement |
| :- | -: | -: | -: |
| All 100 | $\frac{13}{34}$ = 38% | $\frac{9}{33}$ = 27% | $\frac{5}{33}$ = 15% |
| Without the 16 with a setting or label off | $\frac{10}{29}$ = 34% | $\frac{6}{23}$ = 26% | $\frac{5}{32}$ = 16% |
| The 55 that pass all four | $\frac{9}{19}$ = 47% | $\frac{2}{13}$ = 15% | $\frac{4}{23}$ = 17% |

Run is the highest tier in every row. On the 55, Retrain has 13 papers (15% [4%, 42%]), so that subset does not order Retrain and Reimplement.

Source: scratchpad followup_1116/ev_targets/ev_targets_raw.txt lines 42 to 53, revision grades (36 of 220; 34 of 180; 10/29, 6/23, 5/32; 9/19, 2/13, 4/23); rebuttal/results/tiers/tier_tests.md (13/34, 9/33, 5/33); paper.txt 3825.
Caution: on the 55, Muse Spark 1.2 is lowest at Retrain, against the posted "every agent ... lowest ... at the Reimplement tier"; the posted "the other 8" is a different set from the 8 corrected targets (3 papers shared), so do not repeat it.

### If asked: tier tests are selective, no p-values

The table gives the two-proportion z statistic for every agent and every pair of tiers.

| | Run and Reimplement | Retrain and Reimplement | Run and Retrain |
| :- | -: | -: | -: |
| DeepSeek-V4-Flash | **2.46** | 1.55 | 0.96 |
| Muse Spark 1.2 | 1.40 | 0.93 | 0.48 |
| Qwen3.6-27B | 1.16 | 1.51 | -0.38 |
| MiniMax-M2.7 | 0.56 | 1.71 | -1.24 |
| At least one agent | **2.81** | 1.72 | 1.15 |

Two differences are statistically significant, both between Run and Reimplement: two-sided p = 0.014 for DeepSeek-V4-Flash and p = 0.005 for papers reproduced by at least one agent. The other three agents also have a lower rate at Reimplement than at Run, by a margin that 33 or 34 papers per tier do not separate. No row separates Run from Retrain, so the tests support one statement: the reproduction rate falls where no code is released (Section 5.2).

Source: rebuttal/results/tiers/tier_tests.md (15 z values); paper.txt 579 to 581 (2.46, 0.96, 2.81, 1.15).
Caution: the p-values are computed from z (two-sided normal) and are in no file; no paper-clustered test, no correction for 15 tests.

### If asked: what are the disagreements at score 0?

A score of 0 marks a high-severity integrity flag or one of three related conditions (Table 10). Of the 57 runs with a 0 from at least one grader, both graders gave it on 42, the LLM auditor alone on 11 and the human alone on 4. On the 11, the human scored seven runs between 1 and 5, two at 6 or 7, and two at 8 or 9; those last two are the runs a human called reproduced that the LLM auditor disqualified. On the 4, the LLM auditor gave 1, 2, 4 and 6. No run that the human scored 0 counts as reproduced.

Source: rebuttal/results/e4/matrix_0_10.csv (auditor-0 column 42, 7, 2, 2; human-0 row 1, 2, 4, 6); paper.txt 3590, Table 11.
Caution: the flag kind of each run is not on disk, so the answer gives scores only.

### If asked: all 100 papers are NeurIPS 2025

We agree that one venue and year bounds what the numbers cover, and we limit our claims to these 100 papers and the agents we tested (Section 6). The pipeline starts from the 3,414 NeurIPS 2025 papers with an arXiv ID, a classifier verified the released artifacts of 687 papers in a 1,000-paper sample, and the 100 come from an audit pool stratified by tier and compute band. Humans audit only the selected pool, which keeps the same pipeline usable on another venue or year.

Source: paper.txt 375 to 389 (3,414; 1,000; 687), 400 to 417, 303 to 305, 811.

### Short reply if the follow-up is the predicted one

Thank you for the follow-up, and for confirming that the confusion matrix and the tolerance table answered your two questions.

**Repeat runs.** The 10 Muse Spark 1.2 papers are the Reimplement papers on which a second run with the same budget had finished, and they include all 5 Reimplement papers this agent reproduces, 4 of which are reproduced again. Across agents and tiers, repeat runs keep the reproduced verdict on $\frac{26}{30}$ = 87% [70%, 95%] of model and paper pairs: 9 of 10 for Muse Spark 1.2, 10 of 12 for DeepSeek-V4-Flash (1 Run, 6 Retrain and 5 Reimplement papers), and 7 of 8 for gpt-6.1-sol and gpt-6-astra.

**The 28 runs.** Each run has one human grade. In 18 of the 28 the two scores are a 7 and an 8, and under the human grade Reimplement remains the lowest tier, with 16 of 132 cells reproduced (12%) against 35 of 136 at Run (26%).

**Targets.** On the 55 targets that pass all four questions, $\frac{36}{220}$ = 16% of cells are reproduced, against $\frac{34}{180}$ = 19% on the other 45. The best agent's Run rate there is 9 of 19 (47%), the highest of the three tiers, and with 13 Retrain papers that subset does not order Retrain and Reimplement.

We would be glad to answer any further questions.
