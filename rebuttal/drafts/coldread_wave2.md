# Cold read, wave 2: General reply and the two YGTR replies

Source: rebuttal/drafts/replies.md (line numbers refer to it). Review: rebuttal/reviews-2026-11-06.md lines 41 to 54. Bracketed slots and [AUTHOR] notes are ignored. Rewrites keep every number.

## General reply (replies.md lines 9 to 31)

1. Line 31: "A scan of every transcript for model downloads found 2 reproduced Retrain or Reimplement runs that evaluated a downloaded checkpoint of the claimed model."
Problem: "every transcript" contradicts YGTR part 2 (line 242), which says the scan finished on 368 of the 372 graded runs.
Rewrite: A scan of the transcripts for model downloads finished on 368 of the 372 graded runs and found 2 reproduced Retrain or Reimplement runs that evaluated a downloaded checkpoint of the claimed model.

2. Line 31: "We traced all 28 cells that produced no graded run. Six failed for reasons outside the agent, and 16 more stopped when the cluster job running them reached its 48-hour limit or was cancelled."
Problem: 6 plus 16 gives 22 of 28, so the reader asks about the other 6. YGTR part 2 (line 244) accounts for them as 2 with a full context and 4 finished runs with no logged reason.
Rewrite: We traced all 28 cells that produced no graded run: 6 failed for reasons outside the agent, 16 stopped when the cluster job reached its 48-hour limit or was cancelled, 2 ended when the agent's context filled, and 4 finished runs have no logged reason.

3. Line 23: "Both gpt-6.1-sol and Muse Wonder ran in our ReAct-style harness and in a production harness (Codex CLI for gpt-6.1-sol, mini-SWE-agent for Muse Wonder)..."
Problem: "ReAct-style harness", "production harness", "Codex CLI" and "mini-SWE-agent" are not explained in this section, so a reader of the General reply cannot tell what differs between the two harnesses. The paper calls our loop a thin ReAct-style agent loop (paper_latex/iclr2027_conference.tex line 425).
Rewrite: Both gpt-6.1-sol and Muse Wonder ran in our thin ReAct-style agent loop and in a production coding agent (Codex CLI for gpt-6.1-sol, mini-SWE-agent for Muse Wonder), and gpt-6-astra ran in Codex CLI only, all with the same sandbox, task text, GPU grant and auditor.

4. Line 25: "Every rate now carries a 95% Wilson interval, for example 14/34 = 41% [26%, 58%] for the best agent at the Run tier."
Problem: the best agent is not named, and 14/34 does not say what is counted. The denominator is the Run-tier cells for that agent.
Rewrite: Every rate now carries a 95% Wilson interval; for example, [best Run agent] reproduced 14 of its 34 Run-tier cells (41%, interval 26% to 58%).

5. Line 25: "We also queued two more runs of DeepSeek-V4-Flash on each of 12 of those papers..."
Problem: "those papers" has no antecedent in this section, and DeepSeek-V4-Flash is never introduced here.
Rewrite: We also queued two more DeepSeek-V4-Flash runs on each of 12 papers drawn with a fixed seed, four per tier.

6. Line 27: "Appendix D now gives the confusion matrix ... and the auditor is the stricter of the two, with 73 reproductions against the humans' 83."
Problem: 51 words. The base of the 73 and 83 is not stated. The paper says the auditor confirms reproduction on 73 of the 400 cells (paper_latex/iclr2027_conference.tex line 461), so a reader sees two bases. The matrix over 372 runs does agree with precision 88%, recall 77% and F1 0.82 (64 agreeing reproductions), so only the base needs stating.
Rewrite: Appendix D gives the confusion matrix over the 372 runs with both grades: the auditor reproduces 73 runs and the human grader 83, with precision 88%, recall 77% and F1 0.82 on the reproduced verdict.

