# Cold read, wave 1, v2 (T29u and rqBN)

Read as the reviewer, from the review plus post/general.md and the reviewer's own reply files only. Slots in brackets are treated as unknown.

## T29u (rating 3, weak accept)

### 1. Weaknesses and questions

- W1, one run per cell: answered in part. "Its verdict was the same in all three runs on k of 12 papers (95% interval [lo, hi]), so run-to-run variation moves the best Run rate by at most j papers" is the answer, and it is a slot, so I cannot judge it. The rest ("Every rate in the revision carries a 95% Wilson interval", "14/34 = 41% [26%, 58%]") answers the point-estimate complaint. The repeat covers one agent and 12 papers, and the reply says so.
- W1, environment sensitivity: answered. "removing the 24 runs that ended in a build or dependency failure moves no best-agent rate by more than one percentage point".
- W2, closer audit of disagreements: answered. "Of the 28 runs where only one grader called the result reproduced, the human did in 19 and the auditor in 9."
- Q1, confusion matrix: answered for the reproduced boundary. The 5x5 table is there, and "they agree on 75 about which side of the reproduced line the run falls" covers 7/8. High-severity flags are covered only by "they agree on 42" of 57 runs scored 0. That is agreement on a score of 0, not on each anti-cheat flag, so the flag part is half answered.
- Q2, sensitivity to target and 5% tolerance: answered on tolerance ("reproduces 9, 12, 14 and 14 of the 34 Run papers" and the ordering holds). The match-target half is passed to another reviewer ("Our reply to Reviewer rqBN (Q2) gives the full result"), which I would not open.

### 2. Unclear on a first read

1. "The revision compares the reproduction rates of two agents only where their intervals, widened by the run-to-run change these repeat runs measure, do not overlap." I could not tell what widened means or by how much, and the number it depends on is a slot.
2. "The matrix covers the 372 runs that have both grades, since the 396 runs that started include 24 with a human label but no auditor grade." Three counts (400 cells, 396 started, 372 graded) appear with no bridge, and the 24 here is easy to confuse with the 24 build failures in W1. I also read "73 of the 400 cells" next to "372 runs" and wondered whether the 28 ungraded cells were counted as not reproduced. The sentence "so the paper's reproduction counts are, if anything, low" depends on that.

Also minor: the table headers "Unverifiable (1)" and "Disqualified (0)" are scores whose meaning I only get from the later "high-severity integrity flag" sentence.

### 3. Score

Keep at 3, with a raise to 4 possible. The deciding point is the repeat-run slot: if the verdict is the same in most of the 12 papers and the tier ordering holds in every run, my soundness concern is met. If the verdict flips on a third of the papers, I would keep 3 and ask for the ranking claims to be softened.

## rqBN (rating 3, weak accept)

### 1. Weaknesses and questions

- W1, auditor validation (confusion matrix, precision, recall, tier-conditioned errors): answered. "on the reproduced verdict it has precision 64/73 = 88% and recall 64/83 = 77%" plus the per-tier table. The full matrix is only linked ("our reply to Reviewer T29u (Q1) shows the full confusion matrix"), which sends me to a thread that is not mine.
- W1, multi-human adjudication: conceded, not fixed. "That design does not measure agreement between humans, and Appendix D now states this beside the F1." That is an honest answer and I accept it as a limitation.
- W1, validation of the full 0 to 10 scale and anti-cheat flags: answered for the scale ("the same score to 253 of 372 runs and scores within one point to 324"). For flags only "the two agree on 42 of the 57 runs that either placed at 0", which validates the zero grade and not each flag type.
- W2, writable logs: answered and well. "Yes, the agent's shell could have rewritten both logs", then the before and after text, then "Of these, 45,673 match exactly". The reply also admits the host transcript is not hash-chained, which I respect.
- Q1, human-expert baseline: not run ("We did not run a human-expert baseline in any tier"). The substitute is a re-execution with new seeds on 3 papers. It answers a different question (environment-only misses), and the third example is a slot.
- Q2, validation of claims, configurations, targets, tolerances, annotator agreement: answered. "One author reviewed every extracted field before the dataset was frozen and no second person did, so there is no annotator agreement to report." The model check gives "all four for 55" of 100, which is a weak result, and the corrected-target outcome is a slot.

