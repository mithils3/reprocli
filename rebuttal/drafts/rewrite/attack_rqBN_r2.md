# Attack on rqBN reply, round 2 (reviewer rqBN, score 3)

## Read twice
1. "These grades include the corrections in our other replies, which take the reproduced agent-paper cells from 73 to 70 of 400" (Q1). I cannot tell what "cells" are, which replies, or why 73 appears here and as the auditor's 73 in W1. Fix: say "of 400 agent-paper runs, 73 become 70 after the target corrections", once.
2. "the 7/8 boundary" (opening bullet) is unexplained until W1. Fix: write "the pass threshold of 8".
3. "the grant for one agent over the 100 papers (10,208 H100-hours over four agents, divided by 4)". Fix: "2,552 H100-hours per agent, a quarter of the 10,208 granted".
4. "An expert following that pipeline would also have a miss that repeats." Read next to the second bullet, where the miss does not repeat, it contradicts itself. Fix: delete it and state each of the three outcomes.
5. "Stage III, the last of the three construction stages" appears with no earlier mention of stages. Fix: one clause naming all three.

## Not answered directly
7. Q2 asked for independent validation and agreement. Reply: one author, no second annotator, and a model check that saw the answer key. That is a circular check on a weak design, and the rest of Q2 is dressed up around it. Fix: say plainly that independent human validation was not done, then give the model-check result as partial evidence.
8. W1 asked for validation of anti-cheat flags. Only score-0 agreement is given (42 of 57), and 15 of 57 disagree. Fix: say that is the only flag evidence, and what the 15 disagreements were.
9. Q1 baseline: the reply says "single human attempt would become a moving reference". Moving, but still a missing reference. Fix: state what the reader can conclude without it, namely tier ordering and the authors' own reported numbers.

## Unsupported or arithmetic
10. "Comparing ... over all 372 graded runs found one edited log" followed by "119 commands in 65 runs ... left out of commands.log". Both cannot be a clean "all 372" comparison. Fix: say the comparison covers the 45,861 logged entries and does not cover the missing 119.
12. "the edit did not raise that run's score" (score 1) is weak evidence that edits cannot raise scores. Fix: say what is bounded, namely this run.
13. "The differences between tiers are within sampling error" while Run recall is 80% and Reimplement 69%. Fix: give the interval for Run beside Reimplement.
15. 2505.17836: "target about 0.05; measured 0.0395". The ordering of the miss is unclear (below target). Fix: state the tolerance band and the direction.

## Unforced concessions or defensive
16. "Before: ... After:" quote, with the old text instructing the auditor to treat the bundle as unverified claims, concedes my tamper point without being asked what the old design relied on. Fix: keep the after-text, drop the before.
18. "55 of 100 pass all four" is buried; it is the most damaging number. Fix: lead the paragraph with it, then the 8 wrong numbers and two changed verdicts.


## Score
3. Strong on logs and the confusion matrix. The one change that would most raise it: for Q2, a plain statement that target validation was not independent, with the model-check as bounded evidence and the 55-of-100 figure stated with its implication for headline results.