7. Line 27: "One run of the 372 overwrote its commands.log, and the auditor had graded that run 1 of 10 as unverifiable, so the edit gained it nothing."
Problem: "1 of 10" gives no scale, "the edit" is vague, and "gained it nothing" is informal. The sentence admits that a run changed the log the auditor reads, and a reviewer will want the result stated plainly.
Rewrite: One of the 372 runs overwrote its commands.log; the auditor scored that run 1 of 10 on its 0 to 10 scale and marked it unverifiable, so the overwrite did not earn it a reproduction.

8. Line 29: "Moving the default tolerance anywhere from 1% to 10% changes the best agent's count by at most 5 papers at Run (14 at 5% against 9 at 1%), 3 at Retrain and 1 at Reimplement, and the ordering of the tiers holds at every setting we tried."
Problem: the example compares 5% with 1%, but the claimed range runs to 10%, and no 10% count is given. The best agent is not named, and the tier ordering claim has no pointer. The sentence is 50 words.
Rewrite: Across default tolerances from 1% to 10%, the best Run agent's count moves by at most 5 papers (14 at the default 5%, 9 at 1%), by at most 3 at Retrain and 1 at Reimplement, and the tier ordering holds at every setting (Appendix F tolerance table).

## Reply to YGTR, part 1 (replies.md lines 214 to 238)

1. Lines 222, 228 and 238: "**Frontier models and production harnesses (W1, Q1).**", "**Hardware and other confounds (W2a).**", "**One run per cell (W2b).**"
Problem: W1, W2a and W2b are our own labels. The review does not number its weaknesses, so the reviewer cannot map them. Q1 is fine because the review numbers its questions.
Rewrite: Use "(your weakness on harnesses, and question 1)", "(your weakness on confounds)" and "(your weakness on single runs)" as the headings.

2. Line 222: "A Codex run ends when Codex ends its own turn, which is the same stopping rule our harness uses."
Problem: a claim with no pointer. Our internal risk notes say the first ten frontier runs used a median under 2% of their GPU grant, so a reviewer will check this sentence against the run logs.
Rewrite: A Codex run ends when Codex ends its own turn, the same stopping rule our harness uses; the per-run exit reason and grant use are in the new appendix table.

3. Line 222: "The most common failure in the paper, writing the method without checking its output against the paper's numbers, occurs in [k] of the frontier agents' [m] failing runs, labeled with the same procedure as the paper's runs, and an author's blind labels agree with that procedure on [x] of 20 runs."
Problem: 50 words in one sentence. The "same procedure" clauses are hard to follow, and "[x] of 20 runs" does not say which runs.
Rewrite: The paper's most common failure, writing the method without checking its output against the paper's numbers, appears in [k] of the [m] failing frontier runs, and an author's blind labels agree with the paper's labeling on [x] of 20 runs.

4. Line 226: "We keep the ReAct-style harness for the main results because it treats every model in the same way, and the new appendix section reports what a production harness changes."
Problem: defensive, and it skips the reviewer's point. The review calls the loop very minimal and names Claude Code, which this reply never runs.
Rewrite: We keep the thin ReAct-style loop for the main results so that every model runs under one harness; the new appendix section runs Codex CLI and mini-SWE-agent and reports how the results change.

5. Line 228: "First, 24 of the 372 graded runs ended in a build or dependency failure, and our reading of their transcripts traces 14 of them to a package with no build for the aarch64 CPUs of our GH200 nodes, 7 to other environment problems and 3 to agent error." Also line 228: "For the 12 of the 14 with a replayable install command, we re-ran the install on x86 nodes, and 9 of 12 build and import (95% Wilson interval 47% to 91%)."
Problem: the first sentence is 48 words. "replayable" is our term, and "9 of 12 build and import" does not say what 9 of 12 counts.
Rewrite: First, 24 of the 372 graded runs failed at build or dependency install: 14 on a package with no build for the aarch64 CPUs of our GH200 nodes, 7 on other environment problems and 3 on agent error. For 12 of those 14 whose install command we could replay, we reran the install on x86 nodes, and 9 of the 12 installs succeeded (95% Wilson interval 47% to 91%).

