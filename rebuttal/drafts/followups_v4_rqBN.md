# Second-round answers for Reviewer rqBN, 2026-11-16, prepared, not posted (result paths under rebuttal/; S = scratchpad followup_1116)

### If asked: only 55 targets pass all four checks

The 92 counts the value question alone, and 55 targets pass all four questions of Table 15. The table pools the four agents at the revision's grades.

| Tier | All 100 | 55 passing all four |
| :- | -: | -: |
| Run | $\frac{30}{136}$ = 22% | $\frac{19}{76}$ = 25% |
| Retrain | $\frac{28}{132}$ = 21% | $\frac{7}{52}$ = 13% |
| Reimplement | $\frac{12}{132}$ = 9% | $\frac{10}{92}$ = 11% |
| All | $\frac{70}{400}$ = 18% | $\frac{36}{220}$ = 16% |

Reimplement stays the lowest tier, and the rate on the other 45 targets is $\frac{34}{180}$ = 19% (Fisher's exact test, p = 0.51). Removing the 16 targets whose number matches the paper while a setting or label is off leaves $\frac{53}{336}$ = 16%, with Reimplement lowest at $\frac{12}{128}$ = 9%. gpt-6.1-sol saw each frozen target and quoted the passage behind every answer, and one author reviewed every target, so these counts are the agreement between that review and a second reader.

Source: S/ev_targets/ev_targets_raw.txt section B: 36 of 220, 34 of 180, 53 of 336, p = 0.5119; per-model rows on the 55 sum to 19, 7, 10.
Source: recomputed today from results/e6/table.csv and mithil/e7_merged.md at the revision's grades: 30, 28, 12; 12 of 128 (the grades at submission give 31, 29, 13, which is Table 13's auditor column).
Caution: 17 of the 70 reproduced cells sit on 7 of the 16 setting-or-label targets, and not all 16 were rescored. The best agent on the 55 reproduces 9 of 19, 2 of 13 and 4 of 23, so Retrain falls below Reimplement there; on the other 45, Retrain (21 of 80) beats Run (11 of 60).

### If asked: a small stratified human baseline is feasible

We agree that a few papers per tier is the right size for this baseline, and since we have no human reproduction at any size, we give the two closest measurements from the same sandbox and GPU grant. First, at least one of our four agents reproduces 32 of the 100 papers, and the frontier models reproduce 2 of the 12 sampled papers that none of the four had, both at Run. That makes 34 targets known to be reachable there: 18 at Run, 11 at Retrain and 5 at Reimplement. Second, if each of the 76 runs that executed the paper's pipeline and landed outside tolerance is charged to the paper and dropped, the best agent at the submitted grades reproduces $\frac{14}{29}$ = 48% at Run, $\frac{9}{18}$ = 50% at Retrain and $\frac{5}{31}$ = 16% at Reimplement, so the low Reimplement rate remains.

Source: PDF Section 5.2: 32 (16, 11, 5). PDF Appendix B.3 and results/frontier/same_paper_baselines.md line 60: 2 papers (2505.10475, 2506.20671, both Run).
Source: S/ev_faithful/ev_faithful.md: 76; 14 of 29, 9 of 18, 5 of 31.
Caution: no human reproduction exists. The 34 is my sum, 32 + 2, and equals the submission's old 34 by coincidence. The second rates use submitted grades and are in no PDF table.

### If asked: each run has only one human label

Each run has one human label, so the F1 of 0.82 measures the auditor against one grader per run and we cannot report agreement between humans. The human labels alone give $\frac{35}{136}$ = 26% at Run, $\frac{32}{132}$ = 24% at Retrain and $\frac{16}{132}$ = 12% at Reimplement (Table 13), the same order as the auditor's grades. Across the three graders, who each scored a different share of the runs, the auditor's score is within one point of the human's on $\frac{324}{372}$ = 87% of runs ($\kappa$ = 0.89). A second grading of 38 runs by the auditor moved none between reproduced and not reproduced.

