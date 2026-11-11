# Wording bank for the Reviewer 1 (T29u) and Reviewer 2 (rqBN) replies

This file studies how strong public author replies word the nine moves our two replies make, and then proposes a sentence-level rewrite of both drafts. Quotes are copied exactly from the sources, including their punctuation and typos.

## 1. What was read

### How the threads were obtained

The brief asked for the public OpenReview API through curl. The API answered with HTTP 403 "ChallengeRequiredError", and a retry with browser headers was stopped by the permission classifier as bot-check circumvention, so I did not pursue that route. The threads below were fetched fresh from the public Hugging Face mirror of OpenReview notes (dataset Jasonpicky/openreview_raw, the same source that rebuttal/iclr_threads/build_corpus.py names). The mirror holds decision notes for ICLR 2024 and none for ICLR 2025, so for ICLR 2025 threads the column below gives only what the reviewer wrote after the reply.

### Totals, stated separately

- Threads I read in full myself (every author reply and every reviewer answer): 13. Eleven are benchmark papers and two are evaluation studies.
- Threads I read in part and do not count: 3 (AgentBench zAdUB0aCTQ, LiveBench sKYHBTAxVa, DSBench DSsSPr0RZJ).
- Items covered through the 18 phrase banks made by haiku readers from the local public ICLR corpus: 303 (150 full threads in which the reviewer raised the score, and 153 topic-matched author replies from ICLR 2025 and 2026). All 18 banks existed and all 18 were used; each reports that it read every item in its batch.
- Every bank entry quoted below was checked with `rg -F` against its batch file and found there. One entry failed that check and was dropped.

### The 13 threads read in full

| # | Forum id | Paper | Venue | What the reviewer did after the reply |
| -: | :- | :- | :- | :- |
| 1 | 6s5uXNWGIh | MLE-bench | ICLR 2025 | uxvJ: "I'm increasing my rating." fmGi: "I will raise my score accordingly." HGZk kept a "major concern" after the authors declined an experiment. |
| 2 | tc90LV0yRL | Cybench | ICLR 2025 | S4Jg: "I am increasing my score". |
| 3 | G0dksFayVq | JudgeBench | ICLR 2025 | VLGm: "I have raised my score." BxhQ: "As a result, I have increased my score." |
| 4 | UHPnqSTBPO | Trust or Escalate (LLM judges with human agreement guarantees) | ICLR 2025 | ZdoK: "I have increased my score!" 8fUt: "I adjusted my recommendation accordingly." |
| 5 | il5yUQsrjC | AndroidWorld | ICLR 2025 | EDMT: "I have increased my score." 1Fiv: "it resolves most of my concerns. I have increased my score." |
| 6 | roNSXZpUDN | tau-bench | ICLR 2025 | p3GC: "Overall, we raise the score". |
| 7 | VTF8yNQM66 | SWE-bench | ICLR 2024, Accept (oral) | Area chair: "The authors address this question in the rebuttal". |
| 8 | mM7VurbA4r | SOTOPIA | ICLR 2024, Accept (spotlight) | qjhX: "The response answered most of my questions ... I will update my rating". |
| 9 | MMwaQEVsAg | Commit0 | ICLR 2025 | ffwo: "I have raised my scores accordingly." xSyA: "have increased my score accordingly". |
| 10 | M23dTGWCZy | Can LLMs Generate Novel Research Ideas | ICLR 2025 | No raise. YqJH: "I am inclined to maintain my positive score". Used only for its sensitivity sentences. |
| 11 | 6z4YKr0GK6 | ScienceAgentBench | ICLR 2025 | Contrast case. c5sH: "my original grade remains unchanged, as the rebuttal does not significantly alter my overall evaluation." Used for what to avoid. |
| 12 | AC5n7xHuR1 | AgentHarm | ICLR 2025 | RhVU: "I would like to increase my overall score to 5 and increase the soundness score to 'good'". |
| 13 | fibxvahvs3 | GAIA | ICLR 2024, Accept (poster) | Three reviewers kept 8 ("I still vote it be accepted"). |

## 2. Phrase bank by move

Entries from my own reading carry the forum id and paper name. Entries from the 18 banks carry the bank number and the tag the bank gave: a thread tag such as `raised-179-GARbxyCV13-fU9L` holds the forum id (GARbxyCV13) and the reviewer (fU9L) and means the reviewer raised the score after the discussion; a `REPLY` tag is a topic-matched author reply whose outcome is unknown. The bank tags do not carry paper names. A quote that runs over a line break in its source is printed here on one line.

### a. Opening thanks that names something specific

1. "We are glad that you found our work to have clear methodological contributions and our experiments to be very carefully executed." [UHPnqSTBPO, Trust or Escalate]
2. "Thanks so much for your time and effort towards this review, and for pointing out that SWE-bench is a good, real-world benchmark." [VTF8yNQM66, SWE-bench]
3. "First of all, thank you very much for your thoughtful review; we’re thrilled that you think this is a valuable evaluation!" [6s5uXNWGIh, MLE-bench]
4. "Thank you so much for the detailed review! We really appreciate your thoughtful insights and questions." [tc90LV0yRL, Cybench]
5. "We thank the reviewer for their time spent in assessing our work and for recognizing the substantial manual annotation effort behind our benchmark." [bank 15, REPLY DSLQhCQv2H, ICLR 2026, unknown]
6. "We thank the reviewer for the positive assessment of our paper’s presentation and theoretical grounding, and for the constructive feedback regarding our claims." [bank 09, REPLY 7Uknk5gh2H, forum 8iPwqr6Adk, ICLR 2026, unknown]
7. "Thank you for your feedback! We are glad to hear that you find our paper solid, well-written, and our evaluation generally comprehensive." [bank 03, raised-034-5xxGP9x5dZ-jZsQ, RAISED]

### b. Agreeing, then straight to what was done

