# Open agents on each frontier arm's own papers

Source: rebuttal/results/databook/frontier_cells.csv (63 graded rows). Reproduced means score 8 or more. Open-agent columns use the submitted score of that agent on the same papers, an empty cell scoring 0. Intervals are Wilson 95%.

| arm | graded | reproduced | mean score | DeepSeek-V4-Flash reproduced | DeepSeek-V4-Flash mean | Muse Spark 1.2 reproduced | Muse Spark 1.2 mean | Qwen3.6-27B reproduced | Qwen3.6-27B mean | MiniMax-M2.7 reproduced | MiniMax-M2.7 mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| codex-gpt-6-astra | 8 | 2/8 [7%, 59%] | 3.75 | 4/8 | 5.88 | 3/8 | 5.62 | 2/8 | 4.38 | 2/8 | 3.50 |
| codex-gpt-6.1-sol | 23 | 4/23 [7%, 37%] | 5.00 | 8/23 | 5.74 | 7/23 | 5.57 | 5/23 | 4.00 | 4/23 | 2.96 |
| thin-gpt-6.1-sol | 12 | 5/12 [19%, 68%] | 5.67 | 4/12 | 5.42 | 4/12 | 5.25 | 3/12 | 3.83 | 2/12 | 3.00 |
| miniswe | 5 | 3/5 [23%, 88%] | 6.60 | 2/5 | 5.40 | 2/5 | 5.40 | 2/5 | 4.60 | 1/5 | 2.80 |
| thin-gpt-6-astra | 6 | 1/6 [3%, 56%] | 4.83 | 4/6 | 7.17 | 3/6 | 7.17 | 2/6 | 4.67 | 2/6 | 4.33 |
| thin-gpt-6-astra-x86 | 3 | 2/3 [21%, 94%] | 6.00 | 2/3 | 6.67 | 1/3 | 6.33 | 2/3 | 6.67 | 1/3 | 4.67 |
| thin-gpt-6.1-sol-x86 | 3 | 2/3 [21%, 94%] | 8.00 | 2/3 | 6.67 | 1/3 | 6.00 | 2/3 | 6.00 | 1/3 | 5.33 |
| thin-muse-wonder-1.0 | 1 | 0/1 [0%, 79%] | 3.00 | 0/1 | 4.00 | 0/1 | 4.00 | 0/1 | 4.00 | 0/1 | 0.00 |
| codex-gpt-6.1-sol-nudge | 2 | 1/2 [9%, 91%] | 7.50 | 2/2 | 8.00 | 1/2 | 8.00 | 0/2 | 4.00 | 1/2 | 6.00 |

## Frontier runs by tier

| arm | Run | Retrain | Reimplement |
|---|---|---|---|
| codex-gpt-6-astra | 1/3 | 0/3 | 1/2 |
| codex-gpt-6.1-sol | 2/7 | 1/8 | 1/8 |
| thin-gpt-6.1-sol | 4/4 | 0/4 | 1/4 |
| miniswe | 2/2 | 0/1 | 1/2 |
| thin-gpt-6-astra | 1/2 | 0/2 | 0/2 |
| thin-gpt-6-astra-x86 | 1/1 | 0/0 | 1/2 |
| thin-gpt-6.1-sol-x86 | 2/2 | 0/0 | 0/1 |
| thin-muse-wonder-1.0 | 0/0 | 0/0 | 0/1 |
| codex-gpt-6.1-sol-nudge | 1/1 | 0/1 | 0/0 |
| all arms on GH200 nodes | 11/19 [36%, 77%] | 1/19 [1%, 25%] | 4/19 [9%, 43%] |

## gpt-6.1-sol, our loop against Codex CLI, papers graded in both

| paper | tier | our loop | Codex CLI |
|---|---|---|---|
| 2502.05795 | run | 8 | 8 |
| 2503.02809 | reimplement | 8 | 7 |
| 2503.14698 | reimplement | 1 | 2 |
| 2504.12463 | retrain | 2 | 2 |
| 2504.20571 | run | 8 | 8 |
| 2505.16927 | reimplement | 1 | 1 |
| 2505.19087 | reimplement | 7 | 8 |
| 2506.06991 | retrain | 6 | 6 |
| 2506.08898 | retrain | 4 | 4 |
| 2506.20671 | run | 8 | 2 |
| 2510.21363 | retrain | 7 | 7 |

Papers in both: 11. Reproduced: our loop 4, Codex CLI 3. Same verdict on 8; reproduced only in our loop 2, only in Codex CLI 1. Mean score: our loop 5.45, Codex CLI 5.00.

## Share of the GPU grant used

Frontier runs on GH200 nodes with a recorded spend: 57 of 57; median 5.0% of the grant, 29 of 57 under 5%. Open agents, submitted runs on the same 24 papers: 92 runs, median 14.3% of the grant.

## Paper 2506.08898 (Retrain, 32 H100-hour grant)

Frontier runs: thin-gpt-6.1-sol score 4, 0.18 H100-h; codex-gpt-6-astra score 2, 0.17 H100-h; miniswe score 6, 0.29 H100-h; codex-gpt-6.1-sol score 4, 0.61 H100-h; thin-gpt-6-astra score 4, 0.46 H100-h.
Open agents: dsv4 score 7, 29.4 H100-h; minimax score 0, 0.7 H100-h; muse score 8, 27.1 H100-h.
