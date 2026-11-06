# E10 environment check: selection and rerun scripts

Selection: `runs` in `resolved_modes.json` with mode near-miss-partial (appendix H: "Ran, outside tolerance"), tiers run and retrain, paper band 0-8. Best run per paper by audit score (tie: lower spent_h100). `random.Random(22528)`: `sample(sorted run papers, 6)`, then `sample(sorted retrain papers, 4)`. All selected workspaces exist on DeltaAI.

Scripts: `scripts/<arxiv_id>.rerun.sh`. Each line of transcript code carries its `# L<n>` line in `evidence/commands.log`. `check` matched 10 of 10, 2 of 2, 2 of 2, 1 of 1 entries. Lines marked PATCH are not in the transcript (seed flag, copied wrappers).

Estimated GPU-hours per seed: 7.30; two seeds: 14.6 (limit 90).

Skipped:
- Run 2505.18809, 2510.21311, 2510.23574: final number depends on hand-edited code or a node-local /tmp checkpoint from many earlier steps.
- Run 2505.24864: 20-prompt pilot, budget exhausted; not the paper's pipeline.
- Run 2506.20990: report degraded, no scoring command.
- Retrain 2505.21077: reported ratio spans benchmark rounds from four GPU sessions.

Result: 1 Run paper of 6 and 3 Retrain papers of 4 are scripted.

Caveats: 2503.09657 keeps the transcript's `--kl_topk 2048` (paper: 8192). The data shuffle seed is fixed at 0 (`src/data_utils.py:71`), so SEED changes search and pruning only.
