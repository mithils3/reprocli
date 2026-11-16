# Reviewer YGTR second-round answers, 2026-11-16, prepared, not posted

### If asked: Does the task prompt cause early stopping?

The task text allows an early stop in two cases. When the claim depends on a trained artifact that is neither released nor retrainable within the grant, it asks the agent to say so early and document its search, and when code is unreleased it asks for a time-boxed search and then a port validated against released material, or a declaration that the paper cannot be reproduced. Every agent received this text and the same stopping rule. When we code the reason each failing run gives as it ends, without the model's name, 16 of 39 frontier runs name a missing artifact (41% [27%, 57%]), against 6 of 30 failing runs of DeepSeek-V4-Flash and Muse Spark 1.2 on the same papers (20% [10%, 37%]). On 11 of the 27 frontier runs that never ran the experiment at full scale, an open agent reproduced the same paper (Appendix G.3). The continue-prompt runs cover three papers whose unprompted runs had used 49.2%, 10.6% and 52.8% of the grant, and with the prompts they received the same scores (8, 8 and 7).

Source: rebuttal/results/frontier/stop_study/summary.md: 16/39, 6/30 with intervals.
Source: paper.txt 4654-4663 (11 of the 27), 6362-6365 (task text), Table 8 (grant shares, scores).
Caution: no continue-prompt run was graded on a paper whose unprompted run stopped under 5% of the grant. The 16 of 39 is the stop-reason coding of the run's closing part; Appendix G.3's full-transcript reading counts 12 of the 27 runs that never ran at full scale as stopping on unreleased code, checkpoint or data. If asked about the two counts, say they come from two separate codings.

### If asked: The open-agent comparison is biased by selection

We agree that the pooled columns favour the open agents on the half of the sample drawn because one of them had reproduced it, so we read the two halves separately. The 24 papers come from a seeded draw frozen before any frontier run with half that at least one of our four agents had reproduced and half that none had. On the first half the frontier runs reproduce 14 of 33, against 23 and 20 for DeepSeek-V4-Flash and Muse Spark 1.2, and on the second they reproduce 4 of 24, where both open agents have 0 by construction. The frontier reproduction rate itself, 18 of 57 = 32% [21%, 44%], does not depend on these columns, and its sample holds 12 of 24 papers that an open agent had reproduced, against 34 of 99 in the benchmark (Appendix B.3).

Source: rebuttal/results/frontier/same_paper_baselines.md: 14/33, 23, 20, 4/24, 0/24, 18/57.
Source: rebuttal/subset.json (draw); paper.txt 3233: 34 of the 99.
Caution: no baseline independent of open-agent outcomes exists; reweighting the halves to the benchmark mix gives about 26% (my arithmetic, in no results file).

### If asked: How many of the 76 are agent errors?

We cannot assign each of the 76 runs to the agent or to the paper, and the three we re-executed differ. On 2505.17836 both reruns repeat the agent's number (0.0400 and 0.0393 against 0.0395, target about 0.05), so the released code produces that miss. On 2510.07501 the agent's run and the two reruns span 0.28, far more than the agent's miss of 0.02, so its near miss is within seed noise. On 2506.10351 the reruns repeat the agent's number, which is within 5% of the target, and the partial grade came from a protocol deviation the agent disclosed. To bound all 76, we removed them from every denominator: on the grades as submitted, the best agent then reproduces 14 of 29 papers at Run, 9 of 18 at Retrain and 5 of 31 at Reimplement, so Reimplement remains the lowest tier.

Source: rebuttal/results/e10/results.md: 0.0395, 0.0400, 0.0393; -0.2241 to +0.0566; 94.19 against 93.12.
Source: followup_1116/ev_faithful/ev_faithful.md: 14/29, 9/18, 5/31.
Caution: the 2506.10351 sentence narrows the posted "in all three ... outside the agent"; denominators use submitted grades.

### If asked: Abstract and conclusion omit the frontier result

We agree that the headline should carry the frontier result, and the abstract and conclusion of the revised PDF now state it. For gpt-6.1-sol, gpt-6-astra and Muse Wonder on 24 papers, 18 of 57 runs are reproduced (32% [21%, 44%]). Their failures have a different main cause from those of the four open agents: 27 of the 39 failing runs never ran the paper's experiment at full scale, and writing the method without checking it against the paper's numbers accounts for 5 of the 39, against 63 of 300 failing runs of the open agents (Table 23).

