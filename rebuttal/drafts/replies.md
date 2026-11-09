# OpenReview replies, ICLR 2027 submission 22528 (RECLAIM)

Draft of 2026-11-06 for Mithil to read, restructured on 2026-11-08 to the format and length targets of the iclr-review skill (~/.claude/skills/iclr-review, style.md Section 10): a general reply near 1,900 characters, and three posts per reviewer near 8,000 characters in all, the first near 4,000, with bold numbered point labels. The longer draft it replaces is rebuttal/drafts/replies_long_2026-11-08.md. Nothing here has been posted. Square brackets mark numbers from runs or labels that are not frozen yet, and each bracketed sentence is written so that either outcome fits. Each part stays under 5,000 characters, and the count of each part (with the slots still unfilled) is given in its heading line. Each fact sits in one reply and the others point to it, so a Sources table can list a number that its reply now gives by pointer. The author notes that marked sentences waiting on Mithil's decisions were resolved on 11-09 (rebuttal/mithil/decisions_monday.md). Post each part under the title "Response to Reviewer X (k/N)", with N = 2 for T29u, whose answers fit in two parts, and N = 3 for rqBN and YGTR. The Sources tables and the Risks section are not posted.

Order of posting from PLAN.md Section 4: T29u and rqBN on 11-11, then YGTR and the general reply on 11-14.

## General

### General reply (one part, 1,996 characters)

We thank the three reviewers for their careful reading. They found the task important and the evaluation design unusually careful (T29u), the design sound and reusable (YGTR), and the methodological disclosure excellent (rqBN). In RECLAIM a language model, the auditor, grades each run from its logs and outputs. The revision makes these changes, and each reviewer reply gives the numbers.
- **Frontier models in production harnesses** (Section 5.1 and Appendix B). We ran gpt-6.1-sol in our agent loop and in Codex CLI, gpt-6-astra in Codex CLI, and Muse Wonder in our loop and in mini-SWE-agent, on papers from all three release tiers chosen in advance.
- **Uncertainty** (Section 5.2). Every rate has a 95% Wilson interval, and two more runs of DeepSeek-V4-Flash on 12 papers measure run-to-run variation.
- **Auditor validation** (Appendix D). A confusion matrix compares auditor and human grades on the 372 runs both graded, with precision and recall per tier, agreement at the boundary between 7 (partial) and 8 (reproduced), and agreement on anti-cheat flags.
- **Log integrity** (Appendix A). Besides the agent's logs, the harness copies every command to a host transcript the agent cannot reach. Checking all 45,861 log entries against it found one overwritten log, on a run already graded unverifiable.
- **Targets and tolerances** (Appendices E and F). A model from a different lab than our auditor checked each frozen target, the result fixed per paper in advance, against its paper, and every graded run is rescored at 1%, 2%, 5% and 10% relative tolerance.
- **Failures outside the agent** (Sections 5.2 and 5.3). We traced all 28 cells (one agent on one paper) with no graded run, replayed failed builds from our aarch64 nodes on x86 to bound their effect, and reran missed runs' last commands with new seeds.
- **Checkpoint downloads** (Section 5.2). Scanning every transcript found 2 runs evaluating a downloaded checkpoint of the claimed model; both now count as not reproduced.

### Sources (General)

