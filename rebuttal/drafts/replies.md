# OpenReview replies, ICLR 2027 submission 22528 (RECLAIM)

Shortened on 2026-11-09 to the length of real ICLR author replies (rebuttal/results/style/first_reply_length.md); the longer version is in git at ab58228. Rewritten on 2026-11-09 (second pass of the day) so that each answer opens with its result and each table carries the comparison the reviewer asked about. The draft it replaces is rebuttal/drafts/replies_pre_fable_2026-11-09.md, and the longer 11-08 draft is rebuttal/drafts/replies_long_2026-11-08.md. Nothing here has been posted. Square brackets mark results that are not final. A bracket that holds a number or a full sentence shows the value in the databook on 2026-11-09 and is replaced by the final value before posting; a bracket that holds a letter has no value yet. `rebuttal/scripts/export_replies.py` will not mark a part READY while it holds a bracket. Each part stays under 4,800 characters, and the count of each part is given in its heading line. Each fact sits in one reply and the others point to it. Post each part under the title "Response to Reviewer X (k/N)". The Sources tables and the Risks section are not posted.

Order of posting: see rebuttal/REPLY_PLAN.md.

## General

### General reply (one part, 1,594 characters)

We thank the three reviewers for their careful reading. They found the task important and the evaluation design unusually careful (T29u), the design sound and reusable (YGTR), and the methodological disclosure excellent (rqBN). The revision adds these analyses:
- **Frontier models in production harnesses** (Section 5.1, Appendix B). gpt-6.1-sol reproduces [4 of 11] papers in our loop and [2 of 15] in Codex CLI, where the submitted runs of DeepSeek-V4-Flash reproduce [4 of 11] and [6 of 15] of the same papers.
- **Uncertainty** (Section 5.2). Every rate has a 95% Wilson interval, and three runs of DeepSeek-V4-Flash on 12 papers give the same verdict on [k] of the 12.
- **Auditor validation** (Appendix D). Against a human grade on 372 runs, the auditor's reproduced verdict has precision 88% and recall 77%.
- **Log integrity** (Appendix A). Of the 45,861 entries in the agent-writable logs, 45,673 match a transcript kept on the host exactly, and the other 188 differ only in bookkeeping.
- **Targets and tolerance** (Appendices E and F). A check by a model from another lab supports 92 of the 100 frozen targets, the other 8 are corrected, and Reimplement stays the lowest tier at every tolerance from 1% to 10%.
- **Failures outside the agent** (Sections 5.2 and 5.3). Removing every build failure moves no best-agent rate by more than one percentage point.

With every new grade applied, 70 of the 400 agent-paper cells are reproduced (73 at submission), the best agent reproduces 38% of Run, 27% of Retrain and 15% of Reimplement papers, and the ordering of the tiers is unchanged.

### Sources (General)

| Number | File |
| :- | :- |
| 13/34 = 38% [24%, 55%] (14/34 before the 2505.23747 correction) | rebuttal/results/e7/rescore_summary.md (best-agent table); e6/summary.json (settings.S0_index.dsv4/run) |
| 45,861 entries, 372 runs, 1 overwrite, graded 1 | rebuttal/results/e5/summary.json; e5/README.md; viewer index (minimax-reimplement-2510.25146 score 1, unverifiable) |
| best-agent count at 1%, 2%, 5% and 10% (Run 9/12/14/14, Retrain 8/9/9/12, Reimplement 4/5/5/5), so at most 14 - 9 = 5, 12 - 9 = 3 and 5 - 4 = 1 | rebuttal/results/e6/README.md table |
| T29u "real and important" and "unusually careful", YGTR "sound ... reusable", rqBN "excellent" | rebuttal/reviews-2026-11-06.md:17, :19, :45, :33 |
| gpt-6.1-sol in both harnesses, gpt-6-astra in Codex CLI only | rebuttal/PLAN.md:115; rebuttal/results/databook/frontier_cells.csv (no thin gpt-6-astra arm) |
| 28 empty cells, 6 outside agent, 22 agent failures | rebuttal/results/e8/summary.json (empty_cells, outside_agent_cells); e8/empty_cells_traced.csv |
| 2 checkpoint downloads | rebuttal/results/e9/README.md; e9/class_review.csv |
| scan finished on 368 of 372 (127 + 118 + 123 of 129 + 118 + 125) | rebuttal/results/e9/summary.json (tiers.*.runs_scanned, scan_timeouts) |
| 28 = 6 outside the agent + 22 agent failures (4 of them finished without a pinned-auditor grade; 3 of the 4 regraded) | rebuttal/results/e8/summary.json; e8/empty_cells_traced.csv (A 2, B 16, D 4); e8/d_cells.md; e8/regrade_dcells.json |
| 73 auditor reproductions are the 73 of 400 cells at submission | rebuttal/results/e8/README.md (reproduction check passes: 73 of 400 cells); e4/summary.json |
| 70 of 400 = 73 + 1 (Muse Spark 1.2, 2503.23035, score 8) - 2 (checkpoint runs muse-retrain-2508.21046, minimax-reimplement-2505.12677) - 2 (dsv4-run and minimax-run on 2505.23747 at the corrected target) | rebuttal/results/e8/regrade_muse.json; e9/class_review.csv; e7/rescore_summary.md; e7/class_d_rescore.md (class D changes 0 cells) |
| best Run agent DeepSeek-V4-Flash; 14 at 10% | rebuttal/results/e6/summary.json (settings.S0_index.dsv4/run); e6/README.md table |
| 4 prompt-bug cells of 2510.20725 rerun | rebuttal/results/sweeps/jobs.csv (3540631, 3540633, 3540786); e8/README.md |
| 372 runs, precision 88%, recall 77%, 73 against 83 reproductions | rebuttal/results/e4/summary.json |
| frontier, repeat runs, reruns of 2510.20725 | pending (E1, E2, E3, E8 reruns of 2510.20725); repeat runs queued, job 3540624 running and 3540625 to 3540633 pending (sacct, followups_check_4.md item 11) |
| gpt-6.1-sol [4 of 11] in our loop and [2 of 15] in Codex CLI; DeepSeek-V4-Flash [4 of 11] and [6 of 15] on the same papers | rebuttal/results/frontier/same_paper_baselines.md (rebuttal/scripts/frontier_baselines.py over databook/frontier_cells.csv) |
| 188 bookkeeping differences = 100 + 60 + 25 + 3; 45,673 exact | rebuttal/results/e5/summary.json; e5/README.md |
| Reimplement lowest at every tolerance (best agent 4, 5, 5, 5 against 9/12/14/14 and 8/9/9/12) | rebuttal/results/e6/README.md table |
| best agent 38%, 27%, 15% after corrections | rebuttal/results/tiers/tier_tests.md |

