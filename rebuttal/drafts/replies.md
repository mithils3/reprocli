# OpenReview replies, ICLR 2027 submission 22528 (RECLAIM)

Draft of 2026-11-06 for Mithil to read. Nothing here has been posted. Square brackets mark numbers from runs or labels that are not frozen yet, and each bracketed sentence is written so that either outcome fits. The ICLR 2027 author guide does not state a per-comment character limit, so every part below is kept under 5,000 characters, and the count of each part (with the slots still unfilled) is given in its heading line. Each reply now opens with one sentence of thanks and a list of the changes with their locations, following the iclr-review skill (~/.claude/skills/iclr-review), and the T29u reply is now two parts.

Order of posting from PLAN.md Section 4: T29u and rqBN on 11-11, then YGTR and the general reply on 11-14.

## General

### General reply (one part, 3,678 characters)

We thank the three reviewers for their time. They agree that the task and the grading design are sound and well documented, and their requests fall into four groups: stronger agents in production harnesses, repeated runs, a fuller validation of the auditor and of the logs it reads, and a clearer account of failures that the agent did not cause. This is what we added for each, and the replies to each reviewer give the details.

**Revisions by section.**
- Section 5.1 and a new appendix section: the frontier models and production harnesses, with a table by model, harness and tier.
- Section 5.2: Wilson intervals on every rate, the repeat-run result, and rates updated for the regraded and rerun cells.
- Section 4 and Appendix D: the auditor-versus-human confusion matrix and boundary table.
- Appendix A: the log comparison and its limit, and a corrected sentence on what the auditor prompt says.
- Appendix E and F: what the final construction stage checked, the target check, and the tolerance table.
- Section 5.3 and Limitations: the hardware bound, the checkpoint scan and the re-execution check, each where its claim is made.

**Frontier agents and production harnesses.** We ran [gpt-6-astra and gpt-6.1-sol] from OpenAI on [n] papers and Muse Wonder from Meta on [m] papers, drawn with a fixed seed from every tier and frozen before any run. Each model ran in our ReAct-style harness and in a production harness (Codex CLI for the OpenAI models, mini-SWE-agent for Muse Wonder), with the same sandbox, task text, GPU grant and auditor as the main runs. [Result sentence: gpt-6-astra in Codex CLI reproduced a of 8 papers, gpt-6.1-sol b of n in our harness and c of n in Codex CLI, and Muse Wonder d of m.] [Failure-mode sentence: the frontier agents' failures fall into the paper's three most common failure modes at shares inside the 95% intervals of the open agents, or Codex CLI removes mode X in k runs.]

**Repeated runs.** Every rate now carries a 95% Wilson interval, for example 14/34 = 41% [26%, 58%] for the best agent at the Run tier. We also ran DeepSeek-V4-Flash twice more on 12 of those papers, and [its verdict was the same in all three runs on k of 12].

**Auditor and logs.** [Appendix D now gives the confusion matrix of auditor verdict against human verdict, with the 7/8 boundary and high-severity flags.] We compared the 45,861 entries that agent commands produced in commands.log and trajectory.jsonl across all 372 graded runs with the transcript the harness writes on the host, outside the agent's sandbox. One run of the 372 overwrote its commands.log, and the auditor had graded that run 1 of 10 as unverifiable, so the edit gained it nothing.

**Tolerance and targets.** Moving the default tolerance from 5% to 2% or 10% changes the best agent's count by at most 2 papers at Run, 3 at Retrain and 0 at Reimplement, and the ordering of the tiers holds at every setting we tried. A model from a different lab than our auditor checked every frozen target against its paper, and [k] targets the paper does not support were corrected and their runs rescored.

**Failures outside the agent and checkpoint downloads.** We traced all 28 cells that produced no graded run. Six failed for reasons outside the agent, and 16 more stopped when the cluster job running them reached its 48-hour limit or was cancelled. The two missing audits are now graded, and [the 20 other cells were rerun, with r reproduced]. A scan of every transcript for model downloads found 2 reproduced Retrain or Reimplement runs that evaluated a downloaded checkpoint of the claimed model. Neither was the best agent's run, and the revision counts both as not reproduced.