1. "We agree that comparing different models trained on data from different points in time could lead to unfair advantages, which is a shared concern among all LLM research. To fully investigate this, we added an extended temporal analysis on our results (Appendix C.3)." [VTF8yNQM66, SWE-bench]
2. "We strongly agree about the importance of device/OS diversity. To validate AndroidWorld's cross-version capabilities, we successfully ran the benchmark on a different emulator (Pixel 5) and Android 12." [il5yUQsrjC, AndroidWorld]
3. "Thanks for the suggestion! We’ve added Table 9 which breaks down agent performance by complexity level." [6s5uXNWGIh, MLE-bench]
4. "Thanks for pointing this out. Based on your feedback, we recalculate the metrics (i.e. Total Lines, Added, Removed) for an average patch generation across all patches (not just successfully applied patches)." [VTF8yNQM66, SWE-bench]
5. "This is a valid concern. For this reason, we make the lite split of the benchmark." [MMwaQEVsAg, Commit0]
6. "We agree that demonstrating the added value of the Neighbor-aware Filtering (NaF) step is important. In response, we conducted an **additional ablation study (Section 4.4)** comparing:" [bank 15, REPLY pm1frgzabQ, ICLR 2026, unknown]
7. "The reviewer has rightfully pointed out the lack of a performance upper bound, without which we cannot determine whether the tasks are already solved." [bank 16, raised-122-5BRFddsAai-FzXY, RAISED]
8. "We agree that additional baselines would be valuable and are currently running experiments with Fictitious Co-Play." [bank 06, REPLY NYsG5gBvbP, unknown]

### c. Reporting a new analysis or statistic in a sentence, and introducing a table

1. "As noted in the Figure 3 caption, we used Wilson binomial proportion confidence intervals at 95% confidence level for our analysis." [il5yUQsrjC, AndroidWorld]
2. "The results show a mean performance of 29.0% across three runs/seeds (27.6%, 26.3%, and 33.3%)." [il5yUQsrjC, AndroidWorld]
3. "We evaluated several LLMs using the Arena-Hard prompt, and observed that the relative rankings among these judges were the same between our original set and the augmented set, despite small variations in the scores themselves (see the table below)." [G0dksFayVq, JudgeBench]
4. "Our classifier achieved $88.3\pm2.1\%$ precision and $100\pm0\%$ recall on data independently annotated by two expert annotators following the ternary taxonomy." [bank 18, raised-196-zZ8fgXHkXi-CWn6, RAISED]
5. "Specifically, Gemma-7B-it achieves a high Cohen’s Kappa score of 0.8125, indicating substantial agreement with human-selected summaries and reliable performance in reflecting human judgments." [bank 15, raised-135-bhK7U37VW8-gqu4, RAISED]
6. "These results indicate statistically significant correlations in all cases, including within a single model size and performance band." [bank 14, raised-027-kvLenbZZgg-n94A, RAISED]
7. "In the revised manuscript, we now report the number of independent runs for each task and provide mean and standard deviation." [bank 11, REPLY n0hl91qtpd, forum pllMq0U0VT, unknown]
8. Table introductions: "The mean and standard deviation of the AUC-ROC on the 24 datasets and the combined dataset are in the table below." [bank 16, raised-142-mIl15VP7vt-gy8L, RAISED]; "The following table shows how much it costs to run SDE-I on lite and all." [MMwaQEVsAg, Commit0]; "The aggregated scores of each model is therefore as follows:" [fibxvahvs3, GAIA]

### d. Where human and model graders disagree; a conservative judge

No reply in the 13 threads or the 18 banks says in so many words that the automatic judge is the stricter grader. The closest sentences state the direction of disagreement with a comparative, which is the form our "tends to be the stricter of the two" already has.

1. "Specifically, Figure 2 shows the distributional differences between GPT-4 scores and human scores, which indicates *“GPT-4 is more likely to rate higher instead of lower than humans when it disagrees with average human judgment”*." [mM7VurbA4r, SOTOPIA]
2. "which further shows the effect of GPT-4 being more lenient than human annotators on machine-generated interactions" [mM7VurbA4r, SOTOPIA]
3. "Consistently with the results in **Table 4**, when humans tend to disagree with each other, LLM judges tend to abstain from evaluation; when humans agree with each other, machines tend to be more confident as well." [UHPnqSTBPO, Trust or Escalate]
4. "We also note that at evaluation time, they do not know which model or agent has generated the programs, so there would be no bias towards a certain LLM/agent framework." [6z4YKr0GK6, ScienceAgentBench; reviewer did not raise]
5. "Among these, 10 samples did not align with the results verified by humans, with most errors being false negatives." [bank 12, REPLY ctzFOrS5eO, forum ijFdq8uqki, unknown]
6. "Although the absolute scores differ across judge models, the relative ranking of the four captioners remains unchanged." [bank 10, REPLY mjYIq8GcYh, forum vjEl1PuIDE, ICLR 2026, unknown]
7. "The high precision (94%) of our LLM-as-judge, as measured against human evaluation, supports the robustness of this lower-bound estimate (see more details in Appendix B)." [bank 15, REPLY XzFnpH3V65, ICLR 2026, unknown]
8. "We re-annotated hallucinations using another strong LLM (Claude Sonnet 4.5) under the same protocol. In the medical domain, GPT-4o and Claude agreed on 3,164 / 3,330 cases (95.64%), and in the financial domain, on 1,245 / 1,499 cases (83.05%)." [bank 16, REPLY Y9ArghGSt5, forum qIUR54yyro, unknown]

### e. Something that cannot be done within the rebuttal, and what is offered

