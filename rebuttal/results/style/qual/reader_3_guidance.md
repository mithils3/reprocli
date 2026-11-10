# Reader 3: reader guidance and economy

Raised replies keep the reviewer inside the reply, so every answer can be judged from the text on the screen, and when the reviewer misread something the authors blame the paper's wording and say what they rewrote. Unchanged replies more often hand work back to the reviewer, by pointing to the general response, other threads or an external link, by asking what the reviewer meant, or by saying the point was already in the paper. They also spend sentences on the authors' own diligence where raised replies work a case or state a result's limits.

## Features

**1. Sends the reviewer elsewhere**
- **Test**: Does any author post under this review ask the reviewer to (a) read the general response or replies to other reviewers, (b) open an external link to see a new result, (c) run or inspect code, or (d) say more precisely what they meant or which works they had in mind?
- **Counts**: yes in 0 of 10 raised, 7 of 10 unchanged (001, 002, 026, 043, 108, 118, 163); in 4 of the 7 the request came before the reviewer said the score would stay.
- **Quotes**: Raised: "Specifically, with 40% cost reduction, OCCAM is able to achieve less than 1% accuracy drop while the baselines suffer from accuracy drops of at least 7%." (raised-169, repeating the general-response result in place). Unchanged: "We would deeply appreciate it if you could read the general comment we wrote at the top of the rebuttal page." (unchanged-108).- **Why it might work**: A reviewer reading for two minutes can only credit what is on the screen. **Confound**: Redirects cluster on concerns shared across reviewers, such as novelty, which are harder to settle anyway.

**2. Correction without owning the text**
- **Test**: Does any answer say the reviewer misread, or that something they called missing or unclear is already in the paper, without that answer admitting the presentation was at fault or saying what was added or rewritten to fix that point?
- **Counts**: yes in 1 of 10 raised (170), 8 of 10 unchanged (001, 002, 026, 043, 080, 108, 118, 195).
- **Quotes**: Raised: "We acknowledge that this motivation is not clearly stated in the paper." (raised-238). Unchanged: "While our baselines did use different input formats, we clearly stated it in our original draft." (unchanged-118). "The results of the conditional generators can be found in the supplementary material (page 3)." (unchanged-195).
- **Why it might work**: Treating the reviewer's confusion as a wording problem lets the reviewer and the authors both be right. **Confound**: It overlaps with the known dismissive-disagreement signal, and reviewers who misread may simply be less engaged.

**3. Authors praise their own conduct**
- **Test**: Does any author post under this review describe the authors' own effort, cost, commitment, honesty, thoroughness or pioneering status, as opposed to a property of the method or a result?
- **Counts**: yes in 1 of 10 raised (185), 5 of 10 unchanged (043, 108, 118, 163, 195); four of the five came before the reviewer said the score would stay.
- **Quotes**: Raised: "the difference in “Time to Baseline Best Loss” between SGD and PDT (648.39 seconds vs 507.62 seconds) is much larger than the standard deviations of both methods" (raised-148, where the evidence carries the care). Unchanged: "As oppose to many published open-source code-bases, we are proud to adhere to pep8 standards in addition to provide rigorous documentation" (unchanged-195).- **Why it might work**: Self-description spends attention on a claim the reader cannot check and suggests the content alone may not persuade. **Confound**: Authors who expect to lose may write more of it, so it may be a symptom.

**4. One case worked through**
- **Test**: Does any answer carry one concrete case through at least two steps, either explicit arithmetic with the numbers shown or a named scenario or toy instance traced through the method?
- **Counts**: yes in 6 of 10 raised (082, 089, 148, 169, 170, 185), 2 of 10 unchanged (001, 026).
- **Quotes**: Raised: "we could calculate the average number of epochs for the Baseline to converge is 2145.36/21.45 = 100" (raised-148). "For instance, in Door Open (Figure 2a of the draft), the subtasks are (i) reaching the door handle" (raised-185). Unchanged: "Overall, both terms are indispensable for achieving a balanced semantic style transfer." (unchanged-043, answering why both terms are needed). "For example, they assign different attention weights to image tokens and input text tokens when generating specific output text tokens." (unchanged-080, the whole mechanism answer).
- **Why it might work**: A worked case lets the reviewer check the answer in seconds without rereading the method. **Confound**: Two of the eight (089, 026) were requested, and method papers lend themselves to toy cases.

**5. Own result stated with limits**
- **Test**: Does any author sentence say the authors' own method or finding is worse than, only equal to, or only slightly better than a baseline or setting, or that its gain is limited somewhere?
- **Counts**: yes in 7 of 10 raised (065, 082, 089, 148, 166, 170, 185), 3 of 10 unchanged (002, 080, 163).
- **Quotes**: Raised: "However, as shown in Table 2, TCTO shows limited improvement on large-sample datasets." (raised-065). "As shown in the table below, GST achieved comparable results, but DUSt3R" (raised-082). Unchanged: "However, the results already demonstrate clear convergence, validating that AHL-Gaussian significantly outperforms C51 on these tasks." (unchanged-097, in a post admitting the runs "could not reach 200M steps"). "These limitations further underscore the robustness and fidelity of our approach compared to GSGEN." (unchanged-002).
- **Why it might work**: A summary line that claims only what the numbers show tells the reviewer the other summary lines can be trusted. **Confound**: Authors with strong results can afford to admit a weak cell.

## Nothing here

- **First sentence answers or sets up background.** Most answers open with the answer or the action in 8 of 10 threads in each group, and raised-166 and raised-169 opened most answers with background ("Our current evaluation covers 7 mainstream image classifiers", raised-169) and still moved the reviewer.
- **Echoing the reviewer's labels and words.** Nine of ten threads in each group head each answer with the reviewer's own item.
- **Opening and closing lines of the whole reply.** Openings are formulaic thanks in both groups, explicit score requests appear in 5 of 10 raised and 4 of 10 unchanged, and content-free reminders in 2 and 3. Pasted repetition did not block a raise (raised-166 repeats one paragraph three times).
