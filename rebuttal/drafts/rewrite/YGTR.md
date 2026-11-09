### Reply to YGTR, part 1 of 3 (3,707 characters)

Thank you for the review. We ran frontier models in production harnesses and measured the confounds you named. The revision makes these changes:
- Section 5.1 and a new subsection of Appendix B: gpt-6.1-sol in Codex CLI and in our loop, [gpt-6-astra] in Codex CLI, and Muse Wonder in mini-SWE-agent and in our loop, on papers frozen before any run.
- Section 5.3: the bound on build failures with an x86 replay, and a re-execution of missed runs with new seeds.
- Section 5.2: a 95% Wilson interval on every rate, and repeated runs of one agent.
- Section 5.2: the trace of all 28 cells with no graded run, the missing grades added, and the two runs that evaluated a downloaded checkpoint counted as not reproduced.

Each paper sits in one tier by what its authors released: Run (code, data and weights; 34 papers), Retrain (no weights, so the agent trains the model; 33 papers) or Reimplement (no code, so the agent writes it; 33 papers). A cell is one agent on one paper. Our auditor is an LLM grader, Claude Sonnet 5, that scores every run against the paper's pinned number, and a score of 8 or more counts as reproduced.

**W1 and Q1: Frontier models and production coding harnesses.**

We ran two current OpenAI models, [gpt-6-astra and gpt-6.1-sol], and Meta's Muse Wonder on papers from every tier, drawn with a fixed seed and frozen before any run. The last row gives Muse Spark 1.2, the Meta model of our main runs, on Muse Wonder's papers, for a comparison within one model family.

| Model | Harness | Papers | Reproduced |
| :- | :- | :- | :- |
| [gpt-6-astra] | Codex CLI | 8 | [a] |
| gpt-6.1-sol | our loop | 12 | [b] |
| gpt-6.1-sol | Codex CLI | [n] | [c] |
| Muse Wonder | our loop | [m] | [d] |
| Muse Wonder | mini-SWE-agent | [h] | [g] |
| Muse Spark 1.2 | our loop | [m] | [e] |

A harness is the program around the model that supplies its tools, system prompt and context handling. gpt-6.1-sol and Muse Wonder each ran in our thin ReAct-style loop and in a production harness, Codex CLI and mini-SWE-agent respectively. Between the two harnesses of one model the tools, prompt and context handling change, while the sandbox, task text, GPU grant, GPU metering and auditor stay those of the main runs. A Codex run ends when Codex ends its own turn, as in our loop, and the appendix table gives each run's exit reason and each count's 95% interval.

The two gpt-6.1-sol arms share 12 papers, and 9 of them are graded under both harnesses so far. On those 9, our loop reproduced 3 and Codex CLI 2, and they agreed on 6. On all 12, the paired difference is [q] papers (exact McNemar p = [x]), which is [within / larger than] the change between repeated runs of DeepSeek-V4-Flash on the same 12 papers (W3 below). The frontier runs used a median of [u]% of their GPU grant.

To compare failures, Claude Sonnet 5 labelled the main failure of each of the 27 failing frontier runs from its transcript, without seeing the verdict or the harness. Every label is one of the Appendix G failure modes that the open agents also show. The paper's most common failure, writing the method without checking its output against the paper's numbers, is the main failure in 3 of the 27. In 5, the main failure was never launching an experiment, all on the two Reimplement papers with no released code (2505.16927 and 2503.14698), where the runs reported the missing artifacts and stopped with almost all of their GPU grant unused. Section 5.3 names this pattern.

We keep the thin loop for the main results so that every model runs under one harness. We did not run Claude Code because it bills to Anthropic, and our budget for new runs covered OpenAI and Meta models. Our auditor is itself a Claude model.

### Reply to YGTR, part 2 of 3 (2,431 characters)

**W1, continued: Whether the findings generalize to stronger models.**

