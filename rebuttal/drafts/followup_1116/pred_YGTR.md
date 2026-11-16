# Reviewer YGTR, predicted response

R1 and R2 are rebuttal/post/YGTR_1.md and YGTR_2.md, PDF lines are paper.txt lines, results/ is rebuttal/results/.

## 1. Verdict

The reviewer most likely raises 2 to 3 by a small margin, because every point received a new measurement and Q2 changed two grades. The raise is fragile, since the main new result (frontier models stop early and reproduce fewer papers than DeepSeek-V4-Flash) can be read as a product of the task text and the stopping rule, which keeps the rating at 2. Evidence that the early-stopped runs still fail when told to continue would move the rating most.

## 2. Likely follow-up

> Thank you for the new runs, which answer W3 and Q2. The frontier result convinces me less. gpt-6.1-sol in Codex CLI reproducing fewer papers than DeepSeek-V4-Flash is surprising, and I suspect the setup: half of the papers were chosen because an open model had reproduced them, a run ends when the agent first ends its turn, and the continue prompt was tried on 3 runs that had not stopped early. Does the task prompt tell agents to stop when an artifact is missing? In Q3 all three reruns place the miss outside the agent, so how many of the 76 similar runs are the agent's fault? The abstract still reports only the weaker models.

## 3. Surviving objections

**1. Early stopping may come from the setup.**
(a) "Frontier models stop at turn 9 because code is unreleased at the tier where they must write it. Is that your prompt and stopping rule?"
(b) High.
(c) R1:32: "On 3 papers it spent more of its grant and received the same scores as the unprompted runs (8, 8 and 7)". In PDF Table 8 those unprompted runs spent 49.2%, 10.6% and 52.8% of the grant. The task prompt (PDF line 6341) says "declare early, evidence the search, wind down."
(d) Continue-prompt runs on papers that stopped under 5% of the grant.
(e) Partly. results/frontier/stop_study/summary.md: under the same task text, 16 of 39 failing frontier runs stop on a missing artifact against 6 of 30 open-agent runs. Tallied from its deep_all.json, 17 of 24 Codex CLI failures and 8 of 13 in the authors' harness never ran the full experiment. Continue-prompt grades on early-stopped papers: not found (rebuttal/STATUS.md:137).

**2. The comparison with open agents is biased.**
(a) "Half of the papers were chosen because an open agent's single run reproduced them, and rows cover 2 to 23 papers. This cannot show that frontier models do no better."
(b) High.
(c) PDF B.3 (line 3202): "those columns favor the open agents". R1:5 still sets 18 against 23 and 20.
(d) A baseline that does not depend on open-agent outcomes.
(e) Partly. results/frontier/same_paper_baselines.md: gpt-6.1-sol in the authors' harness reproduces 5 of 12 against DeepSeek-V4-Flash's 4. Outcome-independent baseline: not found.

**3. The 76 faithful-pipeline misses.**
(a) "All three reruns give the agent's number without the agent. How many of the 76 such failures belong to the paper?"
(b) Medium to high.
(c) R2:32: "we read their misses as coming from outside the agent." PDF Section 6 (line 803): "we cannot separate agent error from seed and hardware variance, beyond the three runs we re-executed".
(d) A bound over the 76.
(e) Partly. results/e6/README.md: 9 partial runs become reproduced at 10% tolerance. Per-paper count: not found.

**4. The headline claims are unchanged.**
(a) "Your data confirm that failure modes change for frontier models, yet the abstract and conclusion report only the four weaker models."
(b) Medium to high.
(c) R1:30: "the main failure mode changes." PDF abstract (line 34): "The most common agent error is writing the method without checking any part against the paper's numbers".
(d) One abstract and one conclusion sentence with the frontier result.
(e) Numbers exist (PDF Table 23: 5 of 39 frontier failures against 63 of 300).

**5. Claude Code was not run.**
(a) "Claude Code was the first harness I named, and people graded 372 runs, so they could grade a small sample."
(b) Medium.
(c) R1:26: "validated against human grades as in Appendix D, which we leave to future work."
(d) A human-graded Claude Code sample.
(e) Not found.

**6. Hardware effects beyond labeled build failures.**
(a) "A run that worked around a missing aarch64 package and then failed is also a hardware failure."
(b) Medium.
(c) R2:3: "Our hardware therefore explains 9 failures". PDF line 695 has such a case under another label: "it replaced the package with an unvalidated port the auditor disqualified."
(d) A count of such runs over all 372 transcripts.
(e) Partly: 4 of 8 on x86 against 3 of 8 (PDF B.3). All-transcript count: not found.

**7. Repeat runs.**
(a) "Pairs that fail twice carry 23 of 27. How stable are pairs with a reproduced run?"
(b) Low to medium.
(c) R2:13: "the verdict is stable for 23 of 27 model and paper pairs". Pairs with a reproduced run number 5 + 5 + 4 = 14, and 4 change.
(d) State 10 of 14.
(e) Exists. results/e13/README.md: updated pool 26 of 30.

## 4. Mismatches

- **2506.08898.** R1:37, citing Section 5.3: "three runs projected 33 to 51 hours of retraining and stopped". PDF line 708: "5 of 6 frontier runs stopped [...] because no matching checkpoint is released".
- **2506.10351.** R2:32 reads its miss "as coming from outside the agent". results/e10/results.md:7: "the run's partial grade came from a protocol deviation the agent disclosed".
- **Repeats.** R2:10: "9 papers from all three tiers". PDF Section 6 (line 815): "the second runs cover one agent on 10 papers of one tier".
- **Totals absent from the PDF.** "23 of 27" (general.md:3, citing Section 5.2) and "27 of the 400 cells" (R2:21).
- **Inside the reply.** R2:3: "3 fail again" on x86. R2:24 counts all "14 aarch64 packages" as outside the agent.
- **PDF only.** Line 138: "1 of them reproduces its claim". Line 728: "none of them reproduces".
