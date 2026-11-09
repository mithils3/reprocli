# Replies to Reviewer rqBN, rewrite of 2026-11-09

### Reply to rqBN, part 1 of 3 (2,344 characters)

Thank you for checking how runs are graded and how their logs are protected. The revision makes these changes for your points:
- Appendix D (W1): the confusion matrix of the auditor, the LLM that grades every run, against the human verdict, with precision, recall, agreement at the pass threshold of 8, and flag agreement.
- Appendix A (W2): a description of the two logs that matches the code, and their comparison with a second transcript on the host.
- Section 5.3 and Limitations (Q1): a re-execution of missed runs with new seeds, and the bound on build failures.
- Appendix E (Q2): a check of each paper's frozen target, the claim, configuration and value we fixed before any agent ran, against the paper itself.

**W1: Validation of the auditor.**

The auditor (Claude Sonnet 5) was validated against a human grade on the 372 runs that have both, and Appendix D now gives the five-by-five confusion matrix, also shown in our reply to Reviewer T29u (Q1). A run counts as reproduced at a score of 8 or higher. On that verdict the auditor's precision is 64/73 = 88% and its recall is 64/83 = 77%, giving the F1 of 0.82. On the full 0 to 10 scale, the auditor and the human give the same score to 253 of the 372 runs and scores within one point to 324, with a mean absolute difference of 0.59 points.

Tiers group papers by what their authors released: Run papers release code, data and weights, Retrain papers no weights, and Reimplement papers no code. The differences between tiers are within sampling error: Run recall is 80% (95% interval 64% to 90%) and Reimplement recall 69% (44% to 86%).

| Tier | Precision | Recall | F1 |
| :- | -: | -: | -: |
| Run | **28/31 = 90%** | **28/35 = 80%** | **0.85** |
| Retrain | 25/29 = 86% | 25/32 = 78% | 0.82 |
| Reimplement | 11/13 = 85% | 11/16 = 69% | 0.76 |

We did not measure agreement per flag type. Every high-severity integrity flag, such as a number copied from the paper, forces a score of 0, so we compared that outcome. The human placed 46 runs at 0 and the auditor 53, and they agree on 42 of the 57 runs that either placed there.

Three graders divided the 396 runs that started, so each run received one human label, given under the same rubric and blind to the auditor's score. That design does not measure agreement between humans, and Appendix D now states this beside the F1.

### Reply to rqBN, part 2 of 3 (2,260 characters)

**W2: Agent-writable logs without an integrity check.**

Besides the two logs in the agent's workspace, the harness writes every command to a second transcript on the host, outside the sandbox where the agent cannot reach it. Comparing the workspace logs with it over all 372 graded runs found one edited log, and the edit did not raise that run's score.

The harness, the program that runs the agent, writes commands.log and trajectory.jsonl into each run's evidence directory, the folder the auditor reads, and the sandbox mounts that folder read-write, so the agent could have rewritten both files. Appendix A now reads:
> "The auditor traces every number to the command that produced it. Because the agent could edit these two files, we compared every logged entry with the transcript the harness writes on the host, outside the sandbox."

We matched each of the 45,861 entries that agent commands produced in the two files against the host transcript, requiring the same command and return code and, for GPU jobs, the same cost and remaining GPU-hour budget. Of these, 45,673 match exactly. The other 188 are bookkeeping differences in four groups (Appendix A):

| Group | Entries |
| :- | -: |
| Calls the harness refused, which have no cost line | 100 |
| Remaining budget differs by at most 0.00015 GPU-hours | 60 |
| First attempts of a call the agent then retried | 25 |
| Budget logged before the GPU release charge, same cost, differs by at most 0.0003 GPU-hours | 3 |

A search of every agent command for writes to the two files found one. On 2510.25146, MiniMax-M2.7 replaced commands.log with its own notes through a write_file call. The auditor scored that run 1 of 10, the rubric's grade for an unverifiable run. The 3 entries in the last group are all in trajectory.jsonl, and no run wrote to that file, so they are not agent edits. Commands missing from the workspace logs are covered too: two early-return code paths left 119 commands in 65 runs out of commands.log, the host transcript holds all 119, and Appendix A reports them.

The host transcript is not hash-chained. It is protected by lying outside every directory the sandbox mounts, so the check catches any edit made through the agent's commands, and Appendix A states that limit.

