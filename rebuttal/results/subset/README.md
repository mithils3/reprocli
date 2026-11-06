# Rebuttal subset (seed 22528)

Built by `python3 rebuttal/subset.py` into `rebuttal/subset.json`. Inputs: the lockfile `hf://datasets/Mithilss/reclaim/eval_100.jsonl` (tier, band, granted budget) and `tools/anon_viewer/public/data/index.json` (audit verdict per run). Lockfile tiers Easy, Medium and Hard are Run, Retrain and Reimplement. Tier and band agree with index.json on all 100 papers, and every run's budget equals its band ceiling (8, 32, 96 H100-h). Rule: PLAN.md Section 2. Paper 2510.20725 is excluded.

Counts per tier and band. R means at least one agent reproduced the paper; N means none did.

| Tier | Band (H100-h) | Candidates R / N | Core R / N | Extension R / N |
| :- | :- | :-: | :-: | :-: |
| Run | 0-8 | 13 / 14 | 2 / 1 | 1 / 2 |
| Run | 8-32 | 3 / 4 | 0 / 1 | 1 / 0 |
| Run | 32-96 | 0 / 0 | 0 / 0 | 0 / 0 |
| Retrain | 0-8 | 6 / 9 | 1 / 1 | 1 / 1 |
| Retrain | 8-32 | 5 / 8 | 1 / 0 | 0 / 1 |
| Retrain | 32-96 | 1 / 3 | 0 / 1 | 1 / 0 |
| Reimplement | 0-8 | 6 / 10 | 2 / 0 | 2 / 0 |
| Reimplement | 8-32 | 0 / 9 | 0 / 1 | 0 / 1 |
| Reimplement | 32-96 | 0 / 8 | 0 / 1 | 0 / 1 |

Substitutions. Reimplement has no reproduced candidate at 8-32 or 32-96, so its two reproduced slots fall at 0-8 in both sets, and its 8-32 and 32-96 slots hold non-reproduced papers. Run has no candidate at 32-96 and takes no slot there.

Granted budget is the band ceiling. Core totals 344 H100-h; all 24 papers total 688. The two smoke papers are dev-split Run papers at 0-8 (8 H100-h each), not counted in either total.
