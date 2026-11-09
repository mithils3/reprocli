# OpenReview replies, ICLR 2027 submission 22528 (RECLAIM)

Draft of 2026-11-06 for Mithil to read, restructured on 2026-11-08 to the format and length targets of the iclr-review skill (~/.claude/skills/iclr-review, style.md Section 10): a general reply near 1,900 characters, and three posts per reviewer near 8,000 characters in all, the first near 4,000, with bold numbered point labels. The longer draft it replaces is rebuttal/drafts/replies_long_2026-11-08.md. Nothing here has been posted. Square brackets mark numbers from runs or labels that are not frozen yet, and each bracketed sentence is written so that either outcome fits. Each part stays under 5,000 characters, and the count of each part (with the slots still unfilled) is given in its heading line. Each fact sits in one reply and the others point to it, so a Sources table can list a number that its reply now gives by pointer. Each [AUTHOR: ...] note marks a sentence that waits on Mithil's decision, comes out before posting and is left out of the counts. Post each part under the title "Response to Reviewer X (k/N)", with N = 2 for T29u, whose answers fit in two parts, and N = 3 for rqBN and YGTR. The Sources tables and the Risks section are not posted.

Order of posting from PLAN.md Section 4: T29u and rqBN on 11-11, then YGTR and the general reply on 11-14.

## General

### General reply (one part, 1,812 characters)

We thank the three reviewers for their careful reading. They found the task important and the evaluation design unusually careful (T29u), the design sound and reusable (YGTR), and the methodological disclosure excellent (rqBN). The revision makes the following changes, and each reviewer reply gives the numbers.
- **Frontier agents and production harnesses** (Section 5.1 and a new appendix section): gpt-6.1-sol in our loop and in Codex CLI, [gpt-6-astra] in Codex CLI, and Muse Wonder in our loop and in mini-SWE-agent, on papers from every tier frozen before any run.
- **Uncertainty** (Section 5.2): a 95% Wilson interval on every rate, and two more runs of DeepSeek-V4-Flash on 12 papers to measure run-to-run variation.
- **Auditor validation** (Appendix D): the confusion matrix of auditor against human verdict over the 372 runs with both grades, with per-tier precision and recall, the 7/8 boundary and agreement on integrity flags.
- **Log integrity** (Appendix A): a corrected description of the two logs the agent can write, and a comparison of all 45,861 logged entries with the host transcript, which found one overwritten log, on a run the auditor had graded unverifiable.
- **Targets and tolerances** (Appendices E and F): every frozen target checked against its paper by a model from a different lab than our auditor, and every graded run rescored at 1%, 2%, 5% and 10% relative tolerance.
- **Failures outside the agent** (Sections 5.2 and 5.3): the trace of all 28 cells with no graded run, the bound on build failures from our aarch64 hardware with an x86 replay, and a re-execution of missed runs with new seeds.
- **Checkpoint downloads** (Section 5.2): a scan of every transcript, after which the 2 runs that evaluated a downloaded checkpoint of the claimed model count as not reproduced.

### Sources (General)

| Number | File |
| :- | :- |
| 14/34 = 41% [26%, 58%] | rebuttal/results/e6/summary.json (settings.S0_index.dsv4/run) |
| 45,861 entries, 372 runs, 1 overwrite, graded 1 | rebuttal/results/e5/summary.json; e5/README.md; viewer index (minimax-reimplement-2510.25146 score 1, unverifiable) |
| best-agent count at 1%, 2%, 5% and 10% (Run 9/12/14/14, Retrain 8/9/9/12, Reimplement 4/5/5/5), so at most 14 - 9 = 5, 12 - 9 = 3 and 5 - 4 = 1 | rebuttal/results/e6/README.md table |
| T29u "real and important" and "unusually careful", YGTR "sound ... reusable", rqBN "excellent" | rebuttal/reviews-2026-11-06.md:17, :19, :45, :33 |
| gpt-6.1-sol in both harnesses, gpt-6-astra in Codex CLI only | rebuttal/PLAN.md:115; rebuttal/results/databook/frontier_cells.csv (no thin gpt-6-astra arm) |
| 28 empty cells, 6 outside agent, 16 job limit or cancel | rebuttal/results/e8/summary.json (empty_cells, outside_agent_cells); e8/empty_cells_traced.csv |
| 2 checkpoint downloads | rebuttal/results/e9/README.md; e9/class_review.csv |
| scan finished on 368 of 372 (127 + 118 + 123 of 129 + 118 + 125) | rebuttal/results/e9/summary.json (tiers.*.runs_scanned, scan_timeouts) |
| 28 = 6 + 16 + 2 context + 4 finished without a pinned-auditor grade; 3 of the 4 regraded | rebuttal/results/e8/summary.json; e8/empty_cells_traced.csv (A 2, B 16, D 4); e8/d_cells.md; e8/regrade_dcells.json |
| 73 auditor reproductions are the 73 of 400 cells | rebuttal/results/e8/README.md (reproduction check passes: 73 of 400 cells); e4/summary.json |
| best Run agent DeepSeek-V4-Flash; 14 at 10% | rebuttal/results/e6/summary.json (settings.S0_index.dsv4/run); e6/README.md table |
| 4 prompt-bug cells and 16 stopped cells rerun | rebuttal/results/e8/README.md (B cells, rerun candidates); Risks item 2 |
| 372 runs, precision 88%, recall 77%, 73 against 83 reproductions | rebuttal/results/e4/summary.json |
| frontier, repeat runs, target corrections, reruns | pending (E1, E2, E3, E7 settlement, E8 reruns); repeat runs queued, job 3540624 running and 3540625 to 3540633 pending (sacct, followups_check_4.md item 11) |

