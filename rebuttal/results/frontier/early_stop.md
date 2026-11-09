# Early stops in the graded frontier runs

Computed 2026-11-08 for the rebuttal reply on GPU budget use.

Sources: `rebuttal/results/databook/frontier_cells.csv` (one row per graded run, 24 rows) for arm, paper, tier, score, exit_reason, queue_wait_min, budget_h100 and spent_h100. Each run's `report.json` on DeltaAI for `agent_assessment` and the first 600 characters of `blockers`. `rg -c run_gpu` on each run's `agent.full.log` on DeltaAI for the GPU request count. Read only.

Stop class is my reading of the blockers text, using the four classes in the brief. "Other" covers failures that are neither a missing released file nor a configuration gap (dependency, launcher or tool-budget stops). Quotes are exact substrings of the blockers, under 25 words.

% GPU budget used = spent_h100 / budget_h100 x 100, one decimal. Queue wait = queue_wait_min / 60. Blank queue waits in the CSV are shown as not recorded.

## Per-run table

| arm | paper | tier | score | % GPU budget used | queue wait (h) | run_gpu | exit_reason | stop class | quote |
|---|---|---|---|---|---|---|---|---|---|
| codex-gpt-6-astra | 2505.16927 | reimplement | 1 | 0.1 | 3.6 | 21 | natural | missing artifact | "did not locate the trained checkpoint" |
| codex-gpt-6.1-sol | 2505.16927 | reimplement | 1 | 0.2 | 10.4 | 32 | natural | missing artifact | "no exact or qualifying sibling STaPLe checkpoint" |
| thin-gpt-6.1-sol | 2505.16927 | reimplement | 1 | 0.2 | not recorded | 4 | natural | missing artifact | "No matching trained STaPLe checkpoint" |
| thin-gpt-6.1-sol | 2504.20571 | run | 8 | 15.7 | not recorded | 10 | natural | finished | "The measured final endpoint does not match 73.6% or exact DSR-sub parity." |
| thin-gpt-6.1-sol | 2506.08898 | retrain | 4 | 0.6 | not recorded | 8 | natural | missing artifact | "No matching POCCO-W checkpoint was found in the pinned repository or GitHub releases." |
| codex-gpt-6-astra | 2506.08898 | retrain | 2 | 0.5 | 8.8 | 59 | natural | missing artifact | "The canonical release contains no matching W checkpoint" |
| miniswe | 2506.08898 | retrain | 6 | 0.9 | not recorded | 68 | submitted | missing artifact | "The exact POCCO-W Bi-TSP50 checkpoint was never released" |
| codex-gpt-6.1-sol | 2506.08898 | retrain | 4 | 1.9 | 14.0 | 90 | natural | missing artifact | "No matching POCCO-W checkpoint was found in the checked canonical repository and releases." |
| codex-gpt-6.1-sol | 2504.20571 | run | 8 | 10.6 | 16.0 | 128 | budget_exhausted | other | "was unfinished when tools stopped" |
| thin-gpt-6.1-sol | 2510.21363 | retrain | 7 | 87.0 | not recorded | 30 | natural | scope or config unresolved | "The paper specifies 28 steps, but both released implementations default to 10." |
| thin-gpt-6.1-sol | 2504.12463 | retrain | 2 | 0.3 | not recorded | 7 | natural | missing artifact | "No matching checkpoint or same-size released sibling was located." |
| thin-gpt-6.1-sol | 2503.02809 | reimplement | 8 | 1.5 | not recorded | 17 | natural | scope or config unresolved | "The reconstructed Figure 1 initialization violates stated initialization constraints." |
| codex-gpt-6.1-sol | 2504.12463 | retrain | 2 | 0.2 | 10.1 | 67 | natural | missing artifact | "No matching checkpoint, same-size sibling, or identifiable original validation shard was located." |
| codex-gpt-6.1-sol | 2503.14698 | reimplement | 2 | 0.0 | 9.4 | 23 | natural | missing artifact | "The canonical project URL returned HTTP 404." |
| codex-gpt-6.1-sol | 2505.12677 | reimplement | 6 | 3.2 | 9.4 | 72 | natural | missing artifact | "The release lacks a CURE-specific scoring command" |
| codex-gpt-6.1-sol | 2412.11979 | run | 2 | 1.2 | 9.4 | 106 | natural | missing artifact | "The required zipf_curves.zip returns HTTP 404." |
| codex-gpt-6.1-sol | 2503.02809 | reimplement | 7 | 0.7 | 11.3 | 49 | natural | scope or config unresolved | "Figure 1's exact initialization is unspecified." |
| codex-gpt-6.1-sol | 2511.01463 | reimplement | 2 | 0.2 | 1.3 | 27 | natural | missing artifact | "No trained Vicuna HMVLM or eligible same-size sibling checkpoint was located." |
| thin-gpt-6.1-sol | 2505.19087 | reimplement | 7 | 3.3 | not recorded | 16 | natural | scope or config unresolved | "Exact author label partition, preprocessing, batch size, bias convention" |
| codex-gpt-6.1-sol | 2506.20671 | run | 2 | 2.1 | 11.0 | 37 | natural | other | "Missing DFA3D and mmcv compiled extensions." |
| codex-gpt-6.1-sol | 2505.19154 | run | 6 | 7.2 | 1.6 | 123 | natural | missing artifact | "No trained FHGS scene checkpoint was found." |
| codex-gpt-6.1-sol | 2602.03066 | reimplement | 7 | 1.5 | 1.1 | 81 | natural | finished | "The measured ordering holds in every seed" |
| codex-gpt-6-astra | 2505.10475 | run | 3 | 2.9 | 8.9 | 51 | wall_clock | other | "A launcher mistake started the full task in a short allocation, which expired." |
| codex-gpt-6-astra | 2510.21363 | retrain | 4 | 4.9 | 0.1 | 37 | natural | scope or config unresolved | "The exact development-selection sweep and selection record were not recovered." |

## Stop class counts per arm

| arm | rows | missing artifact | scope or config unresolved | other | finished | no GPU granted |
|---|---|---|---|---|---|---|
| codex-gpt-6.1-sol | 12 | 8 | 1 | 2 | 1 | 0 |
| thin-gpt-6.1-sol | 7 | 3 | 3 | 0 | 1 | 0 |
| codex-gpt-6-astra | 4 | 2 | 1 | 1 | 0 | 0 |
| miniswe | 1 | 1 | 0 | 0 | 0 | 0 |
| all | 24 | 14 | 5 | 3 | 2 | 0 |

Every run has at least one `run_gpu` line, so no run is "no GPU granted" by the GPU-request test.

## Worked example of the % column

Row: codex-gpt-6.1-sol, paper 2412.11979, run fb8412. spent_h100 = 0.3779, budget_h100 = 32.0. So 0.3779 / 32.0 x 100 = 1.18, shown as 1.2. Its stop class is missing artifact, from "The required zipf_curves.zip returns HTTP 404."

## Notes

- Two rows say budget_exhausted or wall_clock but used little of their budget: codex-gpt-6.1-sol 2504.20571 (run 91bc6a, 10.6%, exit budget_exhausted) and codex-gpt-6-astra 2505.10475 (2.9%, exit wall_clock). The CSV does not say what counts against those limits, so these two exits need a check before the reply cites them.
- Three rows (miniswe 2506.08898, codex-gpt-6-astra 2506.08898, codex-gpt-6.1-sol 2506.08898) also say that retraining was projected to exceed the budget. The main stop class above is still the missing checkpoint.
