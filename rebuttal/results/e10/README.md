# E10 environment check: selection, scripts, reruns

Selection: near-miss-partial runs (appendix H: "Ran, outside tolerance"), tiers run and retrain, band 0-8. Best run per paper by audit score (tie: lower spent). Order: `random.Random(22528)` (6 Run, then 4 Retrain), alternates from the same stream. Only clean single command chains qualify.

Excluded:
- 2503.09657: transcript used --kl_topk 2048 (paper 8192), so not faithful.
- 2505.15201: no seed argument; the code seeds from hash(method); target is a magnitude bar.
- 2505.18809, 2510.21311, 2510.23574: final number depends on hand-edited code or node-local /tmp checkpoints from many steps.
- 2505.24864: 20-prompt pilot, budget exhausted.
- 2506.20990, 2502.06684, 2505.14766: report degraded, no scoring command.
- 2505.21077, 2506.06991, 2506.20233, 2509.16391, 2510.21363, 2504.20571, 2505.19154: spans several GPU sessions.
- 2505.19713, 2505.24873, 2511.00090: 39 to 76 GPU steps.

Result: Run 1 of 6 papers, Retrain 2 of 4. Band 0-8 clean pool exhausted.

Scripts: `scripts/<arxiv_id>.rerun.sh`, checked against `commands.log` by line (`# L<n>`). Run through `jobs/*.sbatch` on ghx4 with `cuda1290-agent.sif`; PATCH lines are not in the transcript. Status and job ids: `/work/nvme/bfvr/msalunkhe/rebuttal/e10/state.json`.

Caveat: the data shuffle seed is fixed at 0 (src/data_utils.py:71), so SEED changes search and pruning only (not used in this subset).