| Number | File |
| :- | :- |
| 13/34 = 38% [24%, 55%] (14/34 before the 2505.23747 correction) | rebuttal/results/e7/rescore_summary.md (best-agent table); e6/summary.json (settings.S0_index.dsv4/run) |
| 45,861 entries, 372 runs, 1 overwrite, graded 1 | rebuttal/results/e5/summary.json; e5/README.md; viewer index (minimax-reimplement-2510.25146 score 1, unverifiable) |
| best-agent count at 1%, 2%, 5% and 10% (Run 9/12/14/14, Retrain 8/9/9/12, Reimplement 4/5/5/5), so at most 14 - 9 = 5, 12 - 9 = 3 and 5 - 4 = 1 | rebuttal/results/e6/README.md table |
| T29u "real and important" and "unusually careful", YGTR "sound ... reusable", rqBN "excellent" | rebuttal/reviews-2026-11-06.md:17, :19, :45, :33 |
| gpt-6.1-sol in both harnesses, gpt-6-astra in Codex CLI only | rebuttal/PLAN.md:115; rebuttal/results/databook/frontier_cells.csv (no thin gpt-6-astra arm) |
| 28 empty cells, 6 outside agent, 22 agent failures | rebuttal/results/e8/summary.json (empty_cells, outside_agent_cells); e8/empty_cells_traced.csv |
| 2 checkpoint downloads | rebuttal/results/e9/README.md; e9/class_review.csv |
| scan finished on 368 of 372 (127 + 118 + 123 of 129 + 118 + 125) | rebuttal/results/e9/summary.json (tiers.*.runs_scanned, scan_timeouts) |
| 28 = 6 outside the agent + 22 agent failures (4 of them finished without a pinned-auditor grade; 3 of the 4 regraded) | rebuttal/results/e8/summary.json; e8/empty_cells_traced.csv (A 2, B 16, D 4); e8/d_cells.md; e8/regrade_dcells.json |
| 73 auditor reproductions are the 73 of 400 cells at submission | rebuttal/results/e8/README.md (reproduction check passes: 73 of 400 cells); e4/summary.json |
| 70 of 400 = 73 + 1 (Muse Spark 1.2, 2503.23035, score 8) - 2 (checkpoint runs muse-retrain-2508.21046, minimax-reimplement-2505.12677) - 2 (dsv4-run and minimax-run on 2505.23747 at the corrected target) | rebuttal/results/e8/regrade_muse.json; e9/class_review.csv; e7/rescore_summary.md; e7/class_d_rescore.md (class D changes 0 cells) |
| best Run agent DeepSeek-V4-Flash; 14 at 10% | rebuttal/results/e6/summary.json (settings.S0_index.dsv4/run); e6/README.md table |
| 4 prompt-bug cells of 2510.20725 rerun | rebuttal/results/sweeps/jobs.csv (3540631, 3540633, 3540786); e8/README.md |
| 372 runs, precision 88%, recall 77%, 73 against 83 reproductions | rebuttal/results/e4/summary.json |
| frontier, repeat runs, reruns of 2510.20725 | pending (E1, E2, E3, E8 reruns of 2510.20725); repeat runs queued, job 3540624 running and 3540625 to 3540633 pending (sacct, followups_check_4.md item 11) |

## T29u

### Reply to T29u, part 1 of 2 (3,885 characters)

Thank you for the careful review. The revision makes these changes for your points:
- Section 5.2: a 95% interval on every rate and mean score, and two more runs of DeepSeek-V4-Flash on 12 papers.
- Appendix D: the five-by-five confusion matrix of auditor against human verdict, with the 7/8 boundary and high-severity flags.
- Appendix F: every graded run rescored at 1%, 2%, 5% and 10% tolerance.
- Appendix E: every frozen target (the value, metric, dataset and configuration fixed before any agent ran) checked against its paper, with 8 corrected and their runs rescored.

**W1: One run per agent-paper cell.**

We reran DeepSeek-V4-Flash, the agent with the highest Run rate, two more times on 12 papers. The 12 were drawn with a fixed seed, four from each tier, and in each tier two are papers some agent had reproduced. The verdict was the same in all three runs on [k] of the 12 papers (95% interval [lo, hi]). Across the three runs, its count of reproduced papers among the 12 moves by at most [j]. As a check on these 12 papers only, Run stays above Retrain and Retrain above Reimplement in [all three] runs, and the revision ranks two agents only when their 95% intervals stay apart after each is widened by [j] papers.

The audit score is the auditor's 0 to 10 grade of a run from its evidence, and 8 or more counts as reproduced. The Run count uses the corrected target of 2505.23747 (14/34 = 41% in the submission, Q2 below), and the mean scores use the original targets:

| Tier, what it releases | Agent with the most papers reproduced | Reproduced | Mean score |
| :- | :- | -: | -: |
| Run: code, data and weights | DeepSeek-V4-Flash | 13/34 = 38% [24%, 55%] | 5.29 [4.13, 6.46] |
| Retrain: no weights | DeepSeek-V4-Flash | 9/33 = 27% [15%, 44%] | 5.45 [4.40, 6.51] |
| Reimplement: no code | Muse Spark 1.2 | 5/33 = 15% [7%, 31%] | 3.85 [2.86, 4.84] |

A cell is one agent on one paper, and over all four agents 70/400 = 18% [14%, 22%] of cells are reproduced. That is the submitted 73, plus one new Muse Spark 1.2 reproduction, less the two runs that used a downloaded checkpoint (W2 below) and the two runs on the corrected target of 2505.23747.

Section 5.2 names no strongest agent and gives all four means: 5.13 [4.55, 5.71] for DeepSeek-V4-Flash, 5.14 [4.59, 5.69] for Muse Spark 1.2 with its two new grades, 3.51 [2.98, 4.04] for Qwen3.6-27B and 3.03 [2.48, 3.58] for MiniMax-M2.7.

Removing the 24 runs that ended in a build or dependency failure moves no best-agent rate by more than one percentage point (Section 5.3).

**W2: The auditor's disagreements with the human grade.**

The human grade finds slightly more reproductions than the auditor in every tier, so the auditor errs toward not reproduced, and the tier ordering is the same under both grades. Submitted grades over all of a tier's cells, an ungraded cell counting as not reproduced:

