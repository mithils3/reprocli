# Likely reviewer follow-ups to the shortened replies (ICLR 2027, submission 22528)

Written 2026-11-08 against rebuttal/drafts/replies.md at commit e0809c7. Each reviewer section reads only that reviewer's review, our posts to them and the General reply. "Earlier" means rebuttal/drafts/followups.md. Every number below was opened in the file named beside it. All paths are under rebuttal/ unless they start with paper_latex/ or src/. A cluster of sentences in the replies waits on runs that are still pending (jobs 3540624 to 3540633 and 3540786, 3540787 had no start time in results/databook/databook.md Section 4), so several answers below say "no evidence on disk".

## T29u (rating 3, soundness 2)

### Follow-up 1: the repeat runs cover one agent on 12 papers and are still empty

Our sentence (W1): "The revision compares the reproduction rates of two agents only where their intervals, widened by the run-to-run change these repeat runs measure, do not overlap, and it says that the measurement covers one agent."

Reviewer voice: "The repeat runs cover one agent on 12 papers, and half of those papers were picked because some agent had reproduced them, so the share of stable verdicts you report will not be the flip rate on the benchmark. Your own best-agent intervals already overlap before any widening, so under this rule almost no two agents can be ranked. What do the three runs actually show?"

Earlier: raised (Follow-up 2). The rewrite is slightly better, because the reply no longer calls DeepSeek-V4-Flash the strongest agent and now ranks by mean audit score. It is worse in one respect: W1, the weakness this reviewer put first, now contains only a bracketed result sentence.

Best answer. No evidence on disk for the repeat result: the jobs are in results/sweeps/jobs.csv (submitted 2026-11-06) and were all PENDING in results/databook/databook.md Section 4. The design is documented (subset.json, results/subset/README.md: four papers per tier, two reproduced and two not). The overlap premise is correct: DeepSeek-V4-Flash at Run is 14/34, 26.4% to 57.8%, and Muse Spark at Run is 9/34, 14.6% to 43.1% (results/e8/bound.csv). A paste-ready answer once the runs finish: "The 12 papers were drawn four per tier with two reproduced and two not, so we report the flip rate separately for each of those two groups and weight them by their share of the 100 papers. The ranking claims in Section 5.2 now rest on the mean audit score, and we state in the revision which pairs of agents the intervals do and do not separate." The smallest analysis is to grade the 24 queued runs and compute the weighted flip rate.

### Follow-up 2: "if anything, low" compares two different sets of runs

Our sentences (W2): "The disagreements lean toward a strict auditor. Of the 28 runs where only one grader called the result reproduced, the human did in 19 and the auditor in 9." and "so the paper's reproduction counts are, if anything, low."

Reviewer voice: "The 9 runs that only the auditor accepted are inside your 73, so the 73 is a different set of runs from the human's 83 and not a lower bound on what a human would accept. Most of those reproductions also sit at the lowest passing score, right on the line where you say graders disagree. How many of the 73 would survive a second grading?"

Earlier: raised (Follow-up 1) and unchanged in substance. The rewrite dropped the fact that makes the reply honest about the line, that the auditor gives exactly 8 to 52 of its 73 reproductions.

Best answer. The premise is correct: results/e4/summary.json gives auditor_col_totals[8] = 52. What can be said: the auditor accepts 73 runs and the human 83, and 64 are accepted by both (e4/summary.json, reproduced_ge8: tp 64, auditor_yes_human_no 9, human_yes_auditor_no 19). On the full scale the quadratic weighted kappa is 0.888 and the auditor scores 0.26 points below the human on average. When the same auditor regraded 38 cells against the unchanged frozen claims, 0 of 38 cells changed between reproduced and not reproduced and 8 of 38 integer scores moved, a mean absolute difference of 0.39 points (results/e7/rescore_summary.md, rescoring noise). Paste-ready: "We agree the 73 and the human's 83 are different sets and the revision says so: 64 runs are in both, 9 only the auditor accepts and 19 only the human accepts. Of the 73, 52 are scored exactly 8. Regrading 38 cells with the same auditor changed no verdict between reproduced and not reproduced." No per-run human label file is on disk (results/e4/README.md), so the 9 cannot be listed.

### Sentences that now read as overclaims or defensive (T29u)

