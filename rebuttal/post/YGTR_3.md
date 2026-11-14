**W3: Agents are only run once.**

We agree that one run per cell leaves the results open to noise, so we measured how much a verdict changes when a run is repeated. We graded a second, independent run of Muse Spark 1.2 on 10 Reimplement papers, made with the same budget as the run in the paper. The two runs reach the same reproduced verdict on 9 of the 10 papers (4 reproduced in both and 5 in neither). We also compared what the two runs measured: in 9 of the 10 pairs both runs measured the same quantity, and their two values differ by a median of 0.11%. The 8 x86 pairs of W2 repeat a model on a paper as well, and 7 of them keep their verdict. Together, 16 of 18 repeated pairs keep their verdict (89%, 95% interval 67% to 97%), and both pairs that change score 8 in one run and 7 in the other, on either side of the threshold. Ten pairs from one agent is a small sample, so our claims rest only on differences that the 95% Wilson intervals separate, and the revision reports every rate with its interval (Section 5.2).

**Q2: Fetching checkpoints over the network.**

Thank you for suggesting this check, which changed two grades. We scanned the run transcripts for model downloads: hf_hub_download, snapshot_download, the Hugging Face CLI (huggingface-cli or hf download), from_pretrained with a repository id, torch.hub, git clone and git lfs of Hugging Face repositories, gdown, and wget or curl of weight files. Downloading released weights is part of the task at Run, so the runs that matter are the 42 that were graded reproduced at Retrain and Reimplement at submission (29 and 13). Of these, 16 matched a pattern, and we read them by hand: 10 were not downloads, 4 fetched a base model that the method starts from, and 2 evaluated a ready checkpoint of the claimed model (Muse Spark 1.2 on 2508.21046 and MiniMax-M2.7 on 2505.12677). At these two tiers the run has to produce the model itself, so the revision counts both as not reproduced. That leaves 40 (28 and 12), and the best rates stay at 9 of 33 at Retrain and 5 of 33 at Reimplement (Section 5.2, Appendix B.2).

**Q3: Failures that were not the agent's fault.**

We traced 27 of the 400 cells to causes outside the agent (Sections 5.2 and 5.3, Appendix B.2):

- **6 cells with no graded run.** Four belong to paper 2510.20725, whose runs did not start because of a harness error that is now fixed, and 2 were Muse Spark 1.2 audits that never returned a verdict. The same auditor has now graded those 2, one reproduced and one partial.
- **21 build and dependency failures.** These are the 14 aarch64 packages of W2 and 7 other environment problems.

You also asked about runs that follow the released pipeline and still miss. To test whether such a miss comes from the agent or from the released code, we took 3 of these runs and executed their final commands again ourselves, with two new seeds and no agent:

- **2505.17836 (Retrain).** Both reruns miss the target by the same amount as the agent, and the three values agree within 0.0007, so the released code produces this miss.
- **2510.07501 (Retrain).** The result changes with the seed (-0.22, -0.13 and +0.06 against a target of -0.20), so the agent's near miss is within seed noise.
- **2506.10351 (Run).** Both reruns land within 0.54 points of the agent's 94.19% (93.65% and 94.15%).

In all three, the agent's number is what the released pipeline gives, so we read these runs as faithful and their misses as coming from outside the agent. Only 3 of the 22 papers we examined had a single command chain that could be rerun unchanged, so we report them as cases and do not extrapolate.

We would be glad to discuss any of these results further. Thank you again.
