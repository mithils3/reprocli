# E7 sensitivity: re-grading the cells of the 10 papers whose frozen target is wrong

This answers one question: if the 10 targets that E7 marked as wrong (kind `value_wrong` in `rebuttal/mithil/e7_verdicts.csv`) are corrected to what each paper reports, how many reproduced / not-reproduced results change, and does any tier's best-agent count move. The frozen file `eval_100.jsonl` (md5 ab205529), the rubric and the audit prompt were not touched.

## What was done

1. `corrected_targets.jsonl` has 10 rows. Each is the frozen claim row with only `match_target` config, value and scope edited, plus `e7_correction_note` and `e7_evidence_line`. Every number that is new to an edited field was found in the paper text by `rebuttal/e7_corrected_targets.py`. The prose fields (`central_claim`, `claim_evidence`, `mre_config`) are unchanged, so for 2505.23747 and 2511.00090 they still mention the old setting; the pinned success bar is what the grader adopts.
2. Every original cell of those papers was graded twice by the pinned auditor (claude-sonnet-5, same rubric and prompt, same session): once against the frozen claim and once against the corrected claim. The grader already accepts `--claims FILE`, so no grader change was needed. Launcher: `scripts/rebuttal/e7_regrade.py`. Raw grades: `rescore_grades.jsonl`. Per-cell table: `rescore_corrected.csv`.
3. 38 of 40 cells have a run and were graded 76 times in all. The other 2 (`dsv4-run-2506.18896`, `minimax-run-2506.18896`) never produced a run and count as not reproduced under every target, so they cannot change.

## Result

A cell counts as reproduced when the auditor's verdict is `reproduced`. Among the 38 graded cells, 3 were reproduced in the paper, 3 after re-grading on the frozen claim, and 1 after re-grading on the corrected claim.

- **Rescoring noise (paper grade vs re-grade on the frozen claim):** 0 cells change reproduced / not-reproduced. 3 cells change verdict label inside not-reproduced (disqualified or unverifiable to not_reproduced), and 8 of 38 integer scores differ, mean absolute difference 0.39 points.
- **Correction effect (re-grade on the frozen claim vs re-grade on the corrected claim):** 2 of 40 cells change reproduced / not-reproduced, both from reproduced to partial: `dsv4-run-2505.23747` and `minimax-run-2505.23747`. 10 of 38 verdict labels differ in all, 15 of 38 scores, mean absolute score difference 1.08 points, mostly in not-reproduced to disqualified or partial moves. Of the 10 papers, 2511.00090 moves most (3 of 4 cells, all downward).
- Both flips are on 2505.23747, where the frozen 51.13% was the v1.1 README number and the paper's Spatial-MLLM-4B value is 48.4%. The third reproduced cell (`muse-run-2505.23747`) stays reproduced, 8 points of 10.

Best agent per tier (reproduced count over the tier size, Wilson 95% interval), with the other 390 cells unchanged from E6:

| Tier | Before (paper) | After, corrected targets |
|---|---|---|
| Run (/34) | dsv4 14 = 41.2% [26.4, 57.8] | dsv4 13 = 38.2% [23.9, 55.0] |
| Retrain (/33) | dsv4, muse 9 = 27.3% [15.1, 44.2] | dsv4, muse 9 (unchanged) |
| Reimplement (/33) | muse 5 = 15.2% [6.7, 30.9] | muse 5 (unchanged) |

Overall reproduced cells fall from 73 to 71 of 400 (18.2% [14.8, 22.3] to 17.8% [14.3, 21.8]). The re-grade on the frozen claim leaves every count at its paper value.

## Worked cell: dsv4-run-2505.23747

The agent evaluated the v1.1 checkpoint on VSI-Bench and measured 51.44 micro average accuracy. Against the frozen target 51.13 with the default 5% relative tolerance: |51.44 - 51.13| / 51.13 = 0.31 / 51.13 = 0.61%, inside the bar, so score 9, reproduced. Against the corrected target 48.4 (paper Table 1, Spatial-MLLM-4B): |51.44 - 48.4| / 48.4 = 3.04 / 48.4 = 6.29%, outside the bar, and the auditor also notes the checkpoint is not the paper's 4B model, so score 6, partial. For dsv4 in the Run tier that moves 14 to 13 of 34 = 41.2% to 38.2%.

## Caveats

- The agents' task text was not changed, so a cell can fall only because the agent worked from the old setting (the v1.1 checkpoint in 2505.23747 is the clear case). The analysis re-grades the existing runs against the corrected target; it does not re-run the agents.
- For 2506.18896 the frozen bar was a threshold (greater than 80%); the paper has no 80, so the corrected value is the Table 2 number 84.8 and the kind was left as threshold. For 2511.00090 the Latte 2.93x row was chosen because the claim sentence names Latte; the Wan2.1 setting is not in the paper.
- Cost: 76 logged grades, $60.35 in the spend ledger (item E7-rescore, provider anthropic). Three calls (two grades that returned no parsable verdict and were re-run, plus the in-flight calls when I restarted at higher concurrency) are not in the ledger and cost a few dollars more; one of them is $1.33 per its log.