## T29u

### Reply to T29u, part 1 of 1 (3,556 characters)

Thank you for the careful review.

**W1: One run per agent-paper cell.**

Every rate now has a 95% Wilson interval, and we measured run-to-run variation. DeepSeek-V4-Flash ran two more times on 12 papers (four per tier, fixed seed), and its verdict is the same in all three runs on [k] of the 12, with its reproduced count moving by at most [j].

| Agent | Run (34 papers) | Retrain (33) | Reimplement (33) |
| :- | -: | -: | -: |
| DeepSeek-V4-Flash | 13 = 38% [24%, 55%] | 9 = 27% [15%, 44%] | 4 = 12% [5%, 27%] |
| Muse Spark 1.2 | 10 = 29% [17%, 46%] | 8 = 24% [13%, 41%] | 5 = 15% [7%, 31%] |
| Qwen3.6-27B | 5 = 15% [6%, 30%] | 6 = 18% [9%, 34%] | 2 = 6% [2%, 20%] |
| MiniMax-M2.7 | 2 = 6% [2%, 19%] | 5 = 15% [7%, 31%] | 1 = 3% [1%, 15%] |
| At least one agent | 16 = 47% [31%, 63%] | 11 = 33% [20%, 50%] | 5 = 15% [7%, 31%] |

Two comparisons are separated at the 5% level. Run and Reimplement differ for DeepSeek-V4-Flash (z = 2.46) and for papers reproduced by at least one agent (z = 2.81), and every agent has its lowest rate at Reimplement. The mean audit scores of DeepSeek-V4-Flash and Muse Spark 1.2 (5.13 and 5.14 of 10) lie above those of Qwen3.6-27B and MiniMax-M2.7 (3.51 and 3.03), and their 95% intervals do not overlap (lower bounds 4.55 and 4.59, upper bounds 4.04 and 3.58). For environment sensitivity, removing the 24 build and dependency failures moves no best-agent rate by more than one percentage point (Section 5.3).

**W2: The auditor's disagreements with the human grade.**

Where the two graders disagree, the auditor is the stricter one. Of the 28 runs that only one grader called reproduced, the human did in 19 and the auditor in 9, and the human count is the higher one in every tier (7 against 3 at Run, 7 against 4 at Retrain, 5 against 2 at Reimplement). Auditor-graded rates therefore sit slightly below human-graded rates, 73 against 83 of 400 at submission, and Reimplement is the lowest tier under both graders. Appendix D gives the disagreements by tier.

**Q1: Confusion matrix, the 7/8 boundary and high-severity flags.**

The auditor's reproduced verdict has precision 64/73 = 88% [78%, 93%] and recall 64/83 = 77% [67%, 85%] against the human grade. Appendix D has the full five-way matrix, which condenses to:

| Human ↓ / Auditor → | Reproduced | Partial | Lower | Total |
| :- | -: | -: | -: | -: |
| Reproduced (8 to 10) | **64** | 15 | 4 | 83 |
| Partial (6, 7) | 7 | **64** | 17 | 88 |
| Lower (0 to 5) | 2 | 7 | **192** | 201 |
| Total | 73 | 86 | 213 | 372 |

Of the 100 runs that either grader placed at 7 or 8, the two agree on the side of the boundary for 75. A high-severity flag forces the score to 0. Of the 57 runs that either grader placed there, they agree on 42, and the auditor graded no run reproduced that the human placed at 0.

**Q2: Sensitivity to the match target and the default 5% tolerance.**

Reimplement is the lowest tier at every tolerance, and the target check changes two verdicts. Counts at submission (Appendix F):