### 2. Unclear on a first read

1. "Of these, 45,673 match exactly, 100 are calls the harness refused and so carry no cost line, 60 differ in remaining budget by at most 0.00015 GPU-hours, 25 are first attempts of a retried call, and 3 are unmatched because the remaining budget was logged before the GPU release charge". These sum to 45,861 but the reply never says so, and the last two categories read like jargon, so I could not tell if 85 entries were an unexplained gap.
2. "so the same commands miss by the same amount without the agent, which places the cause in the environment or the paper." I could not tell what this implies for the human baseline I asked for, and the reply never ties the three papers back to Q1. "Stage III" in the Q2 reply is also undefined for a reader without Appendix E.

### 3. Score

Keep at 3, no raise yet. The deciding point is the corrected-target slot: only 55 of 100 frozen targets pass all four questions, and if an author reading of the 45 failures finds many true errors that change verdicts, I would need the headline rates restated before moving up. If few are real errors and the best-agent rates move by about one paper per tier, I would raise to 4. Lowering is unlikely, because the log check and the confusion matrix both landed.

## Editor: smallest wording fixes (numbers unchanged)

T29u_1
- Old: "The revision compares the reproduction rates of two agents only where their intervals, widened by the run-to-run change these repeat runs measure, do not overlap, and it says that the measurement covers one agent."
  New: "The revision calls one agent better than another only when their 95% intervals do not overlap even after each interval is made wider by the j papers of run-to-run change measured here, and it says that this change was measured for one agent only."
- Old: "The matrix covers the 372 runs that have both grades, since the 396 runs that started include 24 with a human label but no auditor grade."
  New: "The matrix covers the 372 runs that have both grades. Of the 400 agent-paper cells, 396 started a run and 4 never did, and 24 of the 396 have a human label but no auditor grade, which leaves 372 (these 24 are separate from the 24 build failures above)."
- Old: "so the paper's reproduction counts are, if anything, low."
  New: "so the 73 reproductions in the paper are a slight undercount relative to the human grade."
- Old: "| Unverifiable (1) | Disqualified (0) |"
  New: "| Unverifiable (score 1: no evidence to check) | Disqualified (score 0: high-severity integrity flag) |"
- Old: "Our reply to Reviewer rqBN (Q2) gives the full result and the corrections that follow from it."
  New: "The full result, with the corrections that follow, is: all four parts are supported for 55 of the 100 claims, and the value for 92, the metric for 95, the dataset and split for 76 and the method or variant for 69 (Appendix E)."

rqBN_1
- Old: "and our reply to Reviewer T29u (Q1) shows the full confusion matrix that Appendix D now gives."
  New: "and Appendix D now gives the full five-by-five confusion matrix of auditor against human verdict, which our reply to Reviewer T29u (Q1) reproduces."
- Old: "Of these, 45,673 match exactly, 100 are calls the harness refused and so carry no cost line, 60 differ in remaining budget by at most 0.00015 GPU-hours, 25 are first attempts of a retried call, and 3 are unmatched because the remaining budget was logged before the GPU release charge, a gap of up to 0.0003 GPU-hours with the cost equal (Appendix A)."
  New: "Of these, 45,673 match exactly, and the other 188 fall into four harmless groups: 100 are calls the harness refused, which have no cost line; 60 differ in the remaining budget by at most 0.00015 GPU-hours; 25 are first attempts of a call the agent then retried; and 3 differ by at most 0.0003 GPU-hours because the budget was logged before the GPU release charge, with the same cost (Appendix A)."
- Old: "the two agree on 42 of the 57 runs that either placed at 0."
  New: "the two agree on 42 of the 57 runs that either placed at 0, which checks the integrity-flag outcome as a whole and not each flag type."

rqBN_2
- Old: "so the same commands miss by the same amount without the agent, which places the cause in the environment or the paper."
  New: "so the same commands miss by the same amount without the agent. This is the part of a human baseline we could measure: it shows which misses an expert following the same pipeline would also have."

rqBN_3
- Old: "the final construction stage (Stage III, Appendix E)"
  New: "the last of the three construction stages (Stage III, Appendix E)"
