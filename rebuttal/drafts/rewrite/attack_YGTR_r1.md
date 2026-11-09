# Attack on the reply to YGTR, round 1 (reviewer view)

## A. Unanswered or dodged

1. My core claim was that failure modes "would change significantly" with a better harness. The reply never states the answer. Quote: "[outcome] Section 5 and the Limitations section state this scope". Fix: open W1 with one sentence giving the result (for example "in Codex CLI the share of papers reproduced is [a] against [b] in our loop, and the main failure is unchanged") before any scope language.
2. Q1 asks to "repeat the analysis". Reply: "Yes." Then 8 to [n] papers per arm, one model per harness pair. Quote: "gpt-6-astra ran in Codex CLI only". That arm cannot separate model from harness. Fix: replace "Yes." with "Partly: on [n] papers, not all 100", and drop gpt-6-astra from any harness claim.
3. Claude Code, which I named first, is declined on budget and grader grounds. Quote: "It bills to Anthropic, and our budget for new runs covered OpenAI and Meta models." That reads as an excuse, and the grader point is irrelevant to whether a harness matters. Fix: say Codex CLI and mini-SWE-agent are the same class of production harness and that Claude Code is untested, in one sentence, with no budget talk.
4. Q3 asks how many failures were not the agent's fault. The reply gives 27 of 400 and then "no upper bound" and 76 unattributed. I cannot tell whether the answer is 7% or 25%. Fix: give the stated range (27 to 27 + 76 = 103 of 400) in one line.
5. W3 defers to another reviewer: "(our reply to Reviewer T29u, W1)". Fix: state [j] and its meaning here.
6. Whether failures are "transient or consistent" is answered only by [k] of 12 on one agent. Fix: say plainly "consistent on [k] of 12 papers for DeepSeek-V4-Flash only".

## B. Sentences I read twice

7. "The revision widens each comparison between agents by the [j] papers that the best Run rate moves across the three runs." Unclear what is widened. Fix: "we treat differences smaller than [j] papers as noise."
8. "With all 24 runs dropped from every agent's denominator ... had none of these failures there and stays at 13/34". Dropping runs yet keeping 34 is contradictory. Fix: say the denominator stays 34 because DeepSeek had no such failures at Run or Retrain.
9. "A coder that never sees the verdict labelled the main failure of 26 failing frontier runs". "Coder" is undefined; the denominator of frontier runs is missing. Fix: "a blinded LLM labeller ... of the [N] frontier runs, 26 failed".
10. "It finished on 368 runs and timed out on 4". The scan pattern list is a long run-on that is hard to follow. Fix: list the patterns in the appendix; keep "downloads by name".
11. "the paired difference is [k] papers (exact McNemar p = [x])". A reader needs the 2x2 counts. Fix: give discordant counts.
12. "The 2 Retrain papers we tested miss again on both seeds ... and [their results]". Two papers is anecdote; the sentence dangles. Fix: state n and what it shows, or cut.

## C. Claims at risk

13. "At Run the weights are part of the release". Checked against the paper (lines 76 to 77, 349 to 350): Run releases code, data and weights, and Retrain lacks weights. The claim is correct. The inference "so what matters is the 42" is unstated: say "downloading released weights is allowed at Run".
14. The scan "cannot see a download made inside an imported library". That undercuts "Yes, we checked." Fix: say "checked for explicit downloads" and report whether the sandbox restricted network.
15. "Build failures ... move no best-agent rate by more than one percentage point" rests on 9 of 12 replays, interval 47% to 91%. Also 3 of the 14 failed on x86 too. Fix: add "assuming the 2 unreplayed behave alike".
16. The Run best rate dropping 14/34 to 13/34 appears only in General sources. Fix: say it in this reply, since it changes a headline.

## D. Defensive or unprompted concessions

17. "All 5 were on the two Reimplement papers with no released code ... Rebuilding the method from the paper is that tier's task". It sounds defensive and concedes frontier models give up. Fix: report 5 as a fact and move on.
18. "the auditor's agreement ... stays measured on the 372 runs", "the Limitations section states that ... agent error cannot be separated". I did not ask for these. Fix: cut the first; keep the second only as the Q3 range.
19. "We would be glad to hear whether ... address your concern". Filler. Fix: delete.

## E. Tone and slots

20. The opening "We ran frontier models in production harnesses, as you asked" overclaims; two of three models are not what I meant by frontier, and Claude Code is absent. Fix: "We ran Codex CLI and mini-SWE-agent with [models]."
21. [k] is used for the paired difference and for repeat agreement. Fix: use [q] for the paired difference.
22. "[within / larger than]" reads badly if larger: the reply then says harness matters, yet the frame is reassuring. Fix: write both branches' follow-up sentences. A low [u]% GPU use reads as agents giving up; add a clause.
23. [a] to [g] letters are out of order (g before h in the table). Fix: renumber.

## Score and top change

Score after this reply: 3 if the slots fill favourably (within-noise harness effect, [k] at least 9 of 12), 2 otherwise.

Single change: state the harness-effect answer first, with counts and paired comparison, and say plainly it covers [n] papers and one model pair.
