# Area chair reading, 2026-11-16

## 1. Draft meta-review

The paper presents a benchmark of 100 NeurIPS 2025 papers on which an agent must reproduce one fixed result per paper, graded by an LLM auditor from execution logs. The reviewers rated it 3, 3 and 2 out of 4 and agreed that the design is careful. They asked about single runs, auditor validation, agent-writable logs, missing frontier models and harnesses, and attribution of failures. The response adds confidence intervals, repeat runs, a human-against-auditor confusion matrix on 372 runs, a log comparison against an external database, and 57 frontier runs. I consider the log and auditor concerns largely answered. The frontier evidence covers 24 preselected papers with uneven arms, and target validation rests on one author and one LLM check. Lean: borderline, tilting to accept, because the two positive reviewers' concerns are met with data while the negative reviewer's main objection is answered in part and that reviewer has not confirmed it.

## 2. Weaknesses still standing

1. **The frontier models reproduce fewer papers than the open agents because they stop early, and the test of that stopping covers three papers.** Reviewer YGTR (W1, Q1). YGTR_1.md line 32: "On 3 papers it spent more of its grant and received the same scores as the unprompted runs (8, 8 and 7)." Table 8 (Appendix B.3) shows two of those three were already reproduced without the prompt, so the test reaches no run that stopped early. Closes with: the continue prompt on five to eight failed runs that stopped early, such as 2506.08898 and 2504.12463.

2. **The headline failure finding describes the four open agents only.** YGTR (W1). YGTR_1.md line 30: "Two of our findings carry over to the frontier models, and the main failure mode changes." The abstract still states "The most common agent error is writing the method without checking any part against the paper's numbers, in 63 of 400 runs." Closes with: wording that scopes this sentence to the four open agents and names early stopping for the frontier runs.

3. **Targets were set by one author and checked by one LLM, and the comments report the most favourable row of that check.** Reviewer rqBN (Q2), T29u (Q2). rqBN_1.md line 21: "It confirmed our value for 92 of the 100 claims (Appendix E), which is the agreement between our targets and an independent reader." Appendix E.6 says "Of the 100 targets, 55 pass all four questions" and that on 16 "a setting or label is off", with no correction stated. Closes with: tier rates on the 55 fully supported papers, from existing grades.

4. **No human reproduction exists, so a faithful miss cannot be assigned to the agent or to the paper.** rqBN (Q1), YGTR (Q3). rqBN_1.md line 16: "Each target is technically an expert result already" which holds on the original authors' setup only. YGTR_2.md line 32: "In all three, the agent's number is what the released pipeline gives", which suggests part of the 76 faithful misses are not agent errors. Closes with: best-agent rates with all 76 such cells removed from the denominators, as a bound.

5. **Each run has one human label.** rqBN (W1). rqBN_1.md line 5: "Three human graders scored the runs, one grader per run". Appendix D says the study "does not measure agreement between humans". Closes with: a second blind grader on 50 of the 100 runs scored 7 or 8, with agreement reported.

6. **Scope of one venue and year has no reply.** T29u (W1). T29u_1.md line 5 answers "one run per cell" and has no sentence on "one venue/year". Closes with: two sentences to T29u quoting the Scope paragraph of Section 6.

## 3. Cross-comment mismatches

- Target check. general.md line 6: "It supports 92 of the 100". PDF Table 15, Appendix E.6: "All four 55".
- Paper 2506.08898. YGTR_1.md line 37, citing Section 5.3: "three runs projected 33 to 51 hours of retraining and stopped". PDF Section 5.3: "5 of 6 frontier runs stopped under one H100-hour of a 32-hour grant because no matching checkpoint is released".
- Ungraded cells. YGTR_2.md line 23: "6 cells with no graded run". PDF Section 5.2: "Of the 400 cells, 28 produced no graded run". general.md line 15 lists two late audits; Section 5.2 says the auditor "has since graded five of the 28".
- Repeat runs. general.md line 3 cites Section 5.2 for "23 of 27 model and paper pairs". Section 5.2 gives only 9 of 10 and 7 of 9; the pooled figure and YGTR_2.md line 11 "7 keep their verdict" are absent from the PDF.
- Frontier coverage. PDF Section 5.1: "we also ran gpt-6-astra and gpt-6.1-sol ... on 24 papers". YGTR_1.md table: gpt-6-astra on 8 and 6 papers.
- Reruns. rqBN_1.md line 17: "On two papers our reruns repeat the agent's number". YGTR_2.md line 32: "In all three".
- Inside the PDF. The introduction says of the 96-hour band "1 of them reproduces its claim"; Section 5.4 says "none of them reproduces its claim".

## 4. Best remaining moves

1. Run the continue prompt on the failed frontier runs that stopped early and post the result to YGTR with the scoped abstract sentence, since this alone addresses the one negative rating.
2. Post to rqBN the tier rates on the 55 fully supported targets and what was done with the 16, since a reader who opens Table 15 after reading "92 of the 100" will discount the other numbers.
3. Upload a PDF that removes every mismatch in part 3 and adds the bound of weakness 4.
4. A message to the silent reviewers is worth posting once, about a day before closing, in at most three sentences per reviewer: name the analysis that answers their main concern, give its number, and ask whether anything remains open. It should not ask for a higher rating, repeat the response, mention other reviewers' ratings, or state anything missing from the PDF.
