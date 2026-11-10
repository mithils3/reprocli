# Prepared second-round answers (ICLR 2027, submission 22528)

Written 2026-11-09 against rebuttal/post/ at the same commit. Supersedes followups_v2.md, whose numbers predate the target corrections and the frontier runs. Each answer is paste-ready except for bracketed slots, which hold results still to be filled. Rules applied (rebuttal/results/style/qual/blind_check.md): every answer carries a number or a location the first reply did not, none asks the reviewer to restate a point, none promises a result, and a limit on a result is stated once and left standing.

## Reviewer T29u

### If asked: the repeat runs cover one agent on 12 papers, half of them picked as reproduced

The 12 papers are four per tier, two that an agent had reproduced and two that none had, so we report the two groups separately. DeepSeek-V4-Flash keeps its verdict in all three runs on [k1] of the 6 papers it or another agent had reproduced and on [k2] of the 6 others (Section 5.2). The comparisons in our first reply use two-proportion tests on the 100 papers and do not depend on these 12.

Source: rebuttal/subset.json; slots from the repeat runs (DSV4 r2, r3).

### If asked: the auditor's 73 and the human's 83 are different sets of runs

The two sets share 64 runs. Nine more are accepted only by the auditor and 19 only by the human (Appendix D). To measure how stable the auditor's own verdicts are, the same auditor graded 38 cells a second time: no cell moved between reproduced and not reproduced, and 8 of the 38 scores changed, by 0.39 points on average.

Source: rebuttal/results/e4/summary.json (reproduced_ge8); rebuttal/results/e7/rescore_summary.md (rescoring noise).

## Reviewer rqBN

### If asked: the re-execution covers three papers and none at Reimplement

On 2505.17836 the released commands give 0.0395 in the agent's run and 0.0400 and 0.0393 on two new seeds, against a target near 0.05, so that miss does not come from the seed. On 2510.07501 they give -0.2241, -0.1308 and +0.0566 against a target of -0.20, so that miss lies within seed variation. [On 2506.10351 the agent's run gives 94.19 against 93.12, and the new seeds give x and y.] A Reimplement paper releases no code to re-run, so for that tier the evidence is the 5 of 33 papers that at least one agent reproduced.

Source: rebuttal/results/e10/results.md; rebuttal/results/tiers/tier_tests.md.

### If asked: which frozen targets were wrong

Appendix E lists the 8 corrected targets with the passage of the paper behind each new value. The correction with an effect is 2505.23747, where the frozen value 51.13 came from the release README and the paper reports 48.4. Rescoring against 48.4 moves two runs on that paper from reproduced to partial, and no other verdict changes.

Source: rebuttal/results/e7/rescore_summary.md (correction effect); rebuttal/results/e7/summary.json.

## Reviewer YGTR

### If asked: Codex stops early, so a user would simply tell it to continue

We measured that case. A Codex run ends when the model ends its own turn, which is also how a run ends in our loop. In a second set of runs we prompted Codex to continue, up to three times, whenever it stopped with under half of its GPU grant used, and it reproduces [c] of [n] papers against [c0] of the same papers without the prompt (Appendix B). On the [9] papers that gpt-6.1-sol finished in both harnesses the counts are [3] in our loop and [2] in Codex CLI.

Source: rebuttal/results/frontier/same_paper_baselines.md; arm codex-gpt-6.1-sol-nudge (slots).

### If asked: runs that ended at the time limit are counted as failures

Each agent reads the time limit of its partition before it requests GPUs, and the task prompt states that a step still running at that limit is ended (Appendix J). A run that does not finish inside the limit is therefore counted as that agent's failure, in the same way as a run that uses up its GPU grant. Section 5.2 accounts for each of the 28 cells with no graded run, and the 6 with a cause outside the agent are named there.

Source: prompts/prompt_reproduce.txt:157-159; paper_latex/iclr2027_conference.tex:555-562; decision 19.
