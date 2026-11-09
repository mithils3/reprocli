**W1, continued: Whether the failure modes and findings change.**

The failure modes shift toward stopping early, and the reproduction rate does not rise. A coder that saw neither the verdict nor the harness (Claude Sonnet 5 with the Appendix G definitions) labelled the main failure of each of the [27] failing frontier runs. The open-agent column gives the paper's labels over its 300 failing cells.

| Main failure | Open agents | Frontier runs |
| :- | -: | -: |
| Ran, outside tolerance | 76 (25%) | [5] |
| Reimplemented but did not check the result | 63 (21%) | [3] |
| Wrong experiment | 46 (15%) | [4] |
| Wrong artifact measured | 38 (13%) | [0] |
| Failed before any number was produced | 31 (10%) | [6] |
| Build and dependency failures | 24 (8%) | [4] |
| Never launched an experiment | 13 (4%) | [5] |
| Echoed a shipped number | 9 (3%) | [0] |

The failures that report a number without a valid measurement (rows 2, 4 and 8) are rarer in the frontier runs: [3 of 27 = 11%, 95% interval 4% to 28%], against 110 of 300 = 37% [31%, 42%] for the open agents. Applied to 50 open-agent runs, the same blind coder puts that share at 46%, so the difference does not come from the coder (Appendix G). In their place more frontier runs end without a number (rows 5 and 7): [11 of 27], against 15% for the open agents under the paper's labels and 23% (14% to 33%) under the same blind coder. The [5] that never launched are all on the two Reimplement papers that released no code (2505.16927 and 2503.14698), where the open agents also failed, and on every other paper [0 of 22] failing frontier runs never launched.

The early stops are the models' own judgment. The task prompt, identical for every agent and printed in the appendix, allows a run to stop early only when a trained artifact is neither released nor retrainable within the grant. On 2506.08898 (Retrain, 32 H100-hour grant), all [5] frontier runs stopped after less than one H100-hour because no matching checkpoint is released, while under the same prompt Muse Spark 1.2 retrained the model with 27 H100-hours and reproduced the claim. Section 5.3 names this pattern.

On these papers the findings of the submission recur for the stronger models. Reproduction is highest where everything is released: the frontier runs reproduce [5 of 11] at Run, [0 of 12] at Retrain and [3 of 14] at Reimplement. The grant also goes unspent, as it did for the open agents, which used 1,888 of their 10,208 granted H100-hours. Section 5 and the Limitations section state that the rates hold for these agents and these 100 NeurIPS 2025 papers, each with one pinned experiment under a 96 H100-hour cap.

**W2: Failures due to hardware differences.**

At most 14 of the 372 graded runs failed because of our hardware, and removing every build failure changes no best-agent rate by more than one percentage point. In all, 24 runs failed at build or dependency install (13 at Run, 6 at Retrain, 5 at Reimplement): 14 on a package with no build for the aarch64 CPUs of our GH200 nodes, 7 on other environment problems and 3 on agent error.

For 12 of the 14 we replayed the install on x86 nodes, and the other 2 have no install command in their transcripts. On x86, 9 of the 12 build and import (95% Wilson interval 47% to 91%). The other 3 fail on x86 too, on a Python or package version conflict, so we do not attribute those 3 to the hardware.

We then dropped all 24 runs from every agent's denominator (Section 5.3). DeepSeek-V4-Flash, the best agent at Run and Retrain, had none of these failures at those tiers, so its rates stay at 13/34 = 38% [24%, 55%] and 9/33 = 27% [15%, 44%]. Muse Spark 1.2, the best at Reimplement, goes from 5/33 = 15% [7%, 31%] to 5/32 = 16% [7%, 32%]. The agent most affected is MiniMax-M2.7 at Run, which goes from 2/34 to 2/26 and is best at no tier. [x86 frontier arm: gpt-6.1-sol and gpt-6-astra in our loop on x86 nodes reproduce a of n, against b of n for the same models and papers on GH200 nodes.]