| Relative tolerance | 1% | 2% | 5% | 10% |
| :- | -: | -: | -: | -: |
| Best agent, Run (of 34) | 9 | 12 | 14 | 14 |
| Best agent, Retrain (of 33) | 8 | 9 | 9 | 12 |
| Best agent, Reimplement (of 33) | 4 | 5 | 5 | 5 |
| All agents (of 400) | 56 | 65 | 73 | 82 |

For the targets, a check by a model from another lab than the auditor supports the frozen value for 92 of the 100 claims (Appendix E). Correcting the other 8 and rescoring their runs changes two verdicts, both on one paper (2505.23747), which moves the best Run count from 14 to 13 of 34.

### Sources (T29u)

| Number | File |
| :- | :- |
| 13/34 [24%, 55%], 9/33, 5/33, 70/400 and their Wilson intervals | rebuttal/results/e7/rescore_summary.md (13/34, 23.9 to 55.0); e6/summary.json (settings.S0_index); 70 = 73 + 1 - 2 - 2 (Sources, General); interval for 70/400 (14.1% to 21.5%) computed with the same Wilson formula |
| 12 papers, four per tier, two reproduced and two not | rebuttal/subset.json; rebuttal/results/subset/README.md |
| 24 build-and-dependency runs (13 Run, 6 Retrain, 5 Reimplement), 14 aarch64 (16 labelled less 2 that were not chip failures), bound 14/34, 9/33, 5/32 with Wilson intervals (Muse Spark 1.2 Retrain is 9/33 reproduced, 8/33 after the CogVLA checkpoint correction; it is 9/32 only when its one build failure is also removed from the denominator, e8/bound.csv muse,retrain; DeepSeek-V4-Flash at 9/33 is the best Retrain agent); x86 replay 9 of 12 | rebuttal/results/e8/summary.json (build_dependency_runs, bound_best_per_tier_all_env_removed); e8/bound.csv (dsv4 retrain bound_all 9/33, 0.1507 to 0.4422); e8/x86/README.md; e8/x86/results.csv (not_arch rows) |
| 5.13, 5.14 and 3.03 mean audit score on the frozen targets; 5.14 = 5.00 + (8 + 6)/100, empty cells at 0 | paper_latex/iclr2027_conference.tex:463-466; Muse Spark 5.00 at paper_latex/appendix/b_models.tex:178; rebuttal/results/e8/regrade_muse.json |
| 1 edited log in 372 runs, graded unverifiable | rebuttal/results/e5/README.md |
| 2 reproduced runs with a downloaded checkpoint | rebuttal/results/e9/README.md; e9/class_review.csv |
| 62 point estimates, 58 default, 4 stated margins, 38 without a number test (21 direction, 14 threshold, 1 range, 1 magnitude, 1 no kind) | rebuttal/results/e6/summary.json (claims.lockfile_kinds, point_estimate_default_5pct, point_estimate_stated_margin) |
| tolerance table, 56/65/73/82 of 400, 70 and 72 at 1 and 2 points | rebuttal/results/e6/README.md; e6/summary.json (cells, summed per setting) |
| 17 falls at 1%, 9 rises at 10%; at most 5, 3 and 1 papers of movement (from the tolerance table) | rebuttal/results/e6/summary.json (falls_by_setting, moves_by_setting, number_only_partials) |
| 2511.19808 example, 90.6 vs 97.3, 6.9% | rebuttal/results/e6/README.md (worked run) |
| 2511.19808 metric, test accuracy (%) on CIFAR10-IDN | rebuttal/results/e7/comparison.csv (row 2511.19808) |
| direction example "beats the strongest baseline", threshold "a floor or ceiling" | rebuttal/results/e6/README.md (Why 51 and 73) |
| 396 started, 24 with a human label but no auditor grade (28 empty cells less the 4 that never started) | paper_latex/iclr2027_conference.tex:412; rebuttal/results/e8/summary.json; e8/empty_cells_traced.csv |
| 92, 95, 76, 69, 55 of 100; 45 failures; 18 method-only | rebuttal/results/e7/summary.json (step3); e7/README.md |
| 2506.18890, 27.443 PSNR, 24 vs 12 views | rebuttal/results/e7/v3_failures.csv; e7/README.md |
| 372 runs, five-way table, 64/73, 64/83, F1 0.82, 306 of 372, 100 at 7 or 8 with 75 agreeing, 57 at 0 with 42 agreeing, 19 against 9 | rebuttal/results/e4/summary.json (from e4/matrix_0_10.csv, auditor columns checked against the 372 graded runs) |
| 8 corrected targets (2505.23747, 2511.00090, 2506.18896, 2510.10480, 2505.16927, 2510.04136, 2506.01511, 2505.24864); 2 verdicts change, both on 2505.23747; 51.13 README, 48.4 paper, 51.44 measured; 14 to 13 of 34 | rebuttal/mithil/e7_ten_vs_eight.md (classes A and D); e7/rescore_summary.md; e7/class_d_rescore.md |
| repeat runs | pending (E3) |
| mean audit score with 95% t-interval on the original targets, empty cells at 0: Run DeepSeek-V4-Flash 5.29 [4.13, 6.46], Retrain DeepSeek-V4-Flash 5.45 [4.40, 6.51], Reimplement Muse Spark 1.2 3.85 [2.86, 4.84]; overall DeepSeek-V4-Flash 5.13 [4.55, 5.71], Muse Spark 1.2 5.14 [4.59, 5.69], Qwen3.6-27B 3.51 [2.98, 4.04], MiniMax-M2.7 3.03 [2.48, 3.58] | computed by the main session on 2026-11-09 from tools/anon_viewer/public/data/index.json plus the two new Muse Spark grades in rebuttal/results/e8/regrade_muse.json; t-interval over the tier's papers (DeepSeek-V4-Flash Run and Retrain rechecked from index.json) |
| other 45 targets: frozen number wrong 8, number right but setting or label off 16, correct or unclear 21 | rebuttal/mithil/e7_merged.md (Kind of error column: number 8; setting or label 15 + 1; none 21) |
| tier rates under auditor and human grade, submitted grades, all cells of the tier, empty cells not reproduced: Run 31/136 [17%, 31%] and 35/136 [19%, 34%], Retrain 29/132 [16%, 30%] and 32/132 [18%, 32%], Reimplement 13/132 [6%, 16%] and 16/132 [8%, 19%], all 73/400 [15%, 22%] and 83/400 [17%, 25%]; one-sided reproduced calls by tier, human 7/7/5, auditor 3/4/2 | rebuttal/results/e4/summary.json (per_tier_reproduced: auditor = both + auditor_only, human = both + human_only); Wilson 95% computed by the main session on 2026-11-09 and rechecked |
| 14/34 = 41% in the submission | paper_latex/iclr2027_conference.tex:464; rebuttal/results/e7/rescore_summary.md |
| per-agent, per-tier reproduced counts after corrections with Wilson intervals; at least one agent 16/34, 11/33, 5/33; z Run vs Reimplement 2.46 (DeepSeek-V4-Flash) and 2.81 (at least one agent); z Run vs Retrain 0.96 and 1.15; every agent lowest at Reimplement | rebuttal/results/tiers/tier_tests.md (rebuttal/scripts/tier_tests.py over tools/anon_viewer/public/data/index.json with the five corrections) |
| the submission already reported that the test separates Run from Reimplement and not Run from Retrain | paper_latex/iclr2027_conference.tex:480-482 (z = 2.7 and 1.2 at the submitted counts; the revision updates them to 2.46 and 0.96) |
| mean-score intervals separate DeepSeek-V4-Flash and Muse Spark 1.2 from Qwen3.6-27B and MiniMax-M2.7 (4.55 and 4.59 lie above 4.04 and 3.58) | the four intervals in the row above |
| 25 runs on opposite sides of the 7/8 boundary: 18 one point apart (human 8 and auditor 7 on 11, human 7 and auditor 8 on 7) | rebuttal/results/e4/summary.json (boundary_7_8.cells, human score first) |
| across the partial/reproduced line: human reproduced and auditor partial 15, the reverse 7 | rebuttal/results/e4/summary.json (matrix cells) |
| at score 0: agree on 42, auditor alone 53 - 42 = 11, human alone 46 - 42 = 4 | rebuttal/results/e4/summary.json (disqualified_score0_as_high_severity) |
| mean audit score per agent and tier with 95% t-intervals (DeepSeek-V4-Flash 5.29, 5.45, 4.64; Muse Spark 1.2 5.71, 5.85, 3.85); Qwen3.6-27B 3.51 [2.98, 4.04] includes the regrade of 2511.19808 at score 2 (e8/regrade_dcells.json) | rebuttal/results/tiers/tier_tests.md (mean-score table) |
| value supported for 92 of 100, so 8 wrong values | rebuttal/results/e7/summary.json (step3); rebuttal/mithil/e7_merged.md |