6. Line 228: "Removing all 24 from the denominators moves no best-agent rate by more than one percentage point, because DeepSeek-V4-Flash had none of these failures at Run (Section 5.3):"
Problem: the "because" covers only the Run tier. The table rows for Retrain (6 failures) and Reimplement (5 failures) need the same reason, and the table names no best agent at any tier.
Rewrite: Removing all 24 from the denominators moves no best-agent rate by more than one percentage point (table below); the table names each tier's best agent and states that agent's build-failure count at each tier.

7. Line 236: "Second, we re-ran the final command sequence of runs that followed the released pipeline and still missed, on the same nodes with two new seeds and no model in the loop. ... the measured value repeating within 0.0007 on 2505.17836 and spreading by 0.28 on 2510.07501..."
Problem: "final command sequence", "single clean command chain" and "no model in the loop" are internal phrasing. The 0.0007 and 0.28 have no metric and no target, so a reader cannot tell whether 0.28 is large. The sources table gives the targets as about 0.05 for 2505.17836 and -0.20 for 2510.07501 (replies.md line 206).
Rewrite: Second, we re-ran the last command sequence of 3 papers whose runs followed the released pipeline and still missed, on the same nodes with two new seeds and no agent; across seeds the measured value varies by 0.0007 on 2505.17836 (target about 0.05) and by 0.28 on 2510.07501 (target -0.20).

8. Line 238: "we queued two more runs of DeepSeek-V4-Flash on 12 papers drawn with a fixed seed, four per tier, two of which some agent had reproduced and two of which none had."
Problem: "two of which" could mean two per tier or two in total. The sentence also says "queued", so a reader cannot tell whether a result exists.
Rewrite: ...on 12 papers drawn with a fixed seed, four per tier; in each tier, two of the four were reproduced by some agent and two by none [confirm per tier or in total].

Reviewer points this part does not answer:
- Claude Code. The review names Claude Code, Codex and mini-SWE-agent as the harnesses a researcher would use. The reply runs Codex CLI and mini-SWE-agent and says nothing about Claude Code.
- Failure modes. The review says the failure modes "would change significantly" under a better harness. The reply reports one failure share but does not compare the mix of failure modes with the open agents.
- Minimal loop. The review calls the ReAct loop very minimal for long tasks. The reply defends it on consistency only.

## Reply to YGTR, part 2 (replies.md lines 240 to 246)

1. Line 242: "The scan finished on 368 of the 372 graded runs, and none of the 4 it could not finish was reproduced."
Problem: "finished" is unclear, and the sentence contradicts the General reply, which says "every transcript".
Rewrite: The scan could not finish on 4 of the 372 graded runs, and none of those 4 was reproduced.

2. Line 242: "...so Muse Spark's Retrain count goes from 9/33 to 8/33 and MiniMax-M2.7's Reimplement count from 2/33 to 1/33, while the best-agent rates stay at 9/33 at Retrain (DeepSeek-V4-Flash) and 5/33 at Reimplement (Muse Spark)."
Problem: the counts do not say what they count, and the 9/33 for Muse Spark sits next to the 9/33 for the best agent, which a reader can confuse. The sentence is 44 words, so it is dense.
Rewrite: Muse Spark's count of reproduced Retrain cells falls from 9 of 33 to 8 of 33, and MiniMax-M2.7's count of reproduced Reimplement cells falls from 2 of 33 to 1 of 33. The best-agent rates stay at 9 of 33 at Retrain (DeepSeek-V4-Flash) and 5 of 33 at Reimplement (Muse Spark).

3. Line 242: "The scan cannot see a download made inside an imported library, and the revision states that limit."
Problem: no pointer to where the limit is stated. The General reply puts the scan in Section 5.2, so confirm that the limit sentence is there.
Rewrite: The scan cannot see a download made inside an imported library (Section 5.2 states this limit).

4. Line 244: "...while 16 further cells were stopped by the cluster job (Section 5.2 and Section 5.3)."
Problem: "further" says the 16 are outside the 27, but they are among the 28 cells with no graded run. As written, the counts add up to 43.
Rewrite: ...and 16 of the 28 cells with no graded run stopped when the cluster job reached its 48-hour limit or was cancelled (Sections 5.2 and 5.3).

