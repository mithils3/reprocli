# OpenReview replies, ICLR 2027 submission 22528 (RECLAIM)

Draft of 2026-11-06 for Mithil to read. Nothing here has been posted. Square brackets mark numbers from runs or labels that are not frozen yet, and each bracketed sentence is written so that either outcome fits. The ICLR 2027 author guide does not state a per-comment character limit, so every part below is kept under 5,000 characters, and the count of each part (with the slots still unfilled) is given in its heading line. Each reply now opens with one sentence of thanks and a list of the changes with their locations, following the iclr-review skill (~/.claude/skills/iclr-review), and the T29u reply is now two parts. The edits of 2026-11-08 apply the fact-checks in followups_check_1.md to followups_check_4.md, and each [AUTHOR: ...] note marks a sentence that waits on Mithil's decision, comes out before posting and is left out of the counts.

Order of posting from PLAN.md Section 4: T29u and rqBN on 11-11, then YGTR and the general reply on 11-14.

## General

### General reply (one part, 4,148 characters)

We thank the three reviewers for their time. T29u calls the evaluation design unusually careful, YGTR calls it sound, and rqBN names the validity of the auditor and of the evidence it reads as a material concern. Their requests fall into four groups: stronger agents in production harnesses, repeated runs, a fuller validation of the auditor and of the logs it reads, and a clearer account of failures that the agent did not cause. This is what we added for each, and the replies to each reviewer give the details.

**Revisions by section.**
- Section 5.1 and a new appendix section: the frontier models and production harnesses, with a table by model, harness and tier.
- Section 5.2: Wilson intervals on every rate, the repeat-run result, and rates updated for the regraded and rerun cells.
- Section 4 and Appendix D: the auditor-versus-human confusion matrix and boundary table.
- Appendix A: the log comparison and its limit, and a corrected sentence on what the auditor prompt says.
- Appendix E and F: what the final construction stage checked, the target check, and the tolerance table.
- Section 5.3: the bound on build failures from the aarch64 hardware, with an x86 replay.
- Section 5.3 and Limitations: the re-execution of missed runs with new seeds.
- Section 5.2: the scan for downloaded checkpoints, with two runs counted as not reproduced.

**Frontier agents and production harnesses.** We ran [gpt-6-astra and gpt-6.1-sol] from OpenAI on [n] papers and Muse Wonder from Meta on [m] papers, drawn with a fixed seed from every tier and frozen before any run. Both gpt-6.1-sol and Muse Wonder ran in our ReAct-style harness and in a production harness (Codex CLI for gpt-6.1-sol, mini-SWE-agent for Muse Wonder), and gpt-6-astra ran in Codex CLI only, all with the same sandbox, task text, GPU grant and auditor as the main runs. [Result sentence: gpt-6-astra in Codex CLI reproduced a of 8 papers, gpt-6.1-sol b of n in our harness and c of n in Codex CLI, and Muse Wonder d of m.] [Failure-mode sentence: the frontier agents' failures fall into the paper's three most common failure modes at shares inside the 95% intervals of the open agents, or Codex CLI removes mode X in k runs.]

**Repeated runs.** Every rate now carries a 95% Wilson interval, for example 14/34 = 41% [26%, 58%] for the best agent at the Run tier. We also queued two more runs of DeepSeek-V4-Flash on each of 12 of those papers, and [its verdict was the same in all three runs on k of 12].

**Auditor and logs.** Appendix D now gives the confusion matrix of auditor verdict against human verdict over the 372 runs with both grades, with precision 88%, recall 77% and F1 0.82 on the reproduced verdict, and the auditor is the stricter of the two, with 73 reproductions against the humans' 83. We compared the 45,861 entries that agent commands produced in commands.log and trajectory.jsonl across all 372 graded runs with the transcript the harness writes on the host, outside the agent's sandbox. One run of the 372 overwrote its commands.log, and the auditor had graded that run 1 of 10 as unverifiable, so the edit gained it nothing.

**Tolerance and targets.** Moving the default tolerance anywhere from 1% to 10% changes the best agent's count by at most 5 papers at Run (14 at 5% against 9 at 1%), 3 at Retrain and 1 at Reimplement, and the ordering of the tiers holds at every setting we tried. A model from a different lab than our auditor checked every frozen target against its paper, and [k] targets the paper does not support were corrected and their runs rescored.

**Failures outside the agent and checkpoint downloads.** We traced all 28 cells that produced no graded run. Six failed for reasons outside the agent, and 16 more stopped when the cluster job running them reached its 48-hour limit or was cancelled. The two missing audits are now graded, and [the 20 other cells were rerun, with r reproduced]. A scan of every transcript for model downloads found 2 reproduced Retrain or Reimplement runs that evaluated a downloaded checkpoint of the claimed model. Neither was the best agent's run, and the revision counts both as not reproduced.

