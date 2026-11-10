**W2: Failures due to hardware differences.**

At most 14 of the 372 graded runs failed because of our hardware, and removing every build failure changes no best-agent rate by more than one percentage point. In all, 24 runs failed at build or dependency install, 14 of them on a package with no build for the aarch64 CPUs of our nodes. Of those 14, 12 have an install command in their transcripts. We replayed the 12 on x86 nodes, and 9 build there (95% Wilson interval 47% to 91%). With all 24 dropped from every denominator, DeepSeek-V4-Flash stays at 13/34 at Run and 9/33 at Retrain, and Muse Spark 1.2 goes from 5/33 to 5/32 at Reimplement (Section 5.3). [x86 frontier arm: gpt-6.1-sol and gpt-6-astra in our loop on x86 nodes reproduce a of n, against b of n for the same models and papers on GH200 nodes.]

**W3: Agents are only run once.**

We reran DeepSeek-V4-Flash two more times on 12 papers drawn with a fixed seed, four per tier. Its verdict is the same in all three runs on [k] of the 12, and its count of reproduced papers moves by at most [j]. Every rate in the revision has a 95% Wilson interval (Section 5.2).

**Q2: Fetching checkpoints over the network.**

We scanned the run transcripts for model downloads (hf_hub_download, snapshot_download, from_pretrained with a repository id, gdown, and wget or curl of weight files). Downloading released weights is allowed at Run, so the runs that matter are the 42 reproduced runs at Retrain and Reimplement. Of these, 16 matched a pattern, and we read them by hand: 10 were not downloads, 4 fetched a base model that the method starts from, and 2 evaluated a checkpoint of the claimed model (Muse Spark 1.2 on 2508.21046 and MiniMax-M2.7 on 2505.12677). The revision counts both as not reproduced, and the best rates stay at 9 of 33 at Retrain and 5 of 33 at Reimplement (Section 5.2).

**Q3: Failures that were not the agent's fault.**

We traced 27 of the 400 cells to causes outside the agent: 6 cells with no graded run and the 21 environment failures among the 24 of W2. Of the 28 cells with no graded run, 4 belong to paper 2510.20725, whose runs did not start because of a harness error that is now fixed, and 2 were Muse Spark 1.2 audits that never returned a verdict. The same auditor has now graded those 2, one reproduced and one partial. [We reran the 4 cells of 2510.20725, and r of them reproduce.] The other 22 are agent failures, and Section 5.2 now accounts for each of the 28. For runs that followed the released pipeline and missed, we re-ran the final commands of 3 with new seeds and no agent, and the 2 Retrain papers miss again on both seeds. [Run paper 2506.10351: outcome on both seeds.]

Thank you again for the review.