## T29u

### Reply to T29u, part 1 of 2 (3,443 characters)

Thank you for the careful review. The revision makes these changes for your points:
- Section 5.2: a 95% Wilson interval on every rate, and two more runs of DeepSeek-V4-Flash on 12 papers.
- Appendix D: the five-by-five confusion matrix of auditor against human verdict, with the 7/8 boundary and high-severity flags.
- Appendix F: every graded run rescored at 1%, 2%, 5% and 10% tolerance.
- Appendix E: every frozen target (the value, metric, dataset and configuration fixed for each claim before any agent ran) checked against its paper by a model from a different lab than our auditor[, with k targets corrected and their runs rescored].
- Section 5.3: how much build failures on the aarch64 hardware move the best-agent rates.

**W1: One run per agent-paper cell.**

We tested whether one run per cell is enough by running DeepSeek-V4-Flash, the best agent at Run, twice more on 12 papers. The papers were drawn with a fixed seed, four per tier, two of which some agent had reproduced and two of which none had. [Its verdict was the same in all three runs on k of 12 papers (95% interval [lo, hi]), so run-to-run variation moves the best Run rate by at most j papers, and the ordering Run, Retrain, Reimplement held in every run / held in j of 3 runs.] The revision calls one agent better than another only when their 95% intervals do not overlap even after each interval is made wider by the j papers of run-to-run change measured here, and it says that this change was measured for one agent only.

Every rate in the revision carries a 95% Wilson interval. The best agent per tier reproduced 14/34 = 41% [26%, 58%] of Run papers, 9/33 = 27% [15%, 44%] of Retrain papers and 5/33 = 15% [7%, 31%] of Reimplement papers. Over all four agents, 73/400 = 18% [15%, 22%] of agent-paper cells are reproduced.

Section 5.2 had called DeepSeek-V4-Flash the strongest agent, and it now gives each agent's mean audit score on the 0 to 10 rubric instead. The scores run from 5.13 for DeepSeek-V4-Flash and 5.00 for Muse Spark 1.2 down to 3.03 for MiniMax-M2.7.

On environment sensitivity, removing the 24 runs that ended in a build or dependency failure moves no best-agent rate by more than one percentage point (Section 5.3, and our reply to Reviewer YGTR, W2).

[AUTHOR: the 73 may become 72 (73 + 1 newly graded reproduction on 2503.23035 - 2 checkpoint runs = 72, Wilson 15% to 22%), and the best Run rate 14/34 here and at every other use may become 13/34 if the E7 target corrections are final; both wait on your Risk 5 decision and the E7 verdicts (followups_check_1.md, item 4).]

[AUTHOR: if the two new Muse Spark grades (8 and 6, rebuttal/results/e8/regrade_muse.json) count, its mean becomes 5.00 + 14/100 = 5.14 and leads DeepSeek-V4-Flash by 0.01.]

**W2: A closer audit of the auditor's disagreements.**

The disagreements lean toward a strict auditor. Of the 28 runs where only one grader called the result reproduced, the human did in 19 and the auditor in 9.

Over the 372 runs with both grades the auditor marks 73 reproduced and the human 83. These 73 are the reproductions that Section 5.2 reports as 73 of the 400 cells, so the 73 reproductions in the paper are a slight undercount relative to the human grade.

Two checks that do not depend on the auditor also bear on high-severity problems. A comparison of the agent's logs with the host transcript, which the harness writes outside the agent's sandbox, found one edited log in 372 runs, on a run the auditor had already graded unverifiable (our reply to Reviewer rqBN, W2). A scan of every transcript for model downloads found two reproduced runs that evaluated a downloaded checkpoint of the claimed model. They were MiniMax-M2.7 at Reimplement and Muse Spark 1.2 at Retrain, where Muse Spark had tied DeepSeek-V4-Flash for best; the revision counts both as not reproduced, so DeepSeek-V4-Flash alone is best at Retrain with 9 of 33 (our reply to Reviewer YGTR, Q2).

### Reply to T29u, part 2 of 2 (3,477 characters)

**Q1: Confusion matrix, the 7/8 boundary and high-severity flags.**

Against the human grade the auditor's reproduced verdict has precision 64/73 = 88% and recall 64/83 = 77%, and the full confusion matrix is below and in Appendix D. The matrix covers the 372 runs that have both grades. Of the 400 agent-paper cells, 396 started a run and 4 never did, and 24 of the 396 have a human label but no auditor grade, which leaves 372 (these 24 are separate from the 24 build failures above).

Of the 73 runs the auditor called reproduced, the human agreed on 64, a precision of 64/73 = 88% (95% Wilson interval 78% to 93%). Recall is 64/83 = 77% (67% to 85%), F1 is 0.82, and the two give the same one of the five verdicts in the table to 306 of 372 runs.

| Human ↓ / Auditor → | Reproduced (8 to 10) | Partial (6, 7) | Not reproduced (2 to 5) | Unverifiable (score 1: no evidence to check) | Disqualified (score 0: high-severity integrity flag) | Total |
| :- | -: | -: | -: | -: | -: | -: |
| Reproduced | **64** | 15 | 2 | 0 | 2 | 83 |
| Partial | 7 | **64** | 15 | 0 | 2 | 88 |
| Not reproduced | 2 | 6 | **130** | 3 | 5 | 146 |
| Unverifiable | 0 | 0 | 1 | **6** | 2 | 9 |
| Disqualified | 0 | 1 | 2 | 1 | **42** | 46 |
| Total | 73 | 86 | 150 | 10 | 53 | 372 |