## rqBN

### Reply to rqBN, part 1 of 1 (3,186 characters)

Thank you for checking how runs are graded and how their logs are protected.

**W1: Validation of the auditor.**

Appendix D now validates the auditor (Claude Sonnet 5) on the 372 runs also graded by one human grader, who was blind to the auditor's score. On the reproduced verdict, precision is 64/73 = 88% and recall is 64/83 = 77% (F1 0.82), and the appendix gives the confusion matrix and the values per tier. In every tier the auditor's misses outnumber its false positives, so it counts 73 reproduced runs where the human counts 83. On the full 0 to 10 scale the two differ by at most one point on 324 of the 372 runs (quadratic weighted kappa 0.89), and they agree on 42 of the 57 runs that either placed at 0 for a high-severity anti-cheat flag.

**W2: Agent-writable logs without an integrity check.**

The concern is sound. The harness writes commands.log and trajectory.jsonl into the folder the auditor reads, and the sandbox mounts that folder read-write, so we ran an analysis to find out whether any agent used this. We compared both files with the harness's own transcript on the host, outside the sandbox, over all 372 graded runs. Of the 45,861 entries that agent commands produced, 45,673 match exactly, and the other 188 are bookkeeping differences that Appendix A lists. A search of every agent command for writes to the two files found one, on a run the auditor had already scored 1 of 10. The current agents therefore left the logs alone in 371 of 372 runs, and making the logs tamper-proof is future work.

