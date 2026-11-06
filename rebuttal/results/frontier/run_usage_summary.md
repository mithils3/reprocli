# Frontier run budget use

Source: run_usage.csv, built by scripts/rebuttal/run_usage_table.py from the run dirs.
pct_budget_used = gpu_h100h_used / budget_h100h x 100, where gpu_h100h_used is the sum of
cost_h100h over every run_gpu line in agent.full.log.

| model | runs | median % of GPU budget used | runs under 10% | exit reasons |
|---|---|---|---|---|
| gpt-6-astra | 1 | 1.31 | 1 of 1 | natural 1 |
| gpt-6.1-sol | 2 | 0.32 | 2 of 2 | natural 2 |
| gpt-6.1-terra | 7 | 0.06 | 7 of 7 | natural 7 |
| muse-wonder-1.0 | 1 | 1.40 | 1 of 1 | submitted 1 |

## Worked example

Run 2506.08898, gpt-6-astra, budget 32.0 H100-h. Its 14 run_gpu costs sum to 0.0003 + 0.0828 + 0.0435 + 0.0042 + 0.016 + 0.011 + 0.0114 + 0.015 + 0.0068 + 0.0048 + 0.2067 + 0.004 + 0.0077 + 0.0041 = 0.4183 H100-h:

0.4183 / 32 x 100 = 1.31% of budget.