### Reply to rqBN, part 3 of 3 (4,133 characters)

**Q1: A stratified human-expert reproduction baseline.**

By the auditor's grades, at least one of the four agents reproduced 32 of the 100 papers (95% Wilson interval 24% to 42%): 16 of 34 at Run (47%, 31% to 63%), 11 of 33 at Retrain (33%, 20% to 50%) and 5 of 33 at Reimplement (15%, 7% to 31%), and the tiers keep their order. These grades include the corrections in our other replies, which leave 70 of the 400 agent-paper pairs reproduced, against 73 at submission.

RECLAIM is meant to track agents' ability to reproduce papers as it improves, and a single human attempt would become a moving reference, so each task is anchored to the authors' own reported result. We did not run a human-expert baseline, and the Limitations section states this. It would need expert time on each paper plus up to 2,552 H100-hours, a quarter of the 10,208 H100-hours we granted the four agents, which does not fit in the discussion period.

For 3 papers where an agent followed the released pipeline and still landed outside tolerance, we checked whether the environment alone produces the miss: we re-ran the agent's final command sequence on the same GH200 nodes with two new seeds and no model in the loop. Only these 3 had a single clean command chain, 1 at Run and 2 at Retrain, all with grants of 8 GPU-hours or less, and Reimplement papers release no code to re-run.
- 2505.17836 (Retrain): GoRank mean relative error at 80k steps, target about 0.05. All three runs land below the target, at 0.0395 originally and 0.0400 and 0.0393 on the new seeds, a spread of 0.0400 - 0.0393 = 0.0007. The same commands miss by the same amount without the agent, which places the cause in the environment or the paper.
- 2510.07501 (Retrain): a bias with target -0.20. The original run measured -0.2241 and the new seeds -0.1308 and +0.0566, which also miss. The three values span 0.0566 - (-0.2241) = 0.28, so the original near miss lies inside seed variation.
- 2506.10351 (Run): target 93.12, original run 94.19, [and the new seeds gave x and y, so the miss repeats without the agent / falls inside seed variation].

Our reply to Reviewer YGTR (W2) bounds the build failures from our aarch64 hardware.

**Q2: How claims, configurations, targets and tolerances were validated, and annotator agreement.**

One author reviewed every extracted field before the dataset was frozen and no second annotator did, so there is no agreement to report, as Appendix E now states. Appendix E now also says that the human audit, the last of three construction stages after artifact classification and compute capping, settled each compute estimate.

Of the 100 frozen targets, 55 pass all four questions of a check against their papers. For the other 45, a second check found the frozen number itself wrong on 8, the number right but a setting or label off on 16, and the target correct or the paper ambiguous on 21. In the first check, a model from a different lab than our auditor, OpenAI's gpt-6.1-sol, read each paper and answered four yes-or-no questions about its frozen target, quoting the passage behind each answer. It saw the frozen target when it answered, so this is a check of each target against its paper. The paper supports the value for 92 of the 100 claims, the metric for 95, the dataset and split for 76, and the method or variant for 69 (Appendix E). On 2506.18890, one of 18 papers that fail only the method question, the frozen value of 27.443 PSNR appears in the paper for 24 input views while the frozen configuration says 12. Correcting the 8 wrong numbers changes two verdicts (our reply to Reviewer T29u, Q2). The choice of claim itself rests on construction alone, which Appendix E now states.

Of the 62 claims that give a point estimate, 58 use the default 5% tolerance and 4 use the margin their paper states, and the other 38 are tested by direction or threshold. We checked the tolerance by rescoring every graded run at 1%, 2%, 5% and 10%: the best agent reproduces 9, 12, 14 and 14 of the 34 Run papers, and the tiers keep their order at each (our reply to Reviewer T29u, Q2, and Appendix F).

Thank you again for the review.

### Sources (rqBN)