On the 100 runs that either the auditor or the human placed at 7 or 8, they agree on 75 about which side of the reproduced line the run falls.

The rubric gives a score of 0 to any run with a high-severity integrity flag, and of the 57 runs that either of them placed at 0 they agree on 42.

**Q2: Sensitivity to the match target and the default 5% tolerance.**

The ordering of the tiers holds at every tolerance we tried, from 1% to 10%. The best agent's count of reproduced papers moves by at most 5 of the 34 Run papers (14 at 5% against 9 at 1%), 3 at Retrain and 1 at Reimplement.

Only the 62 claims that are point estimates (a single reported value) use a tolerance, and 58 of them use the default 5% relative tolerance while 4 state their own margin. The other 38 are tested by direction (21, for example "beats the strongest baseline"), by a threshold (14, a floor or ceiling) or in another way (3: a range, a magnitude and one whose test type was not recorded).

At relative tolerances of 1%, 2%, 5% and 10%, the best agent reproduces 9, 12, 14 and 14 of the 34 Run papers, 8, 9, 9 and 12 of the 33 Retrain papers and 4, 5, 5 and 5 of the 33 Reimplement papers. All agents together reproduce 56, 65, 73 and 82 of the 400 cells, with 70 or 72 at an absolute tolerance of 1 or 2 points on percentage metrics (Appendix F).

Tightening to 1% moves 17 of the 73 reproduced runs to partial, and loosening to 10% moves up to reproduced the 9 partial runs whose only failed criterion was the number. For example, on 2511.19808 DeepSeek-V4-Flash measured 90.6% test accuracy on CIFAR10-IDN against a frozen target of 97.3%, a gap of 6.7 / 97.3 = 6.9%, so that run is partial at 5% and reproduced at 10%.

On the match target itself, a model from a different lab than our auditor read each paper and checked four parts of its frozen target (value, metric, dataset and split, method or variant), and the paper supports all four for 55 of the 100 claims. The full result, with the corrections that follow, is: all four parts are supported for 55 of the 100 claims, and the value for 92, the metric for 95, the dataset and split for 76 and the method or variant for 69 (Appendix E).

Thank you again for the review.

### Sources (T29u)

| Number | File |
| :- | :- |
| 14/34, 9/33, 5/33, 73/400 and their Wilson intervals | rebuttal/results/e6/summary.json (settings.S0_index); interval for 73/400 computed with the same Wilson formula |
| 12 papers, four per tier, two reproduced and two not | rebuttal/subset.json; rebuttal/results/subset/README.md |
| 24 build-and-dependency runs (13 Run, 6 Retrain, 5 Reimplement), 14 aarch64 (16 labelled less 2 that were not chip failures), bound 14/34, 9/33, 5/32 with Wilson intervals (Muse Spark 1.2 Retrain is 9/33 reproduced, 8/33 after the CogVLA checkpoint correction; it is 9/32 only when its one build failure is also removed from the denominator, e8/bound.csv muse,retrain; DeepSeek-V4-Flash at 9/33 is the best Retrain agent); x86 replay 9 of 12 | rebuttal/results/e8/summary.json (build_dependency_runs, bound_best_per_tier_all_env_removed); e8/bound.csv (dsv4 retrain bound_all 9/33, 0.1507 to 0.4422); e8/x86/README.md; e8/x86/results.csv (not_arch rows) |
| 5.13, 5.00 and 3.03 mean audit score | paper_latex/iclr2027_conference.tex:463-466; Muse Spark 5.00 at paper_latex/appendix/b_models.tex:178 |
| 1 edited log in 372 runs, graded unverifiable | rebuttal/results/e5/README.md |
| 2 reproduced runs with a downloaded checkpoint | rebuttal/results/e9/README.md; e9/class_review.csv |
| 62 point estimates, 58 default, 4 stated margins, 38 without a number test (21 direction, 14 threshold, 1 range, 1 magnitude, 1 no kind) | rebuttal/results/e6/summary.json (claims.lockfile_kinds, point_estimate_default_5pct, point_estimate_stated_margin) |
| tolerance table, 56/65/73/82 of 400, 70 and 72 at 1 and 2 points | rebuttal/results/e6/README.md; e6/summary.json (cells, summed per setting) |
| 17 falls at 1%, 9 rises at 10%; at most 5, 3 and 1 papers of movement (from the tolerance table) | rebuttal/results/e6/summary.json (falls_by_setting, moves_by_setting, number_only_partials) |
| 2511.19808 example, 90.6 vs 97.3, 6.9% | rebuttal/results/e6/README.md (worked run) |
| 2511.19808 metric, test accuracy (%) on CIFAR10-IDN | rebuttal/results/e7/comparison.csv (row 2511.19808) |
| direction example "beats the strongest baseline", threshold "a floor or ceiling" | rebuttal/results/e6/README.md (Why 51 and 73) |
| 396 started, 24 with a human label but no auditor grade (28 empty cells less the 4 that never started) | paper_latex/iclr2027_conference.tex:412; rebuttal/results/e8/summary.json; e8/empty_cells_traced.csv |
| 92, 95, 76, 69, 55 of 100; 45 failures; 18 method-only | rebuttal/results/e7/summary.json (step3); e7/README.md |
| 2506.18890, 27.443 PSNR, 24 vs 12 views | rebuttal/results/e7/v3_failures.csv; e7/README.md |
| 372 runs, five-way table, 64/73, 64/83, F1 0.82, 306 of 372, 100 at 7 or 8 with 75 agreeing, 57 at 0 with 42 agreeing, 19 against 9 | rebuttal/results/e4/summary.json (from e4/matrix_0_10.csv, auditor columns checked against the 372 graded runs) |
| repeat runs, target corrections | pending (E3, E7 settlement) |

