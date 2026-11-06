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
| E7 targets (v3, gpt-6.1-sol) | Of 100 targets: paper reports the frozen number 92, for the frozen metric 95, dataset/split 76, method variant 69, all four 55. 45 papers for Mithil's Monday read (v3_failures.csv); 2506.18890's 27.443 is the paper's 24-view row while the frozen config says 12 views. $12.70 | rebuttal/results/e7 |
| E9 checkpoints | 2 of 44 reproduced Retrain/Reimplement runs evaluated a downloaded checkpoint of the claimed trained model: muse-retrain-2508.21046 (CogVLA, hf download liwei2013/cogvla_libero_spatial_60000_chkpt, commands.log:483, verified) and minimax-reimplement-2505.12677 (CURE, gdown of authors' erased SD-v1.4). Neither is a best-agent cell: Retrain best stays DSv4 9/33 if Muse drops to 8/33 | rebuttal/results/e9 |

## Running or next

| Item | State |
| :- | :- |
| E10 environment check | 3 clean pipelines (1 Run, 2 Retrain); smoke job queued |
| OpenAI path | Responses API adapter with flex, tested live (commit 37f186d) |
| Smokes: gpt-6.1-terra x2, Muse Wonder x1, mini-SWE x1, Codex x1 (dev papers) | running |
| Brain jobs on betw | 10 submitted 11:55 (6 DSv4 E3 repeats, 3 DSv4 reruns, 1 MiniMax rerun), pending; Qwen serve OOM being diagnosed, its 2 rerun jobs held |
| Reruns: 2510.20725 x4 agents + 16 job-killed cells (10 DSv4, 6 Qwen) | after brain smokes |
| E3 DSv4 repeats x2 on core 12 | after brain smokes |
| Grading of new runs (Sonnet-5, local run dirs) | after runs |

## Notes for Mithil
- Supabase host does not resolve (project likely paused); nothing depends on it.
- An HF token string appears in raw run files on DeltaAI (muse-reimplement-2505.22860 trajectory.jsonl:19). It is not in the public viewer data. Rotate before releasing run logs.

## Decisions taken while Mithil is away (2026-11-06 evening)
- Codex runs end when Codex ends its own turn, the same rule as the thin harness (an agent turn with no tool call ends the episode, loop.py). No continuation nudges are added. First finished Codex runs stop early: gpt-6.1-terra on 2505.16927 (Retrain, 32 h budget) ended after 16 minutes and one GPU check, reporting "could not run". This is a measured behavior of the production harness and goes in the reply as such; revisit if Mithil prefers a fixed number of "continue" prompts.
- Codex launcher fixes: one BLAS thread per process (login-node 1000-pid cap), unlimited API retries plus session resume on rate limits, flex-capacity refusals retried and a run moved to standard price after 3 in a row, children read /dev/null. Runs that failed from harness causes carry a VOID file and are rerun.
- OpenAI rate limit is 1M tokens per minute per model (cached tokens count); Codex arms run 2 at a time per model.
- 2026-11-06 21:42Z, Mithil: gpt-6.1-sol first. Paused (SIGSTOP, in-flight runs continue) the dispatchers of terra core 4-12 and astra 1-8 on gh-login01 and terra 13-24 on gh-login02. Sol runs core 4-12 then 1 (gh-login02, rb-codex-sol-b) and extension 13-24 (gh-login03, rb-codex-sol-ext), 3 at a time each. Resume the others with `bash /work/nvme/bfvr/msalunkhe/rebuttal/sweep_ctl.sh CONT <model> <ranks>` on the node once sol is through. Script copy: scripts/rebuttal/codex_arm/sweep_ctl.sh.