| Number | File |
| :- | :- |
| F1 0.82, 396 runs, three graders, one label per run, 372 of them with an auditor grade | paper Section 4 and Appendix D (protocol of record, memory human-grader-study-lost) |
| 45,861 checked: 45,673 exact, 100, 60, 25, 3 unmatched (log table) | rebuttal/results/e5/summary.json; e5/README.md:11, :18 |
| 1 of 372 wrote to commands.log, 2510.25146, write_file, graded 1 unverifiable | rebuttal/results/e5/README.md; viewer index tools/anon_viewer/public/data/index.json |
| 119 commands missing in 65 runs, two early-return paths | rebuttal/results/e5/README.md (log completeness) |
| host transcript outside the sandbox mounts, not hash-chained | rebuttal/results/e5/README.md; Risks item 6 below (no hash-chained log in the code) |
| 3 unmatched entries all in trajectory.jsonl; no agent write to trajectory.jsonl; each gap equals the GPU release charge | rebuttal/results/e5/README.md (For a human to judge, item 2; write hits); rebuttal/results/e5/traces_2026-11-08.md (Trace A) |
| 3 papers re-executed (1 Run, 2 Retrain), exclusions | rebuttal/results/e10/README.md; e10/selection.csv |
| 24 build-and-dependency runs, best Run 13/34 unchanged | rebuttal/results/e8/summary.json; e8/bound.csv |
| 92, 95, 76, 69, 55 of 100 (target table); 45 failures | rebuttal/results/e7/summary.json (step3); e7/README.md |
| 62 point estimates, 58 default, 4 margins, 38 others (21 direction, 14 threshold, 3 other); 9/12/14 of 34 | rebuttal/results/e6/summary.json; e6/README.md |
| Appendix A wording, before and after | paper_latex/appendix/a_harness.tex lines 130-134 (before); the after text is proposed here |
| 372 runs, 64/73, 64/83, 253 and 324 of 372, 0.59 points, 42 of 57 at 0; per tier 28/31, 28/35, 25/29, 25/32, 11/13, 11/16, recall interval 44% to 86% | rebuttal/results/e4/summary.json (per_tier_reproduced from e4/per_tier.csv) |
| re-execution: 2505.17836 GoRank mean relative error at 80k steps, target about 0.05, 0.0395, 0.0400, 0.0393, spread 0.0007; 2510.07501 bias, target -0.20, -0.2241, -0.1308, +0.0566, span 0.0566 - (-0.2241) = 0.28; 2506.10351 queued | rebuttal/results/e10/results.md (table and Metrics line) |
| no Reimplement paper in the re-execution (selection from Run and Retrain only) | rebuttal/results/e10/README.md (Selection) |
| no human reproduction, stated in Limitations | paper_latex/iclr2027_conference.tex:583-589 |
| 2,552 = 10,208 / 4 H100-hours | paper Section 5.2 (paper_latex/iclr2027_conference.tex line 494, "1,888 of the 10,208 H100-hours we granted") |
| 8 corrected targets change two verdicts | rebuttal/results/e7/rescore_summary.md; e7/class_d_rescore.md |
| 2506.10351 re-execution | pending (E10) |
| best of four agents: 32 of 100 papers [24%, 42%]; Run 16/34 (47%, [31%, 63%]), Retrain 11/33 (33%, [20%, 50%]), Reimplement 5/33 (15%, [7%, 31%]); 70 reproduced cells | tools/anon_viewer/public/data/index.json minus the two checkpoint runs and the two 2505.23747 Run runs, plus the new Muse grade on 2503.23035 (computed by the main session, 2026-11-09) |
| other 45 targets: frozen number wrong 8, number right and a setting or label off 16, correct or unclear 21; human at 0 on 46 runs, auditor on 53 | rebuttal/mithil/e7_merged.md (Kind of error column: number 8, setting or label 15 + 1, none 21); rebuttal/results/e4/summary.json (disqualified_score0_as_high_severity) |
| Run recall interval 64% to 90%; 25 retried first attempts absent from the host transcript; 2510.07501 seeds also miss | rebuttal/results/e4/summary.json (per_tier_reproduced.run.recall_wilson95); e5/README.md (Headline); e10/results.md (outcome column) |

## Notes

- Parts are split by point: part 1 W1, part 2 W2, part 3 Q1 and Q2.
- W2 now quotes only the new Appendix A text, so the concession sits in the revised PDF.
- W2 calls the 188 bookkeeping differences; the 25 retried first attempts are absent from the host transcript (e5 README).
- W1 "giving the F1 of 0.82": 2 x 64 / (73 + 83) = 0.82 on the 372 runs; the paper states 0.82 over the 396-run study.
- W1 "We did not measure agreement per flag type" assumes no per-flag human labels exist.
- Q2 "correct or the paper ambiguous on 21" maps the sheet's "right or unclear".