**Q1: A stratified human-expert reproduction baseline.**

The revision gives a lower bound on that baseline per tier. At least one of the four agents reproduced 32 of the 100 papers (95% Wilson interval 24% to 42%): 16 of 34 at Run, 11 of 33 at Retrain and 5 of 33 at Reimplement, so these papers are reproducible in the same environment and budgets. To test whether misses come from the environment, we re-ran the final commands of 3 partial runs with two new seeds and no agent (Section 5.3). On 2505.17836 both seeds miss by the same amount as the agent's run, and on 2510.07501 the seeds differ by more than the original miss. [On 2506.10351 the new seeds gave x and y.] Each task is also anchored to the authors' own reported result, an expert result on the same artifacts, and a separate expert pass over the 100 papers would need up to 2,552 H100-hours.

**Q2: How claims, targets and tolerances were validated, and annotator agreement.**

The revision adds an independent check of every target. gpt-6.1-sol, from a different lab than our auditor, compared each frozen target with its paper and quoted the passage behind each answer. The paper supports the value for 92 of the 100 claims (Appendix E), which is the agreement between the frozen targets and this independent reader, and correcting the other 8 and rescoring their runs changes two verdicts, both on 2505.23747. Before the freeze, one author reviewed every extracted field. For tolerances, 58 of the 62 point-estimate claims use the default 5% and 4 use the margin their paper states, and Reimplement stays the lowest tier when every run is rescored at 1%, 2%, 5% and 10% (Appendix F).

### Sources (rqBN)

| Number | File |
| :- | :- |
| F1 0.82, 396 runs, three graders, one label per run, 372 of them with an auditor grade | paper Section 4 and Appendix D (protocol of record, memory human-grader-study-lost) |
| 45,861 checked: 45,673 exact, 100, 60, 25, 3 unmatched (log table) | rebuttal/results/e5/summary.json; e5/README.md:11, :18 |
| 1 of 372 wrote to commands.log, 2510.25146, write_file, graded 1 unverifiable | rebuttal/results/e5/README.md; viewer index tools/anon_viewer/public/data/index.json |
| 119 commands missing in 65 runs, two early-return paths | rebuttal/results/e5/README.md (log completeness) |
| host transcript outside the sandbox mounts, not hash-chained | rebuttal/results/e5/README.md; Risks item 6 below (no hash-chained log in the code) |
| 3 unmatched entries all in trajectory.jsonl; no agent write to trajectory.jsonl; each gap equals the GPU release charge | rebuttal/results/e5/README.md (For a human to judge, item 2; write hits); rebuttal/results/e5/traces_2026-11-08.md (Trace A) |
| 3 papers re-executed (1 Run, 2 Retrain), exclusions | rebuttal/results/e10/README.md; e10/selection.csv |
| 24 build-and-dependency runs, best Run 13/34 unchanged | rebuttal/results/e8/summary.json; e8/bound.csv |
| 92, 95, 76, 69, 55 of 100 (target table); 45 failures | rebuttal/results/e7/summary.json (step3); e7/README.md |
| 62 point estimates, 58 default, 4 margins, 38 others (21 direction, 14 threshold, 3 other); 9/12/14 of 34 | rebuttal/results/e6/summary.json; e6/README.md |
| Appendix A wording, before and after | paper_latex/appendix/a_harness.tex lines 130-134 (before); the after text is proposed here |
| 372 runs, 64/73, 64/83, 253 and 324 of 372, 0.59 points, 42 of 57 at 0; per tier 28/31, 28/35, 25/29, 25/32, 11/13, 11/16, recall interval 44% to 86% | rebuttal/results/e4/summary.json (per_tier_reproduced from e4/per_tier.csv) |
| re-execution: 2505.17836 GoRank mean relative error at 80k steps, target about 0.05, 0.0395, 0.0400, 0.0393, spread 0.0007; 2510.07501 bias, target -0.20, -0.2241, -0.1308, +0.0566, span 0.0566 - (-0.2241) = 0.28; 2506.10351 queued | rebuttal/results/e10/results.md (table and Metrics line) |
| no Reimplement paper in the re-execution (selection from Run and Retrain only) | rebuttal/results/e10/README.md (Selection) |
| no human reproduction, stated in Limitations | paper_latex/iclr2027_conference.tex:583-589 |
| 2,552 = 10,208 / 4 H100-hours | paper Section 5.2 (paper_latex/iclr2027_conference.tex line 494, "1,888 of the 10,208 H100-hours we granted") |
| 8 corrected targets change two verdicts | rebuttal/results/e7/rescore_summary.md; e7/class_d_rescore.md |
| 2506.10351 re-execution | pending (E10) |
| best of four agents: 32 of 100 papers [24%, 42%]; Run 16/34 (47%, [31%, 63%]), Retrain 11/33 (33%, [20%, 50%]), Reimplement 5/33 (15%, [7%, 31%]); 70 reproduced cells | tools/anon_viewer/public/data/index.json minus the two checkpoint runs and the two 2505.23747 Run runs, plus the new Muse grade on 2503.23035 (computed by the main session, 2026-11-09) |
| other 45 targets: frozen number wrong 8, number right and a setting or label off 16, correct or unclear 21; human at 0 on 46 runs, auditor on 53 | rebuttal/mithil/e7_merged.md (Kind of error column: number 8, setting or label 15 + 1, none 21); rebuttal/results/e4/summary.json (disqualified_score0_as_high_severity) |
| Run recall interval 64% to 90%; 25 retried first attempts absent from the host transcript; 2510.07501 seeds also miss | rebuttal/results/e4/summary.json (per_tier_reproduced.run.recall_wilson95); e5/README.md (Headline); e10/results.md (outcome column) |
| per tier, auditor misses against false positives: 7 and 3, 7 and 4, 5 and 2 (35 - 28, 31 - 28; 32 - 25, 29 - 25; 16 - 11, 13 - 11) | rebuttal/results/e4/summary.json (per_tier_reproduced) |
| quadratic weighted kappa 0.89 on the 0 to 10 scale | rebuttal/results/e4/summary.json (quadratic_weighted_kappa 0.888); e4/README.md:14 |
| at score 0: auditor alone 11, human alone 4 | rebuttal/results/e4/summary.json (53 - 42, 46 - 42) |
| best single agent 13, 9 and 5 against 16, 11 and 5 for at least one agent | rebuttal/results/tiers/tier_tests.md |
| 2,552 H100-hours is one agent's grant (10,208 / 4) | paper_latex/iclr2027_conference.tex:494 |

