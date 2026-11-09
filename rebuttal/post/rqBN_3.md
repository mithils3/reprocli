**Q1: A stratified human-expert reproduction baseline.**

The revision reports, per tier, a floor on what an expert could reproduce in this environment and a re-execution check on the misses. A full human-expert baseline did not fit in the discussion period, for the cost given below.

*A floor from the agents.* At least one of the four agents reproduced 32 of the 100 papers (95% Wilson interval 24% to 42%): 16 of 34 at Run (47%, 31% to 63%), 11 of 33 at Retrain (33%, 20% to 50%) and 5 of 33 at Reimplement (15%, 7% to 31%). These papers are reproducible with the same environment and budgets, so they bound an expert baseline from below, and the best single agent reaches 13, 9 and 5 of them. The counts include the corrections in our other replies, which leave 70 of the 400 agent-paper cells reproduced, against 73 at submission.

*Whether misses come from the environment.* For 3 papers where an agent followed the released pipeline and the auditor graded the run partial (6 or 7 of 10), we re-ran the agent's final command sequence on the same GH200 nodes with two new seeds and no model in the loop. Only these 3 had a single clean command chain. All have grants of 8 GPU-hours or less, 1 is at Run and 2 are at Retrain, and Reimplement papers release no code to re-run.
- 2505.17836 (Retrain): GoRank mean relative error at 80k steps, target about 0.05. The original run measured 0.0395 and the new seeds 0.0400 and 0.0393, a spread of 0.0007. The same commands miss by the same amount without the agent, which places the cause in the environment or the paper.
- 2510.07501 (Retrain): a bias with target -0.20. The original run measured -0.2241 and the new seeds -0.1308 and +0.0566, a span of 0.0566 - (-0.2241) = 0.28, so the original near miss lies inside seed variation.
- 2506.10351 (Run): target 93.12, original run 94.19, [and the new seeds gave x and y, so the miss repeats without the agent / falls inside seed variation].

*Cost of the full baseline.* Each task is anchored to the authors' own reported result, which is an expert result on the same artifacts, so the benchmark can follow agents as they improve. One human pass over the 100 papers at the same budgets needs expert time on each paper and up to 2,552 H100-hours, the grant of one agent. The Limitations section states that we have not run one.

**Q2: How claims, configurations, targets and tolerances were validated, and annotator agreement.**

One author reviewed every extracted field before the dataset was frozen and no second annotator did, so there is no agreement figure, as Appendix E now states. For the revision we added an independent check of every target, and it finds the frozen value wrong on 8 of the 100 claims.

*Targets.* A model from a different lab than our auditor, OpenAI's gpt-6.1-sol, read each paper and answered four yes-or-no questions about its frozen target, quoting the passage behind each answer. It saw the frozen target, so it verifies each target against the paper and does not extract targets on its own. The paper supports the value for 92 of the 100 claims, the metric for 95, the dataset and split for 76, and the method or variant for 69, and 55 pass all four (Appendix E). A second pass over the other 45 found the value itself wrong on 8, the value right and a setting or label off on 16, and the target correct or the paper ambiguous on 21. On 2506.18890, for example, the frozen 27.443 PSNR appears in the paper for 24 input views while the frozen configuration says 12. We corrected the 8 values and rescored their runs, which changes two verdicts (our reply to Reviewer T29u, Q2).

*Claims and configurations.* The choice of the central claim rests on the author review alone, which Appendix E now states. The human audit, the last of three construction stages, also settled each compute estimate.

*Tolerances.* Of the 62 claims that give a point estimate, 58 use the default 5% tolerance and 4 the margin their paper states, and the other 38 are tested by direction (21), threshold (14) or another form (3). Rescoring every graded run at 1%, 2%, 5% and 10% gives the best agent 9, 12, 14 and 14 of the 34 Run papers, and Reimplement stays the lowest tier at each (our reply to Reviewer T29u, Q2, and Appendix F).

Thank you again for the review.
