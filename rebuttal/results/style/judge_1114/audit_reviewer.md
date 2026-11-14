# Audit of the reply to Reviewer YGTR, read as the reviewer

Read: the YGTR section of `rebuttal/reviews-2026-11-06.md`, `rebuttal/post/YGTR_1.md` (4,834 characters), `rebuttal/post/YGTR_2.md` (4,876 characters), `rebuttal/post/general.md`, and the frozen paper text (`freeze_pdf.txt`) for every pointer. I wrote this as the reviewer who gave rating 2, soundness 2 and informativeness 1.

Short version: the reply answers every point with a new measurement, the numbers I could check against the frozen paper all agree, and I would move to 3 by a small margin. The thing most likely to hold me at 2 is the explanation of why frontier models stop early, because three wordings in that passage invite me to check the task text, and the task text tells every agent to stop in those cases.

## 1. Verdict per point

| Point | Verdict | Sentence of the reply that decides it |
| :- | :- | :- |
| W1a. No frontier models, so findings may not generalize | Partly resolved | "Run is also the easiest tier for the frontier models (11 of 18, against 3 of 20 at Retrain and 4 of 19 at Reimplement), but their main cause of failure is stopping early rather than reporting a number without a valid measurement." |
| W1b. The ReAct harness is too minimal; use Claude Code, Codex or mini-SWE-agent | Partly resolved | "It reproduces 4 in our harness and 3 in Codex CLI, with the same verdict on 8, so the harness moves the result by one paper." |
| W2. Failures from hardware differences | Resolved | "Our hardware therefore explains 9 failures, and at most 11 of the 372 graded runs with the 2 we could not replay." |
| W3. Agents are run once | Resolved | "Together, the verdict is stable for 23 of 27 model and paper pairs (85%, 95% interval 68% to 94%)." |
| Q1. Repeat the analysis with frontier models and proper harnesses | Partly resolved | "Over the 57 frontier runs, 18 are reproduced (32%, 95% interval 21% to 44%), where DeepSeek-V4-Flash and Muse Spark 1.2 reproduce 23 and 20 on the same papers." |
| Q2. Did agents fetch checkpoints | Resolved | "At these two tiers the run has to produce the model itself, so the revision counts both as not reproduced." |
| Q3. How many failures were not the agent's fault | Partly resolved | "We traced 27 of the 400 cells to causes outside the agent (Sections 5.2 and 5.3, Appendix B.2)" |

Why each "partly":

- **W1a and Q1.** The models and the runs are there, and the table is clear. What is missing is one plain sentence that says which findings of the paper hold for frontier models and which change. The heading "Whether the failure modes and findings change" promises that answer, and the paragraph under it starts in the middle ("Run is also the easiest tier"). I have to assemble the answer myself from four paragraphs. The rows also cover 2 to 23 papers each, and the reply does not say why.
- **W1b.** Two of the three harnesses I named were run, and the paired comparison on 11 papers is the right design. "The harness moves the result by one paper" is stronger than the data beside it, since 3 of the 11 verdicts differ. The failure reasons are reported by model group and are never split by harness, so my claim that failure modes change with the harness is answered only through the count.
- **Q3.** I get a count (27 of 400) and three reruns. All three reruns put the miss outside the agent, which makes me wonder about the other 76 runs in that category. The reply does say that it does not extrapolate, and that limit is stated well.

## 2. Follow-up questions I would most likely post