### Sources (General)

| Number | File |
| :- | :- |
| 14/34 = 41% [26%, 58%] | rebuttal/results/e6/summary.json (settings.S0_index.dsv4/run) |
| 45,861 entries, 372 runs, 1 overwrite, graded 1 | rebuttal/results/e5/summary.json; e5/README.md; viewer index (minimax-reimplement-2510.25146 score 1, unverifiable) |
| best-agent count at 1%, 2%, 5% and 10% (Run 9/12/14/14, Retrain 8/9/9/12, Reimplement 4/5/5/5), so at most 14 - 9 = 5, 12 - 9 = 3 and 5 - 4 = 1 | rebuttal/results/e6/README.md table |
| T29u "unusually careful", YGTR "sound", rqBN "material concerns" | rebuttal/reviews-2026-11-06.md:19, :45, :35 |
| gpt-6.1-sol in both harnesses, gpt-6-astra in Codex CLI only | rebuttal/PLAN.md:115; rebuttal/results/databook/frontier_cells.csv (no thin gpt-6-astra arm) |
| 28 empty cells, 6 outside agent, 16 job limit or cancel | rebuttal/results/e8/summary.json (empty_cells, outside_agent_cells); e8/empty_cells_traced.csv |
| 2 checkpoint downloads | rebuttal/results/e9/README.md; e9/class_review.csv |
| 372 runs, precision 88%, recall 77%, 73 against 83 reproductions | rebuttal/results/e4/summary.json |
| frontier, repeat runs, target corrections, reruns | pending (E1, E2, E3, E7 settlement, E8 reruns); repeat runs queued, job 3540624 running and 3540625 to 3540633 pending (sacct, followups_check_4.md item 11) |

## T29u

### Reply to T29u, part 1 of 2 (3,030 characters)

Thank you for the careful review. These are the changes, each detailed below:
- Section 5.2: a 95% Wilson interval on every rate, and two more runs of DeepSeek-V4-Flash on 12 papers, now queued, to measure run-to-run variation.
- Appendix D: the five-by-five confusion matrix of auditor against human verdict, with the 7/8 boundary and high-severity flags.
- Appendix F: every graded run rescored at 1%, 2%, 5% and 10% tolerance.
- Appendix E: every frozen target (the value, metric, dataset and configuration fixed for each claim before any agent ran) checked against its paper by a model from a different lab than our auditor[, with k targets corrected and their runs rescored].
- Section 5.3: how much build failures on the aarch64 hardware move the best-agent rates, with an x86 replay of the failed installs.

**One run per cell (W1).** We agree that one rollout per cell gives a point estimate, so every rate in the revision carries a 95% Wilson interval. For the best agent per tier, the papers it reproduced out of the papers in that tier are 14/34 = 41% [26%, 58%] at Run, 9/33 = 27% [15%, 44%] at Retrain and 5/33 = 15% [7%, 31%] at Reimplement. Over all four agents, 73 of the 400 agent-paper cells are reproduced, 73/400 = 18% [15%, 22%]. [AUTHOR: the 73 may become 72 (73 + 1 newly graded reproduction on 2503.23035 - 2 checkpoint runs = 72, Wilson 15% to 22%), and the best Run rate 14/34 here and at every other use may become 13/34 if the E7 target corrections are final; both wait on your Risk 5 decision and the E7 verdicts (followups_check_1.md, item 4).] To measure run-to-run variation directly, we queued two more runs of DeepSeek-V4-Flash, the best agent at Run, on 12 papers drawn with a fixed seed, four per tier, two of which some agent had reproduced and two of which none had. [Its verdict was the same in all three runs on k of 12 papers (95% interval [lo, hi]), and the ordering Run, Retrain, Reimplement held in every run / held in j of 3 runs.] The revision compares the reproduction rates of two agents only where their intervals, widened by the run-to-run change these repeat runs measure, do not overlap, and it says that the measurement covers one agent. Section 5.2 now gives each agent's mean audit score on the 0 to 10 rubric, from 5.13 for DeepSeek-V4-Flash and 5.00 for Muse Spark 1.2 down to 3.03 for MiniMax-M2.7, where it had called DeepSeek-V4-Flash the strongest agent. [AUTHOR: if the two new Muse Spark grades (8 and 6, rebuttal/results/e8/regrade_muse.json) count, its mean becomes 5.00 + 14/100 = 5.14 and leads DeepSeek-V4-Flash by 0.01.]

Of the 372 graded runs, 24 ended in a build or dependency failure, which bears on environment sensitivity. Our reading of their transcripts traces 14 of them to a package that has no build for the aarch64 CPUs of our GH200 nodes. For the 12 of these 14 with an install command we could replay, we re-ran the install on x86 nodes, and 9 of 12 build and import (95% Wilson interval 47% to 91%). Removing these 24 runs from each agent's own denominator leaves the best Run rate at 14/34, because DeepSeek-V4-Flash had none of these failures at Run, and moves the other best-agent rates by less than one percentage point (Section 5.3):