## rqBN

### Reply to rqBN, part 1 of 3 (4,694 characters)

Thank you for checking how the logs and the auditor are validated. The revision makes these changes for your points:
- Appendix A: the description of the two harness logs now matches the code, and a comparison of all 45,861 logged entries with the host transcript found one overwritten log, on a run the auditor had graded unverifiable.
- Appendix D: the confusion matrix of auditor against human verdict, with precision, recall, the 7/8 boundary and flag agreement, and a statement that the study gives one human label per run.
- Appendix E: what the final construction stage checked, and a check of every frozen target (the target tuple and minimal configuration fixed before any agent ran) against its paper.
- Section 5.3 and Limitations: a re-execution of missed runs with new seeds, and the bound on build failures.

**W1: Validation of the auditor.**

Yes, the auditor was validated against the human grade on the 372 runs that have both grades, and on the reproduced verdict it has precision 64/73 = 88% and recall 64/83 = 77% alongside the F1 of 0.82, and Appendix D now gives the full five-by-five confusion matrix of auditor against human verdict, which our reply to Reviewer T29u (Q1) reproduces.

On the full 0 to 10 scale the auditor and the human give the same score to 253 of 372 runs and scores within one point to 324 of the 372 runs, and the mean absolute difference is 0.59 points. By tier, precision, recall and F1 on the reproduced verdict are as follows:

| Tier | Precision | Recall | F1 |
| :- | -: | -: | -: |
| Run | **28/31 = 90%** | **28/35 = 80%** | **0.85** |
| Retrain | 25/29 = 86% | 25/32 = 78% | 0.82 |
| Reimplement | 11/13 = 85% | 11/16 = 69% | 0.76 |

Recall is lowest at Reimplement, but it rests on 16 human reproductions and its 95% interval (44% to 86%) overlaps those of the other tiers, so the errors do not concentrate in one tier. The rubric gives a score of 0 to any run with a high-severity integrity flag, and the two agree on 42 of the 57 runs that either placed at 0, which checks the integrity-flag outcome as a whole and not each flag type.

In the original study, three graders divided the 396 runs that started, so each run received one human label, given blind to the auditor's score under the same rubric. That design does not measure agreement between humans, and Appendix D now states this beside the F1.

**W2: Agent-writable logs without an integrity check.**

Yes, the agent's shell could have rewritten both logs, because the harness process writes commands.log and trajectory.jsonl and the sandbox mounts the evidence directory read-write. Appendix A said we instruct the auditor to read these files as unverified claims, but the auditor prompt has no such instruction for these two files. The revision changes the text:
> Before: "We therefore instruct the auditor to read the bundle as unverified claims and to trace every number to the command that produced it."
> After: "The auditor traces every number to the command that produced it. Because the agent could edit these two files, we compared every logged entry with the transcript the harness writes on the host, outside the sandbox."

For all 372 graded runs we matched each of the 45,861 entries that agent commands produced in the two files against that host transcript, requiring the same command and return code and, for GPU jobs, the same cost and remaining GPU-hour budget. Of these, 45,673 match exactly, and the other 188 fall into four harmless groups: 100 are calls the harness refused, which have no cost line; 60 differ in the remaining budget by at most 0.00015 GPU-hours; 25 are first attempts of a call the agent then retried; and 3 differ by at most 0.0003 GPU-hours because the budget was logged before the GPU release charge, with the same cost (Appendix A).

A search of every agent command for writes to the two files found one: MiniMax-M2.7 on 2510.25146 replaced commands.log with its own notes through a write_file call. The auditor scored that run 1 of 10, the rubric's unverifiable grade, so the edit did not raise its score. No run wrote to trajectory.jsonl, which holds the 3 unmatched entries, so those 3 are not agent edits.

The comparison also found 119 commands in 65 runs that the harness ran but never wrote to commands.log, because two code paths return before writing the log. The host transcript holds all 119, and Appendix A reports the gap.

The host transcript is not hash-chained, so it is not tamper-evident by construction; its protection is that it lies outside every directory the sandbox mounts. This check catches any edit made through the agent's own commands, which the transcript records, and Appendix A states that limit.

### Reply to rqBN, part 2 of 3 (1,985 characters)

**Q1: A stratified human-expert reproduction baseline.**

We did not run a human-expert baseline in any tier, and the Limitations section states this. A human reproduction under the same environment and budgets would need expert time on each paper plus up to 2,552 H100-hours, the grant for one agent over the 100 papers (10,208 H100-hours over four agents divided by 4), which does not fit in the discussion period.

What we can measure is how often the environment alone produces a miss. For papers where an agent followed the released pipeline and still landed outside tolerance, we extracted the final command sequence from its transcript and re-ran it on the same GH200 nodes with two new seeds and no model in the loop.