### Sources (General)

| Number | File |
| :- | :- |
| 14/34 = 41% [26%, 58%] | rebuttal/results/e6/summary.json (settings.S0_index.dsv4/run) |
| 45,861 entries, 372 runs, 1 overwrite, graded 1 | rebuttal/results/e5/summary.json; e5/README.md; viewer index (minimax-reimplement-2510.25146 score 1, unverifiable) |
| best-agent change at 2% and 10% (Run 12/14/14, Retrain 9/9/12, Reimplement 5/5/5) | rebuttal/results/e6/README.md table |
| 28 empty cells, 6 outside agent, 16 job limit or cancel | rebuttal/results/e8/summary.json (empty_cells, outside_agent_cells); e8/empty_cells_traced.csv |
| 2 checkpoint downloads | rebuttal/results/e9/README.md; e9/class_review.csv |
| frontier, repeat runs, confusion matrix, target corrections, reruns | pending (E1, E2, E3, E4, E7 settlement, E8 reruns) |

## T29u

### Reply to T29u, part 1 of 2 (2,234 characters)

Thank you for the careful review. These are the changes, each detailed below:
- Section 5.2: a 95% Wilson interval on every rate, and DeepSeek-V4-Flash run twice more on 12 papers to measure run-to-run variation.
- Appendix D: [the five-by-five confusion matrix of auditor against human verdict, with the 7/8 boundary and high-severity flags].
- Appendix F: every graded run rescored at 1%, 2%, 5% and 10% tolerance.
- Appendix E: every frozen target checked against its paper by a model from a different lab than our auditor[, with k targets corrected and their runs rescored].
- Section 5.3: a bound on build failures from the aarch64 hardware, with an x86 replay of the failed installs.

**One run per cell (W1).** We agree that one rollout per cell gives a point estimate, so every rate in the revision carries a 95% Wilson interval. For the best agent per tier these are 14/34 = 41% [26%, 58%] at Run, 9/33 = 27% [15%, 44%] at Retrain and 5/33 = 15% [7%, 31%] at Reimplement, and the overall count is 73/400 = 18% [15%, 22%]. To measure run-to-run variation directly, we ran DeepSeek-V4-Flash, the best agent at Run, twice more on 12 papers drawn with a fixed seed, four per tier, two of which some agent had reproduced and two of which none had. [Its verdict was the same in all three runs on k of 12 papers (95% interval [lo, hi]), and the ordering Run, Retrain, Reimplement held in every run / held in j of 3 runs.] The revision compares two agents only where their intervals, widened by this rate of change, do not overlap, and it says that the measurement covers one agent.

On environment sensitivity, 24 of the 372 graded runs ended in a build or dependency failure, and our reading of their transcripts traces 16 of them to a package that has no build for the aarch64 CPUs of our GH200 nodes. For the 12 of these with a real aarch64 failure and an install command we could replay, we re-ran the install on x86 nodes, and 9 of 12 build and import (95% Wilson interval 47% to 91%). Removing all 24 from the denominators leaves the best Run-tier rate at 14/34, because DeepSeek-V4-Flash had none of these failures at Run, and moves the best Retrain and Reimplement rates by less than one percentage point (to 9/32 and 5/32).

### Reply to T29u, part 2 of 2 (3,222 characters)

**Auditor disagreements, the 7/8 boundary and high-severity flags (W2, Q1).** Appendix D now gives the five-by-five confusion matrix of auditor verdict against human verdict over the [396] hand-graded runs [counts], with precision [x], recall [y] and F1 0.82 on the reproduced verdict. Scores of 8 and above count as reproduced and 6 or 7 as partial, and on the [n] runs that either the auditor or the human placed at 7 or 8 they agree on [m]. On the [q] runs where either flagged a high-severity integrity problem they agree on [p]. [Disagreement sentence: of the d disagreements, e are auditor reproduced against human partial and f the reverse.]