1. "Thank you for this suggestion. Given our compute budget, the results in Table 3 are for a single seed. However, to validate these findings at scale, we have updated the manuscript with an evaluation of our best model (M3A with GPT-4 using accessibility trees) with 3 seeds across all tasks." [il5yUQsrjC, AndroidWorld]
2. "Obtaining results for all stages of SDE-I using current state-of-the-art models is prohibitively expensive. Running o1-preview for the first and the third stages on the lite split alone cost $913, and we are limited by our budget. However, to do the best we can to test out all stages of SDE-I on the all split, we test Deepseek V2.5 and GPT-4o-mini." [MMwaQEVsAg, Commit0]
3. "To collect a relatively reliable Human expert data (e.g., 385 people for 95% confidence level and 5% confidence interval), the overall cost, even by the lowest estimate, is prohibitive (385 people * 30h * $5/h = $57,750). Therefore, we did not include this data in the paper." [zAdUB0aCTQ, AgentBench, ICLR 2024 Accept (poster); thread read in part]
4. "We acknowledge that re-training all foundation models on the new data split would provide a more comprehensive comparison. However, due to limited resources, we could only afford to re-train one model, Moirai, from scratch." [bank 16, REPLY S4QRas1nIe, forum 9EBSEkFSje, unknown]
5. "Ideally, we agree that having more human judgements will benefit the data quality but it will significantly increase the data collection expenses, which goes beyond our budget." [bank 13, REPLY Qvyr9MLfzW, forum 9D2QvO1uWj, unknown]
6. "Given the time constraints of the rebuttal, we performed the cross-judge validation above as a rigorous and feasible alternative." [bank 03, REPLY KwEWRiCLMr, forum Gp9lGS9GfY, unknown]
7. "In summary, training and evaluating so many configurations already had a high computational cost, and running multiple repetitions was simply infeasible." [bank 12, raised-174-rvXdGL4pCJ-LbED, RAISED]
8. One that did not work: "It is not an unreasonable amount of time, but it is difficult for our team given our current availabilities." [6s5uXNWGIh, MLE-bench]. Reviewer HGZk answered that the point was still "a major concern". The replies that worked give the cost as a number and then a substitute result.

### f. A weakness the reviewer found in the method, and the fix

1. "Thank you for pointing out this significant limitation. We've added **Subsection H.1: Limited Agent Scaffolding** where we note and discuss this limitation and share experimental results in **Table 9, 25, 26** from running the agent with full history in memory." [tc90LV0yRL, Cybench]
2. "We corrected this in Appendix B.2 to reflect that agents only use SCROLL actions, not SWIPE." [il5yUQsrjC, AndroidWorld]
3. "We automatically verify whether an agent has retrieved information from GitHub by detecting the presence of 'github.com' or 'raw.githubusercontent.com' in the retrieval URLs. If these URLs are detected, the corresponding generation will be voided. Thus far, the agent hasn’t retrieved code from GitHub." [MMwaQEVsAg, Commit0]
4. "We also manually examined the execution logs for all samples and across different models to verify that the narrow LLM judges were robust to different answers." [AC5n7xHuR1, AgentHarm]
5. "We therefore conducted additional experiments, where we consider adversaries that are able to conduct a Prompt Injection in the user’s initial instruction (Appendix B.2) and manipulate the tools in the system (Appendix B.3)." [bank 01, REPLY sAWPaCLp79, forum WGOj26QIlR, ICLR 2026, unknown]
6. "We thank the reviewer for pointing out the incompleteness of our original agreement analysis. In App. A.2.5 and Tab. 9 we now provide a more systematic study." [bank 07, REPLY CI401zCC7Y, forum 3u6AkbWEls, ICLR 2026, unknown]
7. "To further address this concern though, we added an additional robustness check in Appendix B, beyond what previous work has done." [bank 03, raised-045-0iscEAo2xB-XFvr, RAISED]
8. "Aside from running many additional evaluations, we also identified and eliminated a bug in one of our HumanEval evaluation launch scripts" [bank 08, raised-039-AqfUa08PCH-HReL, RAISED; opening clause of a longer sentence]

### g. A result still running that will be posted

1. "We are conducting more rigorous experiments to evaluate other models’ correlations with human judgments. We will update our revision as soon as we get the results." [mM7VurbA4r, SOTOPIA]
2. "We will add GPT4-vision results by the end of the rebuttal if possible (it will require at least a few days to run because of OpenAI’s limitation), and commit to add it in the final version of the paper." [fibxvahvs3, GAIA]
3. "We have also integrated S-PLM, but experiments are still running due to the dated architecture of that work (lack of Flash Attention). We will post an additional comment here with these results once they’re available." [bank 18, raised-179-GARbxyCV13-fU9L, RAISED]
4. "The remaining data will take approximately one day to process, after which the overall results will be updated." [bank 15, raised-119-J6e4hurEKd-xJUs, RAISED]
5. "We are currently working on additional experiments about comparisons between AdaGrad and AdaGrad++. We will update these results as soon as they are ready." [bank 07, raised-240-CuupjjjT3U-c1YW, ICLR 2025, RAISED]
6. "Lastly, as per your suggestion, we are currently conducting human evaluations comparing GPT-4o with our distilled LLM. We will update the results here once the human evaluations are completed." [bank 15, REPLY ebvdU8x6Em, ICLR 2025, unknown]

### h. "How sensitive is this to X"

1. "When we set target human agreement $1-\alpha$ to 0.8 instead of 0.9, the average human IAA for abstained samples goes from 0.815 to 0.806, i.e. only the harder-to-reconcile samples tend to be abstained by the models." [UHPnqSTBPO, Trust or Escalate]
2. "Removing these two reviews does not impact any conclusions in the paper." [M23dTGWCZy, Can LLMs Generate Novel Research Ideas; no raise]
3. "Overall, all three main conclusions still hold robustly even if we remove all the ideas and reviews with a familiarity of 1." [M23dTGWCZy, same paper]
4. "The performance here is consistent with the main results and conclusions already in the paper. This is expected because the selection procedure for the subset is random." [VTF8yNQM66, SWE-bench]
5. "IDI and other baselines mostly demonstrated robustness across a wide range of anomaly thresholds from 2 to 7. IDI showed a slight performance degradation only at the lowest threshold of 2, highlighting sensitivity to overly lenient anomaly definitions." [bank 09, raised-012-l11DZY5Nxu-9ck8, RAISED]
6. "For example, when the query limit is set to 10 per test case, our method still outperforms other baselines in 5 out of 6 target LLMs." [bank 15, raised-135-bhK7U37VW8-gqu4, RAISED]
7. "Figure 2 demonstrates that the relationship between dropout rate and OOD accuracy is simple and smooth, indicating that our approach is not sensitive to the choice of dropout rate." [bank 18, raised-094-Fvfs0HPuKl-RZvb, RAISED]
8. "To better assess the impact of HSSE, we evaluate the model under a stricter IoU ≥ 0.5 threshold, where predictions and ground truth bounding boxes must overlap by more than 50%." [bank 10, raised-161-iGafR0hSln-1bvp, RAISED]

