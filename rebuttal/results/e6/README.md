# E6: tolerance sensitivity

Command: `python3 rebuttal/e6_tolerance.py`. Inputs: `tools/anon_viewer/public/data/index.json`, the 372 final audit records in `runs/*.json.gz`, and the lockfile copy (md5 ab205529; no tolerance field, so claim bars come from the lockfile value text).

**5% check.** Per agent and tier, 5% counts equal index.json (73 of 372). One record was corrected: `qwen3-retrain-2506.07673` has measured -37.2, but its value comparison reads 37.20%.

**Claims (of 100).** 62 point estimates: 58 default 5%, 4 state a ± margin. 38 have no number test.

**Worked run.** `dsv4-reimplement-2511.19808`: measured 90.6, target 97.3. |90.6 − 97.3| = 6.7; 6.7 / 97.3 = 6.9%. Partial at 5%, reproduced at 10%.

**Moves.** 17 reproduced runs fall to partial; 9 number-only partials rise to reproduced at 10% (hand-reviewed, listed in `summary.json`).

Reproduced of 372: index/5% 73; 1% 56; 2% 65; 10% 82; 1 point 70; 2 points 72.

Best agent per tier, with Wilson 95%:
- 2%: run dsv4 41.4% (12/29) [25.5, 59.3]; retrain dsv4 28.6% (8/28) [15.3, 47.1]; reimplement muse 15.6% (5/32) [6.9, 31.8].
- 10%: run dsv4 48.3% (14/29) [31.4, 65.6]; retrain muse 37.5% (12/32) [22.9, 54.8]; reimplement dsv4 16.7% (5/30) [7.3, 33.6].

Per-cell counts: `summary.json`. Per-run gaps: `table.csv`. Moves: `moved_runs.csv`.