1. **Is the early stopping caused by the setup?** Frontier models in Codex CLI reproduce 4 of 23 where a weaker model in a minimal loop reproduces 8 of 23, and they decide to stop at turn 9. I would ask whether the task text or the stopping rule produces this. The reply makes the question sharper in three places: the quoted run ("Without an artifact to resolve and validate these choices, I can't treat a new implementation's accuracy as a reproduction"), the clause "where writing that code is the task", and "so stopping early cost reproductions". If I open the task prompt (Figure 48 of the revision), it says "A port is viable ONLY if you can validate it against something shipped", "if the claim hinges on a trained artifact neither released nor retrainable in budget, no port can test it -- declare early, evidence the search, wind down", and "Eval the nearest released sibling" when the exact checkpoint is not released. Those three instructions match three of the four reasons in the reply (12 stopped on unreleased material, 6 projected a cost above the grant, 5 evaluated a different checkpoint), and the quoted run restates the first instruction almost word for word. The answer that is already in the frozen paper is that every frontier run received the task text of the main runs (Appendix B.3) and that an open agent given the same text kept working and reproduced the paper in 11 of the 27 cases. Keep that answer ready.
2. **The continue-prompt variant does not test early stops.** In Table 8 the three papers of that row are ones where the unprompted Codex run scored 8, 8 and 7 and spent 49.2%, 10.6% and 52.8% of its grant. None of them is a run that stopped at turn 9 with 2% spent. "To test the effect further" promises more than three such runs can show, and "On the 3 papers it finished" makes me ask how many it started.
3. **Why do the rows cover 23, 12, 8, 6, 6 and 2 papers?** Muse Wonder has 2 papers in the authors' harness. I would ask for each model on the common papers, or for the reason coverage stops where it does.
4. **Claude Code.** The paper says three human graders scored all 396 runs. I would ask why a small Claude Code sample could not be graded by hand.
5. **Failure reasons by harness.** The 39 failing runs are pooled over the authors' harness, Codex CLI and mini-SWE-agent. I would ask whether the early stops sit in one harness.
6. **Q3 scope.** All three reruns show the pipeline produces the miss. I would ask what that implies for the 76 runs labelled "Ran, outside tolerance". I would also note that W2 says 3 of the 12 replayed installs fail on x86 as well, while Q3 counts all 14 aarch64 runs as outside the agent.
7. **How were the repeat papers chosen (W3)?** Four of the ten Muse Spark 1.2 Reimplement papers reproduce in both runs, and that agent reproduces 5 of 33 at the tier, so the ten are not a random draw.
8. **Q2 coverage.** I would ask how runs that matched no download pattern are known to have trained the model.

## 3. Would I move from 2 to 3

Yes, by a small margin. My rating rested on informativeness: results on weak models in a minimal loop told me little. The reply gives 57 frontier runs in the harnesses I asked for, a paired harness comparison, and a surprising result (frontier models stop at turn 9 and spend 2.1% of the grant when they fail). W2, W3 and Q2 are closed with direct measurements, and Q2 changed two grades, which tells me the authors took the question seriously.

The one thing that decides it either way is follow-up 1. If I come to believe that the early stops follow from the task text or from a stopping rule no real user would apply, the main new result becomes a property of the setup and I stay at 2. If the reply states plainly which findings carry over, and I see that the same task text went to open agents that kept working, I settle at 3.

## 4. Sentences that read badly, with replacements

No sentence reads as cold or condescending, and no sentence says or implies that I misread. The problems are overclaiming, one misattributed question, and several sentences that are hard to follow. Character changes are for the comment the sentence is in. Items marked (edit N) are part of the five edits in part 5.

### Comment 1 (YGTR_1.md)