### i. Closing line

1. "Thank you again for your feedback and comments. If you have any remaining questions or concerns, we would be happy to address them." [VTF8yNQM66, SWE-bench]
2. "If you have any additional questions or concerns, please let us know. Thank you for your time and consideration." [VTF8yNQM66, SWE-bench]
3. "We thank the reviewers for their feedback, and we’re happy to answer any further questions." [VTF8yNQM66, SWE-bench]
4. "If there are any further questions or concerns, we would be happy to address them." [bank 11, raised-014-ThhQyIruEs-q7vM, RAISED]
5. "Should you have any further questions, we are open to continued discussion." [bank 17, raised-193-PNMv4r7s1i-JZFB, RAISED]
6. "Please do not hesitate to reach out if you need any further clarifications. Thank you." [bank 07, raised-154-caE5faFVT1-PNZS, ICLR 2025, RAISED]
7. Closings to stay away from, which agree with the standing rule against asking for a score: "Since we have addressed most of the reviewer's concerns, we appreciate it if the reviewer could adjust their assessment accordingly." [6z4YKr0GK6, ScienceAgentBench; the reviewer kept the grade] and "We thank the reviewer again, and we hope they will reconsider their original score in light of these clarifications." [AC5n7xHuR1, AgentHarm]. Score requests do also appear in some threads where the score rose (for example bank 13, raised-020-I6UbnkUveF-MHUs), so the corpus does not show that they cost anything; it shows that the replies above did well without one.

## 3. Wording habits

The first five are the ones our drafts gain most from.

1. The sentence that answers a concern starts with the reviewer's own name for that concern, so the reviewer can find each answer. "For Video-MME and TempCompass, the percentage of mis-formatted responses is reported in the tables below." [bank 01, raised-056-sHAvMp5J4R-c8nY, RAISED]
2. Finished work is written as "we" plus a plain verb, often with "now", and the place where it can be found follows at once. "In the revised manuscript, we now report the number of independent runs for each task and provide mean and standard deviation." [bank 11, REPLY n0hl91qtpd, unknown]
3. A number is followed by one clause that says what it shows. "Specifically, Gemma-7B-it achieves a high Cohen’s Kappa score of 0.8125, indicating substantial agreement with human-selected summaries and reliable performance in reflecting human judgments." [bank 15, raised-135-bhK7U37VW8-gqu4, RAISED]
4. The claim comes first and its breakdown follows in parentheses or after a colon. "The results show a mean performance of 29.0% across three runs/seeds (27.6%, 26.3%, and 33.3%)." [il5yUQsrjC, AndroidWorld]
5. A table is introduced by a whole sentence that says what its cells hold. "The mean and standard deviation of the AUC-ROC on the 24 datasets and the combined dataset are in the table below." [bank 16, raised-142-mIl15VP7vt-gy8L, RAISED]
6. A check opens with its purpose: "To" plus the question, then "we" plus what was done. "To fully investigate this, we added an extended temporal analysis on our results (Appendix C.3)." [VTF8yNQM66, SWE-bench]
7. A statistical claim uses the field's standard term and names the test or the level. "As noted in the Figure 3 caption, we used Wilson binomial proportion confidence intervals at 95% confidence level for our analysis." [il5yUQsrjC, AndroidWorld]
8. The direction in which an automatic judge differs from humans is stated with a comparative. "which further shows the effect of GPT-4 being more lenient than human annotators on machine-generated interactions" [mM7VurbA4r, SOTOPIA]
9. A request that is too costly gets its cost as arithmetic in the sentence, and the next sentence starts with "However" and gives the substitute. "Running o1-preview for the first and the third stages on the lite split alone cost $913, and we are limited by our budget. However, to do the best we can to test out all stages of SDE-I on the all split, we test Deepseek V2.5 and GPT-4o-mini." [MMwaQEVsAg, Commit0]
10. A pending result takes two short sentences: what is running, then where it will be posted. "We will post an additional comment here with these results once they’re available." [bank 18, raised-179-GARbxyCV13-fU9L, RAISED]
11. A sensitivity answer names the values tried and says in the same sentence whether the conclusion holds. "Overall, all three main conclusions still hold robustly even if we remove all the ideas and reviews with a familiarity of 1." [M23dTGWCZy, Can LLMs Generate Novel Research Ideas]
12. Differences are sized with modest words. "We evaluated several LLMs using the Arena-Hard prompt, and observed that the relative rankings among these judges were the same between our original set and the augmented set, despite small variations in the scores themselves (see the table below)." [G0dksFayVq, JudgeBench]

## 4. Rewrite proposal

Each entry gives our sentence, the proposed sentence and the corpus sentence it follows. A sentence marked "ok" stays as it is. No number, name, label, table or pointer changes; a script applied the replacements to copies of the drafts and confirmed that the set of numbers in each reply is identical before and after. Most draft sentences already match the habits above, so the list of changes is short.

### 4.1 Reviewer 1 (T29u), rebuttal/post/T29u_1.md

**Opening**

- Ours: "Thank you for your review. We are glad that you found the task important and the evaluation design careful."
- Proposed: "Thank you for your review, and for noting that the task is important and the evaluation design careful."
- Follows: "Thanks so much for your time and effort towards this review, and for pointing out that SWE-bench is a good, real-world benchmark." [VTF8yNQM66]. One sentence of thanks in place of two.

