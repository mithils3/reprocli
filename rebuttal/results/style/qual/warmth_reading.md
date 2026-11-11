# Warmth in ICLR author replies: a close reading, and our five drafts read against it

Basis: 100 ICLR 2025 threads read in full, 70 where the reviewer raised the score and 30 where it stayed, drawn with seed 20261110 and preferring reviews with concerns like ours. Corpus quotes are verbatim with the thread id in brackets. "Reviewer:" marks the reviewer's words after the reply. "Draft:" marks our text.

## A. What kind replies sound like

**1. The opening is one sentence and names something the reviewer actually said.**
- "We are glad to hear that the reviewer finds the problems addressed in the paper of great significance" [t264]
- "Thanks so much for appreciating the theoretical and experimental contributions of our work." [t374]
- "We are happy that you acknowledge the impactful contribution of BirdSet" [t046]

A named detail shows the review was read, which a stock adjective cannot show.

**2. An acknowledgment inside the reply is a clause joined to an action.**
- "We agree that it is an important baseline for panorama generation from text prompts, and have therefore added it to our study." [t284]
- "We agree with your feedback and made these updates in the revised paper version." [t237]
- "(thank you again for pointing us to UCI!)" [t206]

The thanks carries information, because the reviewer sees what their point produced.

**3. Most points get no acknowledgment and begin on the fact.**
- "For completeness, we added the consistency equations for trivariate Partial Information Decomposition as an additional appendix section." [t357]
- "A3: We have added ablation experiments of NN size in Appendix D.5." [t037]
- "Yes, all baseline methods were evaluated across the same 5 runs to ensure consistency and fairness." [t019]

How many is typical: in my reading, a raised-thread first reply of 3,000 to 5,000 characters carries one opening sentence of thanks, one or two short acknowledgments inside the answers, and at most one closing line. None inside is common. Five is the most I saw at this length, and only where each one was joined to an action. Three anchors, all raised. [t128], about 4,500 characters, has an opening thanks, one "We agree with the reviewers" inside an answer, a thanks for typos, and no closing line. [t037], about 4,900 characters and seven answers, has one opening line and nothing after it. [t284], about 5,000 characters and four points, is the warm end: five short acknowledgments, each worded differently and each followed at once by what was done. Answering at once reads as respect for the reviewer's time.

**4. When authors do acknowledge, the words are small and different each time.**
- "Good question. We specifically refer to the Scandeval suite" [t349]
- "This is a good suggestion. We created and included an overview figure, which is now Figure 2." [t301]
- "This is a fair criticism; thank you for bringing it up." [t333]

Two or three ordinary words sound like speech, and varied wording shows each point was weighed separately.

**5. A concession names the fault plainly and moves to the fix.**
- "We agree that we should have better supported the decision to employ synchronized group normalization and overlapping predictions." [t284]
- "We realized these points were not explicit in the submission, so we added the following paragraph to the paper." [t333]
- "Unfortunately, this was a labelling mistake." [t301]

There is no drama and no long apology, so the concession reads as confidence.

**6. A correction that hurts the authors' own numbers is stated flatly.**
- "we need to admit that we have a bug in the evaluation script of the 7B model" [t348]
- "which is weaker than the overall trend but still represents a nontrivial relationship" [t034]
- "We observe that this approach performs slightly worse on the PushT task compared to the proposed method" [t095]
- Reviewer: "The updated results appear to be sound." [t348]

The plain report makes every other number in the reply easier to believe.

**7. A request that cannot be met gets a concrete reason first, then what was done in its place.**
- "We could not perform this experiment because for real-world industrial datasets because their dependency graphs are usually considered proprietary." [t374]
- "While a direct RTF comparison is not feasible due to the unavailability of StreamVC's official implementation, we can conduct a fair comparison through algorithm delay metrics and model complexity." [t263]
- "If the reviewer has concrete suggestions of out-of-distribution data points for evaluation we would be glad to run our attack against them." [t369]

The reason lets the reviewer judge the limit, and the substitute shows the request was taken seriously.

**8. The authors run the thing the reviewer cared about most, and say that it was for them.**
- "To address your biggest concern, we have included **SafeDreamer** [1], the most recent state-of-the-art Safe RL method, in our evaluation." [t212]
- "we acknowledge the importance of evaluating OpenAI models given their widespread use" [t256]
- "As requested by the reviewer, we conducted experiments with MiDl on Ego4D dataset." [t075]

In [t212] and [t075] the first reply explained why the run was missing and the reviewer did not move. The run moved them.

**9. Disagreement grants what is true, gives the reason, and leaves a door open.**
- "This is true, however to effectively generate unit tests one needs knowledge of the entire file under test." [t237]
- "We are open to exploring any modifications if we made any mistake, but we believe the above two verifiers confirm that it parses correctly." [t256]
- "We hope the reviewer agrees that for the Vega-lite and privacy case studies, a purely grammar-based solution is infeasible." [t409]