| Tier | Auditor | Human |
| :- | -: | -: |
| Run | 31/136 = 23% [17%, 31%] | 35/136 = 26% [19%, 34%] |
| Retrain | 29/132 = 22% [16%, 30%] | 32/132 = 24% [18%, 32%] |
| Reimplement | 13/132 = 10% [6%, 16%] | 16/132 = 12% [8%, 19%] |
| All tiers | 73/400 = 18% [15%, 22%] | 83/400 = 21% [17%, 25%] |

Of the 28 runs where only one grader called the result reproduced, the human did in 19 and the auditor in 9, or 7 against 3 at Run, 7 against 4 at Retrain and 5 against 2 at Reimplement.

Two checks independent of the auditor test whether it missed an integrity problem. Comparing the agent's logs with a transcript the harness writes on the host, outside the agent's sandbox, found one edited log in 372 runs, on a run the auditor had already graded unverifiable. A scan of every transcript for model downloads found two reproduced runs, MiniMax-M2.7 at Reimplement and Muse Spark 1.2 at Retrain, that evaluated a downloaded checkpoint of the claimed model, and the revision counts both as not reproduced.

### Reply to T29u, part 2 of 2 (3,613 characters)

**Q1: Confusion matrix, the 7/8 boundary and high-severity flags.**

The confusion matrix is below and in Appendix D. Against the human grade, the auditor's reproduced verdict has precision 64/73 = 88% (95% Wilson interval 78% to 93%), recall 64/83 = 77% (67% to 85%) and F1 0.82. The auditor and the human give the same five-way verdict on 306 of 372 runs.

| Human ↓ / Auditor → | Reproduced (8 to 10) | Partial (6, 7) | Not reproduced (2 to 5) | Unverifiable (1: no evidence) | Disqualified (0: flag) | Total |
| :- | -: | -: | -: | -: | -: | -: |
| Reproduced | **64** | 15 | 2 | 0 | 2 | 83 |
| Partial | 7 | **64** | 15 | 0 | 2 | 88 |
| Not reproduced | 2 | 6 | **130** | 3 | 5 | 146 |
| Unverifiable | 0 | 0 | 1 | **6** | 2 | 9 |
| Disqualified | 0 | 1 | 2 | 1 | **42** | 46 |
| Total | 73 | 86 | 150 | 10 | 53 | 372 |

The 372 runs have both grades: of the 400 cells, 4 never started, and 24 of the 396 that did have a human label but no auditor grade.

At the 7/8 boundary, the auditor and the human agree on which side a run falls for 75 of the 100 runs that either placed at 7 or 8.

A high-severity integrity flag, such as a number copied from the paper, forces the score to 0. Of the 57 runs that either grader placed at 0, they agree on 42.

**Q2: Sensitivity to the match target and the default 5% tolerance.**

The tiers keep their order at every tolerance from 1% to 10%, though at 1% Run leads Retrain only 9 to 8, and the target corrections change two verdicts.

The tolerance, how far a measured number may sit from its target and still match, applies only to the 62 claims that are point estimates: 58 use the default 5% relative tolerance and 4 state their own margin. The other 38 test a direction (21, such as "beats the strongest baseline"), a threshold (14) or another form (3: a range, a magnitude and one unrecorded).

Counts before the target corrections:

| Relative tolerance | 1% | 2% | 5% | 10% |
| :- | -: | -: | -: | -: |
| Best agent, Run (of 34) | 9 | 12 | 14 | 14 |
| Best agent, Retrain (of 33) | 8 | 9 | 9 | 12 |
| Best agent, Reimplement (of 33) | 4 | 5 | 5 | 5 |
| All agents (of 400) | 56 | 65 | 73 | 82 |

From the 5% column, the best agent moves by at most 5 papers at Run, 3 at Retrain and 1 at Reimplement. With an absolute tolerance of 1 or 2 points on percentage metrics, all agents reproduce 70 or 72 cells (Appendix F). Tightening to 1% moves 17 of the 73 reproduced runs to partial, and loosening to 10% lifts the 9 partial runs whose only failed criterion was the number. On 2511.19808, for example, DeepSeek-V4-Flash measured 90.6% test accuracy on CIFAR10-IDN against a target of 97.3%. The gap is 6.7 / 97.3 = 6.9%, so the run is partial at 5% and reproduced at 10%.

On the target itself, a model from another lab than our auditor checked four parts of each frozen target against its paper. The paper supports the value for 92 of the 100 claims, the metric for 95, the dataset and split for 76, the method or variant for 69 and all four for 55 (Appendix E). A second check, flagging a target only where the paper contradicts it, sorted the other 45: the frozen number itself is wrong on 8, the number is right but a setting or label is off on 16, and 21 are correct or ambiguous. We corrected the 8 to the paper's value and rescored their runs. Both changed verdicts are on 2505.23747, whose frozen 51.13 came from the authors' README while the paper, which defines the claim, reports 48.4. DeepSeek-V4-Flash (51.44 measured) and MiniMax-M2.7 move from reproduced to partial, so the best Run count falls from 14 to 13 of 34.