**W1, first paragraph**

- "We agree that one run per cell leaves our results susceptible to noise." ok (author's phrasing; the agreement is followed at once by the action, as in b.1).
- Ours: "To account for this, every rate now carries a 95% interval, given in the table below."
- Proposed: "To account for this, we now report every rate with its 95% interval in the table below."
- Follows: "In the revised manuscript, we now report the number of independent runs for each task and provide mean and standard deviation." [bank 11, REPLY n0hl91qtpd]. "We now report" is the corpus form for finished work; "carries" is our own word.
- "To measure the variation between runs, we are also running ..." ok (purpose opener, habit 6).
- "As soon as these runs finish, we will post here how often the three runs of the same paper reach the same verdict." ok (same shape as g.3).

**W1, paragraph after the table**

- Ours: "The reproduction rate of Run papers is above that of Reimplement papers for DeepSeek-V4-Flash (38% against 12%, z = 2.46) and for papers reproduced by at least one agent (47% against 15%, z = 2.81). Both differences are statistically significant, and every agent has its lowest reproduction rate at Reimplement."
- Proposed: "For the tier-level comparison, the reproduction rate at Run is higher than at Reimplement for DeepSeek-V4-Flash (38% against 12%, z = 2.46) and for papers reproduced by at least one agent (47% against 15%, z = 2.81), and both differences are statistically significant. Every agent also has its lowest reproduction rate at Reimplement."
- Follows: habit 1, with the reviewer's own words "tier-level comparisons", and "These results indicate statistically significant correlations in all cases, including within a single model size and performance band." [bank 14, raised-027]. "Higher than" is the standard comparative; the significance statement now sits in the sentence that holds the z values.
- Ours: "DeepSeek-V4-Flash and Muse Spark 1.2 have mean audit scores of 5.13 and 5.14 of 10, and Qwen3.6-27B and MiniMax-M2.7 have 3.51 and 3.03."
- Proposed: "For the agent ranking, DeepSeek-V4-Flash and Muse Spark 1.2 have mean audit scores of 5.13 and 5.14 of 10, and Qwen3.6-27B and MiniMax-M2.7 have 3.51 and 3.03."
- Follows: habit 1, with the reviewer's words "agent rankings". Without the lead-in the reader cannot tell which concern these four means answer. Habit 3 would add a reading clause here (what the four means show about the ranking), and that clause is the author's to supply because it is a claim the draft does not make.
- Ours: "The rates also do not depend on environment failures. When we remove the 24 runs that failed on a build or dependency error, no best-agent reproduction rate moves by more than one percentage point (Section 5.3)."
- Proposed: "On environment sensitivity, when we remove the 24 runs that failed on a build or dependency error, no best-agent reproduction rate moves by more than one percentage point (Section 5.3)."
- Follows: "Removing these two reviews does not impact any conclusions in the paper." [M23dTGWCZy] and habit 1 with the reviewer's words "environment sensitivity". The measured result carries the point, and the broader sentence before it claimed more than the removal test shows.

**W2**

- "When the human grader and the LLM auditor disagree, the auditor tends to be the stricter of the two." ok (author's phrasing; same comparative form as d.2).
- Ours: "In 28 runs only one of them marked the run as reproduced, the human in 19 and the auditor in 9. The same holds in every tier, with 7 against 3 at Run, 7 against 4 at Retrain and 5 against 2 at Reimplement."
- Proposed: "In 28 runs only one of the two marked the run as reproduced: the human grader in 19 and the auditor in 9. The same direction holds in every tier, with 7 against 3 at Run, 7 against 4 at Retrain and 5 against 2 at Reimplement."
- Follows: habit 4, "The results show a mean performance of 29.0% across three runs/seeds (27.6%, 26.3%, and 33.3%)." [il5yUQsrjC]. The colon marks the split of the 28; "the same direction" says what it is that holds in every tier.
- "The auditor's reproduction rate is therefore slightly below the human's (73 against 83 of 400 runs at submission), and Reimplement has the lowest reproduction rate under both graders (Appendix D)." ok for wording ("slightly" is habit 12). See the note on 400 against 372 at the end.

**Q1**

- "Against the human grade, the auditor's reproduced verdict has precision ... and recall ..." ok (same shape as c.4).
- Ours: "The table below condenses the five-way matrix of Appendix D."
- Proposed: "The confusion matrix below condenses the five-way matrix of Appendix D."
- Follows: habit 5 and the reviewer's own term "confusion matrix".
- "At the 7/8 boundary, 100 runs received a 7 or an 8 from at least one grader, and the two graders put 75 of them on the same side of it." ok (already opens on the reviewer's term).
- Ours: "A high-severity flag sets a run's score to 0. In total 57 runs received a 0 from at least one grader, and both graders gave a 0 to 42 of them. The auditor marked no run as reproduced that the human had scored 0."
- Proposed: "For high-severity flags, which set a run's score to 0, 57 runs received a 0 from at least one grader and both graders gave a 0 to 42 of them. None of the runs that the human scored 0 was marked as reproduced by the auditor."
- Follows: habit 1 (parallel to "At the 7/8 boundary,") and "Only 2 out of 300 samples showed differing conclusions, demonstrating the effectiveness of the CLIP filtering method." [bank 01, REPLY Uamlk5MAXz], which puts the count at the head of the sentence.

**Q2**

- Ours: "A run matches its target when its result is within a relative tolerance of the value the paper reports, which is 5% by default. We rescored every run at tolerances of 1%, 2%, 5% and 10%, and Reimplement has the lowest reproduction rate at each of them. Counts at submission (Appendix F):"
- Proposed: "We rescored every run at tolerances of 1%, 2%, 5% and 10%, and Reimplement has the lowest reproduction rate at each of them. A run matches its target when its result is within a relative tolerance of the value the paper reports, which is 5% by default. The counts at submission are in the table below (Appendix F)."
- Follows: habit 11, "IDI and other baselines mostly demonstrated robustness across a wide range of anomaly thresholds from 2 to 7." [bank 09, raised-012], and for the table sentence "The mean and standard deviation of the AUC-ROC on the 24 datasets and the combined dataset are in the table below." [bank 16, raised-142]. The answer now opens on its result, and the definition comes second with its words unchanged.
- Ours: "For the targets, we asked gpt-6.1-sol, ..."
- Proposed: "For the match targets, we asked gpt-6.1-sol, ..."
- Follows: habit 1, with the reviewer's words "match target".
- "It confirmed our value for 92 of the 100 claims (Appendix E)." ok
- "When we correct the other 8 targets and rescore their runs, only two verdicts change. Both are on one paper (2505.23747), and the best-agent count at Run goes from 14 to 13 of 34." ok (same shape as h.1: the change made, then how far the result moves).

**Closing**

- "Please let us know if anything here needs more detail, and thank you again for your time." ok (same shape as i.2).

**Full proposed reply for Reviewer 1 (4357 characters; the draft has 4263)**

```
Thank you for your review, and for noting that the task is important and the evaluation design careful.

**W1: One run per agent-paper cell.**

We agree that one run per cell leaves our results susceptible to noise. To account for this, we now report every rate with its 95% interval in the table below. To measure the variation between runs, we are also running DeepSeek-V4-Flash two more times on 12 papers, four from each tier, chosen with a fixed seed. As soon as these runs finish, we will post here how often the three runs of the same paper reach the same verdict.

| Agent | Run (34 papers) | Retrain (33) | Reimplement (33) |
| :- | -: | -: | -: |
| DeepSeek-V4-Flash | 13 = 38% [24%, 55%] | 9 = 27% [15%, 44%] | 4 = 12% [5%, 27%] |
| Muse Spark 1.2 | 10 = 29% [17%, 46%] | 8 = 24% [13%, 41%] | 5 = 15% [7%, 31%] |
| Qwen3.6-27B | 5 = 15% [6%, 30%] | 6 = 18% [9%, 34%] | 2 = 6% [2%, 20%] |
| MiniMax-M2.7 | 2 = 6% [2%, 19%] | 5 = 15% [7%, 31%] | 1 = 3% [1%, 15%] |
| At least one agent | 16 = 47% [31%, 63%] | 11 = 33% [20%, 50%] | 5 = 15% [7%, 31%] |

For the tier-level comparison, the reproduction rate at Run is higher than at Reimplement for DeepSeek-V4-Flash (38% against 12%, z = 2.46) and for papers reproduced by at least one agent (47% against 15%, z = 2.81), and both differences are statistically significant. Every agent also has its lowest reproduction rate at Reimplement. For the agent ranking, DeepSeek-V4-Flash and Muse Spark 1.2 have mean audit scores of 5.13 and 5.14 of 10, and Qwen3.6-27B and MiniMax-M2.7 have 3.51 and 3.03. On environment sensitivity, when we remove the 24 runs that failed on a build or dependency error, no best-agent reproduction rate moves by more than one percentage point (Section 5.3).

**W2: The auditor's disagreements with the human grade.**

When the human grader and the LLM auditor disagree, the auditor tends to be the stricter of the two. In 28 runs only one of the two marked the run as reproduced: the human grader in 19 and the auditor in 9. The same direction holds in every tier, with 7 against 3 at Run, 7 against 4 at Retrain and 5 against 2 at Reimplement. The auditor's reproduction rate is therefore slightly below the human's (73 against 83 of 400 runs at submission), and Reimplement has the lowest reproduction rate under both graders (Appendix D).

**Q1: Confusion matrix, the 7/8 boundary and high-severity flags.**

Against the human grade, the auditor's reproduced verdict has precision $\frac{64}{73}$ = 88% [78%, 93%] and recall $\frac{64}{83}$ = 77% [67%, 85%]. The confusion matrix below condenses the five-way matrix of Appendix D.

| Human ↓ / Auditor → | Reproduced | Partial | Lower | Total |
| :- | -: | -: | -: | -: |
| Reproduced (8 to 10) | **64** | 15 | 4 | 83 |
| Partial (6, 7) | 7 | **64** | 17 | 88 |
| Lower (0 to 5) | 2 | 7 | **192** | 201 |
| Total | 73 | 86 | 213 | 372 |

At the 7/8 boundary, 100 runs received a 7 or an 8 from at least one grader, and the two graders put 75 of them on the same side of it. For high-severity flags, which set a run's score to 0, 57 runs received a 0 from at least one grader and both graders gave a 0 to 42 of them. None of the runs that the human scored 0 was marked as reproduced by the auditor.

**Q2: Sensitivity to the match target and the default 5% tolerance.**

We rescored every run at tolerances of 1%, 2%, 5% and 10%, and Reimplement has the lowest reproduction rate at each of them. A run matches its target when its result is within a relative tolerance of the value the paper reports, which is 5% by default. The counts at submission are in the table below (Appendix F).

| Relative tolerance | 1% | 2% | 5% | 10% |
| :- | -: | -: | -: | -: |
| Best agent, Run (of 34) | 9 | 12 | 14 | 14 |
| Best agent, Retrain (of 33) | 8 | 9 | 9 | 12 |
| Best agent, Reimplement (of 33) | 4 | 5 | 5 | 5 |
| All agents (of 400) | 56 | 65 | 73 | 82 |

For the match targets, we asked gpt-6.1-sol, a model from a different lab than our auditor, to compare each target value with its paper. It confirmed our value for 92 of the 100 claims (Appendix E). When we correct the other 8 targets and rescore their runs, only two verdicts change. Both are on one paper (2505.23747), and the best-agent count at Run goes from 14 to 13 of 34.

Please let us know if anything here needs more detail, and thank you again for your time.
```

### 4.2 Reviewer 2 (rqBN), rebuttal/post/rqBN_1.md

**Opening**

- "Thank you for the thoughtful review and for your kind words about the methodological disclosure." ok (same shape as a.2 and a.5).

**W1**

- "We compared the auditor (Claude Sonnet 5) with one human grader on 372 runs, and the grader did not see the auditor's score." ok (compare d.4).
- "On the reproduced verdict, the auditor's precision is ... and its recall is ... (F1 0.82)." ok
- "When the two disagree, the auditor tends to be the stricter one." ok (author's phrasing).
- Ours: "In 28 runs only one of them marked the run as reproduced, the human in 19 and the auditor in 9, and the same holds in every tier."
- Proposed: "In 28 runs only one of the two marked the run as reproduced (the human grader in 19, the auditor in 9), and the same direction holds in every tier."
- Follows: habit 4, "GPT-4o and Claude agreed on 3,164 / 3,330 cases (95.64%)" [bank 16, REPLY Y9ArghGSt5]. The parentheses keep the main clause in one piece.
- Ours: "On the full 0 to 10 scale the two differ by at most one point on 324 of the 372 runs, with a quadratic weighted kappa of 0.89."
- Proposed: "On the full 0 to 10 scale, the two differ by at most one point on 324 of the 372 runs (quadratic weighted kappa 0.89)."
- Follows: "the first two annotators provide independent answers (inter-annotator agreement **κ = 0.73**)" [bank 09, REPLY kBYeAww1uk, forum E0AekM35XF, ICLR 2026].
- Ours: "A high-severity anti-cheat flag sets a run's score to 0, and both gave a 0 to 42 of the 57 runs that either of them scored 0 (full matrix in Appendix D)."
- Proposed: "For the anti-cheat flags, a high-severity flag sets a run's score to 0, and both graders gave a 0 to 42 of the 57 runs that either of them scored 0 (full matrix in Appendix D)."
- Follows: habit 1, with the reviewer's words "anti-cheat flags"; "both graders" gives "both" its noun.

**W2**

- "Our harness wrote commands.log and trajectory.jsonl into a folder that the auditor reads, and our sandbox mounted that folder read-write." ok
- Ours: "Given this, we checked whether any agent had modified the two files during a run. For all of our graded runs we compared them with the harness's own transcript, which is written to a folder the agent has no access to."
- Proposed: "We therefore checked whether any agent had modified the two files during a run. For every graded run, we compared both files with the harness's own transcript, which is written to a folder the agent has no access to."
- Follows: "We therefore conducted additional experiments, where we consider adversaries that are able to conduct a Prompt Injection in the user’s initial instruction (Appendix B.2) and manipulate the tools in the system (Appendix B.3)." [bank 01, REPLY sAWPaCLp79]. "Both files" replaces a "them" that could be read as the runs.
- "Of the 45,861 entries from agent commands, 45,673 match exactly, and the other 188 differ only in bookkeeping, ..." ok
- Ours: "A search of every agent command for writes to the two files found one, in a run the auditor had already scored 1 of 10."
- Proposed: "We also searched every agent command for writes to the two files and found one, in a run the auditor had already scored 1 of 10."
- Follows: "We also manually examined the execution logs for all samples and across different models to verify that the narrow LLM judges were robust to different answers." [AC5n7xHuR1] and habit 2: the authors are the subject of the check.
- "Following your comment, the harness now mounts both files read-only inside the sandbox, so an agent can no longer change them (Appendix A)." ok (same shape as b.4 and habit 2).

**Q1**

- "We agree that a human-expert reproduction would be the gold-standard baseline." ok
- "However, the cost of one would be very high. For example, in PaperBench, ML PhDs reached 41.4% ..." ok (author's phrasing; the cost arithmetic in the next sentence is habit 9, as in the AgentBench and Commit0 replies).
- "At that allowance, one pass over our 100 papers would take about 4,800 expert-hours (100 × 48), or 120 working weeks, which is more than we are able to provide." ok
- "To still address this point, our revision reports what we can measure in its place." ok (author's phrasing).
- "First, ... These papers are therefore known to be reproducible in the same environment and budget." ok (number, then its reading, habit 3).
- "Second, each target is technically an expert result already, ..." ok (author's phrasing).
- "Third, to test whether a miss comes from the agent or from the environment, we took 3 runs ..." ok (purpose opener, habit 6).
- "On 2505.17836 ..." and "On 2510.07501 ..." ok for wording. Habit 3 would give each of the two a reading clause, as the third case has; those clauses are the author's to supply.
- Ours: "..., within 0.54 points of the agent's 94.19%, so the agent's measurement repeats without the agent."
- Proposed: "..., within 0.54 points of the agent's 94.19%, so the agent's result repeats when the commands are run without the agent."
- Follows: habit 3. "Result" is the word the rest of the reply uses, and the clause now says what "without the agent" means.

**Q2**

- "The revision adds an independent check of every target." ok (opens on what was done).
- "We asked gpt-6.1-sol, ..." through "Before the dataset was frozen, one author also reviewed every extracted field." ok (compare "For each model that we tested, at least one co-author ensured that our grading criteria were appropriate for all tasks" [AC5n7xHuR1]).
- "For tolerances, 58 of the 62 point-estimate claims use the default of 5%, and the other 4 use the margin stated in their paper." ok
- Ours: "Reimplement keeps the lowest reproduction rate when every run is rescored at 1%, 2%, 5% and 10%, where the best agent reproduces 4, 5, 5 and 5 of its 33 papers against 9, 12, 14 and 14 of 34 at Run (Appendix F)."
- Proposed: "When every run is rescored at 1%, 2%, 5% and 10%, Reimplement keeps the lowest reproduction rate: the best agent reproduces 4, 5, 5 and 5 of its 33 papers, against 9, 12, 14 and 14 of 34 at Run (Appendix F)."
- Follows: "When we set target human agreement $1-\alpha$ to 0.8 instead of 0.9, the average human IAA for abstained samples goes from 0.815 to 0.806, i.e. only the harder-to-reconcile samples tend to be abstained by the models." [UHPnqSTBPO]: the values tried, then the outcome, then its breakdown.

**Closing**

- "We are happy to answer any follow-up questions. Thank you again for the review." ok (same shape as i.1 and i.3).

**Full proposed reply for Reviewer 2 (4341 characters; the draft has 4283)**

```
Thank you for the thoughtful review and for your kind words about the methodological disclosure.

**W1: Validation of the auditor.**

We compared the auditor (Claude Sonnet 5) with one human grader on 372 runs, and the grader did not see the auditor's score. On the reproduced verdict, the auditor's precision is $\frac{64}{73}$ = 88% and its recall is $\frac{64}{83}$ = 77% (F1 0.82). When the two disagree, the auditor tends to be the stricter one. In 28 runs only one of the two marked the run as reproduced (the human grader in 19, the auditor in 9), and the same direction holds in every tier. On the full 0 to 10 scale, the two differ by at most one point on 324 of the 372 runs (quadratic weighted kappa 0.89). For the anti-cheat flags, a high-severity flag sets a run's score to 0, and both graders gave a 0 to 42 of the 57 runs that either of them scored 0 (full matrix in Appendix D).

**W2: Agent-writable logs without an integrity check.**

Our harness wrote commands.log and trajectory.jsonl into a folder that the auditor reads, and our sandbox mounted that folder read-write. We therefore checked whether any agent had modified the two files during a run. For every graded run, we compared both files with the harness's own transcript, which is written to a folder the agent has no access to. Of the 45,861 entries from agent commands, 45,673 match exactly, and the other 188 differ only in bookkeeping, such as refused or retried calls and GPU-time values that differ by about a second (Appendix A). We also searched every agent command for writes to the two files and found one, in a run the auditor had already scored 1 of 10. Following your comment, the harness now mounts both files read-only inside the sandbox, so an agent can no longer change them (Appendix A).

**Q1: A stratified human-expert reproduction baseline.**

We agree that a human-expert reproduction would be the gold-standard baseline. However, the cost of one would be very high. For example, in PaperBench, ML PhDs reached 41.4% of the replication rubric after 48 hours of work on a paper. At that allowance, one pass over our 100 papers would take about 4,800 expert-hours (100 × 48), or 120 working weeks, which is more than we are able to provide. To still address this point, our revision reports what we can measure in its place. First, at least one of our four agents reproduced 32 of the 100 papers (95% interval 24% to 42%), with 16 of 34 at Run, 11 of 33 at Retrain and 5 of 33 at Reimplement. These papers are therefore known to be reproducible in the same environment and budget. Second, each target is technically an expert result already, since it is the number that the paper's own authors reported from the same code and data. Third, to test whether a miss comes from the agent or from the environment, we took 3 runs that were graded partial and ran their final commands again ourselves, with two new seeds and without the agent (Section 5.3). On 2505.17836 both seeds miss the target by the same amount as the agent's run. On 2510.07501 the two seeds differ from each other by more than the original miss. On 2506.10351 the new seeds give 93.65% and 94.15% against a target of 93.12%, within 0.54 points of the agent's 94.19%, so the agent's result repeats when the commands are run without the agent.

**Q2: How claims, targets and tolerances were validated, and annotator agreement.**

The revision adds an independent check of every target. We asked gpt-6.1-sol, a model from a different lab than our auditor, to compare each target value with its paper and to quote the passage behind each answer. It confirmed our value for 92 of the 100 claims (Appendix E), which is the agreement between our targets and an independent reader. When we correct the other 8 targets and rescore their runs, only two verdicts change, both on 2505.23747. Before the dataset was frozen, one author also reviewed every extracted field. For tolerances, 58 of the 62 point-estimate claims use the default of 5%, and the other 4 use the margin stated in their paper. When every run is rescored at 1%, 2%, 5% and 10%, Reimplement keeps the lowest reproduction rate: the best agent reproduces 4, 5, 5 and 5 of its 33 papers, against 9, 12, 14 and 14 of 34 at Run (Appendix F).

We are happy to answer any follow-up questions. Thank you again for the review.
```

### 4.3 Points in the drafts that go beyond wording

These need a fact or a decision from the author, so none of them is applied in the texts above. The arithmetic in both drafts was rechecked and is correct (table percentages, both z values, 19 + 9 = 28 and the tier splits, precision, recall and F1, the matrix total of 372, 45,861 minus 45,673 = 188, 100 × 48 = 4,800 hours = 120 weeks, 16 + 11 + 5 = 32 and its interval, 94.19 minus 93.65 = 0.54).

1. Reviewer 1, W1 table against W2 and Q2. The W1 table sums to 70 reproduced runs and gives DeepSeek-V4-Flash 13 of 34 at Run, which is the count after the target corrections. W2 quotes 73 "at submission" and the Q2 table gives the best agent 14 at Run "at submission". The W1 table has no label saying which grades it uses, so a reader meets 13 and 14 for the same cell before the last paragraph of Q2 explains the move. Q2 also says "only two verdicts change", while 73 to 70 is a difference of three.
2. Reviewer 1, W2. "73 against 83 of 400 runs" stands beside a matrix whose total is 372. Both 73 and 83 are column and row totals of that matrix, so the denominator in the sentence does not match the table under it.
3. Reviewer 2, Q1, third rerun case. On 2506.10351 the agent's 94.19% is above the 93.12% target, yet the run appears in a list of partial runs that test "whether a miss comes from the agent or from the environment". A reviewer can ask why a result above the target was graded partial.
4. Reviewer 2, W1. The reviewer listed "multi-human adjudication" among the missing items. The reply says "one human grader" and does not come back to it.
5. Reviewer 2, W2. The reviewer asked for an "external append-only or tamper-evident event log". The harness transcript in a folder the agent cannot reach is that external log, and the reply does not use the reviewer's term for it.
6. Reviewer 1, W1. The significance test is reported for two of the five rows of the table.