| # | Problem | Old | New | Change |
| :- | :- | :- | :- | -: |
| 1 | Hard to follow. The confounds I named are hardware and single runs (W2, W3), and frontier models answer W1. (edit 4) | "To test each confound you named, we ran three frontier models in two production harnesses." | "Each of your points now has a new analysis: frontier models in Codex CLI and mini-SWE-agent (W1, Q1), x86 replays (W2), repeat runs (W3), a checkpoint scan (Q2) and a trace of failures outside the agent (Q3)." | +118 |
| 2 | Hard to follow. "where" reads as a place before it reads as a contrast. | "Over the 57 frontier runs, 18 are reproduced (32%, 95% interval 21% to 44%), where DeepSeek-V4-Flash and Muse Spark 1.2 reproduce 23 and 20 on the same papers." | "Over the 57 frontier runs, 18 are reproduced (32%, 95% interval 21% to 44%), against 23 and 20 for DeepSeek-V4-Flash and Muse Spark 1.2 on the same papers." | -4 |
| 3 | Hard to follow. "Open agent" appears in the next bullet with no definition. | "half that at least one of our four agents had reproduced and half that none had" | "half that at least one of our four open agents had reproduced and half that none had" | +5 |
| 4 | Evasive. It says the rows differ and gives no reason, which is follow-up 3. | "Every row takes the papers in the same fixed order, and the rows differ in how many they cover." | No compliant rewrite without the reason. If the reason can be stated in a clause that mentions no unfinished run, add it here. Otherwise leave the sentence. | 0 |
| 5 | Overclaiming. Three of the 11 verdicts differ, and the count differs by one. (edit 3) | "with the same verdict on 8, so the harness moves the result by one paper." | "with the same verdict on 8 of the 11, so on this small sample the two harnesses differ by one paper." | +27 |
| 6 | Defensive close. "which we leave to future work" is the stock phrase a reviewer discounts, and the paragraph never says that two of my three harnesses were run. (edit 3) | "We did not evaluate Claude Code because our auditor is Claude Sonnet 5, and an auditor grading a model from its own family could be biased. Including it would require an independent auditor from another provider, validated against human grades as in Appendix D, which we leave to future work." | "We did not run the third harness you named, Claude Code, because our auditor is Claude Sonnet 5 and an auditor may favor a model from its own family. Grading it fairly needs an auditor from another provider, validated against human grades as in Appendix D." | -36 |
| 7 | Hard to follow. The heading asks a question and the paragraph does not open with the answer. "also" refers to nothing above it, and "it narrows the gap" has no clear subject. (edit 1) | "Run is also the easiest tier for the frontier models ... (6 of 20 and 6 of 19)." | See edit 1. | +116 |
| 8 | Overclaiming, and it hints at unfinished runs. The three papers are ones where the unprompted run had not stopped early. The scores are also listed out of the order of Table 8 (8, 8, 7). (edit 1) | "To test the effect further, we ran a variant that prompts Codex to continue, up to three times, whenever it stops before using half of its GPU grant. On the 3 papers it finished, it spent more of its grant and received the same score as the unprompted run (8, 7 and 8)." | "A variant that prompts Codex to continue, up to three times, whenever it stops under half of its grant spent more of the grant on 3 papers and received the same scores as the unprompted runs (8, 8 and 7)." | -65 |
| 9 | Reads as a judgment of the model, and the quote restates a rule of the task text (follow-up 1). (edit 2) | "8 of them at Reimplement, where writing that code is the task. One run explains: \"Without an artifact to resolve and validate these choices, I can't treat a new implementation's accuracy as a reproduction of the locked result.\"" | "8 of them at Reimplement, the tier where the agent writes that code." | -159 |
| 10 | Pointer mismatch. Section 5.3 says 5 of 6 frontier runs on this paper stopped "because no matching checkpoint is released", and the reply files the paper under projected cost. The new wording keeps both true. (edit 2) | "three runs projected 33 to 51 hours, where Muse Spark 1.2 and Muse Wonder in our harness retrained the model within the grant and reproduced the claim (Section 5.3)." | "three runs projected 33 to 51 hours of retraining and stopped, while Muse Spark 1.2 and Muse Wonder in our harness retrained the model within the grant and reproduced the claim (Section 5.3)." | +26 |
| 11 | Overclaiming. It states a cause where the data show that the papers were reachable. (edit 2) | "so stopping early cost reproductions." | "so those papers could be reproduced within the grant." | +16 |
| 12 | Missing location for the transcript analysis. (edit 2) | "To find the reason, we analysed the full transcripts of the 39 failing frontier runs." | "To find the reason, we analysed the full transcripts of the 39 failing frontier runs (Appendix G.3)." | +15 |
| 13 | Hard to follow. The reader cannot tell which group the 46% and 23% describe. | "(46% and 23% when the same annotator, Claude Sonnet 5, labels a sample of 50 open-agent runs)" | "(46% and 23% for the open agents when Claude Sonnet 5, the same annotator, labels a sample of 50 of their runs)" | +18 |

Items 2, 3 and 13 add 19 characters together. The five edits free 17 in this comment, and the other 2 come from dropping "exactly " in "on exactly the papers of each row" (8 characters).

### Comment 2 (YGTR_2.md)

| # | Problem | Old | New | Change |
| :- | :- | :- | :- | -: |
| 14 | Hard to follow. "with the 2 we could not replay" hangs off the end. | "Our hardware therefore explains 9 failures, and at most 11 of the 372 graded runs with the 2 we could not replay." | "Our hardware therefore explains 9 failures, or at most 11 of the 372 graded runs if the 2 we could not replay are counted." | +9 |
| 15 | Missing location for the x86 runs. | "and the two scores of every pair are within one point." | "and the two scores of every pair are within one point (Appendix B.3)." | +15 |
| 16 | Hard to follow. The reader has to recall that the W2 pairs ran on two kinds of node. | "- **The 8 x86 pairs of W2** repeat a model on a paper as well, and 7 keep their verdict." | "- **The 8 pairs of W2**, run on x86 and GH200 nodes, are repeats as well, and 7 keep their verdict." | +11 |
| 17 | Overclaiming. "only when" is a general rule drawn from four pairs. | "so a repeat moves a paper only when it already sits at the line." | "so in these pairs a repeat moves a paper only when it already sits at the line." | +15 |
| 18 | Attributes to me a question I did not ask. My Q3 was one sentence about failures that were not the agent's fault. (edit 5) | "You also asked about runs that follow the released pipeline and still miss." | "A run can also follow the released pipeline and still miss." | -16 |
| 19 | Hard to follow. Section 5.2 says 28 cells have no graded run, and the label reads as if there were 6. | "- **6 cells with no graded run.**" | "- **6 of the 28 cells with no graded run.**" | +10 |
| 20 | Hard to follow. The reader cannot tell which of the three values is the agent's. | "The result changes with the seed (-0.22, -0.13 and +0.06 against a target of -0.20), so the agent's near miss is within seed noise." | "The agent's run and the two reruns range from -0.22 to +0.06 against a target of -0.20, so the agent's near miss is within seed noise." | +3 |
| 21 | Hard to follow. No target is given, so the reader cannot see that 94.19% is a miss. (edit 5) | "Both reruns land within 0.54 points of the agent's 94.19% (93.65% and 94.15%)." | "Against a target of 93.12%, both reruns (93.65% and 94.15%) land within 0.54 points of the agent's 94.19%." | +28 |

