# Open agents on each frontier arm's own papers

Source: rebuttal/results/databook/frontier_cells.csv (42 graded rows). Reproduced means score 8 or more. Open-agent columns use the submitted score of that agent on the same papers, an empty cell scoring 0. Intervals are Wilson 95%.

| arm | graded | reproduced | mean score | DeepSeek-V4-Flash reproduced | DeepSeek-V4-Flash mean | Muse Spark 1.2 reproduced | Muse Spark 1.2 mean | Qwen3.6-27B reproduced | Qwen3.6-27B mean | MiniMax-M2.7 reproduced | MiniMax-M2.7 mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| codex-gpt-6-astra | 7 | 1/7 [3%, 51%] | 3.14 | 3/7 | 5.57 | 2/7 | 5.14 | 2/7 | 4.43 | 2/7 | 3.43 |
| codex-gpt-6.1-sol | 16 | 2/16 [3%, 36%] | 4.44 | 7/16 | 6.25 | 5/16 | 5.50 | 4/16 | 4.25 | 3/16 | 3.00 |
| thin-gpt-6.1-sol | 11 | 4/11 [15%, 65%] | 5.45 | 4/11 | 5.91 | 4/11 | 5.73 | 3/11 | 3.91 | 2/11 | 3.27 |
| miniswe | 3 | 1/3 [6%, 79%] | 5.67 | 0/3 | 3.67 | 1/3 | 4.00 | 0/3 | 2.33 | 0/3 | 0.00 |
| thin-gpt-6-astra | 3 | 1/3 [6%, 79%] | 4.33 | 1/3 | 6.33 | 1/3 | 6.33 | 1/3 | 4.00 | 0/3 | 2.00 |
| thin-gpt-6-astra-x86 | 1 | 0/1 [0%, 79%] | 2.00 | 0/1 | 4.00 | 0/1 | 4.00 | 0/1 | 4.00 | 0/1 | 0.00 |
| thin-gpt-6.1-sol-x86 | 1 | 0/1 [0%, 79%] | 7.00 | 1/1 | 8.00 | 1/1 | 8.00 | 1/1 | 8.00 | 1/1 | 8.00 |

## Frontier runs by tier

| arm | Run | Retrain | Reimplement |
|---|---|---|---|
| codex-gpt-6-astra | 0/2 | 0/3 | 1/2 |
| codex-gpt-6.1-sol | 1/6 | 0/3 | 1/7 |
| thin-gpt-6.1-sol | 3/3 | 0/4 | 1/4 |
| miniswe | 1/1 | 0/1 | 0/1 |
| thin-gpt-6-astra | 1/1 | 0/1 | 0/1 |
| thin-gpt-6-astra-x86 | 0/0 | 0/0 | 0/1 |
| thin-gpt-6.1-sol-x86 | 0/0 | 0/0 | 0/1 |
| all arms on GH200 nodes | 6/13 [23%, 71%] | 0/12 [0%, 24%] | 3/15 [7%, 45%] |

## gpt-6.1-sol, our loop against Codex CLI, papers graded in both

| paper | tier | our loop | Codex CLI |
|---|---|---|---|
| 2502.05795 | run | 8 | 3 |
| 2503.02809 | reimplement | 8 | 7 |
| 2503.14698 | reimplement | 1 | 2 |
| 2504.12463 | retrain | 2 | 2 |
| 2504.20571 | run | 8 | 8 |
| 2505.16927 | reimplement | 1 | 1 |
| 2505.19087 | reimplement | 7 | 8 |
| 2506.08898 | retrain | 4 | 4 |
| 2506.20671 | run | 8 | 2 |
| 2510.21363 | retrain | 7 | 7 |

Papers in both: 10. Reproduced: our loop 4, Codex CLI 2. Same verdict on 6; reproduced only in our loop 3, only in Codex CLI 1. Mean score: our loop 5.40, Codex CLI 4.40.

## Share of the GPU grant used

Frontier runs on GH200 nodes with a recorded spend: 37 of 40; median 2.1% of the grant, 25 of 37 under 5%. Open agents, submitted runs on the same 18 papers: 70 runs, median 17.5% of the grant.

## Paper 2506.08898 (Retrain, 32 H100-hour grant)

Frontier runs: thin-gpt-6.1-sol score 4, 0.18 H100-h; codex-gpt-6-astra score 2, 0.17 H100-h; miniswe score 6, 0.29 H100-h; codex-gpt-6.1-sol score 4, 0.61 H100-h; thin-gpt-6-astra score 4, 0.00 H100-h.
Open agents: dsv4 score 7, 29.4 H100-h; minimax score 0, 0.7 H100-h; muse score 8, 27.1 H100-h.