5. Line 244: "The 27 is the count we could trace and does not bound the failures outside the agent, because the 76 runs that ran a faithful pipeline and still missed are not in it, and the Limitations section says that for them we cannot separate agent error from seed and hardware variance."
Problem: 51 words. The number 76 appears for the first time here, and "faithful pipeline" is undefined.
Rewrite: The 27 is the count we could trace; it does not bound failures outside the agent, since 76 runs that followed the released pipeline and still missed are excluded, and the Limitations section explains that for them agent error and seed and hardware variance cannot be separated.

6. Line 244: "the four cells of paper 2510.20725 never started because of a bug in our prompt rendering, since fixed"
Problem: the reply does not say whether these four cells were rerun and graded, and a reviewer will ask.
Rewrite: ...never started because of a bug in our prompt rendering, since fixed; [state whether these four cells are among the rerun cells].

7. Line 244: "for 4 finished runs the logs do not record why they are missing from the graded set."
Problem: the reply then says "Every rate in the revision includes these grades", yet four runs have no reason. The General reply leaves these four out.
Rewrite: for 4 finished runs our logs give no reason they are missing from the graded set; [list their IDs and what was done].

8. Line 246: "We would be glad to hear whether the frontier and harness results address the concern about generalization behind your informativeness score."
Problem: the review never states an informativeness concern. Its closest text is "it is not obvious that any claimed findings/results would generalize". Attributing the score to that concern is presumptuous.
Rewrite: Please tell us whether the frontier and harness results address your concern that the tested models are too weak for the findings to generalize.

Reviewer points this part does not answer:
- Generalization beyond the benchmark. The review says it is not obvious that the findings generalize. The reply runs 3 frontier models on [n] and [m] papers and does not state what the benchmark covers beyond its 100 NeurIPS 2025 papers.
- Tier labels (our judgment, not in the review). The authors released the checkpoints for CogVLA and CURE. A reviewer may ask why these two papers stay at Retrain and Reimplement. Internal risk 5 lists this.

## Numbers that differ between the General reply and the YGTR parts

- Scan coverage: General line 31 says "every transcript". YGTR part 2 line 242 says 368 of 372 graded runs.
- No-graded-run accounting: General line 31 gives 6 and 16 (22 of 28). YGTR part 2 line 244 gives 6, 16, 2 and 4 (28 of 28).
- Auditor counts: General line 27 gives 73 and 83 over the 372 runs with both grades. Paper line 461 gives 73 of the 400 cells. State the base.
- Muse Wonder: General line 23 says [m] papers. YGTR part 1 line 224 says "Muse Wonder d of 12". Confirm m is 12, or fix the "same 12 papers" wording.
- Build failures: YGTR part 2 counts 14 aarch64 builds as outside the agent (line 244), but part 1 says 3 of the 12 replayed installs still fail on x86 and their cause is still open (line 244). The 27 should not count those 3 as traced.
- Matching values: 14/34, 9/33, 5/33, the 2 downloaded-checkpoint runs, 24 build failures, F1 0.82 and the two audit scores agree across both parts.

## Applied 2026-11-08

Totals over the 24 flagged sentences, the 5 unanswered points and the 5 cross-part numbers: 11 applied, 20 adapted, 3 rejected. Character counts after the edits: General 4,561, YGTR part 1 4,972, YGTR part 2 3,599. The wave-1 parts (T29u, rqBN) are unchanged, and no part of General or YGTR ranks agents by mean audit score, so the T29u means need no echo here.