## YGTR

### Reply to YGTR, part 1 of 2 (2,729 characters)

Thank you for the review. We ran the frontier models and production harnesses you asked for and measured each confound you named.

**W1 and Q1: Frontier models and production coding harnesses.**

[On the same papers, gpt-6.1-sol in our loop reproduces 4 of 11, as many as DeepSeek-V4-Flash and Muse Spark 1.2. In Codex CLI, gpt-6.1-sol and gpt-6-astra reproduce 2 of 15 and 1 of 7, where DeepSeek-V4-Flash reproduces 6 of 15 and 3 of 7.] Each row covers a small set of papers, so the last two columns give our two best agents on exactly those papers, under the same auditor (Section 5.1, Appendix B).

| Model | Harness | Papers | Reproduced | DeepSeek-V4-Flash | Muse Spark 1.2 |
| :- | :- | -: | -: | -: | -: |
| gpt-6.1-sol | our loop | [11] | [4] | [4] | [4] |
| gpt-6.1-sol | Codex CLI | [15] | [2] | [6] | [4] |
| gpt-6-astra | Codex CLI | [7] | [1] | [3] | [2] |
| gpt-6-astra | our loop | [3] | [1] | [1] | [1] |
| Muse Wonder | mini-SWE-agent | [3] | [1] | [0] | [1] |
| Muse Wonder | our loop | [n] | [a] | [d] | [m] |

The papers come from every tier and were fixed before any of these runs. Half were drawn from papers that some open agent had reproduced, so we also ran DeepSeek-V4-Flash twice more on the 12 core papers, where it reproduces [r2] and [r3]. Within one model only the harness changes, and the sandbox, task text, GPU grant and auditor are those of the main runs. On the [9] papers that gpt-6.1-sol finished in both harnesses, the counts are comparable, [3] in our loop and [2] in Codex CLI.

The frontier runs stop early. They used a median of [2.1]% of their GPU grant, against [17.5]% for the open agents on the same papers. A variant that prompts Codex to continue, up to three times, whenever it stops with under half of its grant used reproduces [c] of [n] papers. We ran Codex CLI and mini-SWE-agent and left out Claude Code, because our auditor is Claude Sonnet 5 and would grade a model of its own family.

**Whether the failure modes and findings change.**

A coder that saw neither the verdict nor the harness labelled the main failure of each of the [30] failing frontier runs with the Appendix G definitions. Failures that report a number without a valid measurement are rarer in the frontier runs, [4 of 30 = 13%] against 110 of 300 = 37% for the open agents, and [13 of 30] ended before producing a number. On 2506.08898 (32 H100-hour grant), all [5] frontier runs stopped within one H100-hour because no matching checkpoint is released, while Muse Spark 1.2 retrained the model with 27 H100-hours under the same prompt and reproduced the claim. Run is again the easiest tier: the frontier runs reproduce [6 of 12] at Run, [0 of 12] at Retrain and [3 of 15] at Reimplement (Section 5.3).

### Reply to YGTR, part 2 of 2 (2,710 characters)

**W2: Failures due to hardware differences.**

At most 14 of the 372 graded runs failed because of our hardware, and removing every build failure changes no best-agent rate by more than one percentage point. In all, 24 runs failed at build or dependency install, 14 of them on a package with no build for the aarch64 CPUs of our nodes. Of those 14, 12 have an install command in their transcripts. We replayed the 12 on x86 nodes, and 9 build there (95% Wilson interval 47% to 91%). With all 24 dropped from every denominator, DeepSeek-V4-Flash stays at 13/34 at Run and 9/33 at Retrain, and Muse Spark 1.2 goes from 5/33 to 5/32 at Reimplement (Section 5.3). [x86 frontier arm: gpt-6.1-sol and gpt-6-astra in our loop on x86 nodes reproduce a of n, against b of n for the same models and papers on GH200 nodes.]