The reviewer keeps their standing while the authors keep their position. In [t256] the reviewer then found the error on their own side.

**10. When the answer was already in the paper, the authors take the blame for the unclear text.**
- "However, we realize that this might not be clear throughout the rest of our text" [t301]
- "which might give the impression that the discretization error was omitted" [t412]
- "We agree this is not clear and will clarify this in the next revision, thanks!" [t349]

The reviewer is never told they missed something.

**11. A number arrives with one clause that says what it means.**
- "equating to 5 incorrectly classified samples out of all validating samples (more than 50k)" [t252]
- "indicating substantial agreement with human-selected summaries" [t062]
- "making the outlier score computation a negligible portion (approximately 1.2%) of the overall training time" [t195]

The clause does the reading for the reviewer, which is a courtesy that a bare count withholds.

**12. Limits are stated candidly when the reviewer asked about them.**
- "have not yet been tested empirically within our setting" [t371]
- "although the effect of choosing slightly fewer or slightly more bins has not yet been conclusively analyzed" [t357]
- "We speculate that AD demonstrates the in-context ability only on relatively easy tasks" [t068]

An honest hedge on an asked question reads as trustworthy.

**13. The closing is one line that invites more and asks for nothing.**
- "We are happy to follow up if something is not clear." [t333]
- "Please don't hesitate if any questions or remarks remain!" [t349]
- "If you decide not to respond further, that is entirely understandable." [t371]

## B. What lands badly

**1. Telling the reviewer they misread, or grading their understanding.**
- "You might have overlooked Table 2" [t423]
- Reviewer: "I am aware of Table 2" [t423]
- "The reviewer may have some misunderstandings regarding our data synthesis approach." [t085]
- "You've understood correctly!" [t263]

It puts the authors above the reviewer. In [t085] the reviewer's next message showed they had understood all along.

**2. Pointing at the paper as if that settles it.**
- "As our paper clearly states:" [t192]
- "We have described it clearly in our paper (Line 159-161)" [t220]
- "Other hyperparameters used in the model have already been provided in the paper." [t115]

It tells the reviewer the fault is theirs. In [t075] "As mentioned in Section 5.1" changed nothing until the experiment was run.

**3. Thanks as a tic.**
- "Thank you for your suggestion. This is not what we mean here." [t345]
- "Thank you for this comment." [t435]
- "We hope this helps address your concern." [t221]

The same sentence, or a near copy of it, opens or closes answer after answer in these threads, so it stops meaning anything, and it reads worst when a contradiction follows.

**4. Inflated praise of the reviewer or of the paper.**
- "Thank you for raising this profound question" [t129]
- "we are more than glad to find these comments very insightful" [t008]
- "We believe this is an interesting and insightful work in data synthesis area." [t085]

Large adjectives sound written by a machine or by someone who wants something.

**5. Declaring the matter closed, and pleading for the score.**
- "We believe we have now fully addressed W2." [t227]
- Reviewer: "However, my concern W2 has not been fully addressed" [t227]
- "An increased score is critically important to our work at this stage." [t303]
- "We kindly remind you that ICLR guidelines discourage requests for significant additional experiments." [t227]

The verdict belongs to the reviewer, and taking it from them invites the opposite verdict.

**6. Promises and thin excuses in place of results.**
- "We are committed to reporting these results as soon as they are available." [t213]
- Reviewer: "I checked the current version of the PDF and could not find the Replogle results noted in the reply" [t213]
- "would however require computational efforts that would make it hard to include it in time" [t236]
- Reviewer: "Simply aggregate the results in a different way." [t236]

A promise gives the reviewer nothing to score, and an excuse they can see through costs trust.

**7. Blunt contradiction.**
- "Contrary to the reviewer’s concern" [t138]
- "is misplaced" [t171]
- "It would be unfair to dismiss the innovation of our paper" [t226]

The content could have been said with a reason in place of a ruling.

**8. Volunteering a weakness nobody asked about.**
- "so there could be potential confounders that affect our performance on the claims." [t011]
- Reviewer: "The possibility of confounders, as stated by the authors, make the results even more weak." [t011]

**Raised and unchanged threads, as an impression.** The unchanged replies argue about framing more and bring fewer new results ([t223], [t213], [t221]). They put disagreement early and promise more than they show ([t119], [t236], [t205]). Politeness alone did not move a score: [t360] and [t322] are courteous and stayed where they were. Several cold replies were raised because the requested result was there ([t072], [t192], [t138], [t220]). Tone decides how the evidence is received, and the evidence still has to be there.

## C. Phrase bank

