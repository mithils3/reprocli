# Check of rebuttal/drafts/replies.md against the iclr-review rules

## Point map: concern type (concerns.md) and the move the draft uses

- General, frontier agents: missing_baseline and limitation_or_scope; new experiment (results pending).
- General, repeated runs, auditor and logs, tolerance and targets, outside failures: evaluation_validity; new analysis of existing data plus new experiments (some pending).
- T29u W1, one run per cell and environment sensitivity: evaluation_validity; new analysis (Wilson intervals, build-failure bound, x86 replay) and new experiment (repeat runs, pending).
- T29u W2/Q1, confusion matrix, 7/8 boundary, high-severity flags: evaluation_validity; new analysis (pending) plus two checks that do not use the auditor.
- T29u Q2, match target and 5% tolerance: evaluation_validity; new analysis of existing data (tolerance table, target check), corrections pending.
- rqBN W1, auditor validation: evaluation_validity; new analysis (pending), with concede and scope on the single human label.
- rqBN W1, writable logs: evaluation_validity, plus claim_overstated for the Appendix A sentence; text revision with old and new wording and a new analysis (log comparison).
- rqBN Q1, human-expert baseline: missing_baseline; declined, with indirect evidence (re-execution of 3 papers, build bound).
- rqBN Q2, validation of claims, configurations, targets, tolerances: reproducibility_or_details and evaluation_validity; plain admission, text revision, new analysis (target check, tolerance rescore).
- YGTR W1/Q1, frontier models and production harnesses: missing_baseline (named harnesses) and limitation_or_scope; new experiment (pending), plus level disagreement on keeping the ReAct-style harness for the main results.
- YGTR W2, hardware confounds: evaluation_validity; new analysis and new experiment (x86 replay, re-execution).
- YGTR W2, one run per cell: evaluation_validity; new experiment (repeat runs, pending).
- YGTR Q2, checkpoint downloads: evaluation_validity; new analysis of existing data and two verdicts corrected.
- YGTR Q3, failures outside the agent: evaluation_validity; new analysis (trace of 28 cells), regrades, reruns pending.

## Flags, most consequential first

