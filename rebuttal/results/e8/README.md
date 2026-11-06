# E8: environment bound

Command: `python3 rebuttal/e8_bound.py` (reads `~/sweeps/paper-table-2026-09-05/resolved_modes.json`, `paper_latex/tables/eval100.tex` lines 1-121, `tools/anon_viewer/public/data/index.json`, and `stats_index.tsv`, which lists the DeltaAI `stats.json` rows; each of the 372 runs matches one row).

Reproduction check passes: 73 of 400 cells. DeepSeek-V4-Flash: Run 14/34, Retrain 9/33, Reimplement 4/33.

Build-and-dependency label (`environment-fights`): 24 runs (MiniMax 11, Qwen3.6 8, Muse 4, DeepSeek 1). Transcript review: 16 aarch64-caused (10 explicit package message, 6 agent-stated), 5 other environment, 3 agent error.

Bound, Wilson 95%: removing all 24 from denominators gives best Run 14/34 = 41.2% (26.4 to 57.8), unchanged because DeepSeek has no build-dependency run in Run. Best Retrain 9/32 = 28.1% (Muse). Best Reimplement 5/32 = 15.6% (Muse). Removing only the 16 aarch64-caused runs gives the same best Run rate.

Empty cells (28): 4 prompt-rendering bug, 2 audit never returned, 3 run finished with no entry, 2 context limit with no entry, 3 orphan launch errors only, 14 no run directory on record.

Files: `bound.csv`, `build_failures.csv`, `empty_cells.csv`, `summary.json`, `stats_index.tsv`.

## Empty-cell trace (reviewer YGTR Q3)

File: `empty_cells_traced.csv`, one row per of the 22 empty cells not explained by the first six. Sources: `status.tsv` rows and `repro_<id>.log` under the DeltaAI sweep directories, `sacct` states for the sweep job ids, `agent_runs` directories, `stats_index.tsv`, and the cleanup logs (`cleanup-2026-10-23.log`, `cleanup-2026-11-04-inv.log`, `CLEANUP-2026-10-29`). Supabase `repro_runs` was not queried: the host did not answer from DeltaAI or claude-vps.

Counts (22 cells): A, agent ran and failed: 2. B, infrastructure: 16. C, run dir deleted by a cleanup: 0 (no cleanup log names any missing label). D, unknown: 4.

B cells (rerun candidates): dsv4 2505.10475, 2506.01511, 2506.18896, 2410.19933, 2506.10943, 2510.19784, 2511.00119, 2505.22596, 2506.20024, 2510.15194; qwen3 2503.09657, 2506.08898, 2510.05874, 2510.19784, 2506.19839, 2506.20024.

Most B cells are Slurm jobs that stopped mid-run: TIMEOUT at the 2-day limit (sweeps 2896059, 2918306, 2698678, 2759663) or CANCELLED by a foreign uid after 8 to 15 hours (2883229, 2636921, 2666353). The three dsv4 orphan rows were not DeepSeek runs: they came from the Qwen sweep 2635067 and the Laguna sweep 2858779, which failed with a stale file handle on the HF dataset load.

A cells: dsv4 2505.24864 and 2504.12397 ended in the harness stop "context over ceiling and elide-compact freed nothing". This follows the protocol's context-exhaustion rule, but the message points at the compaction step, so a reviewer could argue for B.

D cells: minimax 2506.18896 and qwen3 2511.19808 finished with a report and a score; qwen3 2510.25529 finished with verdict disqualified; qwen3 2510.19314 finished and was scored in sweep 2640098, but its run dir is absent from DeltaAI and from every cleanup log. The viewer index does not contain these runs, and no log gives the reason.

Two qwen3 retrain cells (2503.09657, 2510.19784) also have a completed attempt in sweep 2640098 whose run dir is absent. They are classed B on the timed-out attempt the set expected.