The frontier runs cover a frozen subset of papers from every tier, so they test whether the two main findings, the tier ordering and the most common failure, recur for [gpt-6-astra, gpt-6.1-sol and Muse Wonder] on those papers. [outcome] The main results come from four agents run once per paper on 100 NeurIPS 2025 papers. Each paper has a pinned experiment, the one reported result the agent must reproduce, under a 96 H100-hour cap, and the benchmark excludes papers that need a paid or closed API. Section 5 and the Limitations section state this scope, and the revision adds that the claims hold for these papers and agents.

**W2: Failures due to hardware differences.**

Build failures on our hardware move no best-agent rate by more than one percentage point. Of the 372 graded runs, 24 failed at build or dependency install (13 at Run, 6 at Retrain and 5 at Reimplement). Of these 24, 14 failed on a package with no build for the aarch64 CPUs of our GH200 nodes, 7 on other environment problems and 3 on agent error.

For 12 of the 14 we replayed the install on x86 nodes, and the other 2 have no install command in their transcripts. On x86, 9 of the 12 build and import (95% Wilson interval 47% to 91%). The other 3 fail on x86 too, on a Python or package version conflict, so we do not attribute those 3 to the hardware.

We then dropped all 24 runs from every agent's denominator (Section 5.3). DeepSeek-V4-Flash, the best agent at Run and Retrain, had none of these failures at those tiers, so its rates stay at 13/34 = 38% [24%, 55%] and 9/33 = 27% [15%, 44%]. Muse Spark 1.2, the best at Reimplement, goes from 5/33 = 15% [7%, 31%] to 5/32 = 16% [7%, 32%]. The agent most affected is MiniMax-M2.7 at Run, which goes from 2/34 to 2/26 and is best at no tier. The frontier runs above use the same environment, and [their results].

**W3: Agents are only run once.**

We reran DeepSeek-V4-Flash, the agent with the highest Run and Retrain rates, two more times on 12 papers drawn with a fixed seed, four per tier, and its verdict was the same in all three runs on [k] of the 12. This measures run-to-run variation for that one agent. Its best Run rate moves by [j] papers across the three runs, so the revision ranks two agents only when their 95% Wilson intervals (Section 5.2) stay apart after each count is shifted [j] papers toward the other.

### Reply to YGTR, part 3 of 3 (3,433 characters)

**Q2: Fetching checkpoints over the network.**

A scan of every transcript found two reproduced runs that evaluated a downloaded checkpoint of the claimed model, and the revision counts both as not reproduced.

The harness keeps no network log, so we scanned the transcripts of all 372 graded runs, including the commands, fetched URLs and code the agent wrote, for hf_hub_download, snapshot_download, huggingface-cli, from_pretrained with a repository id, torch.hub, gdown, and wget or curl of weight files. The scan finished on 368 runs and timed out on 4, none of which was reproduced. It cannot see a download made inside an imported library, and Section 5.2 states this limit.

Downloading the released weights is allowed at Run, so what matters is the 42 reproduced runs at Retrain and Reimplement, all scanned, and 16 of them matched a pattern. Reading the 16 by hand, 10 matched text that is not a download, such as an import line, a requirements.txt or a dataset. Another 4 downloaded only a base model that the method starts from, such as the OpenVLA model that CogVLA builds on. In the last 2, Muse Spark 1.2 on CogVLA (2508.21046, Retrain) downloaded a LIBERO-Spatial checkpoint linked from the authors' repository, and MiniMax-M2.7 on CURE (2505.12677, Reimplement) downloaded the authors' erased Stable Diffusion v1.4 weights from their Google Drive folder.

Muse Spark 1.2 now falls from 9 of 33 to 8 of 33 Retrain papers, and MiniMax-M2.7 from 2 of 33 to 1 of 33 Reimplement papers (Section 5.2). The best-agent rates stay at 9 of 33 at Retrain (DeepSeek-V4-Flash) and 5 of 33 at Reimplement (Muse Spark 1.2). CogVLA stays in the Retrain tier, which was fixed before any run, and a footnote in Section 5.2 says that its release includes the claimed checkpoint.

**Q3: Failures that were not the agent's fault.**

