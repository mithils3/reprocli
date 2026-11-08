# iclr-review reference

Rule numbers match SKILL.md. Each rule gives its basis and then verbatim lines from ICLR 2025 OpenReview threads, tagged raised (reviewer moved from 5 or lower to 6 or higher, 244 threads) or unchanged (reviewer replied and stayed at reject, 197 threads). Quotes keep their original spelling and punctuation. Lines marked "coder note" are the coding agent's summary of a thread and are not quotes from it.

Rule strengths and numbers are in SKILL.md and stats.md; this file keeps sources, method and verbatim examples.

## Rules, bases and examples

**1. Focus on the reviewer just below the accept line and on the one furthest below the others (source).** Kargaran et al. (2025) found that the reviewer's own pre-rebuttal rating (average coefficient 0.67) and the co-reviewers' mean rating (0.37) predict score change better than reviewer engagement (0.25), with 5 to 6 the most common move. Gao et al. (2019) found the gap to co-reviewers was the largest predictor at ACL 2018, and the corpus cannot test either finding because both groups were selected below the accept line.
- "Having these questions clarified and seeing that 3 other reviewers viewed this work highly, I will increase my score." ([raised](https://openreview.net/forum?id=sIE2rI3ZPs))

**2. Put every reviewer point in one sheet (source, search excerpts only).** Reviewers settle their score point by point, so a missed point stays open in their final note.
- "Regarding Q3, I am now convinced by the overall contribution. Q4 and Q5 were due to my misunderstandings, and I appreciate your clarifications." ([raised](https://openreview.net/forum?id=636M0nNbPs))
- "Some of my questions remain unaddressed" ([unchanged](https://openreview.net/forum?id=bVdcAZAW2h))

**3. Thank the reviewer in one sentence, then list the changes as bullets (corpus for the list, house rule for its place).** The corpus supports the list, but its place at the top is a house rule, since the opening move itself shows no gap. The Reviewer Guide asks reviewers to state what changed their recommendation, and a list at the top hands them that sentence.
- "We are grateful for your thoughtful review and for highlighting areas of confusion in the experiments presented in our earlier manuscript. In response, we have made substantial improvements, including:" ([raised](https://openreview.net/forum?id=nzgvkQM3EH))

**5. Give every point its own label or heading, such as "W1" with a short paraphrase (corpus).** Headings let the reviewer close points by label.
- "The responses addressing Weakness 1 and Weakness 2 have effectively resolved my concerns." ([raised](https://openreview.net/forum?id=rDRCIvTppL))

**6. A sentence that judges the paper or its authors also names the change (house rule).** A concession that names the finding and the fix in one place gives the reviewer and the area chair a change they can cite. The corpus shows no penalty for blunt admissions, and raised threads contain some ("It is our mistake missing this important work.", [raised](https://openreview.net/forum?id=Y2RW9EVwhT)), so this rule governs tone.

The frame is "The paper said A; the code (or data, or proof) does B; we changed C at D." A filled version from a raised thread: the paper said "competitive performance", the results were second best, and the authors wrote "We agree with your comment – we rephrased “competitive performance” to “second-best results”." ([raised](https://openreview.net/forum?id=tkqNDbukWW)).

Allowed openers, each followed in the same or next sentence by the change and its location:
- "We agree with your comment" ([raised](https://openreview.net/forum?id=tkqNDbukWW))
- "This is a fair criticism; thank you for bringing it up." ([raised](https://openreview.net/forum?id=rvXdGL4pCJ))
- "We see how this sentence might be unclear and would like to clarify." ([raised](https://openreview.net/forum?id=VfYShlQbj7))
- Pattern written for this skill: "We acknowledge that [finding]", with the fix next

Banned as standalone sentences, because each judges the paper or the authors and names no change:
- Pattern written for this skill: "You are right ... our paper overstated"
- "We rushed a bit before submission." and "We acknowledge the fact that the writing is not up to par." (both [unchanged](https://openreview.net/forum?id=UG62fwmOxZ))

The word "overstated" is fine inside a sentence that names the fix, as in "carefully adjust sections that might have overstated" (rule 7 phrasing below).

**7. When a reviewer flags an overclaim, reword it everywhere (coder notes).** Reviewers who raised often named softened claims as part of the reason, so show the change twice: a two-column old and new table in the reply, and the new wording in color in the PDF. When the code or method does less than the paper says, a reviewer needs a weaker claim and, where possible, a measurement of the gap.
- "We agree that the title "RLHF secretly performs imitation learning" may overstate the case, particularly given the nuances of the transition between imitation learning and reinforcement learning within the RLHF pipeline." ([raised](https://openreview.net/forum?id=2QdsjiNXgj); coder note: the authors renamed the paper)
- "the authors made significant efforts to address these limitations during the discussion period (by adding experiments, introducing statistical tests, and softening the main claims). As a result, I have adjusted my score." ([raised](https://openreview.net/forum?id=tkqNDbukWW))
- Coder note: "the rebuttal answered with a long defense rather than a changed claim." ([unchanged](https://openreview.net/forum?id=Jyrwd2wja9))

**8. Answer empirical doubts with a new experiment or ablation (corpus).** This is among the largest corpus gaps, and reviewer triggers name the runs.
- "To further address the reviewer’s concerns, we conducted an additional experiment using GPT-4o as the paraphrasing model using our method while keeping all other settings unchanged." ([raised](https://openreview.net/forum?id=8Me0Y01mkY))

**9. Put results in the reply as numbers in a table (corpus).** The corpus shows a gap for numbers in the reply. Tables usually carry new results, so this gap probably overlaps the new-experiment gap in rule 8.
- "While we observe that this slightly decreases the vulnerability ratio from 76% to 62%, the final ratio still largely exceeds the baseline vulnerability ratio of 22%." ([raised](https://openreview.net/forum?id=h2Q3gOIz8q))

**10. Do not answer a doubt with clarification alone when a number can answer it (corpus; coder notes).** Citations and theory do not track a raise. In mBJF0p9yRR and PflweLMInP the coder notes credit the held score to novelty claims with no new evidence.
- "We argue that stochastic approximation with Markovian noise for **non-expansive mappings** has received limited attention in the literature." ([unchanged](https://openreview.net/forum?id=mBJF0p9yRR)); the reviewer replied: "I am not fully convinced of its originality or significance."
- In g6v09VxgFw the authors wrote "We assure the reviewer that our theoretical results are reliable." ([unchanged](https://openreview.net/forum?id=g6v09VxgFw)); its coder note credits the held score to a numeric check that left the reviewer unconvinced, so that thread is weak support.
- Coder note: "the rebuttal re-asserted novelty and cited another reviewer's score change" ([unchanged](https://openreview.net/forum?id=PflweLMInP))

**11. Run the reviewer's named baseline under your settings (concerns.md).** A raise can follow even when the baseline wins ([coder note](https://openreview.net/forum?id=nf4v09zw6O)).
- "We agree that it is an important baseline for panorama generation from text prompts, and have therefore added it to our study." ([raised](https://openreview.net/forum?id=M2SsqpxGtc))

**12. Disagree with a fact and keep the tone level (corpus).** A number or definition gives the reviewer something they can check. Gao et al. (2019) found politeness mattered more for keeping a score than for raising one.
- "We first clarify that after training, HOPE and init3 in fact have about the same amount of large Hankel singular values." ([raised](https://openreview.net/forum?id=RZwtbg3qYD))
- "It is evident that the reviewer's concern regarding the comparative results is in conflict with the advantages the reviewer has acknowledged." ([unchanged](https://openreview.net/forum?id=NPNUHgHF2w))
- "No, the implementation to combine these two paradigms involves almost no challenge and in fact straightforward." ([unchanged](https://openreview.net/forum?id=ln6QnzBd8o))
- A firm line that stays level: "Since the two frameworks are fundamentally distinct, we do not believe a direct mapping between their components exists." ([raised](https://openreview.net/forum?id=gYNBQygmXG))

**13. Disagree only where you must (corpus).** Concede and scope what you can: a stated limit closes a point that no new run can close.
- "However, WAM will not be able to decode both messages if one watermark is directly on top of the other." ([raised](https://openreview.net/forum?id=IkZVDzdC8M))
- "We have added this as an explicit limitation in `Sec. 7` in our revised manuscript." ([raised](https://openreview.net/forum?id=l11DZY5Nxu))

**14. Write the answer sentence in the reply, then its location as section, page and line (corpus).** Reviewers judge the revised paper, and a clarification that lives only in the thread can be lost. Give the location as Section, page and line, as in the second line below.
- "The clarifications provided in your rebuttal are very helpful but are not reflected in the current manuscript or appendix. A revised manuscript incorporating these points would be necessary to reconsider the evaluation." ([unchanged](https://openreview.net/forum?id=DtATVd5NLc))
- "In the revised manuscript, we have included the necessary clarifications (page 3 line 160)." ([raised](https://openreview.net/forum?id=kiQhuq45hr))

**15. Never tell a reviewer they misread (source).** Soto Valero (2022) advises never saying a reviewer lacks understanding and, when several reviewers misread a point, admitting the paper is unclear and fixing it.
- "We kindly request reviewers not to overlook the context surrounding this statement." ([unchanged](https://openreview.net/forum?id=9VRFPC29nb))
- The same situation handled as a text problem: "We see how this sentence might be unclear and would like to clarify." ([raised](https://openreview.net/forum?id=VfYShlQbj7))

**16. Give a substantive point a full answer of 150 words or more with its number and location (corpus).** The median thread carried 950 words of author text in both groups, so length did not separate them. Short answers worked when they settled the question.
- "Thank you, this sufficiently answers my questions." ([raised](https://openreview.net/forum?id=hWmwL9gizZ))
- "This led to a seemingly longer rebuttal, but we believe that it will streamline the work for the reviewer." ([raised](https://openreview.net/forum?id=qKgd7RaAem))

**18. Answer each reviewer message and post each promised run once it exists (corpus; coder notes).** Raised threads had a median of 4 author posts against 3, and the coder notes tie two unchanged threads to a promised run never posted or an upload the reviewer never saw, so post a dated notice as soon as each item exists. Deferred requests appear in three threads, two unchanged and one raised, and a withdrawal confounds one of the unchanged ones, so treat them as anecdote.
- "I'd like to thank the authors again for their effort and engagement with my concerns! Please include all these new analysis in the revision of the paper and I have raised my score again." ([raised](https://openreview.net/forum?id=uhaLuZcCjH))
- "Also, I was waiting for the improved version of the paper in terms of writing but the authors have not uploaded it yet." ([unchanged](https://openreview.net/forum?id=UG62fwmOxZ))
- "We uploaded the revised manuscript at approximately 3:30 PM UTC on November 27, well before our submission deadline (November 27 End-of-day AoE)." ([unchanged](https://openreview.net/forum?id=UG62fwmOxZ))
- "After reviewing the long-sequence dataset samples, I increased my score." ([raised](https://openreview.net/forum?id=VaowElpVzd))
- Coder note: "the authors deferred the MIPS recomputation, the topology test and the supervised baselines to future work" ([unchanged](https://openreview.net/forum?id=BfI0D1ci9r))
- Coder note: "deferred the restructuring to the camera-ready" ([unchanged](https://openreview.net/forum?id=OnBCQgi2LY))
- Coder note: "framed the requested cross-domain study as future work" ([raised](https://openreview.net/forum?id=dRXxFEY8ZE))

**19. To a silent reviewer, send one civil reminder that names what changed and asks for no score (house rule).** Reminders showed no gap between the groups, so they are neutral in this sample. Rule 18 covers a reviewer who writes back; this rule covers a silent one.
- "We wanted to touch base with you as the deadline for the author-reviewer discussion phase is approaching on November 26." ([raised](https://openreview.net/forum?id=sGqd1tF8P8))

**20. Keep the revision recognizably the same paper (source and one thread).** The Author Guide lets area chairs ignore changes that are significantly different from the original. In one raised thread the authors narrowed the stated goal and the reviewer raised, so a narrower claim fits within the rule.
- "Given the significant difference between the proposed revised version from the one we reviewed, I believe that this paper would greatly benefit from another full round of reviews." ([unchanged](https://openreview.net/forum?id=7BDUTI6aS7))
- "We revised the title, abstract, model name, and the entire manuscript to clarify that our goal is to solve the Entropic Semi-Unbalanced Optimal Transport problem." ([raised](https://openreview.net/forum?id=py34636XvR))

## Concession phrasing

Each line names the finding and the change. Use the pattern and fill in the paper's own location.

A claim was overstated
- "We went through the paper to identify and carefully adjust sections that might have overstated BirdSet’s positioning." ([raised](https://openreview.net/forum?id=dRXxFEY8ZE))
- "In light of this, we have carefully reviewed and rephrased all instances in our paper where Neural Collapse is discussed, ensuring that our claims are accurate and avoid overstatement." ([raised](https://openreview.net/forum?id=eN0RyRVbSm))

An experiment or baseline was missing
- "We have added the experiments with Gaussian random initialization to the revised paper (lines 370-400)." ([raised](https://openreview.net/forum?id=9ngFxN83j2))
- "To address this limitation to some extent, we have included two additional recent baselines for the sequential diagnosis prediction task." ([raised](https://openreview.net/forum?id=y1UHa9sl2w))

A safeguard or guarantee was weaker than described, fixed by weakening the claim
- "The present study does not provide theoretical guarantees for the proposed algorithms, a limitation shared by existing jailbreak attack methodologies to the authors' knowledge." ([raised](https://openreview.net/forum?id=uhaLuZcCjH))
- "We acknowledge that the difference between MGCFNN and MGFNN in the ablation study (Table 4) is not significant." ([raised](https://openreview.net/forum?id=ThhQyIruEs))

The same case, fixed by measuring the gap
- "We also adopt the reviewer’s suggestion to manually verify the results of CodeQL, by investigating 50 generated completions of the test set from unattacked, Init-only attacked, and optimized attacked models, across all CWEs and models." ([raised](https://openreview.net/forum?id=h2Q3gOIz8q)), followed by "The precision of CodeQL among these samples was 98%."

A presentation was unclear
- "We created and included an overview figure, which is now Figure 2." ([raised](https://openreview.net/forum?id=STBPaproaB))
- "We have clarified this in L1002 (Sec. C) of the revised version." ([raised](https://openreview.net/forum?id=kWGHZuW5yJ))

## Missteps

Coders found at least one misstep in nearly every thread, so one misstep rarely decides a thread. These are the recurring kinds.
- Sending the reviewer elsewhere: "Please refer to the general response." ([raised](https://openreview.net/forum?id=4xWQS2z77v))
- Offering in place of doing: "We could include a figure of the signalling game." ([unchanged](https://openreview.net/forum?id=X8Mhumi52G))
- Excusing a gap: "Due to resource constraints we chose a limited number of baselines." ([unchanged](https://openreview.net/forum?id=DKZjYuB6gc))
- Pressure on the score or on other reviewers: "If no further concerns remain, we kindly request a reevaluation of your score." ([raised](https://openreview.net/forum?id=BM9qfolt6p))

## Published advice and the corpus

Kargaran, Nikeghbal, Yang and Ousidhoum (2025), "Insights from the ICLR Peer Review and Rebuttal Process" (arXiv 2511.15462): in ICLR 2025, 23% of reviews rose after rebuttal, 75% stayed and 1% fell, and the own rating and co-reviewer mean were the strongest predictors. Their strategy results were left unread and are unused here.

Gao, Eger, Kuznetsov, Gurevych and Miyao (2019), "Does My Rebuttal Matter?" (NAACL), found at ACL 2018 that response text added little over scores (macro F1 .526 to .540) and that politeness mattered more for keeping a score than for raising it. The corpus leans the same way on tone, though the intervals overlap.

The ICLR 2026 Author and Reviewer Guides allow revisions until the end of the public discussion, ask authors to communicate changes clearly, let area chairs ignore changes that are significantly different, and ask reviewers to state what changed their recommendation. Page and line locations are house practice drawn from raised threads. ICLR 2027 uses a 4-point rating scale, and its guide was not read, so check its dates, limits and accept line.

Parikh, Batra and Lee (2020), "How we write rebuttals", was seen only in search excerpts. They write for the area chair as well as the reviewer and keep a sheet of every comment.

Soto Valero (2022), "How to Write a Good Paper Rebuttal", targets software-engineering venues with short limits. He recommends 500 to 750 words, a 50-word thanks, major concerns first, new experiments with data links, never saying a reviewer lacks understanding, and treating a point several reviewers misread as unclear text. The corpus agrees on new experiments, finds no gap for generic thanks, and finds longer replies at ICLR, where the number of comments is unlimited.

## Method note

Pre- and post-rebuttal scores came from Paper Copilot's iclr-insights data for ICLR 2025, and thread text from the Hugging Face dataset Jasonpicky/openreview_raw. With selection seed 22528 and one reviewer per forum, raised threads were drawn where the rating went from 5 or lower to 6 or higher, and unchanged controls where the reviewer replied and stayed at 5 or lower. Threads with no author post under the review were dropped. 441 threads (244 raised, 197 unchanged) were recoded blind: coders saw the review, the authors' general response and the authors' posts, with the group, scores, reviewer follow-ups and score-change sentences removed, ten mixed threads per batch (build_blind.py, blind_brief.md, blind_stats.py). An earlier coding that showed coders the group and wrote booleans as strings inflated thread-level gaps about twofold and is retired. Cells report the share of threads with Wilson 95% intervals. A script and a hand check found every quote attributed to a thread verbatim in its source thread after normalising whitespace, punctuation and quote marks, and every coder-note line word for word in the coding output.

Limits: with 244 raised and 197 unchanged threads, a gap needs about 9 points before its 95% interval clears zero. The design is observational, so a feature that is more common in raised threads may follow from a stronger paper or a more open reviewer. Codes come from language-model agents blind to the outcome, and some categories were applied unevenly, severity and the opening codes in particular. The sample covers one year, one reviewer per forum, and only moves across the accept line.