Thank you again for the review.

### Sources (T29u)

| Number | File |
| :- | :- |
| 13/34 [24%, 55%], 9/33, 5/33, 70/400 and their Wilson intervals | rebuttal/results/e7/rescore_summary.md (13/34, 23.9 to 55.0); e6/summary.json (settings.S0_index); 70 = 73 + 1 - 2 - 2 (Sources, General); interval for 70/400 (14.1% to 21.5%) computed with the same Wilson formula |
| 12 papers, four per tier, two reproduced and two not | rebuttal/subset.json; rebuttal/results/subset/README.md |
| 24 build-and-dependency runs (13 Run, 6 Retrain, 5 Reimplement), 14 aarch64 (16 labelled less 2 that were not chip failures), bound 14/34, 9/33, 5/32 with Wilson intervals (Muse Spark 1.2 Retrain is 9/33 reproduced, 8/33 after the CogVLA checkpoint correction; it is 9/32 only when its one build failure is also removed from the denominator, e8/bound.csv muse,retrain; DeepSeek-V4-Flash at 9/33 is the best Retrain agent); x86 replay 9 of 12 | rebuttal/results/e8/summary.json (build_dependency_runs, bound_best_per_tier_all_env_removed); e8/bound.csv (dsv4 retrain bound_all 9/33, 0.1507 to 0.4422); e8/x86/README.md; e8/x86/results.csv (not_arch rows) |
| 5.13, 5.14 and 3.03 mean audit score on the frozen targets; 5.14 = 5.00 + (8 + 6)/100, empty cells at 0 | paper_latex/iclr2027_conference.tex:463-466; Muse Spark 5.00 at paper_latex/appendix/b_models.tex:178; rebuttal/results/e8/regrade_muse.json |
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
| 8 corrected targets (2505.23747, 2511.00090, 2506.18896, 2510.10480, 2505.16927, 2510.04136, 2506.01511, 2505.24864); 2 verdicts change, both on 2505.23747; 51.13 README, 48.4 paper, 51.44 measured; 14 to 13 of 34 | rebuttal/mithil/e7_ten_vs_eight.md (classes A and D); e7/rescore_summary.md; e7/class_d_rescore.md |
| repeat runs | pending (E3) |
| mean audit score with 95% t-interval on the original targets, empty cells at 0: Run DeepSeek-V4-Flash 5.29 [4.13, 6.46], Retrain DeepSeek-V4-Flash 5.45 [4.40, 6.51], Reimplement Muse Spark 1.2 3.85 [2.86, 4.84]; overall DeepSeek-V4-Flash 5.13 [4.55, 5.71], Muse Spark 1.2 5.14 [4.59, 5.69], Qwen3.6-27B 3.51 [2.98, 4.04], MiniMax-M2.7 3.03 [2.48, 3.58] | computed by the main session on 2026-11-09 from tools/anon_viewer/public/data/index.json plus the two new Muse Spark grades in rebuttal/results/e8/regrade_muse.json; t-interval over the tier's papers (DeepSeek-V4-Flash Run and Retrain rechecked from index.json) |
| other 45 targets: frozen number wrong 8, number right but setting or label off 16, correct or unclear 21 | rebuttal/mithil/e7_merged.md (Kind of error column: number 8; setting or label 15 + 1; none 21) |
| tier rates under auditor and human grade, submitted grades, all cells of the tier, empty cells not reproduced: Run 31/136 [17%, 31%] and 35/136 [19%, 34%], Retrain 29/132 [16%, 30%] and 32/132 [18%, 32%], Reimplement 13/132 [6%, 16%] and 16/132 [8%, 19%], all 73/400 [15%, 22%] and 83/400 [17%, 25%]; one-sided reproduced calls by tier, human 7/7/5, auditor 3/4/2 | rebuttal/results/e4/summary.json (per_tier_reproduced: auditor = both + auditor_only, human = both + human_only); Wilson 95% computed by the main session on 2026-11-09 and rechecked |
| 14/34 = 41% in the submission | paper_latex/iclr2027_conference.tex:464; rebuttal/results/e7/rescore_summary.md |

## rqBN

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

## YGTR

### Reply to YGTR, part 1 of 3 (3,703 characters)

