# Reader 4: the hardest point and the second round

The clearest difference shows up when a reviewer pushes back a second time: raised-thread authors answer the re-raised item with exactly what was named (BigCodeBench "as requested", or "Actually, the reviewer is right" plus a text change), while unchanged-thread authors restate, defer, ask the reviewer what they meant, or ask for the score. In the first round the main objection sits in the same place in both groups, but raised authors more often grant in their own words that the worry applies to their paper, and when they cannot run what was asked they put another result in its place. Most raised reviewers moved after round one, so the second-round contrast rests on few raised threads and partly reflects which reviewers stayed unconvinced.

## Features

**1. Asking the reviewer to specify**
- **Test**: Does any author post ask the reviewer to spell out a criticism already made (which step is wrong, which metric, setup or implementation, or which direction to improve in after the reviewer declined)? A general "let us know if you have further concerns" does not count.
- **Counts**: yes in 0 of 10 raised, 5 of 10 unchanged (006, 018, 093, 152, 167).
- **Quotes**: Raised, 183, after listing new runs: "If the reviewer feels we missed any particular set of training parameters, please do not hesitate to let us know." Unchanged, 006: "In the interest of improving our method, we would appreciate clarification on where either step lacks rigor."
- **Why it might work**: the question hands the work back and signals the authors have not taken in an objection the reviewer thinks was clear.
- **Confound**: some questions are fair (in 167 the linked code really was centralized), and they often follow a reviewer who has already decided.

**2. Re-raised item gets nothing new**
- **Test**: In the authors' last reply to a reviewer follow-up naming a remaining concern, is that item left without a new result, figure or table and without the requested change (only restated argument, decline, deferral or a question)?
- **Counts**: yes in 1 of 10 raised (186, after the score was already raised), 4 of 10 unchanged (006, 018, 105, 167); among threads with such a follow-up, 1 of 3 raised and 4 of 6 unchanged.
- **Quotes**: Raised, 039: "As requested, we have run BigCodeBench Instruct pass@1 evaluations for >1B parameter models and updated the submission PDF accordingly (please see Section 3.3.2, Figure 3, and Appendix Table 8)." Unchanged, 105: "... the first-order term can easily be reintroduced by adding a single line of code to our implementation." Unchanged, 167, after the reviewer pasted the exact code lines: "Given these scope constraints, we will leave this comparison to future work."
- **Why it might work**: a repeated request tells the authors where the score hangs, and calling it easy or valuable without doing it confirms the gap.
- **Confound**: the requests left open (Shampoo, DFedSAM) may have cost more than BigCodeBench.

**3. Declined with nothing in its place**
- **Test**: Does any answer say a requested baseline, dataset or experiment will not be run (no code, resources, out of scope, future work, data does not allow it) and report no other new result in that same answer?
- **Counts**: yes in 2 of 10 raised (144, 183), 5 of 10 unchanged (018, 093, 105, 152, 167).
- **Quotes**: Raised, 104: "KAMPNet: The GitHub repository only includes processed data, and the implementation code is unavailable." then "To address this limitation to some extent, we have included two additional recent baselines for the sequential diagnosis prediction task." Unchanged, 018: "Due to resource constraints we chose a limited number of baselines."
- **Why it might work**: the substitute answers the worry behind the request (in 104, an old newest baseline) even when the named run fails.
- **Confound**: whether a substitute exists depends on the field and on compute.

**4. Granting the main objection**
- **Test**: Take the weakness the reviewer calls most critical or hardest, else the first weakness not about writing. Does the answer contain a sentence granting that this problem applies to the authors' own paper or method ("can indeed lead to", "we agree", "this limitation", "the reviewer is right")?
- **Counts**: yes in 7 of 10 raised (026, 039, 047, 071, 104, 183, 221), 3 of 10 unchanged (018, 019, 103).
- **Quotes**: Raised, 047: "In practice, we have observed that directly inputting results into an LLM for evaluation can indeed lead to unstable outcomes." Unchanged, 093: "Our setting is purely vision-based RL problems, using only image observations without access to ground-truth states, with added distractions."
- **Why it might work**: granting the reviewer's reason first shows the authors understood why it matters, so the evidence reads as an answer and not a defence.
- **Confound**: "we agree" overall does not separate the groups, and fixable objections are also the easiest to grant.

**5. Asking for the score**
- **Test**: Does any author post, general response included, ask the reviewer to raise, reevaluate or reconsider the score, or name a positive score as the goal?
- **Counts**: yes in 0 of 10 raised, 3 of 10 unchanged (018, 019, 103).
- **Quotes**: Raised, 039: "We would appreciate it if you could please let us know if you have any additional concerns preventing a recommendation for acceptance." Unchanged, 103: "If we have addressed your concerns, we kindly ask you to reevaluate your score."
- **Why it might work**: asking which concern is left invites one more exchange, while a score request asks the reviewer to close a question they still think is open.
- **Confound**: authors may ask because they sense the reviewer is stuck, and three threads is a small count.

## Nothing here
- **Where the main objection sits**: it is answered first in 7 of 10 raised and 9 of 10 unchanged threads; 071 answered it third and still moved the reviewer.
- **Narrowing a claim in the paper**: rescoping a claim appears in both groups (raised 026, 183; unchanged 103, 105, 152). What differed was whether it reached the claim still in dispute: 103 rewrote Hypothesis 2 but never gave the per-feature evidence the reviewer said would earn a 6.
- **The "While X, Y" concession frame**: granting the known part and then stating what is new appears in raised 071 ("While generating preference data is a consensus...") and unchanged 167 ("While our work builds on NTK-FL...").

Note: in 116 the reviewer raised to 6, then lowered it for a reason outside the paper.