We traced 27 of the 400 cells to causes outside the agent: 6 cells with no graded run and 21 graded runs that failed on the environment, the 14 aarch64 builds and 7 other problems of W2, so 6 + 14 + 7 = 27.

We traced all 28 cells with no graded run using the cluster's job accounting and the harness logs. In the 6 that were ours, the four cells of paper 2510.20725 never started because of a bug in our prompt rendering, since fixed, and two audits of Muse Spark 1.2 never returned a verdict. Those two audits now have grades from the same auditor, reproduced (score 8) on 2503.23035 and partial (score 6) on 2510.08177. [We reran the 4 cells of 2510.20725 with the same settings, and r of them reproduce.]

The other 22 remain agent failures, as in the paper. Four of them were finished runs with no auditor grade, and we graded the 3 whose files survive with the same auditor: none is reproduced (scores 0, 2 and 0). Every rate in the revision includes these five new grades. The rest stay agent failures under the paper's rule.

The 76 runs that followed the released pipeline and landed outside tolerance count as not reproduced, because the benchmark grades whether the run recovers the pinned number. To check the environment behind these misses, we re-ran the final commands of 3 of the 76 runs, on 3 papers, with new seeds and no agent. The 2 Retrain papers miss again on both seeds. [Run paper 2506.10351: outcome on both seeds.] The Limitations section states that for these runs agent error cannot be separated from seed and hardware variance.

Thank you again for the review.

### Sources (YGTR)

