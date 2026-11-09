**W3: Agents are only run once.**

We reran DeepSeek-V4-Flash, the agent with the highest Run and Retrain rates, two more times on 12 papers drawn with a fixed seed, four per tier. Its verdict is the same in all three runs on [k] of the 12, so [12 - k] of 12 verdicts were transient. Its count of reproduced papers moves by at most [j] across the three runs, and the revision ranks two agents only when their 95% Wilson intervals (Section 5.2) stay apart after each count is shifted [j] papers toward the other. This measures run-to-run variation for that one agent.

**Q2: Fetching checkpoints over the network.**

We checked every run, and two reproduced runs had evaluated a downloaded checkpoint of the claimed model. The revision counts both as not reproduced.

The harness keeps no network log, so we scanned the transcripts of all 372 graded runs, including the commands, fetched URLs and code the agent wrote, for hf_hub_download, snapshot_download, huggingface-cli, from_pretrained with a repository id, torch.hub, gdown, and wget or curl of weight files. The scan finished on 368 runs and timed out on 4, none of which was reproduced. It cannot see a download made inside an imported library, and Section 5.2 states this.

Downloading the released weights is allowed at Run, so the runs that matter are the 42 reproduced runs at Retrain and Reimplement. All 42 were scanned and 16 matched a pattern. We read the 16 by hand:

| What the match was | Runs |
| :- | -: |
| Text that is not a download (an import line, a requirements.txt, a dataset) | 10 |
| A base model the method starts from, such as the OpenVLA model that CogVLA builds on | 4 |
| A checkpoint of the claimed model | 2 |

The 2 are Muse Spark 1.2 on CogVLA (2508.21046, Retrain), which downloaded a LIBERO-Spatial checkpoint linked from the authors' repository, and MiniMax-M2.7 on CURE (2505.12677, Reimplement), which downloaded the authors' erased Stable Diffusion v1.4 weights from their Google Drive folder. Muse Spark 1.2 falls from 9 to 8 of 33 Retrain papers and MiniMax-M2.7 from 2 to 1 of 33 Reimplement papers. The best rates are unchanged at 9 of 33 at Retrain (DeepSeek-V4-Flash) and 5 of 33 at Reimplement (Muse Spark 1.2). CogVLA stays in the Retrain tier, which was fixed before any run, and a footnote in Section 5.2 says that its release includes the claimed checkpoint.

**Q3: Failures that were not the agent's fault.**

We traced 27 of the 400 cells to causes outside the agent: 6 cells with no graded run, and 21 graded runs that failed on the environment (the 14 aarch64 builds and 7 other environment problems of W2).

*Cells with no graded run.* We traced all 28 using the cluster's job accounting and the harness logs. Six were ours. The four cells of paper 2510.20725 never started because of a bug in our prompt rendering, since fixed, and two audits of Muse Spark 1.2 never returned a verdict. Those two audits now have grades from the same auditor, reproduced (score 8) on 2503.23035 and partial (score 6) on 2510.08177. [We reran the 4 cells of 2510.20725 with the same settings, and r of them reproduce.] The other 22 are agent failures, as in the paper. Four of them were finished runs with no auditor grade, and we graded the 3 whose files survive with the same auditor: none is reproduced (scores 0, 2 and 0). Every rate in the revision includes these five new grades.

*Runs that followed the released pipeline and missed.* These 76 runs count as not reproduced, because the benchmark grades whether a run recovers the pinned number. To check the environment behind runs of this kind, we re-ran the final commands of 3 partial runs that had followed the released pipeline, with new seeds and no agent. The 2 Retrain papers miss again on both seeds. [Run paper 2506.10351: outcome on both seeds.] The Limitations section states that for these runs agent error cannot be separated from seed and hardware variance.

Thank you again for the review.
