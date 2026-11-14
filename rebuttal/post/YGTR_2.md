**W2: Failures due to hardware differences.**

At most 11 of the 372 graded runs failed to build because of our hardware, and removing every build failure changes no best-agent rate by more than one percentage point. In all, 24 runs failed at build or dependency install, 14 of them on a package with no build for the aarch64 CPUs of our nodes. Of those 14, 12 have an install command in their transcripts, and we replayed them on x86 nodes. There, 9 build (95% Wilson interval 47% to 91%) and 3 fail again, so our hardware explains 9 failures, or 11 with the 2 we could not replay. With all 24 dropped from every denominator, DeepSeek-V4-Flash stays at 13/34 at Run and 9/33 at Retrain, and Muse Spark 1.2 goes from 5/33 to 5/32 at Reimplement (Section 5.3, Appendix B.2). We also ran gpt-6.1-sol and gpt-6-astra in our loop on x86 nodes. They reproduce [4 of 8] model and paper pairs there, against [3 of 8] for the same models and papers on our GH200 nodes, and the two scores of every pair are within one point.

**W3: Agents are only run once.**

We agree that one run per cell leaves the results open to noise. To measure the variation between runs, we graded a second, independent run of Muse Spark 1.2 on 10 Reimplement papers, made with the same budget as the run in the paper. The two runs reach the same reproduced verdict on 9 of the 10 papers (4 reproduced in both runs and 5 in neither), and the tenth pair scored 8 and 7. Every rate in the revision also has a 95% Wilson interval (Section 5.2).

**Q2: Fetching checkpoints over the network.**

Thank you for suggesting this check, which changed two grades. We scanned the run transcripts for model downloads: hf_hub_download, snapshot_download, the Hugging Face CLI (huggingface-cli or hf download), from_pretrained with a repository id, torch.hub, git clone and git lfs of Hugging Face repositories, gdown, and wget or curl of weight files. Downloading released weights is allowed at Run, so the runs that matter are the 42 that were graded reproduced at Retrain and Reimplement at submission (29 and 13). Of these, 16 matched a pattern, and we read them by hand: 10 were not downloads, 4 fetched a base model that the method starts from, and 2 evaluated a checkpoint of the claimed model (Muse Spark 1.2 on 2508.21046 and MiniMax-M2.7 on 2505.12677). The revision counts both as not reproduced, which leaves 40 (28 and 12), and the best rates stay at 9 of 33 at Retrain and 5 of 33 at Reimplement (Section 5.2, Appendix B.2).

**Q3: Failures that were not the agent's fault.**

We traced 27 of the 400 cells to causes outside the agent (Sections 5.2 and 5.3, Appendix B.2). They come from two groups, the 28 cells with no graded run and the 24 build and dependency failures of W2.

- **Cells with no graded run (6 of 28).** Four belong to paper 2510.20725, whose runs did not start because of a harness error that is now fixed, and 2 were Muse Spark 1.2 audits that never returned a verdict. The same auditor has now graded those 2, one reproduced and one partial. Three more of the 28 were finished runs without a grade, and the auditor has graded them as well, none reproduced.
- **Build and dependency failures (21 of 24).** These are the 14 aarch64 packages of W2 and 7 other environment problems. The remaining 3 were agent errors.

For runs that followed the released pipeline and missed, we re-ran the final commands of 3 with two new seeds and no agent. On 2505.17836 the miss repeats within 0.0007 on both seeds. On 2510.07501 the agent's run and our two seeds span 0.28 against a target of -0.20, far more than the agent's original miss of 0.02. Both misses therefore arise without the agent, and we read them as faithful runs of the released pipeline. On the Run paper, 2506.10351, both seeds land within 0.54 points of the agent's 94.19% (93.65% and 94.15%). Only these 3 of the 22 papers we examined for this check had a single command chain that could be rerun unchanged, so we do not extrapolate from them.

We would be glad to discuss any of these results further. Thank you again.
