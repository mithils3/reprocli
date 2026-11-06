# E8: environment bound

Command: `python3 rebuttal/e8_bound.py` (reads `~/sweeps/paper-table-2026-09-05/resolved_modes.json`, `paper_latex/tables/eval100.tex` lines 1-121, `tools/anon_viewer/public/data/index.json`, and `stats_index.tsv`, which lists the DeltaAI `stats.json` rows; each of the 372 runs matches one row).

Reproduction check passes: 73 of 400 cells. DeepSeek-V4-Flash: Run 14/34, Retrain 9/33, Reimplement 4/33.

Build-and-dependency label (`environment-fights`): 24 runs (MiniMax 11, Qwen3.6 8, Muse 4, DeepSeek 1). Transcript review: 16 aarch64-caused (10 explicit package message, 6 agent-stated), 5 other environment, 3 agent error.

Bound, Wilson 95%: removing all 24 from denominators gives best Run 14/34 = 41.2% (26.4 to 57.8), unchanged because DeepSeek has no build-dependency run in Run. Best Retrain 9/32 = 28.1% (Muse). Best Reimplement 5/32 = 15.6% (Muse). Removing only the 16 aarch64-caused runs gives the same best Run rate.

Empty cells (28): 4 prompt-rendering bug, 2 audit never returned, 3 run finished with no entry, 2 context limit with no entry, 3 orphan launch errors only, 14 no run directory on record.

Files: `bound.csv`, `build_failures.csv`, `empty_cells.csv`, `summary.json`, `stats_index.tsv`.