1. **YGTR Q3 (failures not the agent's fault).** Current: "We traced all 28 cells that produced no graded run, using the cluster's job accounting and the harness logs." Rules 10, 14 and 16: the reviewer asked "how many", the draft has the count, and the paragraph never states it, ending instead on "Among the 372 graded runs, the build and dependency bound above covers the failures the environment caused." Replacement, placed first in the paragraph, with the closing sentence cut: "Yes, and at most 27 of the 400 cells failed for reasons outside the agent, namely 6 of the 28 cells with no graded run and 21 graded runs that failed on the environment (16 aarch64 builds and 5 other environment problems), while 16 further cells were stopped by the cluster job (Section 5.2 and Section 5.3)." Arithmetic: 6 + 16 + 5 = 27, from e8/summary.json (outside_agent_cells, class_counts A 16, O 5). "At most" because 3 of the 12 replayed aarch64 installs also fail on x86.

2. **YGTR W2 (one run per cell).** Current: "Every rate now carries a 95% Wilson interval, and we ran DeepSeek-V4-Flash twice more on 12 papers, four per tier." Rules 10 and 16: the answer is about 60 words with no number outside the bracket, while the T29u reply already has the intervals and the selection rule. Replacement: "Every rate now carries a 95% Wilson interval in Section 5.2, for example 14/34 = 41% [26%, 58%] for the best agent at Run and 5/33 = 15% [7%, 31%] at Reimplement, and we ran DeepSeek-V4-Flash twice more on 12 papers drawn with a fixed seed, four per tier, two of which some agent had reproduced and two of which none had."

3. **YGTR W2 (hardware) and T29u W1 (environment sensitivity).** Current (YGTR): "Removing all 24 from the denominators leaves the best Run-tier rate at 14/34 = 41%, because DeepSeek-V4-Flash had none of these failures at Run, and moves the best Retrain and Reimplement rates by less than one percentage point." Rules 9 and 14: the bound carries a dozen numbers in prose and neither paragraph names its section. Replacement: "Removing all 24 from the denominators moves no best-agent rate by more than one percentage point, because DeepSeek-V4-Flash had none of these failures at Run (Section 5.3):" followed by this table, which can also replace "(to 9/32 and 5/32)" in the T29u paragraph.

   | Tier | Build or dependency failures | Best agent as graded (95% interval) | Best agent with the 24 removed (95% interval) |
   | :- | :- | :- | :- |
   | Run | 13 | 14/34 = 41% [26%, 58%] | 14/34 = 41% [26%, 58%] |
   | Retrain | 6 | 9/33 = 27% [15%, 44%] | 9/32 = 28% [16%, 45%] |
   | Reimplement | 5 | 5/33 = 15% [7%, 31%] | 5/32 = 16% [7%, 32%] |

   Sources: e8/summary.json (build_dependency_runs.by_tier, bound_best_per_tier_all_env_removed.wilson95) and e6/summary.json (settings.S0_index).

4. **YGTR Q3 (the 16 cells stopped by the cluster job).** Current: "Sixteen more stopped before the agent finished, when the cluster job running them reached its 48-hour limit or was cancelled." Rules 6 and 14: this reverses Appendix B's rule that "a cell without a graded run counts as a failure at score 0" (appendix/b_models.tex line 128) and names neither the old rule nor where it changes. Replacement, if Mithil keeps this admission (Risk 2): "Sixteen more stopped before the agent finished, when the cluster job running them reached its 48-hour limit or was cancelled. Appendix B counted every cell without a graded run as a failure at score 0, and the revision replaces those zeros with the grades of the reruns below and states the change in Section 5.2."

5. **T29u W2/Q1 and rqBN W1 (confusion matrix).** Current (T29u): "Appendix D now gives the five-by-five confusion matrix of auditor verdict against human verdict over the [396] hand-graded runs [counts], with precision [x], recall [y] and F1 0.82 on the reproduced verdict." Rule 9: the one result both soundness-2 reviewers asked for is planned as prose. Replacement: "The confusion matrix of auditor verdict against human verdict over the [396] hand-graded runs is below and in Appendix D, with precision [x], recall [y] and F1 0.82 on the reproduced verdict." followed by a five-row table, human verdict down and auditor verdict across (reproduced, partial, not_reproduced, unverifiable, disqualified). The disqualified row and column also answer the high-severity flag question, since score 0 is the high-severity verdict. In rqBN W1, point to the same table.

6. **rqBN W1 (single human label).** Current: "That design does not measure agreement between humans, and the revision says so." Rule 6 (the change has no location) and the evaluation_validity move in concerns.md (concede and scope sits at 21% [5, 42]; new evidence is recommended). Replacement: "That design does not measure agreement between humans, and Appendix D now states this beside the F1." Once the bracketed second-grader sentence that follows has numbers, put it first in the paragraph and cut this sentence, so the answer leads with the new evidence.

7. **rqBN Q1 (re-execution outcome).** Current: "[On k of the 3 the re-run misses again on both seeds, which places those misses with the environment or the paper, and on the other 3 minus k it reaches the target, which points to seed variation or agent error.]" Rule 10: the result exists (rebuttal/results/e10/results.md) and the YGTR reply already reports it. Replacement: "Two of the 3 have finished, and both miss again on both seeds: on 2505.17836 the measured value repeats within 0.0007, which places that miss with the environment or the paper, and on 2510.07501 it moves by 0.28 across seeds, which puts the original near miss inside seed variation, while the jobs for 2506.10351 are queued."

8. **rqBN Q1 (declining the human baseline).** Current: "A stratified human reproduction across the three tiers, under the same environment and budgets, is beyond what we can run, and the Limitations section says so." Rules 12 and 13 and the missing_baseline move: declining a named baseline is needed here, but the sentence asserts it without a fact. Replacement: "A human reproduction across the three tiers under the same environment and budgets would need expert time on each paper plus up to the 2,552 H100-hours we grant one agent over the 100 papers (the 10,208 H100-hours granted over four agents divided by 4), which we cannot run within the discussion period, and the Limitations section says so." Source: paper Section 5.2, "the agents spend 1,888 of the 10,208 H100-hours we granted".

9. **General revision list and YGTR Q2 (checkpoint scan location).** Current (General): "Section 5.3 and Limitations: the hardware bound, the checkpoint scan and the re-execution check, each where its claim is made." Rules 3 and 14: three changes share one bullet, and the YGTR list puts the checkpoint correction in Section 5.2, so the two replies disagree on where it is. Replacement, as three bullets: "Section 5.3: the bound on build failures from the aarch64 hardware, with an x86 replay." / "Section 5.3 and Limitations: the re-execution of missed runs with new seeds." / "Section 5.2: the scan for downloaded checkpoints, with two runs counted as not reproduced." In YGTR Q2, change "The revision counts both as not reproduced, so" to "The revision counts both as not reproduced in Section 5.2, so".

10. **T29u Q2 (tolerance answer sentence).** Current: "Of the 100 claims, 62 are point estimates and 38 are tested by direction or by a threshold (for example "beats the strongest baseline"), which a tolerance does not affect." Rule 14: the answer to "how sensitive" comes only after the table, and the paragraph names no section. Add this sentence before it: "The ordering of the tiers holds at every tolerance from 1% to 10%, and the best agent's count moves by at most 5 papers at Run, 3 at Retrain and 1 at Reimplement (Appendix F and the table below)." Arithmetic from the draft's table: Run 14 at 5% against 9 at 1%, Retrain 9 against 12 at 10%, Reimplement 5 against 4 at 1%.

11. **rqBN Q2 and T29u Q2 (target check results).** Current (rqBN): "The paper reports the frozen value for 92 of 100 targets, for the frozen metric for 95, on the frozen dataset and split for 76, and for the frozen method or variant for 69, and all four hold for 55." Rule 9: five counts in one sentence. Replacement: "The papers supported each part of the frozen target as follows (Appendix E):" followed by a table with rows Value 92, Metric 95, Dataset and split 76, Method or variant 69, All four 55, each of 100. Use the same table in T29u Q2.

12. **rqBN W1 (log comparison counts).** Current: "Of the 45,861 such entries, 45,673 match exactly." and the two sentences after it. Rule 9. Replacement: "The 45,861 entries compare with the host transcript as follows (Appendix A):" followed by a table: Match exactly 45,673; Call refused by the harness, so no cost line 100; Remaining budget within 0.00015 GPU-hours 60; First attempt of a retried call 25; Remaining budget within 0.0003 GPU-hours, cost equal 3; Total 45,861. The rows sum: 45,673 + 100 + 60 + 25 + 3 = 45,861.

13. **rqBN W1 (missing log lines).** Current: "The comparison also found 119 commands in 65 runs that our harness ran but never wrote to commands.log, because two early-return paths in our code skip the log, and the host transcript holds all of them." Rule 6: the sentence finds a fault in the harness and names no change. Replacement: "The comparison also found 119 commands in 65 runs that our harness ran but never wrote to commands.log, because two early-return paths in our code skip the log; the host transcript holds all of them, and Appendix A now reports this gap with its count."

14. **rqBN Q2 (claims and configurations).** Current: "The final construction stage (Stage III, Appendix E) audited only the availability calls, meaning which artifacts each paper's authors released, so the targets had no independent check and there was no annotator agreement to report." Rule 16: the reviewer asked about claims and minimal configurations as well as targets, and the answer covers only targets. Replacement: "The final construction stage (Stage III, Appendix E) audited only the availability calls, meaning which artifacts each paper's authors released, so the claims, minimal configurations and targets had no independent check and there was no annotator agreement to report." After the target check, add: "Its dataset-and-split and method-or-variant questions check the minimal configuration, its value and metric questions check the target, and the choice of claim rests on construction alone, which Appendix E now states."

15. **rqBN W1 and YGTR W2 (shared labels).** Current: "**Writable logs (W1).**" (after "**Auditor validation (W1).**") and "**One run per cell (W2).**" (after "**Hardware and other confounds (W2).**"). Rule 5: two answers carry one label each time. Replacement: "**Auditor validation (W1a).**", "**Writable logs (W1b).**", "**Hardware and other confounds (W2a).**" and "**One run per cell (W2b).**".

The draft already does well on the core rules: T29u and rqBN open with one sentence of thanks and a located change list, every point has a label, the Appendix A before-and-after wording follows the rule 6 frame and rule 7 exactly, the tolerance result is a table, YGTR Q2 opens with its answer and carries its numbers and examples, and no answer disagrees dismissively or without a reason.

## Applied 2026-11-08

1. Applied to YGTR Q3, with the upper-bound reason (3 of the 12 replayed aarch64 installs also fail on x86) written out as its own sentence and the closing sentence cut.
2. Applied to YGTR W2b.
3. Applied to YGTR W2a and to the T29u environment paragraph, where the table replaces "(to 9/32 and 5/32)".
4. Skipped: it depends on Mithil's decision on Risk 2.
5. Skipped: already done, since the T29u reply carries the five-way table.
6. Applied; the second-grader sentence stays a bracketed slot until it has numbers.
7. Adapted: the E10 numbers were confirmed in rebuttal/results/e10/results.md, the reply gives the three measured values for 2505.17836 and shows 0.0400 - 0.0393 = 0.0007, the 0.28 for 2510.07501 is stated as the spread from the original -0.2241 to the seed value +0.0566 (the two new seeds alone differ by less), and 2506.10351 is "queued" because its seeds were resubmitted tonight after the first attempt lacked data. The YGTR W2a bracket on the same check now says the same thing.
8. Applied, with the paper Section 5.2 source in the rqBN Sources table.
9. Applied to the General list (three bullets) and to YGTR Q2.
10. Adapted: the sentence leads the T29u Q2 paragraph with the Run arithmetic (14 at 5% against 9 at 1%), and the repeated "ordering of the tiers holds" clause after the tolerance table was cut.
11. Applied to rqBN Q2 and T29u Q2.
12. Applied to rqBN W1b.
13. Applied.
14. Applied; the added sentence sits right after the target table.
15. Applied.

Character counts after these edits: General 3,957; T29u 2,505 and 4,210; rqBN 4,615 and 3,716; YGTR 4,924 and 3,050. YGTR part 1 has 76 characters left before 5,000, so filling its frontier slots will need tighter wording there.