**Opening**
- "Thank you for the insightful review." [t115]
- "We thank Reviewer MXUG for the detailed review." [t284]
- "We thank you for your detailed review and constructive feedback." [t128]
- "Thank you for your review and your feedback. We address below your points:" [t098]
- "Thanks a lot for the review!" [t264]
- "We would like to thank the reviewer for their thorough technical review." [t435]
- "We thank the reviewer for the feedback and would like to discuss the weaknesses and questions outlined." [t068]
- "Thank you for your comments. We have revised the paper to correct the typos and ambiguous claims you raised." [t037]

**Acknowledging**
- "Good point." [t349]
- "We appreciate the attentive study from the reviewer." [t256]
- "Thank you for bringing PanFusion to our attention." [t284]
- "The reviewer has rightfully pointed out" [t212]
- "we understand your concern about potential data leakage" [t252]
- "Thanks for pointing out this confusion." [t279]
- "which initially puzzled us as well" [t034]
- "You raised a great point on verbosity control at test time." [t181]

**Conceding**
- "You are correct that the current questions are relatively simple" [t326]
- "We agree also this comes out unclear." [t349]
- "We apologize for not including these findings in the initial submission" [t062]
- "Upon reflection, the term "hybrid" might seem ambiguous in this context." [t242]
- "We will reduce the emphasis and claims regarding the hard constraints in the writing." [t212]
- "It is true that RGP shows some overlap with the baselines in certain cases." [t345]
- "In the above answer, we make a slight mistake in the verification" [t089]
- "Yes we agree that we have not accounted for time for generating 512 training samples." [t072]

**Declining a request**
- "such modifications are not feasible for the following reasons:" [t095]
- "we chose not to repeat this specific ablation study" [t284]
- "is too computationally expensive for us at the moment and it is left for future research" [t068]
- "Considering the limited time, we did not retrain the vocoder." [t263]
- "this is a normative question outside the scope of our paper" [t128]
- "running multiple repetitions was simply infeasible" [t333]
- "Time and engineering resources were the main constraints" [t322]
- "lies somewhat outside the main scope of this paper" [t371]

**Disagreeing**
- "We argue that Rust would still fall into our paradigm" [t237]
- "We hope to point out that the advantage of the proposed method lies in the better speed and accuracy tradeoffs" [t037]
- "However, our evaluation setting is more controlled" [t369]
- "However, this approach involves constructing a separate trie" [t409]
- "first, let us clarify a potential misunderstanding" [t371]
- "We feel obligated to say that this is a theory paper." [t206]
- "but contend that it remains more effective than ranking-based methods" [t062]
- "If we understood correctly, this is the same work as [3]" [t259]

**Introducing a result**
- "To clarify reviewer’s concerns, we conducted an additional experiment" [t068]
- "Following your suggestions, we further compare" [t439]
- "In response to your comment, we have taken models from Table 1" [t038]
- "The table below shows that our model achieves more than 0.90 consistency" [t279]
- "We also make a copy here for your convenience:" [t348]
- "As you can see, when no choices are provided, the performance significantly drops." [t326]
- "Motivated by this, we design the following experiments." [t264]
- "To further address this concern though, we added an additional robustness check in Appendix B" [t128]

**Closing**
- "We hope our revisions address the reviewer’s concerns." [t284]
- "Please feel free to ask if any additional clarifications are needed" [t098]
- "We'd be happy to address any further questions the reviewer may have." [t409]
- "We are open to further feedback to enhance the paper." [t374]
- "Please do not hesitate to let us know if you have any additional comments." [t081]
- "We would be happy to answer anything else in addition." [t371]
- "we are eager to continue the discussion" [t369]
- "We thank you again for your feedback." [t128]

## D. Our five replies, line by line

I reread the cut-back files. Measured against A3, each reply now carries a realistic amount of thanks: an opening, one to three acknowledgments tied to an action, and a closing. None is over-warm, and nothing in them tells a reviewer they misread. What remains is a shared template across the posts, one empty thanks, one flat refusal, and two places in the reply to YGTR where a result arrives with no sentence that speaks to the reviewer's question.

### general.md

Stays: the second sentence, which names what each reviewer praised (A1), and the totals sentence, which gives 70 beside 73 with no comment (A6).

- Draft: "The revision adds these analyses:" The opening thanks is not yet tied to anything the reviews produced (A2). Suggested: "Following the reviews, the revision adds these analyses:"

As a whole it sounds like a person, briefly, and that is the right length for a general post.

### YGTR_1.md

Stays: the opening pair of sentences. "We ran the frontier models and production harnesses you asked for and measured each confound you named" is our version of [t212] in A8 and the strongest line in the five files. The sentence explaining how to read the table stays (A11), and so does the reason for leaving out Claude Code (A7).