- "so the paper's reproduction counts are, if anything, low": defensive and an overclaim, see Follow-up 2. Replace with the 64, 9, 19 counts.
- "Neither was the best agent's run": Muse Spark 1.2 is tied for best at Retrain (9/33, results/e6/README.md) and sole best at Reimplement, and the CogVLA run is a Muse Retrain run, so the sentence is false for the tie. The true statement is that neither run changes a best-agent rate (Retrain stays 9/33 through DeepSeek-V4-Flash, results/e8/bound.csv).
- "The ordering of the tiers holds at every tolerance we tried" is true for the best agent (9, 8, 4 at 1%; results/e6/README.md) and false per agent (MiniMax-M2.7 has 3 at Run and 5 at Retrain, results/e8/bound.csv). The next sentence names the best agent, so adding "for the best agent" to this one closes it.
- Q2 is about sensitivity, yet tolerance only touches the 62 point-estimate claims, and 22 of the 73 reproductions have no number test (11 direction, 10 threshold, 1 magnitude, results/e6/README.md, "Why 51 and 73"). The reply states 62 and 38 but not the 22, so a reviewer will compute it. Earlier: listed under open questions; the rewrite made it more visible because the 62/38 split is now stated.
- "Q1 ... the full confusion matrix" answers the 7/8 boundary but, for high-severity flags, only reports agreement on a score of 0 (42 of 57; results/e4/summary.json, disqualified_score0_as_high_severity). The rubric gives 0 for other causes too (paper_latex/appendix/c_rubric.tex, row 0), so "bears on high-severity problems" needs the words "score of 0" in place of "flags". Earlier: Follow-up 3 and unchanged.

## rqBN (rating 3, confidence 2)

### Follow-up 1: the human baseline is replaced by three papers, none at Reimplement

Our sentences (Q1): "We did not run a human-expert baseline in any tier" and "Only 3 papers had a single clean command chain, 1 at Run and 2 at Retrain ... and no Reimplement paper can enter this check, because that tier releases no code to re-run."

Reviewer voice: "A stratified baseline across the three tiers was my request, and the substitute covers two Retrain papers and one Run paper with no Reimplement paper. Two of the three finished, and the 2505.17836 target is 'about 0.05', which looks read off a plot. Please say what this check tells us about the share of misses caused by the environment."

Earlier: partly raised (the overclaim bullet on 2505.17836). The rewrite is better, since it now says the miss places the cause "in the environment or the paper" and gives the span arithmetic on 2510.07501. It is worse in that the third paper is a bracket and the cost argument (2,552 H100-hours) answers a question about GPU budget when the reviewer asked about a human baseline.

Best answer. The target of 2505.17836 is marked unclear in mithil/e7_verdicts.csv ("not stated in text; only Figure 2b/2c curves"), so the reply's own caveat is correct, and the measured 0.0395 against "~0.05" is a gap of 0.0105 that depends on a figure reading (results/e10/selection.csv). What the check shows (results/e10/results.md): 2505.17836 repeats within 0.0007 across the original and two seeds, and 2510.07501 moves from -0.2241 to -0.1308 and +0.0566 across seeds against a target of -0.20. Paste-ready: "The re-execution is 3 papers and we describe it only as that: on 2505.17836 the same commands give 0.0395, 0.0400 and 0.0393, so the miss does not come from seed variation, and on 2510.07501 they give -0.2241, -0.1308 and +0.0566 against -0.20, so that near miss is within seed variation. We make no claim for the Reimplement tier or for a human baseline." No evidence on disk for a human baseline in any tier. The smallest analysis is one expert running the Run-tier papers whose grants are 8 GPU-hours or less, which results/e10/selection.csv shows to be the band where clean chains exist.

### Follow-up 2: which frozen targets are wrong, and who extracted them

Our sentences (Q2): "The papers support the value for 92 of the 100 claims ... and all four for 55" and the bracket "[An author read each of the 45 papers with a failed question against the paper itself ...]".

Reviewer voice: "Only 55 of 100 targets pass all four of your own checks, and the count of targets that are actually wrong is still a bracket. The paper says the claims were extracted by MiniMax-M2.7, which is one of the agents you evaluate, and one author checked everything with no second reader. How many frozen targets are wrong, and does the extractor's role favor it?"

