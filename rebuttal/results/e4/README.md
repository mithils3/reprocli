# E4: auditor against human grades

Input: `matrix_0_10.csv`, the 0 to 10 table of human score (rows) against pinned-auditor score (columns), supplied by Mithil on 2026-11-08 as an aggregate table. No per-run label file is on disk, so per-tier F1 and per-run checks are not possible.

Check: the auditor column totals equal the score counts of the 372 graded runs in `tools/anon_viewer/public/data/index.json` (53, 10, 47, 17, 72, 14, 60, 26, 52, 16, 5); `e4_stats.py` asserts this before computing. The paper says 396 runs were hand-graded; the table covers the 372 that also have an auditor grade.

Run: `python3 e4_stats.py matrix_0_10.csv ../../../tools/anon_viewer/public/data/index.json summary.json`

| Result | Value |
| :- | :- |
| Reproduced (8 or more): auditor 73, human 83, both 64 | precision 64/73 = 88% [78, 93], recall 64/83 = 77% [67, 85], F1 2 × 64 / (73 + 83) = 0.82 |
| Only one side called it reproduced | human 19, auditor 9 |
| Five-way verdict agreement | 306 of 372 |
| Same 0 to 10 score / within one point | 253 / 324 of 372; mean absolute difference 0.59; auditor minus human −0.26 on average; quadratic weighted kappa 0.89 |
| Either at 7 or 8 | 100 runs, 75 agree on the side of the 8 line |
| Score 0 (high-severity flag) | human 46, auditor 53, both 42, either 57 |