Two checks that do not depend on the auditor also bear on high-severity problems. A comparison of the agent's logs with the host transcript found one edited log in 372 runs, on a run the auditor had already graded unverifiable, and a scan of every transcript for model downloads found two reproduced runs that evaluated a downloaded checkpoint of the claimed model. Neither was the best agent's run, and the revision counts both as not reproduced. The reply to rqBN gives both checks in full.

**Choice of match target and the default 5% tolerance (Q2).** Of the 100 claims, 62 are point estimates and 38 are tested by direction or by a threshold (for example "beats the strongest baseline"), which a tolerance does not affect. Of the 62 point estimates, 58 use the default 5% relative tolerance and 4 state their own margin. We rescored every graded run at four relative tolerances.

| Relative tolerance | Run, best of 34 | Retrain, best of 33 | Reimplement, best of 33 | All agents, of 400 cells |
| :- | :- | :- | :- | :- |
| 1% | 9 | 8 | 4 | 56 |
| 2% | 12 | 9 | 5 | 65 |
| 5% (default) | 14 | 9 | 5 | 73 |
| 10% | 14 | 12 | 5 | 82 |

The ordering of the tiers holds at every setting, and with an absolute tolerance of 1 or 2 points on percentage metrics the total is 70 or 72 of 400. Tightening to 1% moves 17 of the 73 reproduced runs to partial, and loosening to 10% moves 9 partial runs, whose only failed criterion was the number, up to reproduced. For example, DeepSeek-V4-Flash measured 90.6 on 2511.19808 against a frozen target of 97.3, a gap of 6.7 / 97.3 = 6.9%, so that run is partial at 5% and reproduced at 10%.