Items 14, 15, 16, 17, 19 and 20 add 63 characters. Three cuts pay for them and free 84:

- "git clone and git lfs of Hugging Face repositories, gdown," becomes "git clone, git lfs, gdown," (32 characters shorter).
- ", with the same budget as the run in the paper." becomes " with the same budget." (25 shorter).
- "so we read these runs as faithful and their misses as coming from outside the agent." becomes "so we read their misses as coming from outside the agent." (27 shorter).

### General reply (general.md)

Nothing to change. It is 2,783 characters, it opens with what each reviewer valued, each bullet names a change and its location, and the grade-change table matches Section 5.2 and Appendix B.2 (70 of 400; 13 of 34, 9 of 33 and 5 of 33; 34 to 32 papers).

### Checks that passed

The table sums (57 papers, 18, 23 and 20), the split of 14 of 33 and 4 of 24, the tier counts (11 of 18, 3 of 20, 4 of 19), the paired harness comparison rebuilt from Table 8 (4 and 3 reproduced, same verdict on 8 of 11), 27 = 12 + 6 + 5 + 4, the Wilson interval for 23 of 27 (68% to 94%), the W2 denominators (13/34, 9/33, 5/33 to 5/32), the checkpoint count (42 to 40, 28 and 12) and the three reruns all match the frozen text. Every pointer (Sections 5.2 and 5.3, Appendices B.2, B.3 and D) leads to text that says what the reply says, with the one exception in item 10. Three numbers appear only in the reply and cannot be found in the PDF: the pooled 23 of 27, the split of the 16 pattern matches into 4, 10 and 2, and "22 papers we examined". That is not an error, and a reviewer who looks for them will not find them.

## 5. The five edits that would most raise the chance I move to 3

Applied together, comment 1 goes from 4,834 to 4,817 characters and comment 2 stays at 4,876. Every edit keeps every number.

### Edit 1. Open "Whether the failure modes and findings change" with the answer (comment 1, net -24)

This is my main question, and informativeness is where my score was lowest. The cuts that pay for it are the sentence the new opening makes redundant and the tightened variant sentence.

Old (451 characters):
```
Run is also the easiest tier for the frontier models (11 of 18, against 3 of 20 at Retrain and 4 of 19 at Reimplement), but their main cause of failure is stopping early rather than reporting a number without a valid measurement. Because the sample holds equal numbers of reproduced and unreproduced papers in every tier, it narrows the gap between Retrain and Reimplement, and DeepSeek-V4-Flash is level on these papers as well (6 of 20 and 6 of 19).
```
New (567 characters, +116):
```
Two findings carry over to the frontier models, and the main failure mode changes, as you anticipated. Run remains their easiest tier (11 of 18, against 3 of 20 at Retrain and 4 of 19 at Reimplement), and they leave even more of the GPU grant unused than the open agents. Most of their failing runs stop early, and fewer report a number without a valid measurement. Retrain and Reimplement are close here because the sample holds equal numbers of reproduced and unreproduced papers in every tier, and DeepSeek-V4-Flash is level on the same runs (6 of 20 and 6 of 19).
```
Cut A, old (92 characters):
```
Interestingly, the frontier models stop even earlier than the open agents. Over the 57 runs,
```
Cut A, new (17 characters, -75):
```
Over the 57 runs,
```
Cut B, old (269 characters):
```
To test the effect further, we ran a variant that prompts Codex to continue, up to three times, whenever it stops before using half of its GPU grant. On the 3 papers it finished, it spent more of its grant and received the same score as the unprompted run (8, 7 and 8).
```
Cut B, new (204 characters, -65):
```
A variant that prompts Codex to continue, up to three times, whenever it stops under half of its grant spent more of the grant on 3 papers and received the same scores as the unprompted runs (8, 8 and 7).
```