| Tier | Build or dependency failures | Best agent as graded (95% interval) | Best agent with the 24 removed (95% interval) |
| :- | :- | :- | :- |
| Run | 13 | 14/34 = 41% [26%, 58%] | 14/34 = 41% [26%, 58%] |
| Retrain | 6 | 9/33 = 27% [15%, 44%] | 9/33 = 27% [15%, 44%] |
| Reimplement | 5 | 5/33 = 15% [7%, 31%] | 5/32 = 16% [7%, 32%] |

### Reply to T29u, part 2 of 2 (4,669 characters)

**Auditor disagreements, the 7/8 boundary and high-severity flags (W2, Q1).** The confusion matrix of auditor verdict against human verdict is below and in Appendix D. It covers the 372 runs that have both grades, since the 396 runs that started include 24 with a human label but no auditor grade. Of the 73 runs the auditor called reproduced, the human agreed on 64, a precision of 64/73 = 88% (95% Wilson interval 78% to 93%). Recall is 64/83 = 77% (67% to 85%), F1 is 0.82, and the two give the same one of the five verdicts in the table to 306 of 372 runs.

| Human ↓ / Auditor → | Reproduced (8 to 10) | Partial (6, 7) | Not reproduced (2 to 5) | Unverifiable (1) | Disqualified (0) | Total |
| :- | -: | -: | -: | -: | -: | -: |
| Reproduced | 64 | 15 | 2 | 0 | 2 | 83 |
| Partial | 7 | 64 | 15 | 0 | 2 | 88 |
| Not reproduced | 2 | 6 | 130 | 3 | 5 | 146 |
| Unverifiable | 0 | 0 | 1 | 6 | 2 | 9 |
| Disqualified | 0 | 1 | 2 | 1 | 42 | 46 |
| Total | 73 | 86 | 150 | 10 | 53 | 372 |

On the 100 runs that either the auditor or the human placed at 7 or 8, they agree on 75 about which side of the reproduced line the run falls. The rubric gives a score of 0 to any run with a high-severity integrity flag, and of the 57 runs that either of them placed at 0 they agree on 42. The errors lean one way: of the 28 runs where only one of them called the result reproduced, the human did in 19 and the auditor in 9, so the auditor is the stricter grader and the paper's reproduction counts are, if anything, low.

Two checks that do not depend on the auditor also bear on high-severity problems. A comparison of the agent's logs with the host transcript, which the harness writes outside the agent's sandbox, found one edited log in 372 runs, on a run the auditor had already graded unverifiable. A scan of every transcript for model downloads found two reproduced runs that evaluated a downloaded checkpoint of the claimed model. Neither was the best agent's run, and the revision counts both as not reproduced. The reply to rqBN gives both checks in full.

**Choice of match target and the default 5% tolerance (Q2).** Each claim is scored against a frozen target, the value, metric, dataset and configuration fixed before any agent ran. The ordering of the tiers holds at every tolerance we tried, from 1% to 10%. The best agent's count of reproduced papers moves by at most 5 of the 34 Run papers (14 at 5% against 9 at 1%), 3 at Retrain and 1 at Reimplement (Appendix F and the table below). Of the 100 claims, 62 are point estimates (a single reported value), and only these use a tolerance. The other 38 are tested by direction (21, for example "beats the strongest baseline"), by a threshold (14, a floor or ceiling) or in another way (3: a range, a magnitude and one whose test type was not recorded). Of the 62 point estimates, 58 use the default 5% relative tolerance and 4 state their own margin. We rescored every graded run at four relative tolerances.

| Relative tolerance | Run, best of 34 | Retrain, best of 33 | Reimplement, best of 33 | All agents, of 400 cells |
| :- | :- | :- | :- | :- |
| 1% | 9 | 8 | 4 | 56 |
| 2% | 12 | 9 | 5 | 65 |
| 5% (default) | 14 | 9 | 5 | 73 |
| 10% | 14 | 12 | 5 | 82 |

With an absolute tolerance of 1 or 2 points on percentage metrics the total is 70 or 72 of 400. Tightening to 1% moves 17 of the 73 reproduced runs to partial, and loosening to 10% moves 9 partial runs, whose only failed criterion was the number, up to reproduced. For example, on 2511.19808 DeepSeek-V4-Flash measured 90.6% test accuracy on CIFAR10-IDN against a frozen target of 97.3%, a gap of 6.7 / 97.3 = 6.9%, so that run is partial at 5% and reproduced at 10%.