Thank you for the review. We ran frontier models in production harnesses and measured the confounds you named. The revision makes these changes:
- Section 5.1 and a new subsection of Appendix B: gpt-6.1-sol in Codex CLI and in our loop, gpt-6-astra in Codex CLI, and Muse Wonder in mini-SWE-agent and in our loop, on papers frozen before any run.
- Section 5.3: the bound on build failures with an x86 replay, and a re-execution of missed runs with new seeds.
- Section 5.2: a 95% Wilson interval on every rate, and repeated runs of one agent.
- Section 5.2: the trace of all 28 cells with no graded run, the missing grades added, and the two runs that evaluated a downloaded checkpoint counted as not reproduced.

Each paper sits in one tier by what its authors released: Run (code, data and weights; 34 papers), Retrain (no weights, so the agent trains the model; 33 papers) or Reimplement (no code, so the agent writes it; 33 papers). A cell is one agent on one paper. Our auditor is an LLM grader, Claude Sonnet 5, that scores every run against the paper's pinned number, and a score of 8 or more counts as reproduced.

**W1 and Q1: Frontier models and production coding harnesses.**

We ran two current OpenAI models, gpt-6-astra and gpt-6.1-sol, and Meta's Muse Wonder on papers from every tier, drawn with a fixed seed and frozen before any run. The last row gives Muse Spark 1.2, the Meta model of our main runs, on Muse Wonder's papers, for a comparison within one model family.

| Model | Harness | Papers | Reproduced |
| :- | :- | :- | :- |
| gpt-6-astra | Codex CLI | [8] | [a] |
| gpt-6.1-sol | our loop | 12 | [b] |
| gpt-6.1-sol | Codex CLI | [n] | [c] |
| Muse Wonder | our loop | [m] | [d] |
| Muse Wonder | mini-SWE-agent | [h] | [g] |
| Muse Spark 1.2 | our loop | [m] | [e] |

A harness is the program around the model that supplies its tools, system prompt and context handling. gpt-6.1-sol and Muse Wonder each ran in our thin ReAct-style loop and in a production harness, Codex CLI and mini-SWE-agent respectively. Between the two harnesses of one model the tools, prompt and context handling change, while the sandbox, task text, GPU grant, GPU metering and auditor stay those of the main runs. A Codex run ends when Codex ends its own turn, as in our loop, and the appendix table gives each run's exit reason and each count's 95% interval.

The two gpt-6.1-sol arms share 12 papers, and 9 of them are graded under both harnesses so far. On those 9, our loop reproduced 3 and Codex CLI 2, and they agreed on 6. On all 12, the paired difference is [q] papers (exact McNemar p = [x]), which is [within / larger than] the change between repeated runs of DeepSeek-V4-Flash on the same 12 papers (W3 below). The frontier runs used a median of [u]% of their GPU grant.

To compare failures, Claude Sonnet 5 labelled the main failure of each of the 27 failing frontier runs from its transcript, without seeing the verdict or the harness. Every label is one of the Appendix G failure modes that the open agents also show. The paper's most common failure, writing the method without checking its output against the paper's numbers, is the main failure in 3 of the 27. In 5, the main failure was never launching an experiment, all on the two Reimplement papers with no released code (2505.16927 and 2503.14698), where the runs reported the missing artifacts and stopped with almost all of their GPU grant unused. Section 5.3 names this pattern.

We keep the thin loop for the main results so that every model runs under one harness. We did not run Claude Code because it bills to Anthropic, and our budget for new runs covered OpenAI and Meta models. Our auditor is itself a Claude model.

### Reply to YGTR, part 2 of 3 (2,429 characters)

**W1, continued: Whether the findings generalize to stronger models.**

The frontier runs cover a frozen subset of papers from every tier, so they test whether the two main findings, the tier ordering and the most common failure, recur for gpt-6-astra, gpt-6.1-sol and Muse Wonder on those papers. [outcome] The main results come from four agents run once per paper on 100 NeurIPS 2025 papers. Each paper has a pinned experiment, the one reported result the agent must reproduce, under a 96 H100-hour cap, and the benchmark excludes papers that need a paid or closed API. Section 5 and the Limitations section state this scope, and the revision adds that the claims hold for these papers and agents.

**W2: Failures due to hardware differences.**

Build failures on our hardware move no best-agent rate by more than one percentage point. Of the 372 graded runs, 24 failed at build or dependency install (13 at Run, 6 at Retrain and 5 at Reimplement). Of these 24, 14 failed on a package with no build for the aarch64 CPUs of our GH200 nodes, 7 on other environment problems and 3 on agent error.

For 12 of the 14 we replayed the install on x86 nodes, and the other 2 have no install command in their transcripts. On x86, 9 of the 12 build and import (95% Wilson interval 47% to 91%). The other 3 fail on x86 too, on a Python or package version conflict, so we do not attribute those 3 to the hardware.

