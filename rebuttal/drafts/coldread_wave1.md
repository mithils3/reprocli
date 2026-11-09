# Cold read, wave 1: T29u and rqBN replies

Read as an ML reviewer who has read the paper once. Line numbers refer to rebuttal/drafts/replies.md. Bracketed slots and [AUTHOR] notes were skipped. Rewrites keep every number in the source line.

## T29u, part 1 of 2 (lines 49-66): 8 problems

1. Line 58, "**One run per cell (W1).**" The label W1 is our internal review tag. Rewrite: "**One run per cell.**"
2. Line 58, "For the best agent per tier these are 14/34 = 41% [26%, 58%] at Run". The reader cannot tell what 14 and 34 count. Rewrite: "For the best agent per tier, the reproduced count out of its graded Run-tier papers is 14/34 = 41% [26%, 58%]."
3. Line 56, "a bound on build failures from the aarch64 hardware". "Bound" does not say whether it is an upper limit, an estimate, or a range. Rewrite: "an estimate of how much build failures on the aarch64 hardware could move each rate, with an x86 replay of the failed installs."
4. Line 58, "widened by this rate of change". "This rate of change" has no referent in the reply. Rewrite: "widened by the run-to-run change measured with the two extra DeepSeek-V4-Flash runs."
5. Line 58, "Section 5.2 now calls DeepSeek-V4-Flash the agent with the highest mean audit score (5.13 of 10, against 3.03 for MiniMax-M2.7)". "Mean audit score" is never defined, and the sentence runs long. Rewrite: "Section 5.2 now ranks DeepSeek-V4-Flash first by mean LLM auditor score, 5.13 of 10 against 3.03 for MiniMax-M2.7."
6. Line 55, "every frozen target checked against its paper". "Frozen target" is our term and the reply never defines it. Rewrite: "every frozen target (the value, metric, dataset and method each claim is scored against, fixed before any agent ran) checked against its paper."
7. Line 60, "24 of the 372 graded runs ended in a build or dependency failure". Line 70 says the 24 runs outside the graded set are different runs. The reader cannot tell whether the two sets of 24 are the same. Rewrite: "Of the 372 graded runs, 24 ended in a build or dependency failure" and reconcile with line 70 before posting.
8. Line 60, "Removing all 24 from the denominators moves no best-agent rate". The Run denominator stays at 34 in the table, which a reader will find odd. Rewrite: "Removing all 24 from the denominators leaves the best Run rate at 14/34 because DeepSeek-V4-Flash had none of these failures at Run, and moves the other best rates by at most one point."

Three worst: items 7, 2 and 6.

## T29u, part 2 of 2 (lines 68-106): 8 problems

1. Line 70, "**Auditor disagreements, the 7/8 boundary and high-severity flags (W2, Q1).**" W2 and Q1 are our internal review tags. Rewrite: "**Auditor disagreements, the 7/8 boundary and high-severity flags.**"
2. Line 70, "(the other 24 runs that started are not in the graded set)". This conflicts with line 60 (24 failures inside the 372) and with rqBN line 145 (each of the 396 runs that started has a human label). Rewrite: "Of the 396 runs that started, 372 have both grades and form the basis of this table." Then fix the source count.
3. Line 70, "the auditor has precision 64/73 = 88% (95% Wilson interval 78% to 93%), recall 64/83 = 77% (67% to 85%) and F1 0.82, and the two agree on the five-way verdict for 306 of 372 runs." Precision, recall, F1 and "five-way verdict" are never explained, and the sentence is long. Rewrite: "Of the 73 runs the auditor called reproduced, 64 were reproduced by the human too, so precision is 64/73 = 88% (95% Wilson interval 78% to 93%). Recall is 64/83 = 77% (67% to 85%), and F1, the harmonic mean of the two, is 0.82."
4. Line 81, "The rubric gives a score of 0 to any run with a high-severity integrity flag". This term is never defined in the reply. Rewrite: "The rubric scores as 0 any run with a high-severity anti-cheat flag, the flag category the review names."
5. Line 83, "A comparison of the agent's logs with the host transcript found one edited log in 372 runs". "Host transcript" is first used here without a definition. Rewrite: "A comparison of the agent's logs with the host transcript, the harness record kept outside the sandbox, found one edited log in 372 runs."
6. Line 85, "62 are point estimates, and a tolerance does not affect the other 38: 21 are tested by direction, 14 by a threshold ... and 3 in other ways (a range, a magnitude and one with no kind recorded)." "Point estimate" and "tested by direction" are undefined, and "no kind recorded" uses our internal field name. Rewrite: "Of the 100 claims, 62 are point estimates (one reported value) and tolerance applies only to these. The other 38 are tested by direction (21), by a threshold (14), or otherwise (3: a range, a magnitude, and one whose type we did not record)."
7. Line 94, "DeepSeek-V4-Flash measured 90.6 on 2511.19808 against a frozen target of 97.3". The metric is never named, so 90.6 has no unit or meaning. Rewrite: "DeepSeek-V4-Flash measured 90.6 on the metric of 2511.19808 (name it here) against a frozen target of 97.3, a gap of 6.7 / 97.3 = 6.9%."
8. Line 96, "On the match target itself". "Match target" is our term and the reply never defines it. Rewrite: "On the target itself, a model from a different lab than our auditor (OpenAI's gpt-6.1-sol) read each of the 100 papers and checked the frozen target."