Earlier: raised (rqBN Follow-up 1, highest threat). The rewrite is better, since it now says one author reviewed every field and no second person did, which matches paper_latex/iclr2027_conference.tex:667-669. It still never names the extractor.

Best answer. The settlement of the 45 is on disk (mithil/e7_verdicts.csv): 17 right, 13 unclear because the value appears only in a figure, 5 wrong only in the setup text, 10 wrong in the value. Rescoring the 40 cells of the 10 value-wrong papers changes 2 cells from reproduced to partial, both on 2505.23747 (frozen 51.13 from a release README, paper 48.4), moves the best Run rate from 14/34 = 41.2% to 13/34 = 38.2% [23.9%, 55.0%], leaves Retrain and Reimplement unchanged and takes the total from 73 to 71 of 400 (results/e7/rescore_summary.md). The extractor was MiniMax-M2.7 (paper_latex/iclr2027_conference.tex:331-333), the agent with the lowest mean audit score, 3.03 against 5.13 for the highest (same file, line 466). Paste-ready: "10 of the 100 frozen values disagree with the paper, 13 more cannot be settled because the paper reports the number only in a figure, and 5 differ only in the setup text. We rescored every cell of the 10 papers: 2 of 40 cells change and the best Run rate moves from 14/34 to 13/34. MiniMax-M2.7 extracted the claims and has the lowest mean audit score of the four agents, so the extraction gives it no visible advantage." This depends on the Mithil decision flagged in the [AUTHOR] note of T29u W1; the E7 verdicts may still change.

### Sentences that now read as overclaims or defensive (rqBN)

- "its protection is that it lies outside every directory the sandbox mounts": results/e5/README.md does not state this. src/reprocli_repro/sandbox.py binds workspace and evidence read-write, which supports it, but the sentence has no cited file in the Sources table. Add src/reprocli_repro/sandbox.py:288-302 as the source. Earlier: not raised.
- "so the errors do not concentrate in one tier": Reimplement recall is 11/16 = 69% (44% to 86%), which the reply admits is the lowest. With 16 human reproductions an interval of that width cannot show absence of a difference, and the sentence reads as defensive. Say "we cannot tell". Earlier: not raised.
- "Yes, the auditor was validated ... our reply to Reviewer T29u (Q1) shows the full confusion matrix": rqBN's own post carries no matrix, so a reader of this post alone does not have the answer to the main weakness. This is new in the rewrite. Move the five-by-five table into this reply or give a two-by-two (64, 9 / 19, 280) here. The 280 is 372 - 64 - 9 - 19 from results/e4/summary.json.
- The log check covers only two files while the auditor also reads the numbered GPU step logs. Agents wrote into evidence/ outside the two logs in 360 of 372 runs and the directory's modification time was more than 60 seconds after run end in 63 (results/e5/README.md, lines 12 and 14). The reply is silent on both. Earlier: Follow-up 2 and unchanged.
- "multi-human adjudication": the reply states one human label per run and offers no remedy, and the General reply lists no change for it. A reviewer who asked for it in W1 will see the gap. No evidence on disk for a second grader; the smallest analysis is a second blind grader on about 40 runs stratified by auditor verdict.

## YGTR (rating 2, informativeness 1)

### Follow-up 1: the frontier question is answered with brackets, and the early-stop data points at the harness setup

Our sentences (W1 and Q1): "We ran two current OpenAI models ... and Meta's Muse Wonder on papers drawn with a fixed seed ..." and "A Codex run ends when Codex ends its own turn, the same stopping rule as our loop."

Reviewer voice: "Your reply says you ran the frontier models and then gives me no result, only placeholders. If the first Codex runs used a few percent of their GPU grant and stopped on a missing checkpoint, that looks like a harness configuration that ends early, and a researcher using Codex would simply say continue. You also say Claude Code was left out because your auditor is a Claude model, which does not stop you from testing other harnesses or other judges."

Earlier: raised (YGTR Follow-up 1, highest threat). The rewrite is slightly worse, because the opening line now claims "We ran frontier models in production harnesses, as you asked" before any number and the Claude Code sentence is new.

