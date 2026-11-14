**W2: Failures due to hardware differences.**

To separate failures caused by our aarch64 nodes from failures of the agent, we took every run that failed at build or dependency install and replayed its install commands on x86 nodes. There are 24 such runs, 14 of them on a package with no aarch64 build, and 12 of the 14 have an install command in their transcripts. On x86, 9 of the 12 build (95% Wilson interval 47% to 91%) and 3 fail again. Our hardware therefore explains 9 failures, or at most 11 of the 372 graded runs if the 2 we could not replay are counted. With all 24 dropped from every denominator, DeepSeek-V4-Flash stays at 13/34 at Run and 9/33 at Retrain, and Muse Spark 1.2 goes from 5/33 to 5/32 at Reimplement, so no best-agent rate moves by more than one percentage point (Section 5.3, Appendix B.2). As a direct test we also ran gpt-6.1-sol and gpt-6-astra in our harness on x86 nodes. They reproduce 4 of 8 model and paper pairs there, against 3 of 8 for the same pairs on our GH200 nodes, and the two scores of every pair are within one point (Appendix B.3).

**W3: Agents are only run once.**

We agree that one run per cell leaves the results open to noise, so we measured how much a verdict changes when a run is repeated with the same budget.

- **Muse Spark 1.2, 10 Reimplement papers.** A second run reaches the same reproduced verdict on 9 of the 10 (4 reproduced in both and 5 in neither). In 9 of the 10 pairs both runs measured the same quantity, and their two values differ by a median of 0.11%.
- **DeepSeek-V4-Flash, 9 papers from all three tiers.** We graded 16 repeat runs, and on 7 of the 9 papers every repeat reaches the verdict of the run in the paper.
- **The 8 pairs of W2**, run on x86 and GH200 nodes, are repeats as well, and 7 keep their verdict.

Together, the verdict is stable for 23 of 27 model and paper pairs (85%, 95% interval 68% to 94%). In the four that change, every run scores 7, 8 or 9, on either side of the threshold of 8, so in these pairs a repeat moves a paper only when it already sits at the line. This is still a modest sample, and the revision reports every rate with its 95% Wilson interval (Section 5.2).

**Q2: Fetching checkpoints over the network.**

Thank you for suggesting this check, which changed two grades. We scanned the run transcripts for model downloads: hf_hub_download, snapshot_download, the Hugging Face CLI, from_pretrained with a repository id, torch.hub, git clone and git lfs of Hugging Face repositories, gdown, and wget or curl of weight files. Downloading released weights is part of the task at Run, so the runs that matter are the 42 that were graded reproduced at Retrain and Reimplement at submission (29 and 13). Of these, 16 matched a pattern, and we read them by hand: 4 were not downloads, 10 fetched only a base model or tokenizer that the method starts from, and 2 evaluated a ready checkpoint of the claimed model (Muse Spark 1.2 on 2508.21046 and MiniMax-M2.7 on 2505.12677). At these two tiers the run has to produce the model itself, so the revision counts both as not reproduced. That leaves 40 (28 and 12), and the best rates stay at 9 of 33 at Retrain and 5 of 33 at Reimplement (Section 5.2, Appendix B.2).

**Q3: Failures that were not the agent's fault.**

We traced 27 of the 400 cells to causes outside the agent (Sections 5.2 and 5.3, Appendix B.2):

- **6 cells with no graded run.** Four belong to paper 2510.20725, whose runs did not start because of a harness error that is now fixed, and 2 were Muse Spark 1.2 audits that never returned a verdict. The same auditor has now graded those 2, one reproduced and one partial.
- **21 of the 24 build and dependency failures of W2.** These are the 14 aarch64 packages and 7 other environment problems.

A run can also follow the released pipeline and still miss. To test whether such a miss comes from the agent or from the released code, we executed the final commands of 3 such runs again ourselves, with two new seeds and no agent:

- **2505.17836 (Retrain).** Both reruns miss the target by the same amount as the agent, and the three values agree within 0.0007, so the released code produces this miss.
- **2510.07501 (Retrain).** The agent's run and the two reruns range from -0.22 to +0.06 against a target of -0.20, so the agent's near miss is within seed noise.
- **2506.10351 (Run).** Against a target of 93.12%, both reruns (93.65% and 94.15%) land within 0.54 points of the agent's 94.19%.

In all three, the agent's number is what the released pipeline gives, so we read their misses as coming from outside the agent. Only 3 of the 22 papers we examined had a single command chain that could be rerun unchanged, so we report them as cases and do not extrapolate.

We would be glad to discuss any of these results further. Thank you again.