Source: PDF Table 13, human column. results/e4/README.md: 324 of 372, kappa 0.89. results/e7/rescore_summary.md: 0 of 38 cells change.
Caution: nothing on disk names the graders or holds per-run labels, so "were they authors" is yours to answer. The 38 regraded runs come from 10 papers picked for target errors; 3 were reproduced and 8 scores differ.

### If asked: score 0 agreement does not validate flags

A score of 0 covers a high-severity flag and three related conditions (Table 10), so the 42 of 57 is agreement on integrity breaks as a whole. The human graders disqualified 46 runs, and the auditor called none of them reproduced (Table 11), while the auditor alone placed 11 runs at 0 against 4 for the human, so the auditor is the stricter of the two on integrity. The checkpoint scan, which uses neither grader, covered all 42 reproduced Retrain and Reimplement runs and found 2 that evaluated a downloaded checkpoint of the claimed model. The auditor had accepted both, and both now count as not reproduced, which leaves $\frac{40}{42}$ = 95% with no such download found.

Source: PDF Table 11, human Disqualified row: 0, 1, 2, 1, 42. PDF Appendix D: 57, 42, 11, 4.
Source: PDF Appendix B.2 and results/e9/README.md: 42 runs (29 + 13), 2 ready checkpoints.
Caution: no human check of individual flags exists, and the scan misses downloads made inside an imported library.

### If asked: the numbered step logs stay writable

The numbered step logs stay in the agent-writable evidence folder, and the numbers in them are backed by copies that the sandbox cannot reach. The harness streams each GPU step's output to its step log and returns that output, shortened when long, as the tool result. It writes the result to the host transcript, outside every directory the sandbox mounts, and posts it with the command to the external database. Of the 30,790 commands in both the logs and the database, 30,739 match on text and exit code, and the other 51 match on text and have no exit code stored in the database. Our search of every agent command for writes into the evidence folder found none that targets a numbered step log.

Source: results/e5/db_check/db_summary.json: matched 30739, matched_command_only 51. Code: src/reprocli_repro/tools/run_gpu.py:12,179 and src/reprocli_repro/supabase_sink.py:38,87-95.
Source: results/e5/flags_all.tsv.gz, counted today: 4 of 6,243 write_evidence rows contain gpu_step_, each a `cp` that reads it.
Caution: no comparison of stored output against step-log content has been run. The write search is a pattern match that misses writes made inside a script or after a `cd`, and the database keeps only the first 8,000 characters of a result.

### Short reply if the follow-up is the predicted one

Thank you for the follow-up, and for setting the 55 of Table 15 beside the 92 from our reply, since the full answer needs both numbers.

**Targets.** The 92 counts the value question alone, and 55 targets pass all four. Pooled over the four agents, the reproduction rate is $\frac{36}{220}$ = 16% on those 55 and $\frac{34}{180}$ = 19% on the other 45 (Fisher's exact test, p = 0.51). On the 55 it is $\frac{19}{76}$ = 25% at Run, $\frac{7}{52}$ = 13% at Retrain and $\frac{10}{92}$ = 11% at Reimplement, so Reimplement stays the lowest tier. One author reviewed each target, and these counts are the agreement between that review and a second reader.

**One human label.** Each run has one label, so we cannot report agreement between humans. The human labels alone give $\frac{35}{136}$ = 26% at Run, $\frac{32}{132}$ = 24% at Retrain and $\frac{16}{132}$ = 12% at Reimplement (Table 13), the same order as the auditor's grades.

**Baseline.** We agree that a few papers per tier is the right size, and we have no human reproduction at any size. In the same sandbox and GPU grant, our four agents reproduce 32 of the 100 papers and the frontier models add 2 that none of the four had, so 34 targets are known to be reachable there: 18 at Run, 11 at Retrain and 5 at Reimplement.