Only 3 papers had a single clean command chain, 1 at Run and 2 at Retrain, all with grants of 8 GPU-hours or less. The other candidates spanned several GPU sessions or depended on code the agent had edited by hand, and no Reimplement paper can enter this check, because that tier releases no code to re-run.
- On 2505.17836 (Retrain), the metric is GoRank mean relative error at 80k steps with a target of about 0.05. The original run measured 0.0395 and the new seeds 0.0400 and 0.0393, a spread of 0.0400 - 0.0393 = 0.0007, so the same commands miss by the same amount without the agent. This is the part of a human baseline we could measure: it shows which misses an expert following the same pipeline would also have.
- On 2510.07501 (Retrain), the metric is a bias with a target of -0.20, and the original run measured -0.2241. The new seeds gave -0.1308 and +0.0566, so the three values span 0.0566 - (-0.2241) = 0.28, which puts the original near miss inside seed variation.
- On 2506.10351 (Run), the target is 93.12 and the original run measured 94.19, [and the new seeds gave x and y, so the miss repeats without the agent / falls inside seed variation].

The bound on build failures from our aarch64 hardware is in our reply to Reviewer YGTR (W2).

### Reply to rqBN, part 3 of 3 (2,094 characters)

**Q2: How claims, configurations, targets and tolerances were validated, and annotator agreement.**

One author reviewed every extracted field before the dataset was frozen and no second person did, so there is no annotator agreement to report. Appendix E now states this. The claim, minimal configuration and target tuple of each paper (together, below, the frozen target) were extracted during dataset construction and frozen before any agent ran, and the last of the three construction stages (Stage III, Appendix E) checked which artifacts each paper's authors released and settled each compute estimate.