We then dropped all 24 runs from every agent's denominator (Section 5.3). DeepSeek-V4-Flash, the best agent at Run and Retrain, had none of these failures at those tiers, so its rates stay at 13/34 = 38% [24%, 55%] and 9/33 = 27% [15%, 44%]. Muse Spark 1.2, the best at Reimplement, goes from 5/33 = 15% [7%, 31%] to 5/32 = 16% [7%, 32%]. The agent most affected is MiniMax-M2.7 at Run, which goes from 2/34 to 2/26 and is best at no tier. The frontier runs above use the same environment, and [their results].

**W3: Agents are only run once.**

We reran DeepSeek-V4-Flash, the agent with the highest Run and Retrain rates, two more times on 12 papers drawn with a fixed seed, four per tier, and its verdict was the same in all three runs on [k] of the 12. This measures run-to-run variation for that one agent. Its best Run rate moves by [j] papers across the three runs, so the revision ranks two agents only when their 95% Wilson intervals (Section 5.2) stay apart after each count is shifted [j] papers toward the other.

### Reply to YGTR, part 3 of 3 (3,418 characters)

**Q2: Fetching checkpoints over the network.**

A scan of every transcript found two reproduced runs that evaluated a downloaded checkpoint of the claimed model, and the revision counts both as not reproduced.

The harness keeps no network log, so we scanned the transcripts of all 372 graded runs, including the commands, fetched URLs and code the agent wrote, for hf_hub_download, snapshot_download, huggingface-cli, from_pretrained with a repository id, torch.hub, gdown, and wget or curl of weight files. The scan finished on 368 runs and timed out on 4, none of which was reproduced. It cannot see a download made inside an imported library, and Section 5.2 states this limit.

Downloading the released weights is allowed at Run, so what matters is the 42 reproduced runs at Retrain and Reimplement, all scanned, and 16 of them matched a pattern. Reading the 16 by hand, 10 matched text that is not a download, such as an import line, a requirements.txt or a dataset. Another 4 downloaded only a base model that the method starts from, such as the OpenVLA model that CogVLA builds on. In the last 2, Muse Spark 1.2 on CogVLA (2508.21046, Retrain) downloaded a LIBERO-Spatial checkpoint linked from the authors' repository, and MiniMax-M2.7 on CURE (2505.12677, Reimplement) downloaded the authors' erased Stable Diffusion v1.4 weights from their Google Drive folder.

Muse Spark 1.2 now falls from 9 of 33 to 8 of 33 Retrain papers, and MiniMax-M2.7 from 2 of 33 to 1 of 33 Reimplement papers (Section 5.2). The best-agent rates stay at 9 of 33 at Retrain (DeepSeek-V4-Flash) and 5 of 33 at Reimplement (Muse Spark 1.2). CogVLA stays in the Retrain tier, which was fixed before any run, and a footnote in Section 5.2 says that its release includes the claimed checkpoint.

**Q3: Failures that were not the agent's fault.**

We traced 27 of the 400 cells to causes outside the agent: 6 cells with no graded run and 21 graded runs that failed on the environment, the 14 aarch64 builds and 7 other problems of W2, so 6 + 14 + 7 = 27.

We traced all 28 cells with no graded run using the cluster's job accounting and the harness logs. In the 6 that were ours, the four cells of paper 2510.20725 never started because of a bug in our prompt rendering, since fixed, and two audits of Muse Spark 1.2 never returned a verdict. Those two audits now have grades from the same auditor, reproduced (score 8) on 2503.23035 and partial (score 6) on 2510.08177. [We reran the 4 cells of 2510.20725 with the same settings, and r of them reproduce.]

The other 22 remain agent failures, as in the paper. Four of them were finished runs with no auditor grade, and we graded the 3 whose files survive with the same auditor: none is reproduced (scores 0, 2 and 0). Every rate in the revision includes these five new grades. The rest stay agent failures under the paper's rule.

The 76 runs that followed the released pipeline and landed outside tolerance count as not reproduced, because the benchmark grades whether the run recovers the pinned number. To check the environment behind these misses, we re-ran the final commands of 3 of the 76 runs, on 3 papers, with new seeds and no agent. The 2 Retrain papers miss again on both seeds. [Run paper 2506.10351: outcome on both seeds.] The Limitations section states that for these runs agent error cannot be separated from seed and hardware variance.

Thank you again for the review.

### Sources (YGTR)