On the match target itself, a model from a different lab than our auditor (OpenAI's gpt-6.1-sol) read each of the 100 papers and answered four yes-or-no questions about the frozen target, quoting the passage behind each answer. The papers supported each part of the frozen target as follows (Appendix E):

| Part of the frozen target | Supported, of 100 |
| :- | -: |
| Value | 92 |
| Metric | 95 |
| Dataset and split | 76 |
| Method or variant | 69 |
| All four | 55 |

The most common failure is the method or variant question alone (18 papers), which flags cases like 2506.18890, whose frozen value of 27.443 PSNR appears in the paper for 24 input views while the frozen configuration says 12. [An author read all 45 papers with a failed question against the paper itself. The paper does not support the frozen target in k of them, and we corrected those targets and rescored their runs, which changes v verdicts and moves the best-agent rates by at most w papers per tier.]

### Sources (T29u)

| Number | File |
| :- | :- |
| 14/34, 9/33, 5/33, 73/400 and their Wilson intervals | rebuttal/results/e6/summary.json (settings.S0_index); interval for 73/400 computed with the same Wilson formula |
| 12 papers, four per tier, two reproduced and two not | rebuttal/subset.json; rebuttal/results/subset/README.md |
| 24 build-and-dependency runs (13 Run, 6 Retrain, 5 Reimplement), 14 aarch64 (16 labelled less 2 that were not chip failures), bound 14/34, 9/33, 5/32 with Wilson intervals (Muse Retrain 9/32 less the CogVLA checkpoint run is 8/32, so DeepSeek-V4-Flash at 9/33 is the best Retrain agent); x86 replay 9 of 12 | rebuttal/results/e8/summary.json (build_dependency_runs, bound_best_per_tier_all_env_removed); e8/bound.csv (dsv4 retrain bound_all 9/33, 0.1507 to 0.4422); e8/x86/README.md; e8/x86/results.csv (not_arch rows) |
| 5.13 and 3.03 mean audit score | paper_latex/iclr2027_conference.tex:463-466 |
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

### Reply to rqBN, part 1 of 2 (4,975 characters)

Thank you for checking how the logs and the auditor are validated. These are the changes, each detailed below:
- Appendix A: the description of the two harness logs now matches the code (wording below), and a comparison of all 45,861 logged entries with the host transcript found one overwritten log, on a run the auditor had graded unverifiable.
- Appendix D: the confusion matrix of auditor against human verdict, with precision, recall, the 7/8 boundary and flag agreement, and a statement that the study gives one human label per run.
- Appendix E: what the final construction stage checked, and a check of every frozen target (the target tuple and minimal configuration fixed before any agent ran) against its paper.
- Section 5.3 and Limitations: a re-execution of missed runs with new seeds, and the bound on build failures.

**Auditor validation (W1a).** Appendix D now gives the confusion matrix of auditor verdict against human verdict over the 372 runs that have both grades, and the reply to T29u shows it in full. On the reproduced verdict the auditor has precision 64/73 = 88% and recall 64/83 = 77% alongside the F1 of 0.82. On the full 0 to 10 scale the auditor and the human give the same score to 253 of 372 runs and scores within one point to 324, and the mean absolute difference is 0.59 points. By tier, precision, recall and F1 on the reproduced verdict are as follows:

| Tier | Precision | Recall | F1 |
| :- | -: | -: | -: |
| Run | 28/31 = 90% | 28/35 = 80% | 0.85 |
| Retrain | 25/29 = 86% | 25/32 = 78% | 0.82 |
| Reimplement | 11/13 = 85% | 11/16 = 69% | 0.76 |

Recall is lowest at Reimplement, but it rests on 16 human reproductions and its 95% interval (44% to 86%) overlaps those of the other tiers, so the errors do not concentrate in one tier. The rubric gives a score of 0 to any run with a high-severity integrity flag, and of the 57 runs that either the auditor or the human placed at 0 they agree on 42. In the original study, three graders divided the 396 runs that started, so each run received one human label, given blind to the auditor's score under the same rubric. The matrix covers the 372 of these runs that also have an auditor grade. That design does not measure agreement between humans, and Appendix D now states this beside the F1. [If a second grader labels a subset: A second author has now labeled n of these runs blind to both earlier labels, and the two humans agree on k of n.]

**Writable logs (W1b).** The harness process writes commands.log and trajectory.jsonl, and the sandbox mounts the evidence directory read-write, so the agent's shell could have rewritten them. Appendix A said we instruct the auditor to read these files as unverified claims; the auditor prompt has no such instruction for these two files.

| Appendix A | Wording |
| :- | :- |
| Before | "We therefore instruct the auditor to read the bundle as unverified claims and to trace every number to the command that produced it." |
| After | "The auditor traces every number to the command that produced it. Because the agent could edit these two files, we compared every logged entry with the transcript the harness writes on the host, outside the sandbox." |

To find out whether any agent did edit them, we used the transcript the harness writes on the host. That transcript is not hash-chained, so it is not tamper-evident by construction; its protection is that it lies outside every directory the sandbox mounts, where no agent command can write. For all 372 graded runs, we matched each entry that an agent command produced in the two files against that transcript, requiring the same command and return code and, for GPU jobs, the same cost and remaining GPU-hour budget. The 45,861 such entries compare with the host transcript as follows (Appendix A):

| Entry | Count |
| :- | -: |
| Match exactly | 45,673 |
| Call refused by the harness, so no cost line | 100 |
| Remaining budget within 0.00015 GPU-hours | 60 |
| First attempt of a retried call | 25 |
| Unmatched: remaining budget differs by up to 0.0003 GPU-hours, cost equal | 3 |
| Total | 45,861 |

We also searched every agent command for writes to the two files. One run of the 372 wrote to commands.log: MiniMax-M2.7 on 2510.25146 replaced the file with its own notes through a write_file call. The auditor scored that run 1 of 10, the rubric's unverifiable grade, so the edit did not raise its score. No run wrote to trajectory.jsonl, which holds the 3 unmatched entries in the table, so those 3 are not agent edits; we have not yet traced why their remaining budget differs. The comparison also found 119 commands in 65 runs that our harness ran but never wrote to commands.log, because two code paths in the harness return before writing the log. The host transcript holds all 119, and Appendix A now reports this gap with its count. This check catches any edit made through the agent's own commands, which the transcript records, and Appendix A now states that limit.

### Reply to rqBN, part 2 of 2 (4,219 characters)

**Human-expert reproduction baseline (Q1).** We did not run a human-expert baseline in any tier, and the Limitations section states this. A human reproduction under the same environment and budgets would need expert time on each paper plus up to 2,552 H100-hours, which does not fit in the discussion period. That is the grant for one agent over the 100 papers, 10,208 H100-hours over four agents divided by 4. What we can measure is how often the environment alone produces a miss. We took papers where an agent followed the released pipeline and still landed outside tolerance, extracted the final command sequence from its transcript, and re-ran it on the same GH200 nodes with two new seeds and no model in the loop. Only 3 papers had a single clean command chain, 1 at Run and 2 at Retrain, all with grants of 8 GPU-hours or less. The other candidates spanned several GPU sessions or depended on code the agent had edited by hand. No Reimplement paper can enter this check, because that tier releases no code to re-run. Two of the 3 have finished, and both miss again on both seeds. On 2505.17836 the metric is GoRank mean relative error at 80k steps, with a target of about 0.05. The original run measured 0.0395 and the new seeds 0.0400 and 0.0393, a spread of 0.0400 - 0.0393 = 0.0007. The same commands thus miss by the same amount without the agent, which places the cause in the environment or the paper. On 2510.07501 the metric is a bias with a target of -0.20, and the original run measured -0.2241. The new seeds gave -0.1308 and +0.0566, so the three values span 0.0566 - (-0.2241) = 0.28, which puts the original near miss inside seed variation. The two seeds for 2506.10351 are queued. Two further measurements bound the environment's share. Of the 372 graded runs, 24 ended in a build or dependency failure. Removing them leaves the best agent at 14 of the 34 Run papers reproduced and moves the best Retrain and Reimplement rates by less than one percentage point. [The frontier agents in the general reply, run in the same environment, reproduce a of n papers.]

**How claims, configurations, targets and tolerances were validated (Q2).** The claim, minimal configuration and target tuple of each paper were extracted during dataset construction and frozen before any agent ran. Below we call the target tuple and minimal configuration together the frozen target. The final construction stage (Stage III, Appendix E) checked which artifacts each paper's authors released and settled each compute estimate, so the claims, minimal configurations and targets had no independent check and there was no annotator agreement to report. The revision states this in Appendix E. [AUTHOR: the paper's statement at iclr2027_conference.tex:668 says an author reviewed every extracted field. If that review covered the claim, configuration and target fields, this sentence becomes "had only an author review of each extracted field, with no second check and no annotator agreement"; if it did not, line 668 changes instead. The Appendix E file on disk does not yet state either (followups_check_1.md, item 1).]