| Number | File |
| :- | :- |
| 24 build-and-dependency runs; 14 aarch64, 7 other environment (5 labelled plus the 2 not-chip rows), 3 agent error; x86 replay 9 of 12 | rebuttal/results/e8/summary.json (build_dependency_runs.class_counts); e8/README.md; e8/x86/README.md; e8/x86/results.csv (not_arch rows) |
| gpt-6.1-sol in both harnesses, gpt-6-astra in Codex CLI only | rebuttal/PLAN.md:115; rebuttal/results/databook/frontier_cells.csv |
| best Run 13/34 unchanged, Retrain 9/33 (DeepSeek-V4-Flash; Muse 9/33 becomes 8/33 after the checkpoint correction, over the 33 Retrain papers, and 9/32 only when its one build failure is also removed), Reimplement 5/32, MiniMax Run 2/26 (3/26 in e8/bound.csv less minimax-run-2505.23747, e7/rescore_summary.md); table by tier with intervals | rebuttal/results/e8/bound.csv; e8/summary.json (build_dependency_runs.by_tier, bound_best_per_tier_all_env_removed.wilson95); e6/summary.json (settings.S0_index) |
| 13/34 = 38% [24%, 55%], 5/33 = 15% [7%, 31%] | rebuttal/results/e7/rescore_summary.md; e6/summary.json (settings.S0_index) |
| 27 = 6 + 14 + 7 traced outside the agent; 3 of 12 replayed installs fail on x86 | rebuttal/results/e8/summary.json (outside_agent_cells, build_dependency_runs.class_counts A 16, O 5); e8/x86/README.md (2 of the 16 not chip failures, moved to other environment) |
| 76 faithful misses not attributed | paper_latex/iclr2027_conference.tex:584-585 (Limitations) |
| 0.0007 on 2505.17836, 0.28 on 2510.07501, 2506.10351 queued | rebuttal/results/e10/results.md |
| 3 papers re-executed | rebuttal/results/e10/README.md; e10/selection.csv |
| 12 repeat papers, four per tier, two reproduced and two not | rebuttal/subset.json; rebuttal/results/subset/README.md; rebuttal/results/sweeps/jobs.csv |
| 368 of 372 scanned, 4 timeouts not reproduced | rebuttal/results/e9/summary.json (scan_timeouts); viewer index verdicts (partial, not_reproduced, disqualified x2) |
| 42 reproduced Retrain and Reimplement runs, 16 with a hit, 10 / 4 / 2 | rebuttal/results/e9/README.md (13 of 29 plus 3 of 13); e9/class_review.csv |
| 2508.21046 CogVLA and 2505.12677 CURE downloads | rebuttal/results/e9/class_review.csv; rebuttal/STATUS.md (commands.log:483) |
| Muse Retrain 9 to 8, MiniMax Reimplement 2 to 1, best 9/33 and 5/33 | rebuttal/results/e8/summary.json (per_agent_tier) minus the two E9 runs |
| 28 empty cells: 6 outside agent, 22 agent failures (4 of them finished without a grade) | rebuttal/results/e8/summary.json; e8/empty_cells_traced.csv; e8/README.md |
| 4 finished runs with no pinned-auditor grade; 3 regraded at 0, 2 and 0, none reproduced; 2510.19314 no bundle, ungraded | rebuttal/results/e8/d_cells.md; e8/regrade_dcells.json |
| 3 of 12 x86 replays fail on a Python or package version conflict | rebuttal/results/e8/x86/README.md |
| DeepSeek-V4-Flash has no build failure at Run or Retrain (its one is Reimplement) | rebuttal/results/e8/build_failures.csv (dsv4-reimplement-2511.20906) |
| repeat papers: per tier 2 reproduced by some agent, 2 by none | rebuttal/subset.json (rule: within each tier 2 reproduced and 2 not) |
| re-execution targets about 0.05 and -0.20; 0.0395 sits inside 0.0393 to 0.0400 | rebuttal/results/e10/results.md |
| Claude Code left out because it bills to Anthropic; new-run budget OpenAI and Meta only; auditor is Claude Sonnet 5 | rebuttal/PLAN.md:198 and its Budget summary table; paper_latex/iclr2027_conference.tex:389 |
| 27 coded frontier failures; 5 never launched, all on 2505.16927 and 2503.14698, Codex or thin loop, GPU use 0.0027 to 0.0669 H100-hours of 32 or 96; 3 with reimplement-without-validating as main failure; every primary label an Appendix G mode | rebuttal/results/frontier/failure_modes.csv (27 rows, coder claude-sonnet-5, blind to verdict and arm; 6 procrastination/wall-kill); frontier/never_launched_check.md (6cef06 relabeled failed before any number, so 5 of the 6 never launched); frontier/failure_modes.md (open-agent counts for every mode) |
| CogVLA release includes the claimed checkpoint; stays at Retrain | rebuttal/results/e9/class_review.csv (muse-retrain-2508.21046, liwei2013/cogvla_libero_spatial_60000_chkpt); rebuttal/mithil/decisions_monday.md decision 6 |
| 368 scanned, 4 timeouts | rebuttal/results/e9/summary.json (tiers.*.runs_scanned, scan_timeouts) |
| 2503.23035 reproduced (8), 2510.08177 partial (6) | rebuttal/results/e8/regrade_muse.json |
| 12 papers shared by thin and Codex gpt-6.1-sol arms; 9 graded under both; reproduced 3 (thin: 2503.02809, 2504.20571, 2506.20671) and 2 (Codex: 2504.20571, 2505.19087); agree on 6 | rebuttal/results/databook/frontier_cells.csv (arms thin-gpt-6.1-sol, codex-gpt-6.1-sol); rebuttal/subset.json (12 core papers) |
| frontier results, McNemar, budget use, failure-mode shares, blind labels, repeat flips (job 3540624 running, 3540625 to 3540633 pending), 2506.10351 re-execution, 4 reruns of 2510.20725 | pending (E1, E2, E3, E10, E8 reruns of 2510.20725) |

## Notes

- I read "the 28 stay agent failures" as the 22. The 6 that are ours (the prompt bug and the two missing audits) cannot honestly be called agent failures, since one of them now grades reproduced.
- After the 4 finished runs are set apart, the time-limit reason covers the other 18 runs. empty_cells_traced.csv lists 2 of them as class A, cause unchecked.
- The cause of the two missing audits is not stated in e8, so the reply gives none.
- I cut the line saying other venues, years and models remain untested, because the reviewer did not ask for it.
- [within / larger than], [outcome] and [their results] stay open-ended.
- The failure_modes.csv file still labels 6cef06 procrastination.
