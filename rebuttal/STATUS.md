# Rebuttal status (orchestrator-maintained)

Started 2026-11-06 while Mithil is away for the weekend. Caps: OpenAI $700 of $750, Meta $480 of $500, GPU on betw-dtai-gh, Claude usage 65% of the week through Monday.

## Results in hand

| Item | Headline | Files |
| :- | :- | :- |
| Subset | 24 papers in priority order, seed 22528; core 12 = 344 granted H100-hours | rebuttal/subset.json |
| E5 logs | 1 of 372 runs overwrote its commands.log (minimax-reimplement-2510.25146, write_file at agent.full.log:1084); that run was graded 1, unverifiable, so no grade gained from it. 45,673 of 45,861 agent entries match the host transcript exactly, 185 explained by code, 3 differ by under 0.0003 GPU-hours in the remaining-budget field | rebuttal/results/e5 |
| E6 tolerance | Best agent per tier at 1/2/5/10%: Run 9/12/14/14 of 34; Retrain 8/9/9/12 of 33; Reimplement 4/5/5/5 of 33. 17 of 73 reproduced runs fall at 1%, 8 at 2%; 9 partials rise at 10% | rebuttal/results/e6 |
| E8 bound | 24 build-and-dependency failures, 16 caused by aarch64; best Run rate unchanged at 14/34 with all 24 removed (DSv4 had none at Run) | rebuttal/results/e8 |
| E8 empty cells | Of 28: 6 named outside-agent (prompt bug x4, audits x2), 16 more killed by the sweep job's 48 h Slurm limit or a cancel (sacct confirms), 2 agent context exhaustion, 4 unknown | rebuttal/results/e8/empty_cells_traced.csv |
| E8 Muse re-audit | 2503.23035 reproduced (8); 2510.08177 partial (6) | rebuttal/results/e8/regrade_muse.json |

## Running or next

| Item | State |
| :- | :- |
| E7 target re-derivation (gpt-6.1-sol flex) | running on DeltaAI (tmux rb-e7) |
| E9 checkpoint scan | running |
| E10 environment check | 3 clean pipelines (1 Run, 2 Retrain); smoke job queued |
| OpenAI path | Responses API adapter with flex, tested live (commit 37f186d) |
| Smokes: gpt-6.1-terra x2, Muse Wonder x1 (dev papers) | stuck downloading paper bundles; being fixed |
| mini-SWE-agent arm | toy passed; dev smoke next |
| Codex arm | building |
| Brain serve smokes (DSv4, Qwen, MiniMax) | running |
| Reruns: 2510.20725 x4 agents + 16 job-killed cells (10 DSv4, 6 Qwen) | after brain smokes |
| E3 DSv4 repeats x2 on core 12 | after brain smokes |
| Grading of new runs (Sonnet-5, local run dirs) | after runs |

## Notes for Mithil
- Supabase host does not resolve (project likely paused); nothing depends on it.
- An HF token string appears in raw run files on DeltaAI (muse-reimplement-2505.22860 trajectory.jsonl:19). It is not in the public viewer data. Rotate before releasing run logs.