We have now checked the targets and minimal configurations against the papers. A model from a different lab than our auditor (OpenAI's gpt-6.1-sol) read each of the 100 papers and answered four yes-or-no questions about the frozen target, quoting the passage behind each answer. The papers supported each part of the frozen target as follows (Appendix E):

| Part of the frozen target | Supported, of 100 |
| :- | -: |
| Value | 92 |
| Metric | 95 |
| Dataset and split | 76 |
| Method or variant | 69 |
| All four | 55 |

The dataset-and-split and method-or-variant questions check the minimal configuration, the value and metric questions check the target, and the choice of claim rests on construction alone, which Appendix E now states. [An author read each of the 45 papers with a failed question against the paper itself. The paper does not support the frozen target in k of the 45, and we corrected those targets and rescored their runs, which changes v verdicts.] The checking model saw the frozen target when it answered, so this is a check of each target against its paper, and we describe it that way.

On tolerances, 62 of the 100 claims are point estimates, and 58 of those use the default 5% relative tolerance while 4 state their own margin. The other 38 are tested by direction (21), by a threshold (14) or in another way (3). Rescoring at 1%, 2% and 10% gives the best agent 9, 12 and 14 reproduced of the 34 Run papers, against 14 at 5%. The ordering of the tiers holds at every setting (full table in the reply to T29u and in Appendix F).

### Sources (rqBN)

| Number | File |
| :- | :- |
| F1 0.82, 396 runs, three graders, one label per run, 372 of them with an auditor grade | paper Section 4 and Appendix D (protocol of record, memory human-grader-study-lost) |
| 45,861 checked: 45,673 exact, 100, 60, 25, 3 unmatched (log table) | rebuttal/results/e5/summary.json; e5/README.md:11, :18 |
| 1 of 372 wrote to commands.log, 2510.25146, write_file, graded 1 unverifiable | rebuttal/results/e5/README.md; viewer index tools/anon_viewer/public/data/index.json |
| 119 commands missing in 65 runs, two early-return paths | rebuttal/results/e5/README.md (log completeness) |
| host transcript outside the sandbox mounts, not hash-chained | rebuttal/results/e5/README.md; Risks item 6 below (no hash-chained log in the code) |
| 3 unmatched entries all in trajectory.jsonl; no agent write to trajectory.jsonl | rebuttal/results/e5/README.md (For a human to judge, item 2; write hits) |
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

### Reply to YGTR, part 1 of 2 (4,953 characters)

Thank you for the review. Your main concern was whether our findings hold for frontier models in the harnesses people actually use, so we ran that experiment and measured the confounds you named. These are the changes, each detailed below:
- Section 5.1 and a new appendix section: gpt-6.1-sol in Codex CLI and in our harness, [gpt-6-astra] in Codex CLI, and Muse Wonder in mini-SWE-agent and in our harness, on papers frozen before any run.
- Section 5.3: the bound on build failures with an x86 replay, and a re-execution of missed runs with new seeds.
- Section 5.2: a 95% Wilson interval on every rate, and repeated runs of one agent.
- Section 5.2: the trace of all 28 cells with no graded run, the two missing audits graded, and the two runs that evaluated a downloaded checkpoint counted as not reproduced.

**Frontier models and production harnesses (W1, Q1).** We ran two current OpenAI models, [gpt-6-astra and gpt-6.1-sol], and Meta's Muse Wonder on papers drawn with a fixed seed from every tier and frozen before any run ([n] papers for the OpenAI models, [m] for Muse Wonder). Both gpt-6.1-sol and Muse Wonder ran in our ReAct-style harness and in a production harness (Codex CLI and mini-SWE-agent respectively), and gpt-6-astra ran in Codex CLI only. Codex CLI and mini-SWE-agent keep their own tools, system prompts and context handling, and every run gets the same sandbox, task text, GPU grant, GPU metering and auditor as the main runs, so within one model the harness is the only thing that changes. A Codex run ends when Codex ends its own turn, which is the same stopping rule our harness uses.

[Result sentence: gpt-6-astra in Codex CLI reproduced a of 8 papers, gpt-6.1-sol b of n in our harness and c of n in Codex CLI, and Muse Wonder d of m in our harness and g of h in mini-SWE-agent, with 95% intervals in the new appendix table.] [Harness sentence: the paired difference between the two harnesses is k papers for gpt-6.1-sol (exact McNemar p = x), which is within / larger than the run-to-run change we measured below.] [Budget sentence: the frontier runs used a median of u% of their GPU grant.] The most common failure in the paper, writing the method without checking its output against the paper's numbers, occurs in [k] of the frontier agents' [m] failing runs, labeled with the same procedure as the paper's runs, and an author's blind labels agree with that procedure on [x] of 20 runs. Muse Spark 1.2, one of our four main agents, also gives a same-family comparison on the same papers, [Muse Wonder d of 12 against Muse Spark e of 12].

We keep the ReAct-style harness for the main results because it treats every model in the same way, and the new appendix section reports what a production harness changes.

**Hardware and other confounds (W2a).** We cannot fully separate the hardware from agent error, but we can bound its effect in three ways. First, 24 of the 372 graded runs ended in a build or dependency failure, and our reading of their transcripts traces 14 of them to a package with no build for the aarch64 CPUs of our GH200 nodes, 7 to other environment problems and 3 to agent error. For the 12 of the 14 with a replayable install command, we re-ran the install on x86 nodes, and 9 of 12 build and import (95% Wilson interval 47% to 91%). Removing all 24 from the denominators moves no best-agent rate by more than one percentage point, because DeepSeek-V4-Flash had none of these failures at Run (Section 5.3):

| Tier | Build or dependency failures | Best agent as graded (95% interval) | Best agent with the 24 removed (95% interval) |
| :- | :- | :- | :- |
| Run | 13 | 14/34 = 41% [26%, 58%] | 14/34 = 41% [26%, 58%] |
| Retrain | 6 | 9/33 = 27% [15%, 44%] | 9/33 = 27% [15%, 44%] |
| Reimplement | 5 | 5/33 = 15% [7%, 31%] | 5/32 = 16% [7%, 32%] |

The agent most affected is MiniMax-M2.7 at Run, which goes from 3/34 to 3/26. Second, we re-ran the final command sequence of runs that followed the released pipeline and still missed, on the same nodes with two new seeds and no model in the loop. Only 3 papers had a single clean command chain. Two have finished and miss again on both seeds, with the measured value repeating within 0.0007 on 2505.17836 and spreading by 0.28 on 2510.07501, and the third is queued. Third, the frontier runs above use the same environment, and [their results].

**One run per cell (W2b).** Every rate now carries a 95% Wilson interval in Section 5.2, for example 14/34 = 41% [26%, 58%] for the best agent at Run and 5/33 = 15% [7%, 31%] at Reimplement, and we queued two more runs of DeepSeek-V4-Flash on 12 papers drawn with a fixed seed, four per tier, two of which some agent had reproduced and two of which none had. [Its verdict was the same in all three runs on k of 12 papers (95% interval [lo, hi]), so most single-run failures are consistent / a share of failures are transient, and the revision widens the comparisons between agents by this rate.]

### Reply to YGTR, part 2 of 2 (3,325 characters)

**Fetching checkpoints over the network (Q2).** Yes, we checked. The harness keeps no network log, so we scanned every transcript, including the commands, fetched URLs and code the agent wrote, for model downloads (hf_hub_download, snapshot_download, huggingface-cli, from_pretrained with a repository id, torch.hub, gdown, and wget or curl of weight files). The scan finished on 368 of the 372 graded runs, and none of the 4 it could not finish was reproduced. All 42 reproduced Retrain and Reimplement runs were scanned, and 16 of them matched a pattern. Reading those 16 by hand, 10 matched text that is not a download, such as an import line, a requirements.txt or a dataset, and 4 downloaded only a base model that the method starts from, such as the OpenVLA model that CogVLA builds on. The other 2 evaluated a downloaded checkpoint of the model the claim is about. Muse Spark 1.2 on CogVLA (2508.21046, Retrain) downloaded a LIBERO-Spatial checkpoint linked from the authors' repository, and MiniMax-M2.7 on CURE (2505.12677, Reimplement) downloaded the authors' erased Stable Diffusion v1.4 weights from their Google Drive folder. Neither was the best agent's run. The revision counts both as not reproduced in Section 5.2, so Muse Spark's Retrain count goes from 9/33 to 8/33 and MiniMax-M2.7's Reimplement count from 2/33 to 1/33, while the best-agent rates stay at 9/33 at Retrain (DeepSeek-V4-Flash) and 5/33 at Reimplement (Muse Spark). The scan cannot see a download made inside an imported library, and the revision states that limit.

**Failures that were not the agent's fault (Q3).** Yes, and 27 of the 400 cells failed for reasons we traced outside the agent: 6 of the 28 cells with no graded run and 21 graded runs that failed on the environment (14 aarch64 builds and 7 other environment problems), so 6 + 14 + 7 = 27, while 16 further cells were stopped by the cluster job (Section 5.2 and Section 5.3). The 27 is the count we could trace and does not bound the failures outside the agent, because the 76 runs that ran a faithful pipeline and still missed are not in it, and the Limitations section says that for them we cannot separate agent error from seed and hardware variance. Of the 12 aarch64 installs we replayed, 3 also fail on x86, so their cause is still open. We traced all 28 cells that produced no graded run, using the cluster's job accounting and the harness logs. Six failed for reasons outside the agent: the four cells of paper 2510.20725 never started because of a bug in our prompt rendering, since fixed, and two audits of Muse Spark 1.2 never returned a verdict. Sixteen more stopped before the agent finished, when the cluster job running them reached its 48-hour limit or was cancelled. Two ended when the agent's context filled, which the protocol counts as an agent failure, and for 4 finished runs the logs do not record why they are missing from the graded set. The two missing audits now have grades from the same pinned auditor, reproduced (score 8) on 2503.23035 and partial (score 6) on 2510.08177. [We reran the other 20 cells with the same settings, and r of them reproduce.] Every rate in the revision includes these grades.

We would be glad to hear whether the frontier and harness results address the concern about generalization behind your informativeness score.

### Sources (YGTR)

| Number | File |
| :- | :- |
| 24 build-and-dependency runs; 14 aarch64, 7 other environment (5 labelled plus the 2 not-chip rows), 3 agent error; x86 replay 9 of 12 | rebuttal/results/e8/summary.json (build_dependency_runs.class_counts); e8/README.md; e8/x86/README.md; e8/x86/results.csv (not_arch rows) |
| gpt-6.1-sol in both harnesses, gpt-6-astra in Codex CLI only | rebuttal/PLAN.md:115; rebuttal/results/databook/frontier_cells.csv |
| best Run 14/34 unchanged, Retrain 9/33 (DeepSeek-V4-Flash; Muse 9/32 becomes 8/32 after the checkpoint correction), Reimplement 5/32, MiniMax Run 3/26; table by tier with intervals | rebuttal/results/e8/bound.csv; e8/summary.json (build_dependency_runs.by_tier, bound_best_per_tier_all_env_removed.wilson95); e6/summary.json (settings.S0_index) |
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
| 2503.23035 reproduced (8), 2510.08177 partial (6) | rebuttal/results/e8/regrade_muse.json |
| frontier results, McNemar, budget use, failure-mode shares, blind labels, repeat flips (job 3540624 running, 3540625 to 3540633 pending), 2506.10351 re-execution, 20 reruns | pending (E1, E2, E3, E10, E8 reruns) |

## Risks: where a reviewer could push back

1. **The target check shows 45 of 100 targets failing at least one question (rqBN Q2, T29u Q2).** A reviewer can read 55/100 as evidence that the targets are unreliable. What closes it is Mithil's read of the 45 (rebuttal/results/e7/v3_failures.csv), giving the count the paper actually contradicts, and the rescore of those runs at the corrected targets with the change in best-agent rates. If k is large, the replies should lead with the rescored rates.
2. **The reply admits that 16 empty cells were stopped by the cluster job, which contradicts the paper's sentence that all 28 are model failures (YGTR Q3).** This also reverses the 2026-09-10 and 09-19 instructions in memory paper-missing-cells-accounting, so Mithil should decide it before posting. What closes it is the rerun grades of the 20 cells (jobs 3540630 to 3540633, 3540786, 3540787, plus Muse on 2510.20725) and a Section 5.2 sentence that matches the reply.
3. **The confusion matrix comes from an aggregate table, and the paper says 396 hand-graded runs (T29u Q1, rqBN W1).** The matrix Mithil supplied on 11-08 covers the 372 runs with an auditor grade, and its auditor columns match the graded runs exactly, but no per-run label file is on disk. The per-tier reproduced table (e4/per_tier.csv) sums to the matrix totals and its auditor counts match the graded runs per tier (31, 29, 13). Appendix D should say the matrix is over the 372 runs with both grades. The original design has one human label per run, so inter-human agreement cannot be reported; a second blind grader on about 40 runs stratified by verdict would close it if time allows.
4. **Codex runs stop early, which a reviewer may call a configuration artifact (YGTR W1).** The first ten frontier runs used a median under 2% of their GPU grant and most ended with "could not run" (rebuttal/results/frontier/run_usage_summary.md), and two cite GPU requests left in the queue. What closes it is the per-run grant use and exit reason in the appendix table, the queue wait per GPU request from run_gpu logs, and, if Mithil approves, a small variant with a fixed number of "continue" prompts.
5. **The two checkpoint downloads came from the authors' own releases, which questions the tier labels of 2508.21046 and 2505.12677 (YGTR Q2).** A Retrain paper with released weights for the claimed model belongs at Run. What closes it is a check of both papers' availability records against the linked checkpoints, and moving the papers if the release covers the claimed configuration.
6. **The hash-chained host log was removed from the rqBN reply (rqBN W1).** No such log exists in the code, and the frontier runs were graded without it, so the reply now promises only the Appendix A rewording and the log comparison that already exist.
7. **The re-execution check covers only 3 papers (rqBN Q1, YGTR W2).** A reviewer can call it too small to bound the environment. What closes it is the two-seed outcome on all 3 (jobs under /work/nvme/bfvr/msalunkhe/rebuttal/e10/state.json) and, if time allows, adding near-miss papers from the 8 to 32 GPU-hour band.
8. **The log check leaves two loose ends (rqBN W1).** The evidence directory's modification time is more than 60 seconds after run end in 63 of 372 runs with no established cause, and the paper says 396 runs started while the check matched 372 graded runs. What closes it is a trace of what touched those 63 directories (the 40 dated 2026-10-29 likely match a cleanup) and the reconciliation of the 24 started but ungraded runs, which the empty-cell trace already covers.
