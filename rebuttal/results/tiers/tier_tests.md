# Tier comparisons after the rebuttal corrections

Source: tools/anon_viewer/public/data/index.json (372 graded runs), plus [('muse', 'run', '2503.23035')], minus ['muse-retrain-2508.21046', 'minimax-reimplement-2505.12677', 'dsv4-run-2505.23747', 'minimax-run-2505.23747']. Reproduced cells: 70 of 400. z is the two-proportion z statistic with a pooled variance.

| row | Run | Retrain | Reimplement | z Run vs Reimplement | z Retrain vs Reimplement | z Run vs Retrain |
|---|---|---|---|---|---|---|
| dsv4 | 13/34 = 38% [24%, 55%] | 9/33 = 27% [15%, 44%] | 4/33 = 12% [5%, 27%] | 2.46 | 1.55 | 0.96 |
| muse | 10/34 = 29% [17%, 46%] | 8/33 = 24% [13%, 41%] | 5/33 = 15% [7%, 31%] | 1.40 | 0.93 | 0.48 |
| qwen3 | 5/34 = 15% [6%, 30%] | 6/33 = 18% [9%, 34%] | 2/33 = 6% [2%, 20%] | 1.16 | 1.51 | -0.38 |
| minimax | 2/34 = 6% [2%, 19%] | 5/33 = 15% [7%, 31%] | 1/33 = 3% [1%, 15%] | 0.56 | 1.71 | -1.24 |
| papers reproduced by at least one agent | 16/34 = 47% [31%, 63%] | 11/33 = 33% [20%, 50%] | 5/33 = 15% [7%, 31%] | 2.81 | 1.72 | 1.15 |
| all four agents pooled (cells; not independent within a paper) | 30/136 = 22% [16%, 30%] | 28/132 = 21% [15%, 29%] | 12/132 = 9% [5%, 15%] | 2.92 | 2.75 | 0.17 |

## Mean audit score (0 to 10), 95% t-interval over the tier's papers

| agent | Run | Retrain | Reimplement | all 100 papers |
|---|---|---|---|---|
| dsv4 | 5.29 [4.13, 6.46] | 5.45 [4.40, 6.51] | 4.64 [3.79, 5.49] | 5.13 [4.55, 5.71] |
| muse | 5.71 [4.81, 6.60] | 5.85 [4.94, 6.76] | 3.85 [2.86, 4.84] | 5.14 [4.59, 5.69] |
| qwen3 | 3.91 [2.97, 4.85] | 3.58 [2.54, 4.61] | 3.03 [2.17, 3.89] | 3.51 [2.98, 4.04] |
| minimax | 3.09 [2.09, 4.09] | 3.30 [2.24, 4.36] | 2.70 [1.80, 3.59] | 3.03 [2.48, 3.58] |
| all agents (cells) | 4.50 [3.98, 5.02] | 4.55 [4.02, 5.07] | 3.55 [3.10, 4.00] | 4.20 [3.91, 4.49] |