Three worst: items 2, 3 and 7.

## rqBN, part 1 of 2 (lines 131-165): 8 problems

1. Line 147, "**Writable logs (W1b).**" W1b is our internal review tag. Rewrite: "**Writable logs.**"
2. Line 145, "In the original study each of the 396 runs that started received one human label". This disagrees with T29u line 70, which says 24 started runs are not in the graded set. Rewrite: "Each of the 396 runs that started received one human label, from three graders who divided the runs, were each blind to the auditor's score, and used the same rubric." Then confirm the 372 versus 396 count.
3. Line 137, "By tier, the errors on the reproduced verdict are as follows:" The table gives precision and recall. "The two" in "the two give the same score to 253 of 372 runs" is also unnamed. Rewrite: "By tier, precision and recall for the reproduced verdict are as follows:" and "On the full 0 to 10 scale, the auditor and the human give the same score for 253 of 372 runs."
4. Line 154, "requiring the same command and return code and, for GPU jobs, the same cost and remaining budget". "Remaining budget" is never defined here, and the sentence is long. Rewrite: "For all 372 graded runs, we matched each logged command against the host transcript, requiring the same command and return code and, for GPU jobs, the same cost and remaining GPU-hour budget."
5. Line 162 (table), "Unmatched: remaining budget differs by up to 0.0003 GPU-hours, cost equal | 3". The reply never says whether these 3 entries are edits, which the table leaves open. Rewrite: add one sentence after the table that states whether the 3 unmatched entries are edits.
6. Line 165, "The comparison also found 119 commands in 65 runs that our harness ran but never wrote to commands.log, because two early-return paths in our code skip the log". The sentence is long and "early-return paths" is code jargon. Rewrite: "The comparison also found 119 commands in 65 runs that the harness ran but did not write to commands.log, because two early-return code paths skip the log."
7. Line 165, "and the auditor graded that run 1 of 10 as unverifiable, so the edit gained nothing". The scale is unexplained, and "gained nothing" reads as dismissive. Rewrite: "and the auditor scored that run 1 of 10 and marked it unverifiable, so the edit did not raise its score."
8. Reviewer point, "An instruction to distrust them does not replace an external append-only or tamper-evident event log." The reply never says whether the host transcript is append-only or tamper-evident, which is what the review asks for. Rewrite: add one sentence that states the host transcript's write protection.

Three worst: items 2, 8 and 5.

## rqBN, part 2 of 2 (lines 169-185): 8 problems

1. Lines 169, 171, "**Human-expert reproduction baseline (Q1).**" and "**How claims, configurations, targets and tolerances were validated (Q2).**" Q1 and Q2 are our review tags. Rewrite: drop the parenthetical tags from both headings.
2. Line 169, reviewer question, "Can the authors provide a stratified human-expert reproduction baseline across Run, Retrain, and Reimplement using the same environment and budgets?" The reply runs no human baseline, and its three re-runs cover one Run paper and two Retrain papers, with no Reimplement paper. Rewrite: "We ran no human-expert baseline in any tier, and the three re-runs cover one Run paper and two Retrain papers, with no Reimplement paper."
3. Line 169, "On 2510.07501 it moves from -0.2241 to -0.1308 and +0.0566, a spread of 0.28 against a target of -0.20, which puts the original near miss inside seed variation." The metric is unnamed, and "a spread of 0.28 against a target of -0.20" compares unlike quantities. Rewrite: "On 2510.07501 (name the metric) the original run gave -0.2241, 0.0241 below the target of -0.20, and the two new seeds gave -0.1308 and +0.0566, a spread of 0.28."
4. Line 169, "On 2505.17836 the measured value is 0.0395 in the original run ... which places that miss with the environment or the paper." The metric and target are unnamed, and "places that miss with" is unclear. Rewrite: "On 2505.17836 (name the metric and target) the original run gave 0.0395 and the new seeds gave 0.0400 and 0.0393, a spread of 0.0007, so the miss reflects the environment or the paper."
5. Line 171, "The claim, minimal configuration and target tuple of each paper were extracted during dataset construction". "Minimal configuration" and "target tuple" are never defined in the reply. Rewrite: "The claim, the minimal configuration (the setup the claim needs), and the target of each paper were extracted during dataset construction and frozen before any agent ran."
6. Line 171, "audited only the availability calls". "Availability calls" and "Stage III" are our internal terms. Rewrite: "The final construction stage (Stage III, Appendix E) checked only which artifacts the authors released, so the claims, minimal configurations and targets had no independent check."
7. Line 173, "We have now checked them." Line 183 then says the claim choice "rests on construction alone," so "them" overstates the check. Rewrite: "We have now checked the targets and minimal configurations, and the choice of claim still rests on construction alone."
8. Line 183, "Because the checking model saw the frozen tuple, this is a check of each target against its paper, and we describe it that way." "Frozen tuple" is our term. Rewrite: "The checking model saw the frozen target when it answered, so this is a check of each target against its paper, and we describe it that way."