We have now checked every frozen target against its paper. A model from a different lab than our auditor (OpenAI's gpt-6.1-sol) read each of the 100 papers and answered four yes-or-no questions about the frozen target, quoting the passage behind each answer.

The papers support the value for 92 of the 100 claims, the metric for 95, the dataset and split for 76, the method or variant for 69, and all four for 55 (Appendix E). The most common failure is the method or variant question alone (18 papers), as on 2506.18890, whose frozen value of 27.443 PSNR appears in the paper for 24 input views while the frozen configuration says 12.

The dataset and method questions check the minimal configuration, the value and metric questions check the target, and the choice of claim rests on construction alone, which Appendix E now states. The checking model saw the frozen target when it answered, so we describe this as a check of each target against its paper.

[An author read each of the 45 papers with a failed question against the paper itself. The paper does not support the frozen target in k of the 45, and we corrected those targets and rescored their runs, which changes v verdicts and moves the best-agent rates by at most w papers per tier.]

On tolerances, 58 of the 62 point-estimate claims use the default 5% and 4 state their own margin, and the ordering of the tiers holds from 1% to 10% (our reply to Reviewer T29u, Q2, and Appendix F).

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
| 24 build-and-dependency runs, best Run 14/34 unchanged | rebuttal/results/e8/summary.json; e8/bound.csv |
| 92, 95, 76, 69, 55 of 100 (target table); 45 failures | rebuttal/results/e7/summary.json (step3); e7/README.md |
| 62 point estimates, 58 default, 4 margins, 38 others (21 direction, 14 threshold, 3 other); 9/12/14 of 34 | rebuttal/results/e6/summary.json; e6/README.md |
| Appendix A wording, before and after | paper_latex/appendix/a_harness.tex lines 133-134 (before); the after text is proposed here |
| 372 runs, 64/73, 64/83, 253 and 324 of 372, 0.59 points, 42 of 57 at 0; per tier 28/31, 28/35, 25/29, 25/32, 11/13, 11/16, recall interval 44% to 86% | rebuttal/results/e4/summary.json (per_tier_reproduced from e4/per_tier.csv) |
| re-execution: 2505.17836 GoRank mean relative error at 80k steps, target about 0.05, 0.0395, 0.0400, 0.0393, spread 0.0007; 2510.07501 bias, target -0.20, -0.2241, -0.1308, +0.0566, span 0.0566 - (-0.2241) = 0.28; 2506.10351 queued | rebuttal/results/e10/results.md (table and Metrics line) |
| no Reimplement paper in the re-execution (selection from Run and Retrain only) | rebuttal/results/e10/README.md (Selection) |
| no human reproduction, stated in Limitations | paper_latex/iclr2027_conference.tex:583-589 |
| 2,552 = 10,208 / 4 H100-hours | paper Section 5.2 (paper_latex/iclr2027_conference.tex line 494, "1,888 of the 10,208 H100-hours we granted") |
| 2506.10351 re-execution, target corrections | pending (E10, E7 settlement) |

## YGTR

### Reply to YGTR, part 1 of 3 (4,179 characters)

Thank you for the review. We ran frontier models in production harnesses, as you asked, and measured the confounds you named. The revision makes these changes:
- Section 5.1 and a new appendix section: gpt-6.1-sol in Codex CLI and in our loop, [gpt-6-astra] in Codex CLI, and Muse Wonder in mini-SWE-agent and in our loop, on papers frozen before any run.
- Section 5.3: the bound on build failures with an x86 replay, and a re-execution of missed runs with new seeds.
- Section 5.2: a 95% Wilson interval on every rate, and repeated runs of one agent.
- Section 5.2: the trace of all 28 cells with no graded run, the missing grades added, and the two runs that evaluated a downloaded checkpoint counted as not reproduced.

**W1 and Q1: Frontier models and production coding harnesses.**

We ran two current OpenAI models, [gpt-6-astra and gpt-6.1-sol], and Meta's Muse Wonder on papers drawn with a fixed seed from every tier and frozen before any run ([n] papers for the OpenAI models, [m] for Muse Wonder). Both gpt-6.1-sol and Muse Wonder ran in our thin ReAct-style loop and in a production harness (Codex CLI and mini-SWE-agent respectively), and gpt-6-astra ran in Codex CLI only.

Codex CLI and mini-SWE-agent keep their own tools, system prompts and context handling, and every run gets the same sandbox, task text, GPU grant, GPU metering and auditor as the main runs, so within one model only the harness changes. A Codex run ends when Codex ends its own turn, the same stopping rule as our loop, and the appendix table gives each run's exit reason.

[Result sentence: gpt-6-astra in Codex CLI reproduced a of 8 papers, gpt-6.1-sol b of n in our loop and c of n in Codex CLI, and Muse Wonder d of m in our loop and g of h in mini-SWE-agent, with 95% intervals in the new appendix table.] [Harness sentence: the paired difference between the two harnesses is k papers for gpt-6.1-sol (exact McNemar p = x), which is within / larger than the run-to-run change we measured (W3).] [Budget sentence: the frontier runs used a median of u% of their GPU grant.]

[Failure-mode sentence: the frontier agents' failures fall into the paper's three most common failure modes at shares inside the 95% intervals of the open agents, or Codex CLI removes mode X in k runs.] The paper's most common failure, writing the method without checking its output against the paper's numbers, appears in [k] of the [f] failing frontier runs. Muse Spark 1.2 from our main runs gives a same-family comparison, [Muse Wonder d of m against Muse Spark e of m].

We keep the thin loop for the main results so that every model runs under one harness, and the new appendix section measures how Codex CLI and mini-SWE-agent change the results. Claude Code is the one harness you name that we did not run, because our auditor is Claude Sonnet 5 and a Claude agent would be graded by its own model family.

[AUTHOR: n is not one number. The thin gpt-6.1-sol arm is planned at 12 papers (databook/frontier_cells.csv), Codex gpt-6.1-sol at 24 and gpt-6-astra at 8; PLAN.md:115 sets 24 for thin only if papers 13 to 24 launch after the GPU check. Fill n per arm once the sweeps end.]

[AUTHOR: PLAN.md:200 gives Anthropic billing as the reason for leaving Claude Code out; the same-family reason above is new, so confirm it or replace it with yours.]

**W2: Failures due to hardware differences.**

Build failures on our hardware move no best-agent rate by more than one percentage point. Of the 372 graded runs, 24 failed at build or dependency install (13 at Run, 6 at Retrain and 5 at Reimplement): 14 on a package with no build for the aarch64 CPUs of our GH200 nodes, 7 on other environment problems and 3 on agent error.

For 12 of the 14 whose install command we could replay, we reran the install on x86 nodes, and 9 of the 12 build and import (95% Wilson interval 47% to 91%). The other 3 also fail on x86, on a Python or package version conflict, so for those 3 the hardware is not shown to be the cause.

Removing all 24 from the denominators leaves DeepSeek-V4-Flash, the best agent at Run and Retrain, at 14/34 = 41% [26%, 58%] and 9/33 = 27% [15%, 44%], since it had none of these failures there, and moves Muse Spark 1.2, the best at Reimplement, from 5/33 = 15% [7%, 31%] to 5/32 = 16% [7%, 32%] (Section 5.3). The agent most affected is MiniMax-M2.7 at Run, which goes from 3/34 to 3/26.

Our reply to Reviewer rqBN (Q1) re-runs the last commands of missed runs on the same nodes with new seeds and no agent, and both Retrain papers miss again on both seeds. The frontier runs above use the same environment, and [their results].

### Reply to YGTR, part 2 of 3 (2,970 characters)

**W3: Agents are only run once.**

One run per agent is a real limit, and we measured its size by running DeepSeek-V4-Flash twice more on 12 papers drawn with a fixed seed, four per tier (details in our reply to Reviewer T29u, W1). [Its verdict was the same in all three runs on k of 12 papers, so most single-run failures are consistent / a share of failures are transient, and the revision widens the comparisons between agents by this rate.] Every rate now carries a 95% Wilson interval in Section 5.2.

**W1, continued: Whether the findings generalize to stronger models.**

The findings are scoped to the 100 NeurIPS 2025 papers and the agents we tested, and we do not claim more. The benchmark covers 100 papers from one venue and year in three tiers (Run, Retrain and Reimplement), each with a pinned experiment under a 96 H100-hour cap, and it excludes papers that need a paid or closed API. The main results come from four agents run once per paper, and the frontier runs above add [gpt-6-astra, gpt-6.1-sol and Muse Wonder] in production harnesses on a frozen subset. The tier ordering and the most common failure are what we test on those runs [outcome]. Section 5 and the Limitations section state the scope, and the revision adds that the claims hold for these papers and agents and that other venues, years and models remain untested.

**Q2: Fetching checkpoints over the network.**

Yes, we checked, and two reproduced runs evaluated a downloaded checkpoint of the claimed model, which the revision counts as not reproduced.

The harness keeps no network log, so we scanned the transcripts of all 372 graded runs, including the commands, fetched URLs and code the agent wrote, for hf_hub_download, snapshot_download, huggingface-cli, from_pretrained with a repository id, torch.hub, gdown, and wget or curl of weight files. The scan finished on 368 runs and timed out on 4, none of which was reproduced. The scan cannot see a download made inside an imported library, and Section 5.2 states this limit.

All 42 reproduced Retrain and Reimplement runs were scanned, and 16 of them matched a pattern. Reading those 16 by hand, 10 matched text that is not a download, such as an import line, a requirements.txt or a dataset, and 4 downloaded only a base model that the method starts from, such as the OpenVLA model that CogVLA builds on.

In the other 2, Muse Spark 1.2 on CogVLA (2508.21046, Retrain) downloaded a LIBERO-Spatial checkpoint linked from the authors' repository, and MiniMax-M2.7 on CURE (2505.12677, Reimplement) downloaded the authors' erased Stable Diffusion v1.4 weights from their Google Drive folder.

Muse Spark 1.2's reproduced Retrain papers fall from 9 of 33 to 8 of 33 (33 is the number of Retrain papers, one cell per paper), and MiniMax-M2.7's reproduced Reimplement papers fall from 2 of 33 to 1 of 33 (Section 5.2). The best-agent rates stay at 9 of 33 at Retrain (DeepSeek-V4-Flash) and 5 of 33 at Reimplement (Muse Spark 1.2).

### Reply to YGTR, part 3 of 3 (1,920 characters)

**Q3: Failures that were not the agent's fault.**

Yes. We traced all 28 cells that produced no graded run, using the cluster's job accounting and the harness logs. Six failed for reasons outside the agent: the four cells of paper 2510.20725 never started because of a bug in our prompt rendering, since fixed, and two audits of Muse Spark 1.2 never returned a verdict.

Sixteen stopped before the agent finished, when the cluster job running them reached its 48-hour limit or was cancelled. Two ended when the agent's context filled, which the protocol counts as an agent failure. Four finished runs had no grade from the pinned auditor; we graded the 3 whose files survive, none is reproduced (scores 0, 2 and 0), and the fourth lost its files and stays ungraded.

The two missing audits now have grades from the same pinned auditor, reproduced (score 8) on 2503.23035 and partial (score 6) on 2510.08177. [We reran the 4 cells of 2510.20725 and the 16 stopped cells with the same settings, and r of them reproduce.] Every rate in the revision includes these grades.

Across the 400 cells, 27 failed for reasons we traced outside the agent: the 6 cells above and 21 graded runs that failed on the environment (14 aarch64 builds and 7 other environment problems, W2), so 6 + 14 + 7 = 27. The 16 stopped cells are not in the 27, because a stopped job does not show whether the agent would have succeeded, so we reran them [r of the 16 reruns reproduced].

The 27 is the count we could trace and does not bound the failures outside the agent. It leaves out the 76 runs that followed the released pipeline and still missed, and the Limitations section states that for them agent error cannot be separated from seed and hardware variance.

[AUTHOR: Risk 2: the "Sixteen stopped" sentence reverses the paper's count of all 28 empty cells as model failures (memory paper-missing-cells-accounting); decide before posting.]

Thank you again for the review. We would be glad to hear whether the frontier and harness results address your concern that the findings may not generalize beyond the tested models.

### Sources (YGTR)

| Number | File |
| :- | :- |
| 24 build-and-dependency runs; 14 aarch64, 7 other environment (5 labelled plus the 2 not-chip rows), 3 agent error; x86 replay 9 of 12 | rebuttal/results/e8/summary.json (build_dependency_runs.class_counts); e8/README.md; e8/x86/README.md; e8/x86/results.csv (not_arch rows) |
| gpt-6.1-sol in both harnesses, gpt-6-astra in Codex CLI only | rebuttal/PLAN.md:115; rebuttal/results/databook/frontier_cells.csv |
| best Run 14/34 unchanged, Retrain 9/33 (DeepSeek-V4-Flash; Muse 9/33 becomes 8/33 after the checkpoint correction, over the 33 Retrain papers, and 9/32 only when its one build failure is also removed), Reimplement 5/32, MiniMax Run 3/26; table by tier with intervals | rebuttal/results/e8/bound.csv; e8/summary.json (build_dependency_runs.by_tier, bound_best_per_tier_all_env_removed.wilson95); e6/summary.json (settings.S0_index) |
| 14/34 = 41% [26%, 58%], 5/33 = 15% [7%, 31%] | rebuttal/results/e6/summary.json (settings.S0_index) |
| 27 = 6 + 14 + 7 traced outside the agent; 3 of 12 replayed installs fail on x86 | rebuttal/results/e8/summary.json (outside_agent_cells, build_dependency_runs.class_counts A 16, O 5); e8/x86/README.md (2 of the 16 not chip failures, moved to other environment) |
| 76 faithful misses not attributed | paper_latex/iclr2027_conference.tex:584-585 (Limitations) |
| 0.0007 on 2505.17836, 0.28 on 2510.07501, 2506.10351 queued | rebuttal/results/e10/results.md |
| 3 papers re-executed | rebuttal/results/e10/README.md; e10/selection.csv |
| 12 repeat papers, four per tier, two reproduced and two not | rebuttal/subset.json; rebuttal/results/subset/README.md; rebuttal/results/sweeps/jobs.csv |
| 368 of 372 scanned, 4 timeouts not reproduced | rebuttal/results/e9/summary.json (scan_timeouts); viewer index verdicts (partial, not_reproduced, disqualified x2) |
| 42 reproduced Retrain and Reimplement runs, 16 with a hit, 10 / 4 / 2 | rebuttal/results/e9/README.md (13 of 29 plus 3 of 13); e9/class_review.csv |
| 2508.21046 CogVLA and 2505.12677 CURE downloads | rebuttal/results/e9/class_review.csv; rebuttal/STATUS.md (commands.log:483) |
| Muse Retrain 9 to 8, MiniMax Reimplement 2 to 1, best 9/33 and 5/33 | rebuttal/results/e8/summary.json (per_agent_tier) minus the two E9 runs |
| 28 empty cells: 6 outside agent, 16 job limit or cancel, 2 context, 4 unknown | rebuttal/results/e8/summary.json; e8/empty_cells_traced.csv; e8/README.md |
| 4 finished runs with no pinned-auditor grade; 3 regraded at 0, 2 and 0, none reproduced; 2510.19314 no bundle, ungraded | rebuttal/results/e8/d_cells.md; e8/regrade_dcells.json |
| 16 stopped cells are among the 28 and outside the 27 | rebuttal/results/e8/empty_cells_traced.csv (class B); e8/summary.json (outside_agent_cells lists only the 6) |
| 3 of 12 x86 replays fail on a Python or package version conflict | rebuttal/results/e8/x86/README.md |
| DeepSeek-V4-Flash has no build failure at Run or Retrain (its one is Reimplement) | rebuttal/results/e8/build_failures.csv (dsv4-reimplement-2511.20906) |
| repeat papers: per tier 2 reproduced by some agent, 2 by none | rebuttal/subset.json (rule: within each tier 2 reproduced and 2 not) |
| re-execution targets about 0.05 and -0.20; 0.0395 sits inside 0.0393 to 0.0400 | rebuttal/results/e10/results.md |
| auditor is Claude Sonnet 5; Claude Code left out of the plan | paper_latex/iclr2027_conference.tex:389; rebuttal/PLAN.md:200 |
| 368 scanned, 4 timeouts | rebuttal/results/e9/summary.json (tiers.*.runs_scanned, scan_timeouts) |
| 2503.23035 reproduced (8), 2510.08177 partial (6) | rebuttal/results/e8/regrade_muse.json |
| frontier results, McNemar, budget use, failure-mode shares, blind labels, repeat flips (job 3540624 running, 3540625 to 3540633 pending), 2506.10351 re-execution, 20 reruns | pending (E1, E2, E3, E10, E8 reruns) |

## Risks: where a reviewer could push back

1. **The target check shows 45 of 100 targets failing at least one question (rqBN Q2, T29u Q2).** A reviewer can read 55/100 as evidence that the targets are unreliable. What closes it is Mithil's read of the 45 (rebuttal/results/e7/v3_failures.csv), giving the count the paper actually contradicts, and the rescore of those runs at the corrected targets with the change in best-agent rates. If k is large, the replies should lead with the rescored rates.
2. **The reply admits that 16 empty cells were stopped by the cluster job, which contradicts the paper's sentence that all 28 are model failures (YGTR Q3).** This also reverses the 2026-09-10 and 09-19 instructions in memory paper-missing-cells-accounting, so Mithil should decide it before posting. What closes it is the rerun grades of the 20 cells (jobs 3540630 to 3540633, 3540786, 3540787, plus Muse on 2510.20725) and a Section 5.2 sentence that matches the reply.
3. **The confusion matrix comes from an aggregate table, and the paper says 396 hand-graded runs (T29u Q1, rqBN W1).** The matrix Mithil supplied on 11-08 covers the 372 runs with an auditor grade, and its auditor columns match the graded runs exactly, but no per-run label file is on disk. The per-tier reproduced table (e4/per_tier.csv) sums to the matrix totals and its auditor counts match the graded runs per tier (31, 29, 13). Appendix D should say the matrix is over the 372 runs with both grades. The original design has one human label per run, so inter-human agreement cannot be reported; Mithil decided on 11-08 against a second blind grader, so the replies state one label per run and report no inter-human figure.
4. **Codex runs stop early, which a reviewer may call a configuration artifact (YGTR W1).** The first ten frontier runs used a median under 2% of their GPU grant and most ended with "could not run" (rebuttal/results/frontier/run_usage_summary.md), and two cite GPU requests left in the queue. What closes it is the per-run grant use and exit reason in the appendix table, the queue wait per GPU request from run_gpu logs, and, if Mithil approves, a small variant with a fixed number of "continue" prompts.
5. **The two checkpoint downloads came from the authors' own releases, which questions the tier labels of 2508.21046 and 2505.12677 (YGTR Q2).** A Retrain paper with released weights for the claimed model belongs at Run. What closes it is a check of both papers' availability records against the linked checkpoints, and moving the papers if the release covers the claimed configuration.
6. **The hash-chained host log was removed from the rqBN reply (rqBN W1).** No such log exists in the code, and the frontier runs were graded without it, so the reply now promises only the Appendix A rewording and the log comparison that already exist.
7. **The re-execution check covers only 3 papers (rqBN Q1, YGTR W2).** A reviewer can call it too small to bound the environment. What closes it is the two-seed outcome on all 3 (jobs under /work/nvme/bfvr/msalunkhe/rebuttal/e10/state.json) and, if time allows, adding near-miss papers from the 8 to 32 GPU-hour band.
8. **The log check leaves two loose ends (rqBN W1).** The evidence directory's modification time is more than 60 seconds after run end in 63 of 372 runs with no established cause, and the paper says 396 runs started while the check matched 372 graded runs. The 11-08 trace (e5/traces_2026-11-08.md, Trace B) finds the auditor's own writes in 9 directories, only a directory-time change with no changed file in 49 (38 of them dated 2026-10-29, the cleanup day), and 6 files in 5 directories with no writer found. What remains is those 5 directories and the reconciliation of the 24 started but ungraded runs, which the empty-cell trace already covers.