| Number | File |
| :- | :- |
| 24 build-and-dependency runs; 14 aarch64, 7 other environment (5 labelled plus the 2 not-chip rows), 3 agent error; x86 replay 9 of 12 | rebuttal/results/e8/summary.json (build_dependency_runs.class_counts); e8/README.md; e8/x86/README.md; e8/x86/results.csv (not_arch rows) |
| gpt-6.1-sol in both harnesses, gpt-6-astra in Codex CLI only | rebuttal/PLAN.md:115; rebuttal/results/databook/frontier_cells.csv |
| best Run 13/34 unchanged, Retrain 9/33 (DeepSeek-V4-Flash; Muse 9/33 becomes 8/33 after the checkpoint correction, over the 33 Retrain papers, and 9/32 only when its one build failure is also removed), Reimplement 5/32, MiniMax Run 2/26 (3/26 in e8/bound.csv less minimax-run-2505.23747, e7/rescore_summary.md); table by tier with intervals | rebuttal/results/e8/bound.csv; e8/summary.json (build_dependency_runs.by_tier, bound_best_per_tier_all_env_removed.wilson95); e6/summary.json (settings.S0_index) |
| 13/34 = 38% [24%, 55%], 5/33 = 15% [7%, 31%] | rebuttal/results/e7/rescore_summary.md; e6/summary.json (settings.S0_index) |
| 27 = 6 + 14 + 7 traced outside the agent; 3 of 12 replayed installs fail on x86 | rebuttal/results/e8/summary.json (outside_agent_cells, build_dependency_runs.class_counts A 16, O 5); e8/x86/README.md (2 of the 16 not chip failures, moved to other environment) |
| 76 faithful misses not attributed | paper_latex/iclr2027_conference.tex:584-585 (Limitations) |
| 0.0007 on 2505.17836, 0.28 on 2510.07501, 2506.10351 queued | rebuttal/results/e10/results.md |
| 3 papers re-executed | rebuttal/results/e10/README.md; e10/selection.csv |
| 12 repeat papers, four per tier, two reproduced and two not | rebuttal/subset.json; rebuttal/results/subset/README.md; rebuttal/results/sweeps/jobs.csv |
| 368 of 372 scanned, 4 timeouts not reproduced | rebuttal/results/e9/summary.json (scan_timeouts); viewer index verdicts (partial, not_reproduced, disqualified x2) |
| 42 reproduced Retrain and Reimplement runs, 16 with a hit, 10 / 4 / 2 | rebuttal/results/e9/README.md (13 of 29 plus 3 of 13); e9/class_review.csv |
| 2508.21046 CogVLA and 2505.12677 CURE downloads | rebuttal/results/e9/class_review.csv; rebuttal/STATUS.md (commands.log:483) |
| Muse Retrain 9 to 8, MiniMax Reimplement 2 to 1, best 9/33 and 5/33 | rebuttal/results/e8/summary.json (per_agent_tier) minus the two E9 runs |
| 28 empty cells: 6 outside agent, 22 agent failures (4 of them finished without a grade) | rebuttal/results/e8/summary.json; e8/empty_cells_traced.csv; e8/README.md |
| 4 finished runs with no pinned-auditor grade; 3 regraded at 0, 2 and 0, none reproduced; 2510.19314 no bundle, ungraded | rebuttal/results/e8/d_cells.md; e8/regrade_dcells.json |
| 3 of 12 x86 replays fail on a Python or package version conflict | rebuttal/results/e8/x86/README.md |
| DeepSeek-V4-Flash has no build failure at Run or Retrain (its one is Reimplement) | rebuttal/results/e8/build_failures.csv (dsv4-reimplement-2511.20906) |
| repeat papers: per tier 2 reproduced by some agent, 2 by none | rebuttal/subset.json (rule: within each tier 2 reproduced and 2 not) |
| re-execution targets about 0.05 and -0.20; 0.0395 sits inside 0.0393 to 0.0400 | rebuttal/results/e10/results.md |
| Claude Code left out because it bills to Anthropic; new-run budget OpenAI and Meta only; auditor is Claude Sonnet 5 | rebuttal/PLAN.md:198 and its Budget summary table; paper_latex/iclr2027_conference.tex:389 |
| 27 coded frontier failures; 5 never launched, all on 2505.16927 and 2503.14698, Codex or thin loop, GPU use 0.0027 to 0.0669 H100-hours of 32 or 96; 3 with reimplement-without-validating as main failure; every primary label an Appendix G mode | rebuttal/results/frontier/failure_modes.csv (27 rows, coder claude-sonnet-5, blind to verdict and arm; 6 procrastination/wall-kill); frontier/never_launched_check.md (6cef06 relabeled failed before any number, so 5 of the 6 never launched); frontier/failure_modes.md (open-agent counts for every mode) |
| CogVLA release includes the claimed checkpoint; stays at Retrain | rebuttal/results/e9/class_review.csv (muse-retrain-2508.21046, liwei2013/cogvla_libero_spatial_60000_chkpt); rebuttal/mithil/decisions_monday.md decision 6 |
| 368 scanned, 4 timeouts | rebuttal/results/e9/summary.json (tiers.*.runs_scanned, scan_timeouts) |
| 2503.23035 reproduced (8), 2510.08177 partial (6) | rebuttal/results/e8/regrade_muse.json |
| 12 papers shared by thin and Codex gpt-6.1-sol arms; 9 graded under both; reproduced 3 (thin: 2503.02809, 2504.20571, 2506.20671) and 2 (Codex: 2504.20571, 2505.19087); agree on 6 | rebuttal/results/databook/frontier_cells.csv (arms thin-gpt-6.1-sol, codex-gpt-6.1-sol); rebuttal/subset.json (12 core papers) |
| frontier results, McNemar, budget use, failure-mode shares, blind labels, repeat flips (job 3540624 running, 3540625 to 3540633 pending), 2506.10351 re-execution, 4 reruns of 2510.20725 | pending (E1, E2, E3, E10, E8 reruns of 2510.20725) |