## Applied 2026-11-08

Tally: 12 applied, 14 adapted, 6 rejected. Line numbers are those of the cold read.

T29u, part 1
1. Rejected: the W and Q labels map each answer to the reviewer's point, which the iclr-review skill (rule 5) keeps.
2. Adapted: 34 counts every Run paper (empty cells score 0), so the sentence reads "the papers it reproduced out of the papers in that tier", and 73/400 is now "73 of the 400 agent-paper cells".
3. Adapted: the bullet now reads "how much build failures on the aarch64 hardware move the best-agent rates".
4. Applied: "widened by the run-to-run change these repeat runs measure".
5. Adapted: kept the paper's term "mean audit score" and added "on the 0 to 10 rubric".
6. Adapted: frozen target defined in the bullet as the value, metric, dataset and configuration fixed for each claim before any agent ran.
7. Applied: "Of the 372 graded runs, 24 ended in a build or dependency failure"; line 70 now names the other 24 as started runs with a human label and no auditor grade.
8. Adapted: "Removing these 24 runs from each agent's own denominator leaves the best Run rate at 14/34 ... and moves the other best-agent rates by less than one percentage point."

T29u, part 2
1. Rejected: same reason as part 1 item 1.
2. Adapted: "It covers the 372 runs that have both grades, since the 396 runs that started include 24 with a human label but no auditor grade."
3. Adapted: split into two sentences that say what precision counts and name the five verdicts of the table; F1 is left undefined for an ML reviewer.
4. Rejected: "high-severity integrity flags" is the reviewer's own wording.
5. Applied: the host transcript is the record the harness writes outside the agent's sandbox.
6. Adapted: rewritten as suggested, and the example moved to direction, since e6/README.md files "beat a baseline" under direction and gives threshold as a floor or ceiling.
7. Applied: "90.6% test accuracy on CIFAR10-IDN" against 97.3% (e7/comparison.csv).
8. Adapted: kept the reviewer's "match target" and opened the section with a definition of the frozen target.

rqBN, part 1
1. Rejected: same reason as T29u item 1.
2. Applied: three graders divided the 396 started runs, one label each, and the matrix covers the 372 of these with an auditor grade.
3. Applied: "precision, recall and F1 on the reproduced verdict" and "the auditor and the human".
4. Applied: "remaining GPU-hour budget".
5. Applied: all 3 unmatched entries are in trajectory.jsonl, which no agent command wrote to, so none is an agent edit; the cause of the budget difference is stated as not yet traced (e5/README.md).
6. Adapted: "two code paths in the harness return before writing the log", and the sentence is split.
7. Applied: "scored that run 1 of 10, the rubric's unverifiable grade, so the edit did not raise its score".
8. Applied: the host transcript is not hash-chained and so not tamper-evident by construction; its protection is that it lies outside every sandbox mount (Risks item 6, e5/README.md).

rqBN, part 2
1. Rejected: same reason as T29u item 1.
2. Adapted: Q1 now opens "We did not run a human-expert baseline in any tier, and the Limitations section states this", and a new sentence says no Reimplement paper can enter the re-execution because that tier releases no code (e10/README.md selection covers Run and Retrain only).
3. Adapted: metric named (bias, target -0.20), and the 0.28 is the span of all three values, 0.0566 - (-0.2241); the suggested "two new seeds ... spread of 0.28" is wrong, since the two seeds alone span 0.19.
4. Adapted: metric named (GoRank mean relative error at 80k steps, target about 0.05, e10/results.md), and the conclusion now says the same commands miss by the same amount without the agent.
5. Rejected: "minimal configuration" and "target tuple" are the reviewer's words in Q2; a sentence now defines the frozen target as the two together.
6. Adapted: "checked only which artifacts each paper's authors released", keeping the Stage III pointer.
7. Applied: "We have now checked the targets and minimal configurations against the papers."
8. Applied: "The checking model saw the frozen target when it answered".

Also done: 14/34 and its kind of count are stated at first use in each part, long sentences touched here are split under about 40 words, Sources tables carry every new number, and heading counts are updated (T29u 3,030 and 4,669; rqBN 4,975 and 4,219). General and YGTR are unchanged.