On the match target itself, a model from a different lab than our auditor (OpenAI's gpt-6.1-sol) read each of the 100 papers and answered four yes-or-no questions about the frozen target, quoting the passage behind each answer. The paper reports the frozen value for 92 of 100 targets, for the frozen metric for 95, on the frozen dataset and split for 76, and for the frozen method or variant for 69, and all four hold for 55 of 100. The most common failure is the method or variant question alone (18 papers), which flags cases like 2506.18890, whose frozen value of 27.443 PSNR appears in the paper for 24 input views while the frozen configuration says 12. [An author read all 45 papers with a failed question against the paper itself. The paper does not support the frozen target in k of them, and we corrected those targets and rescored their runs, which changes v verdicts and moves the best-agent rates by at most w papers per tier.]

### Sources (T29u)

| Number | File |
| :- | :- |
| 14/34, 9/33, 5/33, 73/400 and their Wilson intervals | rebuttal/results/e6/summary.json (settings.S0_index); interval for 73/400 computed with the same Wilson formula |
| 12 papers, four per tier, two reproduced and two not | rebuttal/subset.json; rebuttal/results/subset/README.md |
| 24 build-and-dependency runs, 16 aarch64, bound 14/34, 9/32, 5/32; x86 replay 9 of 12 | rebuttal/results/e8/summary.json (build_dependency_runs, bound_best_per_tier_all_env_removed); e8/bound.csv; e8/x86/README.md |
| 1 edited log in 372 runs, graded unverifiable | rebuttal/results/e5/README.md |
| 2 reproduced runs with a downloaded checkpoint | rebuttal/results/e9/README.md; e9/class_review.csv |
| 62 point estimates, 58 default, 4 stated margins, 38 without a number test | rebuttal/results/e6/summary.json (claims.lockfile_kinds, point_estimate_default_5pct, point_estimate_stated_margin) |
| tolerance table, 56/65/73/82 of 400, 70 and 72 at 1 and 2 points | rebuttal/results/e6/README.md; e6/summary.json (cells, summed per setting) |
| 17 falls at 1%, 9 rises at 10% | rebuttal/results/e6/summary.json (falls_by_setting, moves_by_setting, number_only_partials) |
| 2511.19808 example, 90.6 vs 97.3, 6.9% | rebuttal/results/e6/README.md (worked run) |
| 92, 95, 76, 69, 55 of 100; 45 failures; 18 method-only | rebuttal/results/e7/summary.json (step3); e7/README.md |
| 2506.18890, 27.443 PSNR, 24 vs 12 views | rebuttal/results/e7/v3_failures.csv; e7/README.md |
| repeat runs, confusion matrix, boundary and flag agreement, target corrections | pending (E3, E4, E7 settlement) |

## rqBN

### Reply to rqBN, part 1 of 2 (3,962 characters)

Thank you for checking how the logs and the auditor are validated. These are the changes, each detailed below:
- Appendix A: the description of the two harness logs now matches the code (old and new wording below), and the appendix reports a comparison of all 45,861 logged entries with the host transcript, which found one overwritten log, on a run the auditor had graded unverifiable.
- Appendix D: [the confusion matrix of auditor against human verdict, with precision, recall, per-tier F1 and flag agreement], and a statement that the study gives one human label per run.
- Appendix E: what the final construction stage checked, and a check of every frozen target against its paper.
- Section 5.3 and Limitations: a re-execution of missed runs with new seeds, and the bound on build failures.

**Auditor validation (W1).** Appendix D now gives the five-by-five confusion matrix of auditor verdict against human verdict [counts], precision [x] and recall [y] on the reproduced verdict alongside the F1 of 0.82, F1 by tier [Run r, Retrain t, Reimplement i], and the mean absolute difference between auditor and human on the full 0 to 10 scale [d]. On runs where either the auditor or the human recorded a high-severity integrity flag, they agree on [p of q]. In the original study each of the 396 runs that started received one human label, since three graders divided the runs, each blind to the auditor's score and using the same rubric. That design does not measure agreement between humans, and the revision says so. [If a second grader labels a subset: A second author has now labeled n of these runs blind to both earlier labels, and the two humans agree on k of n.]

**Writable logs (W1).** The harness process writes commands.log and trajectory.jsonl, and the sandbox mounts the evidence directory read-write, so the agent's shell could have rewritten them. Appendix A said we instruct the auditor to read these files as unverified claims; the auditor prompt has no such instruction for these two files. We rewrote the sentence to state what the auditor does and what the log comparison below adds.

| Appendix A | Wording |
| :- | :- |
| Before | "We therefore instruct the auditor to read the bundle as unverified claims and to trace every number to the command that produced it." |
| After | "The auditor traces every number to the command that produced it. Because the agent could edit these two files, we compared every logged entry with the transcript the harness writes on the host, outside the sandbox." |

To find out whether any agent did edit them, we used the transcript the harness writes on the host, which lies outside every directory the sandbox mounts. For all 372 graded runs, we matched each entry that an agent command produced in the two files against that transcript, requiring the same command and return code and, for GPU jobs, the same cost and remaining budget. Of the 45,861 such entries, 45,673 match exactly. Another 185 differ for reasons the harness code explains: 100 are calls the harness refused, which carry no cost line, 60 are remaining-budget values within 0.00015 GPU-hours of the transcript, and 25 are the first attempt of a call that was retried. The last 3 differ in the remaining-budget field by less than 0.0003 GPU-hours, with the cost equal.

We also searched every agent command for writes to the two files. One run of the 372 wrote to commands.log, where MiniMax-M2.7 on 2510.25146 replaced the file with its own notes through a write_file call, and the auditor graded that run 1 of 10 as unverifiable, so the edit gained nothing. No run wrote to trajectory.jsonl. The comparison also found 119 commands in 65 runs that our harness ran but never wrote to commands.log, because two early-return paths in our code skip the log, and the host transcript holds all of them. This check catches any edit made through the agent's own commands, which the transcript records, and Appendix A now states that limit.

### Reply to rqBN, part 2 of 2 (2,984 characters)

**Human-expert reproduction baseline (Q1).** A stratified human reproduction across the three tiers, under the same environment and budgets, is beyond what we can run, and the Limitations section says so. What we can measure is how often the environment alone produces a miss. We took papers where an agent followed the released pipeline and still landed outside tolerance, extracted the final command sequence from its transcript, and re-ran it on the same GH200 nodes with two new seeds and no model in the loop. Only 3 papers (1 Run, 2 Retrain, all with grants of 8 GPU-hours or less) had a single clean command chain, because the other candidates spanned several GPU sessions or depended on code the agent had edited by hand. [On k of the 3 the re-run misses again on both seeds, which places those misses with the environment or the paper, and on the other 3 minus k it reaches the target, which points to seed variation or agent error.] Two further measurements bound the environment's share. Of the 372 graded runs, 24 ended in a build or dependency failure, and removing all of them leaves the best Run-tier rate at 14/34 and moves the best Retrain and Reimplement rates by less than one percentage point. [The frontier agents in the general reply, run in the same environment, reproduce a of n papers.]

**How claims, configurations, targets and tolerances were validated (Q2).** The claim, minimal configuration and target tuple of each paper were extracted during dataset construction and frozen before any agent ran. The final construction stage (Stage III, Appendix E) audited only the availability calls, meaning which artifacts each paper's authors released, so the targets had no independent check and there was no annotator agreement to report. The revision states this in Appendix E.

We have now checked them. A model from a different lab than our auditor (OpenAI's gpt-6.1-sol) read each of the 100 papers and answered four yes-or-no questions about the frozen target, quoting the passage behind each answer. The paper reports the frozen value for 92 of 100 targets, for the frozen metric for 95, on the frozen dataset and split for 76, and for the frozen method or variant for 69, and all four hold for 55. [An author read each of the 45 papers with a failed question against the paper itself. The paper does not support the frozen target in k of the 45, and we corrected those targets and rescored their runs, which changes v verdicts.] Because the checking model saw the frozen tuple, this is a check of each target against its paper, and we describe it that way.

On tolerances, 62 of the 100 claims are point estimates, and 58 of those use the default 5% relative tolerance while 4 state their own margin. The other 38 are tested by direction or threshold. Rescoring at 1%, 2% and 10% gives the best agent 9, 12 and 14 of 34 Run papers against 14 at 5%, and the ordering of the tiers holds at every setting (full table in the reply to T29u and in Appendix F).

### Sources (rqBN)

| Number | File |
| :- | :- |
| F1 0.82, 396 runs, three graders, one label per run | paper Section 4 and Appendix D (protocol of record, memory human-grader-study-lost) |
| 45,861 checked, 45,673 exact, 185 explained (100, 60, 25), 3 unmatched under 0.0003 h | rebuttal/results/e5/summary.json; e5/README.md |
| 1 of 372 wrote to commands.log, 2510.25146, write_file, graded 1 unverifiable | rebuttal/results/e5/README.md; viewer index tools/anon_viewer/public/data/index.json |
| 119 commands missing in 65 runs, two early-return paths | rebuttal/results/e5/README.md (log completeness) |
| 3 papers re-executed (1 Run, 2 Retrain), exclusions | rebuttal/results/e10/README.md; e10/selection.csv |
| 24 build-and-dependency runs, best Run 14/34 unchanged | rebuttal/results/e8/summary.json; e8/bound.csv |
| 92, 95, 76, 69, 55 of 100; 45 failures | rebuttal/results/e7/summary.json (step3); e7/README.md |
| 62 point estimates, 58 default, 4 margins, 38 others; 9/12/14 of 34 | rebuttal/results/e6/summary.json; e6/README.md |
| Appendix A wording, before and after | paper_latex/appendix/a_harness.tex lines 133-134 (before); the after text is proposed here |
| confusion matrix, per-tier F1, 0-10 difference, flag agreement, re-execution outcome, target corrections | pending (E4, E10, E7 settlement) |

## YGTR

### Reply to YGTR, part 1 of 2 (4,431 characters)

Thank you for the review. Your main concern was whether our findings hold for frontier models in the harnesses people actually use, so we ran that experiment and measured the confounds you named. These are the changes, each detailed below:
- Section 5.1 and a new appendix section: [gpt-6-astra and gpt-6.1-sol] in Codex CLI and in our harness, and Muse Wonder in mini-SWE-agent and in our harness, on papers frozen before any run.
- Section 5.3: the bound on build failures with an x86 replay, and a re-execution of missed runs with new seeds.
- Section 5.2: a 95% Wilson interval on every rate, and repeated runs of one agent.
- Section 5.2: the trace of all 28 cells with no graded run, the two missing audits graded, and the two runs that evaluated a downloaded checkpoint counted as not reproduced.

**Frontier models and production harnesses (W1, Q1).** We ran two current OpenAI models, [gpt-6-astra and gpt-6.1-sol], and Meta's Muse Wonder on papers drawn with a fixed seed from every tier and frozen before any run ([n] papers for the OpenAI models, [m] for Muse Wonder). Each model ran in our ReAct-style harness and in a production harness, Codex CLI for the OpenAI models and mini-SWE-agent for Muse Wonder. Codex CLI and mini-SWE-agent keep their own tools, system prompts and context handling, and every run gets the same sandbox, task text, GPU grant, GPU metering and auditor as the main runs, so within one model the harness is the only thing that changes. A Codex run ends when Codex ends its own turn, which is the same stopping rule our harness uses.

[Result sentence: gpt-6-astra in Codex CLI reproduced a of 8 papers, gpt-6.1-sol b of n in our harness and c of n in Codex CLI, and Muse Wonder d of m in our harness and g of h in mini-SWE-agent, with 95% intervals in the new appendix table.] [Harness sentence: the paired difference between the two harnesses is k papers for gpt-6.1-sol (exact McNemar p = x), which is within / larger than the run-to-run change we measured below.] [Budget sentence: the frontier runs used a median of u% of their GPU grant.] The most common failure in the paper, writing the method without checking its output against the paper's numbers, occurs in [k] of the frontier agents' [m] failing runs, labeled with the same procedure as the paper's runs, and an author's blind labels agree with that procedure on [x] of 20 runs. Muse Spark 1.2, one of our four main agents, also gives a same-family comparison on the same papers, [Muse Wonder d of 12 against Muse Spark e of 12].

We keep the ReAct-style harness for the main results because it treats every model in the same way, and the new appendix section reports what a production harness changes.

**Hardware and other confounds (W2).** We cannot fully separate the hardware from agent error, but we can bound its effect in three ways. First, 24 of the 372 graded runs ended in a build or dependency failure, and our reading of their transcripts traces 16 of them to a package with no build for the aarch64 CPUs of our GH200 nodes, 5 to other environment problems and 3 to agent error. For the 12 of the 16 with a real aarch64 failure and a replayable install command, we re-ran the install on x86 nodes, and 9 of 12 build and import (95% Wilson interval 47% to 91%). Removing all 24 from the denominators leaves the best Run-tier rate at 14/34 = 41%, because DeepSeek-V4-Flash had none of these failures at Run, and moves the best Retrain and Reimplement rates by less than one percentage point. The agent most affected is MiniMax-M2.7 at Run, which goes from 3/34 to 3/26. Second, we re-ran the final command sequence of runs that followed the released pipeline and still missed, on the same nodes with two new seeds and no model in the loop. Only 3 papers had a single clean command chain, and [2 of the 3 have finished, and both still miss on both seeds; on one the measured value repeats within 0.0007, on the other it moves by 0.28 across seeds; third pending]. Third, the frontier runs above use the same environment, and [their results].

**One run per cell (W2).** Every rate now carries a 95% Wilson interval, and we ran DeepSeek-V4-Flash twice more on 12 papers, four per tier. [Its verdict was the same in all three runs on k of 12 papers (95% interval [lo, hi]), so most single-run failures are consistent / a share of failures are transient, and the revision widens the comparisons between agents by this rate.]

### Reply to YGTR, part 2 of 2 (2,726 characters)

**Fetching checkpoints over the network (Q2).** Yes, we checked. The harness keeps no network log, so we scanned every transcript, including the commands, fetched URLs and code the agent wrote, for model downloads (hf_hub_download, snapshot_download, huggingface-cli, from_pretrained with a repository id, torch.hub, gdown, and wget or curl of weight files). The scan finished on 368 of the 372 graded runs, and none of the 4 it could not finish was reproduced. All 42 reproduced Retrain and Reimplement runs were scanned, and 16 of them matched a pattern. Reading those 16 by hand, 10 matched text that is not a download, such as an import line, a requirements.txt or a dataset, and 4 downloaded only a base model that the method starts from, such as the OpenVLA model that CogVLA builds on. The other 2 evaluated a downloaded checkpoint of the model the claim is about. Muse Spark 1.2 on CogVLA (2508.21046, Retrain) downloaded a LIBERO-Spatial checkpoint linked from the authors' repository, and MiniMax-M2.7 on CURE (2505.12677, Reimplement) downloaded the authors' erased Stable Diffusion v1.4 weights from their Google Drive folder. Neither was the best agent's run. The revision counts both as not reproduced, so Muse Spark's Retrain count goes from 9/33 to 8/33 and MiniMax-M2.7's Reimplement count from 2/33 to 1/33, while the best-agent rates stay at 9/33 at Retrain (DeepSeek-V4-Flash) and 5/33 at Reimplement (Muse Spark). The scan cannot see a download made inside an imported library, and the revision states that limit.

**Failures that were not the agent's fault (Q3).** We traced all 28 cells that produced no graded run, using the cluster's job accounting and the harness logs. Six failed for reasons outside the agent: the four cells of paper 2510.20725 never started because of a bug in our prompt rendering, since fixed, and two audits of Muse Spark 1.2 never returned a verdict. Sixteen more stopped before the agent finished, when the cluster job running them reached its 48-hour limit or was cancelled. Two ended when the agent's context filled, which the protocol counts as an agent failure, and for 4 finished runs the logs do not record why they are missing from the graded set. The two missing audits now have grades from the same pinned auditor, reproduced (score 8) on 2503.23035 and partial (score 6) on 2510.08177. [We reran the other 20 cells with the same settings, and r of them reproduce.] Every rate in the revision includes these grades. Among the 372 graded runs, the build and dependency bound above covers the failures the environment caused.

We would be glad to hear whether the frontier and harness results address the concern about generalization behind your informativeness score.

### Sources (YGTR)

| Number | File |
| :- | :- |
| 24 build-and-dependency runs; 16 aarch64, 5 other environment, 3 agent error; x86 replay 9 of 12 | rebuttal/results/e8/summary.json (build_dependency_runs.class_counts); e8/README.md; e8/x86/README.md |
| best Run 14/34 unchanged, Retrain 9/32, Reimplement 5/32, MiniMax Run 3/26 | rebuttal/results/e8/bound.csv |
| 3 papers re-executed | rebuttal/results/e10/README.md; e10/selection.csv |
| 12 repeat papers, four per tier | rebuttal/subset.json; rebuttal/results/sweeps/jobs.csv |
| 368 of 372 scanned, 4 timeouts not reproduced | rebuttal/results/e9/summary.json (scan_timeouts); viewer index verdicts (partial, not_reproduced, disqualified x2) |
| 42 reproduced Retrain and Reimplement runs, 16 with a hit, 10 / 4 / 2 | rebuttal/results/e9/README.md (13 of 29 plus 3 of 13); e9/class_review.csv |
| 2508.21046 CogVLA and 2505.12677 CURE downloads | rebuttal/results/e9/class_review.csv; rebuttal/STATUS.md (commands.log:483) |
| Muse Retrain 9 to 8, MiniMax Reimplement 2 to 1, best 9/33 and 5/33 | rebuttal/results/e8/summary.json (per_agent_tier) minus the two E9 runs |
| 28 empty cells: 6 outside agent, 16 job limit or cancel, 2 context, 4 unknown | rebuttal/results/e8/summary.json; e8/empty_cells_traced.csv; e8/README.md |
| 2503.23035 reproduced (8), 2510.08177 partial (6) | rebuttal/results/e8/regrade_muse.json |
| frontier results, McNemar, budget use, failure-mode shares, blind labels, repeat flips, re-execution outcome, 20 reruns | pending (E1, E2, E3, E10, E8 reruns) |

## Risks: where a reviewer could push back

1. **The target check shows 45 of 100 targets failing at least one question (rqBN Q2, T29u Q2).** A reviewer can read 55/100 as evidence that the targets are unreliable. What closes it is Mithil's read of the 45 (rebuttal/results/e7/v3_failures.csv), giving the count the paper actually contradicts, and the rescore of those runs at the corrected targets with the change in best-agent rates. If k is large, the replies should lead with the rescored rates.
2. **The reply admits that 16 empty cells were stopped by the cluster job, which contradicts the paper's sentence that all 28 are model failures (YGTR Q3).** This also reverses the 2026-09-10 and 09-19 instructions in memory paper-missing-cells-accounting, so Mithil should decide it before posting. What closes it is the rerun grades of the 20 cells (jobs 3540630 to 3540633, 3540786, 3540787, plus Muse on 2510.20725) and a Section 5.2 sentence that matches the reply.
3. **The confusion matrix and the 7/8 boundary table do not exist yet (T29u Q1, rqBN W1).** Both reviewers' soundness scores rest on them, and the original design has one human label per run, so inter-human agreement cannot be reported. What closes it is the E4 label file by 11-10, and a second blind grader on about 40 runs stratified by verdict if time allows.
4. **Codex runs stop early, which a reviewer may call a configuration artifact (YGTR W1).** The first ten frontier runs used a median under 2% of their GPU grant and most ended with "could not run" (rebuttal/results/frontier/run_usage_summary.md), and two cite GPU requests left in the queue. What closes it is the per-run grant use and exit reason in the appendix table, the queue wait per GPU request from run_gpu logs, and, if Mithil approves, a small variant with a fixed number of "continue" prompts.
5. **The two checkpoint downloads came from the authors' own releases, which questions the tier labels of 2508.21046 and 2505.12677 (YGTR Q2).** A Retrain paper with released weights for the claimed model belongs at Run. What closes it is a check of both papers' availability records against the linked checkpoints, and moving the papers if the release covers the claimed configuration.
6. **The hash-chained host log was removed from the rqBN reply (rqBN W1).** No such log exists in the code, and the frontier runs were graded without it, so the reply now promises only the Appendix A rewording and the log comparison that already exist.
7. **The re-execution check covers only 3 papers (rqBN Q1, YGTR W2).** A reviewer can call it too small to bound the environment. What closes it is the two-seed outcome on all 3 (jobs under /work/nvme/bfvr/msalunkhe/rebuttal/e10/state.json) and, if time allows, adding near-miss papers from the 8 to 32 GPU-hour band.
8. **The log check leaves two loose ends (rqBN W1).** The evidence directory's modification time is more than 60 seconds after run end in 63 of 372 runs with no established cause, and the paper says 396 runs started while the check matched 372 graded runs. What closes it is a trace of what touched those 63 directories (the 40 dated 2026-10-29 likely match a cleanup) and the reconciliation of the 24 started but ungraded runs, which the empty-cell trace already covers.