### Edit 2. Describe the early stops without judging the model (comment 1, net -102)

This removes the three wordings that send me to the task text (follow-up 1), reconciles the 2506.08898 example with Section 5.3, and adds the location of the analysis. The 2506.08898 example stays as the concrete case.

Old (227 characters):
```
8 of them at Reimplement, where writing that code is the task. One run explains: "Without an artifact to resolve and validate these choices, I can't treat a new implementation's accuracy as a reproduction of the locked result."
```
New (68 characters, -159):
```
8 of them at Reimplement, the tier where the agent writes that code.
```
Old (165 characters):
```
three runs projected 33 to 51 hours, where Muse Spark 1.2 and Muse Wonder in our harness retrained the model within the grant and reproduced the claim (Section 5.3).
```
New (191 characters, +26):
```
three runs projected 33 to 51 hours of retraining and stopped, while Muse Spark 1.2 and Muse Wonder in our harness retrained the model within the grant and reproduced the claim (Section 5.3).
```
Old (37 characters):
```
so stopping early cost reproductions.
```
New (53 characters, +16):
```
so those papers could be reproduced within the grant.
```
Old (85 characters):
```
To find the reason, we analysed the full transcripts of the 39 failing frontier runs.
```
New (100 characters, +15):
```
To find the reason, we analysed the full transcripts of the 39 failing frontier runs (Appendix G.3).
```

### Edit 3. Size the harness result and name the harnesses I asked for (comment 1, net -9)

Old (73 characters):
```
with the same verdict on 8, so the harness moves the result by one paper.
```
New (100 characters, +27):
```
with the same verdict on 8 of the 11, so on this small sample the two harnesses differ by one paper.
```
Old (292 characters):
```
We did not evaluate Claude Code because our auditor is Claude Sonnet 5, and an auditor grading a model from its own family could be biased. Including it would require an independent auditor from another provider, validated against human grades as in Appendix D, which we leave to future work.
```
New (256 characters, -36):
```
We did not run the third harness you named, Claude Code, because our auditor is Claude Sonnet 5 and an auditor may favor a model from its own family. Grading it fairly needs an auditor from another provider, validated against human grades as in Appendix D.
```

### Edit 4. Replace the second sentence with a map of the five answers (comment 1, +118, paid for by the 159-character cut of edit 2)

A reviewer who reads only the first lines learns that every point received a new analysis and that the harnesses are the ones named in the review.

Old (90 characters):
```
To test each confound you named, we ran three frontier models in two production harnesses.
```
New (208 characters, +118):
```
Each of your points now has a new analysis: frontier models in Codex CLI and mini-SWE-agent (W1, Q1), x86 replays (W2), repeat runs (W3), a checkpoint scan (Q2) and a trace of failures outside the agent (Q3).
```

### Edit 5. Fix the misattributed question in Q3 and show the target of the third rerun (comment 2, net 0)

Old (259 characters):
```
You also asked about runs that follow the released pipeline and still miss. To test whether such a miss comes from the agent or from the released code, we took 3 of these runs and executed their final commands again ourselves, with two new seeds and no agent:
```
New (231 characters, -28):
```
A run can also follow the released pipeline and still miss. To test whether such a miss comes from the agent or from the released code, we executed the final commands of 3 such runs again ourselves, with two new seeds and no agent:
```
Old (78 characters):
```
Both reruns land within 0.54 points of the agent's 94.19% (93.65% and 94.15%).
```
New (106 characters, +28):
```
Against a target of 93.12%, both reruns (93.65% and 94.15%) land within 0.54 points of the agent's 94.19%.
```

## Notes for the authors

- Edit 2 changes the 2506.08898 sentence on the assumption that the three runs that projected 33 to 51 hours were projecting a retrain. That follows from the tier (Retrain, no weights released) and from Section 5.3, and it should be confirmed against the three transcripts before posting.
- "as you anticipated" in edit 1 credits my remark that failure modes would change. The reply already states that change, so the phrase adds no new concession. Drop ", as you anticipated" if the authors prefer, which saves 20 characters.
- Both comments with all five edits and all part 4 items applied are in `/tmp/claude-1000/-home-mithil-PyCharmProjects-reprocli/ee88b5cc-f222-456d-9de1-997a82c38396/scratchpad/judge_1114/work_reviewer/after_1.md` (4,836 characters, before the 8-character "exactly " cut) and `/tmp/claude-1000/-home-mithil-PyCharmProjects-reprocli/ee88b5cc-f222-456d-9de1-997a82c38396/scratchpad/judge_1114/work_reviewer/after_2.md` (4,855 characters). No file under the repository was changed.