General reply
1. Applied: "A scan for model downloads, which finished on 368 of the 372 graded runs" (e9/summary.json runs_scanned).
2. Adapted: lists 6, 16, 2 context and 4 finished runs with no pinned-auditor grade, and says 3 of those 4 are now graded (e8/d_cells.md, regrade_dcells.json); the rerun slot names the 16 stopped and 4 prompt-bug cells.
3. Adapted: "thin ReAct-style agent loop" and "production coding agent", with the shared-settings clause split into its own sentence to stay under 40 words.
4. Adapted: names DeepSeek-V4-Flash and says "14 of its 34 Run papers", keeping the bracketed interval format the other parts use.
5. Applied.
6. Adapted: states the 372-run base and adds that these 73 are the 73 of 400 cells in Section 5.2.
7. Applied, with "had graded" changed to "scored" because the grade followed the overwrite.
8. Adapted: split in two, gives 14 at both 5% and 10% (e6/README.md), points to Appendix F.
Also removed "Neither was the best agent's run": Muse Spark tied DeepSeek-V4-Flash at 9 of 33 at Retrain before the correction, so the sentence now says no best-agent rate changes.

YGTR part 1
1. Adapted: the review numbers its questions but not its weaknesses, so the headings quote the reviewer ("No frontier models are tested", "due to the hardware differences", "Agents are also only run once") and keep Q1.
2. Adapted: points to the appendix table for each run's exit reason; the grant use already has its own budget slot.
3. Applied, and the failing-run slot is renamed [f] because [m] already counts Muse Wonder papers.
4. Adapted: the main results keep the thin loop for one shared harness, the appendix measures the two production harnesses, and a new sentence answers Claude Code.
5. Applied.
6. Adapted: names DeepSeek-V4-Flash as best at Run and Retrain with no build failure there (build_failures.csv shows its one failure at Reimplement) and Muse Spark 1.2 at Reimplement.
7. Adapted: plain wording, targets added, and "the original and new values span" because 0.0395 lies inside 0.0393 to 0.0400, so both numbers now measure the same thing.
8. Adapted: subset.json fixes 2 reproduced and 2 not within each tier, so the sentence says "in each tier"; "queued" stays, since the bracketed result sentence shows the result is pending.
Unanswered, Claude Code: applied. The reply says it is the one named harness we did not run and that our auditor is Claude Sonnet 5 (paper line 389), so a Claude agent would be graded by its own family; an [AUTHOR] note says PLAN.md:200 gave billing as the reason.
Unanswered, failure modes: rejected; the failure-share slot and the blind-label check already answer it once runs finish.
Unanswered, minimal loop: adapted through item 4.

YGTR part 2
1. Adapted: "we scanned the transcripts of all 372 graded runs ... finished on 368 runs and timed out on 4, none of which was reproduced"; the pattern list became its own sentence.
2. Applied, naming Muse Spark 1.2 in full.
3. Applied.
4. Adapted: the Q3 answer now traces the 28 first, then says the 16 stopped cells are among the 28 and outside the 27 and are rerun. An [AUTHOR] note for Risk 2 was added beside the 16 sentence, since none was there.
5. Adapted: split into two sentences, "followed the released pipeline" replaces "faithful pipeline".
6. Adapted: the rerun slot names the 4 cells of 2510.20725 and the 16 stopped cells.
7. Adapted: d_cells.md and regrade_dcells.json settle it, so the reply says 3 of the 4 were regraded by the pinned auditor (scores 0, 2 and 0, none reproduced) and the fourth lost its files.
8. Adapted: "your concern that the findings may not generalize beyond the tested models", without the score.
Unanswered, generalization beyond the benchmark: rejected; the review ties generalization to model strength, which the frontier runs answer.
Unanswered, tier labels: rejected; the reviewer did not raise it, and Risk 5 holds it for Mithil.

Numbers across parts
- Scan coverage: applied (368 of 372 in both).
- No-graded-run accounting: applied (6, 16, 2, 4 in both).
- Auditor base: applied (73 of 372 runs, the same 73 as 73 of 400 cells).
- Muse Wonder: adapted; every Muse Wonder count uses the [m] slot, including the same-family sentence.
- Build failures: adapted; the 27 keeps the 14 transcript-traced aarch64 builds, and the reply states that 3 of the 12 replays fail on x86 on a Python or package version conflict (e8/x86/README.md), so for those 3 the hardware is not shown to be the cause.