## Risks: where a reviewer could push back

1. **The target check shows 45 of 100 targets failing at least one question (rqBN Q2, T29u Q2).** A reviewer can read 55/100 as evidence that the targets are unreliable. What closes it is Mithil's read of the 45 (rebuttal/results/e7/v3_failures.csv), giving the count the paper actually contradicts, and the rescore of those runs at the corrected targets with the change in best-agent rates. If k is large, the replies should lead with the rescored rates. Settled 11-09 (decisions 1 and 7): the replies name the 8 targets the second pass finds with a wrong number, two verdicts change on 2505.23747, and the counts are 70 of 400 and 13 of 34.
2. **Settled 11-09 (decision 5, Mithil): the replies leave out the 16 stopped cells, and the 22 empty cells outside the six traced to our side stay agent failures as the paper says, since each agent knew its time limit.** The earlier draft admitted that 16 empty cells were stopped by the cluster job (YGTR Q3). This also reverses the 2026-09-10 and 09-19 instructions in memory paper-missing-cells-accounting, so Mithil should decide it before posting. What closes it is the rerun grades of the 20 cells (jobs 3540630 to 3540633, 3540786, 3540787, plus Muse on 2510.20725) and a Section 5.2 sentence that matches the reply.
3. **The confusion matrix comes from an aggregate table, and the paper says 396 hand-graded runs (T29u Q1, rqBN W1).** The matrix Mithil supplied on 11-08 covers the 372 runs with an auditor grade, and its auditor columns match the graded runs exactly, but no per-run label file is on disk. The per-tier reproduced table (e4/per_tier.csv) sums to the matrix totals and its auditor counts match the graded runs per tier (31, 29, 13). Appendix D should say the matrix is over the 372 runs with both grades. The original design has one human label per run, so inter-human agreement cannot be reported; Mithil decided on 11-08 against a second blind grader, so the replies state one label per run and report no inter-human figure.
4. **Codex runs stop early, which a reviewer may call a configuration artifact (YGTR W1).** The first ten frontier runs used a median under 2% of their GPU grant and most ended with "could not run" (rebuttal/results/frontier/run_usage_summary.md), and two cite GPU requests left in the queue. What closes it is the per-run grant use and exit reason in the appendix table, the queue wait per GPU request from run_gpu logs, and, if Mithil approves, a small variant with a fixed number of "continue" prompts.
5. **The two checkpoint downloads came from the authors' own releases, which questions the tier labels of 2508.21046 and 2505.12677 (YGTR Q2).** A Retrain paper with released weights for the claimed model belongs at Run. What closes it is a check of both papers' availability records against the linked checkpoints, and moving the papers if the release covers the claimed configuration. Settled 11-09 (decision 6): CogVLA stays at Retrain with a footnote that its release includes the claimed checkpoint, and CURE is Reimplement, so the rule does not move it.
6. **The hash-chained host log was removed from the rqBN reply (rqBN W1).** No such log exists in the code, and the frontier runs were graded without it, so the reply now promises only the Appendix A rewording and the log comparison that already exist.
7. **The re-execution check covers only 3 papers (rqBN Q1, YGTR W2).** A reviewer can call it too small to bound the environment. What closes it is the two-seed outcome on all 3 (jobs under /work/nvme/bfvr/msalunkhe/rebuttal/e10/state.json) and, if time allows, adding near-miss papers from the 8 to 32 GPU-hour band.
8. **The log check leaves two loose ends (rqBN W1).** The evidence directory's modification time is more than 60 seconds after run end in 63 of 372 runs with no established cause, and the paper says 396 runs started while the check matched 372 graded runs. The 11-08 trace (e5/traces_2026-11-08.md, Trace B) finds the auditor's own writes in 9 directories, only a directory-time change with no changed file in 49 (38 of them dated 2026-10-29, the cleanup day), and 6 files in 5 directories with no writer found. What remains is those 5 directories and the reconciliation of the 24 started but ungraded runs, which the empty-cell trace already covers.