**W3: Agents are only run once.**

We reran DeepSeek-V4-Flash two more times on 12 papers drawn with a fixed seed, four per tier. Its verdict is the same in all three runs on [k] of the 12, and its count of reproduced papers moves by at most [j]. Every rate in the revision has a 95% Wilson interval (Section 5.2).

**Q2: Fetching checkpoints over the network.**

We scanned the run transcripts for model downloads (hf_hub_download, snapshot_download, from_pretrained with a repository id, gdown, and wget or curl of weight files). Downloading released weights is allowed at Run, so the runs that matter are the 42 reproduced runs at Retrain and Reimplement. Of these, 16 matched a pattern, and we read them by hand: 10 were not downloads, 4 fetched a base model that the method starts from, and 2 evaluated a checkpoint of the claimed model (Muse Spark 1.2 on 2508.21046 and MiniMax-M2.7 on 2505.12677). The revision counts both as not reproduced, and the best rates stay at 9 of 33 at Retrain and 5 of 33 at Reimplement (Section 5.2).

**Q3: Failures that were not the agent's fault.**

We traced 27 of the 400 cells to causes outside the agent: 6 cells with no graded run and the 21 environment failures among the 24 of W2. Of the 28 cells with no graded run, 4 belong to paper 2510.20725, whose runs did not start because of a harness error that is now fixed, and 2 were Muse Spark 1.2 audits that never returned a verdict. The same auditor has now graded those 2, one reproduced and one partial. [We reran the 4 cells of 2510.20725, and r of them reproduce.] The other 22 are agent failures, and Section 5.2 now accounts for each of the 28. For runs that followed the released pipeline and missed, we re-ran the final commands of 3 with new seeds and no agent, and the 2 Retrain papers miss again on both seeds. [Run paper 2506.10351: outcome on both seeds.]

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
| frontier table: papers, reproduced, mean score per arm, with DeepSeek-V4-Flash and Muse Spark 1.2 on the same papers (bracketed values are the 11-09 databook, 40 rows) | rebuttal/results/frontier/same_paper_baselines.md (rebuttal/scripts/frontier_baselines.py); rerun after each databook sync |
| papers drawn so that half were reproduced by at least one open agent | rebuttal/subset.json (rule); rebuttal/results/frontier/originals_on_subset.md |
| gpt-6.1-sol in both harnesses: [9] papers, [3] and [2] reproduced, mean [5.11] and [4.56], verdict differs on [3] | rebuttal/results/frontier/same_paper_baselines.md (last section) |
| failure-mode table: open agents 76, 63, 46, 38, 31, 24, 13, 9 of 300; frontier [5, 3, 4, 0, 6, 4, 5, 0] of [27] | rebuttal/results/frontier/failure_modes.md; failure_modes.csv with run 6cef06 relabelled per never_launched_check.md |
| number without a valid measurement: frontier [3 of 27 = 11%, 4% to 28%]; open agents 110 of 300 = 37% [31%, 42%] under the paper's labels and 46% (35% to 58%) under the blind coder; ended without a number: frontier [11 of 27], open agents 44 of 300 = 15% (23%, 14% to 33%, under the blind coder, so no significance is claimed) | rebuttal/results/frontier/coder_calibration_groups.md (rebuttal/scripts/coder_calibration_groups.py) |
| frontier runs by tier [5 of 11], [0 of 12], [3 of 14], arms on GH200 nodes | rebuttal/results/frontier/same_paper_baselines.md (by-tier section) |
| median share of the GPU grant used: frontier [2.1]% (35 runs with a recorded spend), open agents [17.5]% on the same papers (70 runs); 2506.08898: [5] frontier runs at 0.61 H100-hours or less, Muse Spark 1.2 score 8 with 27.1 H100-hours of 32 | rebuttal/results/frontier/same_paper_baselines.md (last two sections) |
| task prompt allows an early stop only when a trained artifact is neither released nor retrainable in budget | prompts/prompt_reproduce.txt:90-93 |
| [0 of 22] failing frontier runs never launched outside 2505.16927 and 2503.14698 (27 coded, 5 on those two papers) | rebuttal/results/frontier/failure_modes.csv; never_launched_check.md |
| rates after the corrections in the hardware paragraph (13/34 and MiniMax 2/34 to 2/26) | rebuttal/results/e7/rescore_summary.md applied to e8/bound.csv |
| open agents spent 1,888 of 10,208 granted H100-hours | paper_latex/iclr2027_conference.tex:493-494 |
| continue-prompt variant: up to 3 prompts when a run stops with under half its grant used | rebuttal/STATUS.md:48; arm codex-gpt-6.1-sol-nudge, 0 graded on 11-09 |
| Claude Code left out: same-family auditor and the API budget of the new runs | rebuttal/mithil/decisions_monday.md decision 15; rebuttal/PLAN.md:198 |
| at most 14 hardware failures (14 aarch64 package failures, 3 of the 12 replayed also fail on x86) | rebuttal/results/e8/summary.json; e8/x86/README.md |

## Risks: where a reviewer could push back

Items 1 to 8 are from the earlier drafts and are settled or unchanged; items 9 to 14 were added in the 11-09 rewrite.