Best answer. Over the 24 graded frontier runs the median share of the GPU grant used is 1.33% and 21 of 24 used under 10% (computed from results/databook/frontier_cells.csv, spent_h100 / budget_h100; for example 0.3779 / 32.0 = 1.2% on 2412.11979). Fourteen of the 24 stopped on a missing artifact, 5 on an unresolved configuration, 3 on other causes and 2 finished (results/frontier/early_stop.md). Codex gpt-6.1-sol reproduced 1 of 12 papers (95% interval 1.5% to 35.4%, mean score 4.08), against 3 of those 12 papers for the DeepSeek-V4-Flash original runs (mean score 5.67); the Codex runs waited a median of 9.7 hours in the queue (frontier_cells.csv, queue_wait_min). Paste-ready: "The Codex runs stopped on a missing artifact or an unresolved configuration in 19 of 24 graded runs, which is the early-stopping failure our paper already reports for the open models. We are adding an arm in which Codex receives a fixed number of continue prompts on 8 papers, so the harness setting can be separated from the model." No evidence on disk for that arm (0 of 8 graded, results/databook/databook.md Section 1). The smallest run is to grade those 8. Muse Wonder has 0 of 12 graded in our loop and 1 of 6 in mini-SWE-agent.

### Follow-up 2: the 16 stopped cells are left out of the "not the agent's fault" count

Our sentences (Q3): "The 27 is the count we could trace and does not bound the failures outside the agent" and "The 16 stopped cells are not in the 27, because a stopped job does not show whether the agent would have succeeded."

Reviewer voice: "Sixteen cells were killed by your cluster's 48-hour limit or a cancellation, which is not the agent's fault, yet they count as failures in your rates and you rank agents on those rates. Ten of them are the best agent's. What are the rates with them removed or rerun, and why does W2 only remove build failures?"

Earlier: raised (Follow-up 2) and fixed in wording since then. The rewrite is better on the count and worse on the missing rerun result, which is a bracket, plus an unresolved [AUTHOR] note that this sentence reverses the paper's count.

Best answer. The 16 are class B in results/e8/empty_cells_traced.csv: DeepSeek-V4-Flash 3 Run, 4 Retrain and 3 Reimplement, Qwen3.6-27B 5 Retrain and 1 Reimplement. Removing the 3 DeepSeek-V4-Flash Run cells gives 14/31 = 45.2% (Wilson 29.2% to 62.2%, computed with the same formula as results/e6/summary.json) against 14/34 = 41.2% as graded. Paste-ready: "Removing the 16 stopped cells moves the best Run rate from 14/34 = 41% to 14/31 = 45%, inside the original interval of 26% to 58%, and the reruns are now queued with the same settings. The ordering of the tiers does not change." The rerun outcome is no evidence on disk (all pending, databook.md Section 4). The smallest analysis is the 20 reruns (4 cells of 2510.20725 plus the 16 stopped).

### Sentences that now read as overclaims or defensive (YGTR)

- "Claude Code is the one harness you name that we did not run, because our auditor is Claude Sonnet 5": reads as an excuse, since mini-SWE-agent and Codex do not depend on the auditor. The plan gives a different reason (PLAN.md:200, Anthropic billing). Mithil must pick the true one, as the [AUTHOR] note says.
- "Build failures on our hardware move no best-agent rate by more than one percentage point": true (Reimplement 5/33 = 15.2% to 5/32 = 15.6%, results/e8/bound.csv), but it covers builds only. The reviewer's W2 also asks about numeric differences for runs that built and ran, and the re-execution of three papers is the only evidence for that. Earlier: listed under open questions.
- Q2 answers with a scan, but says nothing on the reviewer's likely next point that the task prompt tells agents to score a released checkpoint when it is the headline and to evaluate the nearest released sibling (prompts/prompt_reproduce.txt, reproduced in paper_latex/appendix/j_prompts.tex). Both flagged runs followed that text, and the matching tier-label question is Risk 5 in replies.md. Earlier: Follow-up 3 and unchanged. Add one sentence that the prompt allowed it and that the count is a correction for the tier label.
- "The scan cannot see a download made inside an imported library": honest, but with 368 of 372 scanned and 62 of 118 Retrain runs with a primary-source hit, the reviewer can ask what the 4 timeouts were. The reply says none was reproduced, which matches results/e9/README.md.
- "Neither was the best agent's run" appears in T29u only, see above; YGTR part 2 is correct that the best-agent rates stay at 9/33 and 5/33.
- The closing line "We would be glad to hear whether the frontier and harness results address your concern" asks the reviewer to judge results that the reply does not yet contain.
