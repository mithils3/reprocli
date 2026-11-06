# E6: tolerance sensitivity

Command: `python3 rebuttal/e6_tolerance.py`. Inputs: `tools/anon_viewer/public/data/index.json`, the 372 final audit records in `runs/*.json.gz`, and the lockfile copy (md5 ab205529; no tolerance field, so claim bars come from the lockfile value text).

**Denominators.** Every agent is graded on every paper in a tier: Run 34, Retrain 33, Reimplement 33 (400 cells). Cells with no run (28 of 400) count as not reproduced. Intervals are Wilson 95%.

**5% check.** Counts equal the paper's best-agent numbers: Run 14/34 (dsv4), Retrain 9/33 (dsv4 and muse tie), Reimplement 5/33 (muse), and 73/400 overall. One record was corrected: `qwen3-retrain-2506.07673` has measured -37.2, but its value comparison reads 37.20%.

**Why 51 and 73.** 51 reproduced runs are point estimates, and all 51 match their recorded bar. The other 22 have no number test: 11 direction (beat a baseline), 10 threshold (floor or ceiling), 1 magnitude.

**Claims (of 100).** 62 point estimates: 58 default 5%, 4 state a ± margin. 38 have no number test.

**Worked run.** `dsv4-reimplement-2511.19808`: measured 90.6, target 97.3. |90.6 − 97.3| = 6.7; 6.7 / 97.3 = 6.9%. Partial at 5%, reproduced at 10%.

**Moves.** 17 reproduced runs fall to partial at 1% (8 at 2%). 9 number-only partials rise to reproduced at 10% (hand-reviewed, listed in `summary.json`). At 2%, 3 falls are best-agent runs: `dsv4-run-2502.05795`, `dsv4-run-2503.23035`, `dsv4-retrain-2510.21363`.

Best agent per tier (rate, Wilson 95%):

| Tolerance | Run (/34) | Retrain (/33) | Reimplement (/33) |
|---|---|---|---|
| 1% | dsv4 26.5% (9) [14.6, 43.1] | dsv4, muse 24.2% (8) [12.8, 41.0] | dsv4, muse 12.1% (4) [4.8, 27.3] |
| 2% | dsv4 35.3% (12) [21.5, 52.1] | muse 27.3% (9) [15.1, 44.2] | muse 15.2% (5) [6.7, 30.9] |
| 5% | dsv4 41.2% (14) [26.4, 57.8] | dsv4, muse 27.3% (9) [15.1, 44.2] | muse 15.2% (5) [6.7, 30.9] |
| 10% | dsv4 41.2% (14) [26.4, 57.8] | muse 36.4% (12) [22.2, 53.4] | dsv4, muse 15.2% (5) [6.7, 30.9] |

Per-cell counts: `summary.json`. Per-run gaps: `table.csv`. Moves: `moved_runs.csv`.