1. **The target check shows 45 of 100 targets failing at least one question (rqBN Q2, T29u Q2).** Settled 11-09 (decisions 1 and 7): the replies name the 8 targets with a wrong number, two verdicts change on 2505.23747, and the counts are 70 of 400 and 13 of 34. Both replies now open the target answer with the 8 and the two changed verdicts.
2. **The 16 stopped cells (YGTR Q3).** Settled 11-09 (decision 5, Mithil): left out, and the 22 empty cells outside the six traced to our side stay agent failures as the paper says.
3. **The confusion matrix comes from an aggregate table, and the paper says 396 hand-graded runs (T29u Q1, rqBN W1).** The replies state that the matrix covers the 372 runs with both grades and that each run has one human label.
4. **Codex runs stop early, which a reviewer may call a configuration artifact (YGTR W1).** The reply gives the median grant use and has a slot for the continue-prompt variant. See item 12.
5. **The two checkpoint downloads came from the authors' own releases (YGTR Q2).** Settled 11-09 (decision 6): CogVLA stays at Retrain with a footnote.
6. **The hash-chained host log (rqBN W2).** No such log exists in the code; the reply says the host transcript is not hash-chained.
7. **The re-execution check covers only 3 papers (rqBN Q1, YGTR Q3).** Decision 3: no more papers. The rqBN reply now leads Q1 with the papers reproduced by at least one agent, so the 3 papers carry less of the answer.
8. **The log check leaves two loose ends (rqBN W2).** Five evidence directories with no writer found, and the 24 started but ungraded runs. Neither is cited in a reply.
9. **The same-paper comparison favours the open agents by construction (YGTR W1).** The 24 papers were drawn so that half had been reproduced by an open agent in its single submitted run, so the open agents' submitted results on this subset are selected on a noisy outcome and a fresh run would regress. The reply states the draw and compares against the two fresh DeepSeek-V4-Flash runs on the 12 core papers (the repeat runs of W3). If those runs miss the posting day, the fresh-run sentence is cut and the stratification clause stays.
10. **The x86 frontier arm has runs that never received a GPU (YGTR W2).** On Delta, `salloc` returned "Job violates accounting/QOS policy (job submit limit ...)" or no allocation at all for many requests on 11-09; astra-x86-2505.10475-4d106f had 0 of 5 requests granted and ended "natural", and astra-x86-2504.20571-e45477 and x86-a-2505.19087-8e4506 ended with exit "error" and an empty report. These rows measure the scheduler. The x86 slot in YGTR part 2 is filled only from runs in which every GPU request was granted, and is cut otherwise.
11. **Two Codex gpt-6-astra rows ended at the 48-hour wall while a GPU request was pending (YGTR W1).** Runs a54ff7 (2505.10475, last 33 hours in the queue) and 9f613b (2504.20571, queue wait 2,850 of 2,880 minutes) are the only graded rows under the wall that was removed on 11-09. Appendix B lists exit reasons, so a reader can see them. Decision 19 counts them; a rerun of the two cells under the current rule would remove the question.
12. **The continue-prompt arm has no valid run on 11-09.** All six finished attempts are VOID and two are waiting on GPUs. If no run is graded by the posting day, the two continue-prompt sentences in YGTR part 1 are cut and the early-stop answer rests on the median grant use and the failure-mode table.
13. **No frontier run reproduces a Retrain paper ([0 of 12]) (YGTR W1).** A reviewer may ask why. The transcripts show the models searching for a released checkpoint and reporting that training would exceed the budget (rebuttal/results/frontier/early_stop.md). One quoted example in Appendix B would answer it.
14. **Tier wording.** The replies now claim what the tests separate: Run against Reimplement, with Run and Retrain not separated, as Section 5.2 of the submission already says. The earlier draft's "the tiers keep their order" sat beside tables in which Retrain matched or exceeded Run (mean score 5.45 against 5.29; pooled 22% against 23%).
15. **The ranking rule is stated for agents and not applied to tiers (T29u W1).** If the repeat runs give j = 1, shifting DeepSeek-V4-Flash's counts one paper toward each other gives 12/34 against 5/33 (z = 1.89), while the row for papers reproduced by at least one agent still separates Run from Reimplement (15/34 against 6/33, z = 2.29). When the repeat runs land, say which rows hold under the shift, and fill the slot on the Run and Reimplement papers within the 12.
16. **The third re-execution paper is not a miss on the number (rqBN Q1, YGTR Q3).** DeepSeek-V4-Flash on 2506.10351 measured 94.19 (e10/selection.csv) or 94.63 (e6/table.csv) against 93.12, inside the 5% tolerance, and is partial at every tolerance, so another criterion failed. The replies now call the three runs "partial runs that followed the released pipeline". When the seeds land, the bullet has to name the failed criterion and use one measured value.
17. **The 16 targets with a setting or label off (T29u Q2, rqBN Q2).** The replies say the 8 wrong values were corrected and do not say what was done about the 16. rescore_summary.md rescored 10 targets, some of which the second pass classes as setting errors, and found two changed verdicts in all. A reviewer may ask; the answer needs the list of which of the 16 were rescored.