Proposed PDF sentence (both need a new PDF upload):
- Abstract: "Three frontier models in our harness, Codex CLI, and mini-SWE-agent reproduce the claim in 18 of 57 runs on 24 papers, and their failed runs use a median of 2.1% of the grant."
- Conclusion: "For three frontier models on 24 papers, 18 of 57 runs reproduce the claim, and the most common failure becomes stopping early: 27 of the 39 failed runs never run the experiment at full scale."

Source: paper.txt 3213 (18/57), 3220 (2.1%), 4654 (27), Table 23 (5, 63).
Caution: post only after the upload; the abstract's 29% is a mean, and the mean over the 39 failed frontier runs is 13.2%.

### If asked: Claude Code could be graded by people

We agree that a human-graded sample of Claude Code runs would be the gold standard here. We are not able to provide one within the discussion period, and the revision makes no claim about Claude models. The human grades we have show which way the LLM auditor errs on models from other providers: on 372 runs it calls 73 reproduced where the human graders call 83 (precision $\frac{64}{73}$ = 88%, recall $\frac{64}{83}$ = 77%), so it is the stricter grader (Appendix D).

Source: rebuttal/results/e4/README.md and paper.txt 462-464: 73, 83, 64.
Caution: no Claude Code run exists, so this answer concedes the point.

### If asked: Hardware effects hide behind workarounds

We agree that a run which works around a missing aarch64 package and then fails would sit outside the 24 build and dependency failures, and the test that covers such runs is an end-to-end one. On x86 nodes, gpt-6.1-sol and gpt-6-astra in our harness reproduce 4 of 8 model and paper pairs, against 3 of 8 for the same pairs on our GH200 nodes, and the two scores of every pair are within one point (Appendix B.3). A hardware effect acting through workarounds would appear as a gap between these two counts, and the gap is one pair.

Source: paper.txt 3231 and rebuttal/results/databook/frontier_cells.csv: 4/8, 3/8.
Caution: the 8 pairs cover 6 papers; no count of such runs exists for the 372 open-agent transcripts.

### If asked: Stability of pairs with a reproduced run

Among the pairs with a reproduced run, 10 of 14 keep their verdict (71% [45%, 88%]), and all 16 pairs with no reproduced run fail again. With the repeat runs graded since our reply, the pooled total is 26 of 30 model and paper pairs (87% [70%, 95%]).

| Repeat set | Pairs | With a reproduced run | Same verdict |
| :- | -: | -: | -: |
| Muse Spark 1.2, Reimplement | 10 | 5 | 4 |
| DeepSeek-V4-Flash, three tiers | 12 | 5 | 3 |
| gpt-6.1-sol and gpt-6-astra, x86 and GH200 | 8 | 4 | 3 |

The four pairs that change lie on two papers, 2503.02809 and 2505.19087. Every run in them scores 7, 8 or 9, and the changes go in both directions.

Source: rebuttal/results/e13/README.md (26/30), e12/README.md, frontier_cells.csv.
Caution: 10 of 14 is my tally from those tables.

### Short reply if the follow-up is the predicted one

Thank you for confirming that the new runs answer W3 and Q2.

**Frontier setup.** The task text allows an early stop when a claim depends on a trained artifact that is neither released nor retrainable within the grant, or when unreleased code cannot be rebuilt and validated against released material. Every agent received this text and the same stopping rule, and under them 16 of 39 failing frontier runs name a missing artifact when they stop (41%), against 6 of 30 for DeepSeek-V4-Flash and Muse Spark 1.2 on the same papers (20%). The three continue-prompt runs repeat papers whose unprompted runs had used 49.2%, 10.6% and 52.8% of the grant, and their scores did not change.

**Paper selection.** We agree that the pooled columns favour the open agents on the half sampled because one of them had succeeded, so we read the halves separately: 14 of 33 against 23 and 20 there, and 4 of 24 against 0 on the other half.

**The 76 runs.** We cannot assign each one, and of the three reruns, one repeats the agent's miss (2505.17836), one is within seed noise (2510.07501), and one repeats a number within 5% of the target whose partial grade came from a protocol deviation the agent disclosed (2506.10351). With all 76 removed from the denominators, the best agent reproduces 14 of 29, 9 of 18 and 5 of 31 papers at Run, Retrain and Reimplement on the grades as submitted, so Reimplement stays lowest.

[After the PDF upload] The abstract and conclusion now state the frontier result.
