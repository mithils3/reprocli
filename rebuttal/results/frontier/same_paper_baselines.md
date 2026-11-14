# Open agents on each frontier arm's own papers

Source: rebuttal/results/databook/frontier_cells.csv (68 graded rows). Reproduced means score 8 or more. Open-agent columns use the submitted score of that agent on the same papers, an empty cell scoring 0. Intervals are Wilson 95%.

| arm | graded | reproduced | mean score | DeepSeek-V4-Flash reproduced | DeepSeek-V4-Flash mean | Muse Spark 1.2 reproduced | Muse Spark 1.2 mean | Qwen3.6-27B reproduced | Qwen3.6-27B mean | MiniMax-M2.7 reproduced | MiniMax-M2.7 mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| codex-gpt-6-astra | 8 | 3/8 [14%, 69%] | 5.00 | 4/8 | 5.88 | 3/8 | 5.62 | 2/8 | 4.38 | 2/8 | 3.50 |
| codex-gpt-6.1-sol | 23 | 4/23 [7%, 37%] | 5.00 | 8/23 | 5.74 | 7/23 | 5.57 | 5/23 | 4.00 | 4/23 | 2.96 |
| thin-gpt-6.1-sol | 12 | 5/12 [19%, 68%] | 5.67 | 4/12 | 5.42 | 4/12 | 5.25 | 3/12 | 3.83 | 2/12 | 3.00 |
| miniswe | 6 | 4/6 [30%, 90%] | 6.83 | 3/6 | 5.83 | 2/6 | 5.67 | 2/6 | 4.50 | 2/6 | 3.67 |
| thin-gpt-6-astra | 6 | 1/6 [3%, 56%] | 4.83 | 4/6 | 7.17 | 3/6 | 7.17 | 2/6 | 4.67 | 2/6 | 4.33 |
| thin-gpt-6-astra-x86 | 3 | 2/3 [21%, 94%] | 6.00 | 2/3 | 6.67 | 1/3 | 6.33 | 2/3 | 6.67 | 1/3 | 4.67 |
| thin-gpt-6.1-sol-x86 | 5 | 2/5 [12%, 77%] | 6.40 | 2/5 | 6.00 | 1/5 | 5.20 | 2/5 | 4.40 | 1/5 | 4.40 |
| thin-muse-wonder-1.0 | 2 | 1/2 [9%, 91%] | 5.50 | 0/2 | 5.50 | 1/2 | 6.00 | 0/2 | 2.00 | 0/2 | 0.00 |
| codex-gpt-6.1-sol-nudge | 3 | 2/3 [21%, 94%] | 7.67 | 3/3 | 8.00 | 1/3 | 7.67 | 1/3 | 5.33 | 1/3 | 6.00 |

## Frontier runs by tier

| arm | Run | Retrain | Reimplement |
|---|---|---|---|
| codex-gpt-6-astra | 2/3 | 0/3 | 1/2 |
| codex-gpt-6.1-sol | 2/7 | 1/8 | 1/8 |
| thin-gpt-6.1-sol | 4/4 | 0/4 | 1/4 |
| miniswe | 2/2 | 1/2 | 1/2 |
| thin-gpt-6-astra | 1/2 | 0/2 | 0/2 |
| thin-gpt-6-astra-x86 | 1/1 | 0/0 | 1/2 |
| thin-gpt-6.1-sol-x86 | 2/2 | 0/2 | 0/1 |
| thin-muse-wonder-1.0 | 0/0 | 1/1 | 0/1 |
| codex-gpt-6.1-sol-nudge | 2/2 | 0/1 | 0/0 |
| all arms on GH200 nodes, continue-prompt runs left out | 11/18 [39%, 80%] | 3/20 [5%, 36%] | 4/19 [9%, 43%] |

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

Frontier runs on GH200 nodes with a recorded spend: 57 of 57; median 5.6% of the grant, 28 of 57 under 5%. Open agents, submitted runs on the same 24 papers: 92 runs, median 14.3% of the grant.
Frontier runs that reproduce: median 21.7% (18 runs); that do not: median 2.1% and mean 13.2% (39 runs). By tier, median: run 14.7%, retrain 8.6%, reimplement 1.5%.

## Pooled over the frontier runs on GH200 nodes, continue-prompt runs left out

Frontier: 18/57 [21%, 44%]. DeepSeek-V4-Flash: 23/57 [29%, 53%]. Muse Spark 1.2: 20/57 [24%, 48%].
By tier, open agents on the same runs: run DeepSeek-V4-Flash 11/18, Muse Spark 1.2 4/18; retrain DeepSeek-V4-Flash 6/20, Muse Spark 1.2 8/20; reimplement DeepSeek-V4-Flash 6/19, Muse Spark 1.2 8/19.
Papers that some open agent reproduced: 12 papers, 33 frontier runs, reproduced 14/33 [27%, 59%] (7 papers by at least one frontier run); DeepSeek-V4-Flash 23/33, Muse Spark 1.2 20/33. By arm: thin-gpt-6.1-sol 3/6 (DeepSeek-V4-Flash 4); codex-gpt-6-astra 2/5 (DeepSeek-V4-Flash 4); miniswe 3/4 (DeepSeek-V4-Flash 3); codex-gpt-6.1-sol 4/12 (DeepSeek-V4-Flash 8); thin-gpt-6-astra 1/5 (DeepSeek-V4-Flash 4); thin-muse-wonder-1.0 1/1 (DeepSeek-V4-Flash 0).
Papers that no open agent reproduced: 12 papers, 24 frontier runs, reproduced 4/24 [7%, 36%] (2 papers by at least one frontier run); DeepSeek-V4-Flash 0/24, Muse Spark 1.2 0/24. By arm: codex-gpt-6-astra 1/3 (DeepSeek-V4-Flash 0); codex-gpt-6.1-sol 0/11 (DeepSeek-V4-Flash 0); thin-gpt-6.1-sol 2/6 (DeepSeek-V4-Flash 0); miniswe 1/2 (DeepSeek-V4-Flash 0); thin-gpt-6-astra 0/1 (DeepSeek-V4-Flash 0); thin-muse-wonder-1.0 0/1 (DeepSeek-V4-Flash 0).
Papers reproduced by at least one frontier run: 9 of 24.
Continue-prompt runs against the unprompted Codex CLI run: 2502.05795 score 8 with 5.70 of 8 H100-h (unprompted 8 with 3.93); 2510.21363 score 7 with 5.37 of 8 H100-h (unprompted 7 with 4.22); 2504.20571 score 8 with 6.48 of 8 H100-h (unprompted 8 with 0.85).

## Paper 2506.08898 (Retrain, 32 H100-hour grant)

Frontier runs: thin-gpt-6.1-sol score 4, 0.18 H100-h; codex-gpt-6-astra score 2, 0.17 H100-h; miniswe score 6, 0.29 H100-h; codex-gpt-6.1-sol score 4, 0.61 H100-h; thin-gpt-6-astra score 4, 0.46 H100-h; thin-muse-wonder-1.0 score 8, 27.49 H100-h.
Open agents: dsv4 score 7, 29.4 H100-h; minimax score 0, 0.7 H100-h; muse score 8, 27.1 H100-h.
