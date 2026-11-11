# Open agents on each frontier arm's own papers

Source: rebuttal/results/databook/frontier_cells.csv (51 graded rows). Reproduced means score 8 or more. Open-agent columns use the submitted score of that agent on the same papers, an empty cell scoring 0. Intervals are Wilson 95%.

| arm | graded | reproduced | mean score | DeepSeek-V4-Flash reproduced | DeepSeek-V4-Flash mean | Muse Spark 1.2 reproduced | Muse Spark 1.2 mean | Qwen3.6-27B reproduced | Qwen3.6-27B mean | MiniMax-M2.7 reproduced | MiniMax-M2.7 mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| codex-gpt-6-astra | 7 | 1/7 [3%, 51%] | 3.14 | 3/7 | 5.57 | 2/7 | 5.14 | 2/7 | 4.43 | 2/7 | 3.43 |
| codex-gpt-6.1-sol | 19 | 2/19 [3%, 31%] | 4.53 | 6/19 | 5.79 | 4/19 | 5.16 | 4/19 | 3.95 | 3/19 | 2.84 |
| thin-gpt-6.1-sol | 11 | 4/11 [15%, 65%] | 5.45 | 4/11 | 5.91 | 4/11 | 5.73 | 3/11 | 3.91 | 2/11 | 3.27 |
| miniswe | 5 | 3/5 [23%, 88%] | 6.60 | 2/5 | 5.40 | 2/5 | 5.40 | 2/5 | 4.60 | 1/5 | 2.80 |
| thin-gpt-6-astra | 5 | 1/5 [4%, 62%] | 5.40 | 3/5 | 7.00 | 2/5 | 6.80 | 2/5 | 4.80 | 2/5 | 4.40 |
| thin-gpt-6-astra-x86 | 2 | 1/2 [9%, 91%] | 5.00 | 1/2 | 6.00 | 0/2 | 5.50 | 1/2 | 6.00 | 0/2 | 3.00 |
| thin-gpt-6.1-sol-x86 | 2 | 1/2 [9%, 91%] | 7.50 | 2/2 | 8.00 | 1/2 | 7.50 | 2/2 | 8.00 | 1/2 | 7.00 |

## Frontier runs by tier

| arm | Run | Retrain | Reimplement |
|---|---|---|---|
| codex-gpt-6-astra | 0/2 | 0/3 | 1/2 |
| codex-gpt-6.1-sol | 1/6 | 0/5 | 1/8 |
| thin-gpt-6.1-sol | 3/3 | 0/4 | 1/4 |
| miniswe | 2/2 | 0/1 | 1/2 |
| thin-gpt-6-astra | 1/1 | 0/2 | 0/2 |
| thin-gpt-6-astra-x86 | 1/1 | 0/0 | 0/1 |
| thin-gpt-6.1-sol-x86 | 1/1 | 0/0 | 0/1 |
| all arms on GH200 nodes | 7/14 [27%, 73%] | 0/15 [0%, 20%] | 4/18 [9%, 45%] |

## gpt-6.1-sol, our loop against Codex CLI, papers graded in both

| paper | tier | our loop | Codex CLI |
|---|---|---|---|
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

Papers in both: 10. Reproduced: our loop 3, Codex CLI 2. Same verdict on 7; reproduced only in our loop 2, only in Codex CLI 1. Mean score: our loop 5.20, Codex CLI 4.70.

## Share of the GPU grant used

Frontier runs on GH200 nodes with a recorded spend: 47 of 47; median 2.6% of the grant, 28 of 47 under 5%. Open agents, submitted runs on the same 21 papers: 81 runs, median 14.7% of the grant.

## Paper 2506.08898 (Retrain, 32 H100-hour grant)

Frontier runs: thin-gpt-6.1-sol score 4, 0.18 H100-h; codex-gpt-6-astra score 2, 0.17 H100-h; miniswe score 6, 0.29 H100-h; codex-gpt-6.1-sol score 4, 0.61 H100-h; thin-gpt-6-astra score 4, 0.46 H100-h.
Open agents: dsv4 score 7, 29.4 H100-h; minimax score 0, 0.7 H100-h; muse score 8, 27.1 H100-h.