- Draft: "We agree that stronger models and production harnesses make the benchmark more informative, and the revision adds both." This is the second acknowledgment in three sentences and repeats the opening, which is a little more agreement than a real reply carries here. Suggested: "We agree that stronger models and production harnesses make the benchmark more informative."
- Draft: "The frontier runs stop early." Five words with no frame read as a ruling on the models the reviewer asked for. Suggested: "One thing we noticed in these runs is that the frontier models stop early."
- Draft: "A coder that saw neither the verdict nor the harness labelled the main failure" The heading asks whether the findings change, and the paragraph opens on method and gives the answer last, so it reads as a lab log (A3, A11). Suggested: open with "The mix of failures shifts in the frontier runs, and Run is again the easiest tier." and end with "The frontier runs reproduce [7 of 14] at Run, [0 of 13] at Retrain and [3 of 17] at Reimplement (Section 5.3)." In a reply about coding agents, "coder" can also be taken for an agent. Suggested: "An annotator that saw neither the verdict nor the harness".

As a whole: yes at the top, then it turns into a report. The two added sentences keep the voice of someone answering this reviewer.

### YGTR_2.md

Stays: the first sentence of W2, which answers before it explains. "We agree, and we reran" stays (A2). "Thank you for suggesting this check, which changed two grades" is the best acknowledgment in the set, because it credits the reviewer with a change that lowered our own count, and "The revision counts both as not reproduced" follows it plainly (A6). W2 needs no thanks added.

- Draft: "6 cells with no graded run and the 21 environment failures among the 24 of W2" This reads as a ledger. Suggested: "6 cells with no graded run, and the 21 of W2's 24 build and dependency failures that came from the environment"
- Draft: "We would be glad to answer any further questions. Thank you again for the detailed review." The same two sentences close three posts, and "the detailed review" already opened YGTR_1. Suggested: "We would be glad to discuss any of these results further."

As a whole: yes. This is the reply that most sounds glad the reviewer pushed.

### T29u_1.md

Stays: "We agree that one run per cell leaves the comparisons open to noise" (A5), "Where the two graders disagree, the auditor is the stricter one", and the plain report that the best Run count moves from 14 to 13 (A6). One agreement in 3,800 characters is what [t128] carries at the same length.

- Draft: "Thank you for the careful review and for your encouraging words about the task and the evaluation design." It shares one frame with the other two openings ("Thank you for the ... review and for your ... words about"), and the area chair reads all three. Suggested: "Thank you for the careful review. We are glad that you found the task important and the evaluation design careful."
- Draft: "We would be glad to answer any further questions. Thank you again for your time." Template again. Suggested: "Please let us know if anything here needs more detail."

As a whole it sounds like a careful colleague. The middle is all numbers, which is what this reviewer asked for, so no thanks should be added there.

### rqBN_1.md

Stays: the opening, and the W2 account from "so we first checked whether any agent had used it" to "the agents left the logs alone in 371 of 372 runs", which is the most human paragraph in the set. "Following your comment we have also closed the gap" stays (A2).

- Draft: "Thank you for raising this." A bare thanks with no content is the tic of B3, and the same paragraph already credits the reviewer later. Suggested: delete it and begin with "The harness wrote commands.log".
- Draft: "We are not able to provide one within our resources." The refusal comes before its reason, so it reads as a shrug (A7). Suggested order: "We agree that a human-expert reproduction would be the gold-standard baseline. In PaperBench, ML PhDs reached 41.4% of the replication rubric after 48 hours of work on a paper. At that allowance one pass over our 100 papers is about 4,800 expert-hours (100 × 48), or 120 working weeks, which is more than we are able to provide. The revision reports what we can measure in its place."

As a whole: yes, and with the bare thanks removed it sits at two acknowledgments in 4,000 characters, which is what the raised replies carry.

## E. Five things to change first

1. **YGTR_1, failure-modes paragraph.** Open with a sentence that answers the heading ("The mix of failures shifts in the frontier runs, and Run is again the easiest tier."), and turn "The frontier runs stop early." into an observation ("One thing we noticed in these runs is that the frontier models stop early."). This is the reviewer who gave the 2, and these are the two places where the reply stops speaking to them.
2. **rqBN_1, Q1.** Put the 4,800 expert-hours before the refusal, so that the "no" reads as arithmetic.
3. **Break the template across posts.** Three openings share one frame, and the four closings are one sentence with small variations. Reword the T29u opening with the reviewer's own words, give YGTR a closing about these results, and drop the repeated "the detailed review".
4. **rqBN_1, W2.** Delete the bare "Thank you for raising this." and keep "Following your comment we have also closed the gap".
5. **Hold the amount of thanks where it is.** The drafts now match what raised replies carry: one opening, one or two acknowledgments joined to an action, one closing. The only trim is "and the revision adds both" in YGTR_1, and the only addition is "Following the reviews" in the general post. Any other effort is better spent on the ledger sentence in YGTR_2 Q3.
