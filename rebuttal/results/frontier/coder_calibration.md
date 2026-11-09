# Calibrating the blind failure-mode coder on open-agent runs

The blind coder of `rebuttal/scripts/frontier_failure_modes.py` (claude-sonnet-5, prompt and digest unchanged, never shown the verdict, score or arm) was run on open-agent runs that already carry a paper label, so its labels can be compared with the paper's. Script: `rebuttal/scripts/coder_calibration.py`. Per-run output: `coder_calibration.csv`.

## Sample

Frame: the 372 graded open-agent runs, with the primary mode of record in `~/sweeps/paper-table-2026-09-05/resolved_modes.json`, joined to the run directory on Delta by sweep job id and arXiv id (339 of 372 have exactly one directory with an `agent.full.log`; all 13 "Never launched an experiment" runs do). Failing means any mode other than Reproduced (271 runs in the frame). Draw rule with `random.Random(20261109)`: all 13 "Never launched an experiment" runs; then 3 runs from each other failing mode that has at least 5 runs in the frame (7 modes, 21 runs); then 19 more drawn uniformly from the remaining non-"Never launched" failing runs, so the stratified part has 40 runs. That makes 53 drawn. Three could not be scored because the coder returned unparseable output twice (two environment-fights runs and one artifact-provenance run, muse-run-2505.14827, muse-retrain-2510.05874, dsv4-reimplement-2511.20906), leaving 50 coded runs. The coder ran on Delta with the key in that host's environment, since the laptop key was rejected.

## Agreement, paper primary mode against blind-coder primary mode

| Paper label \ blind coder | Ran, outside tolerance | Reimplemented, unchecked | Build and dependency | Wrong artifact | Wrong experiment | Echoed shipped number | Never launched | Failed before number | Reproduced | N |
|---|---|---|---|---|---|---|---|---|---|---|
| Ran, outside tolerance | 2 | 1 | 0 | 1 | 2 | 0 | 0 | 1 | 1 | 8 |
| Reimplemented, unchecked | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Build and dependency | 0 | 2 | 1 | 0 | 1 | 0 | 0 | 1 | 0 | 5 |
| Wrong artifact | 0 | 1 | 0 | 2 | 1 | 0 | 1 | 0 | 0 | 5 |
| Wrong experiment | 1 | 1 | 0 | 1 | 2 | 0 | 0 | 1 | 0 | 6 |
| Echoed shipped number | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 4 |
| Never launched | 0 | 0 | 0 | 0 | 0 | 0 | 13 | 0 | 0 | 13 |
| Failed before number | 1 | 0 | 0 | 0 | 0 | 0 | 4 | 1 | 0 | 6 |

Exact agreement is 28 of 50 (56%, Wilson 95% interval 42% to 69%). Cohen's kappa over the nine labels is 0.48. Agreement is perfect on the two narrow modes (13 of 13 "Never launched", 4 of 4 "Echoed a shipped number") and weak on the broad ones (Ran outside tolerance 2 of 8, Build and dependency 1 of 5, Failed before any number 1 of 6).

## "Never launched an experiment" in both directions

For a run the paper labelled "Never launched", the blind coder agrees in 13 of 13 cases, so it does not miss that mode. For a run the paper labelled otherwise, the blind coder says "Never launched" in 5 of 37 cases (14%, Wilson 6% to 28%): 4 of the 6 runs the paper labelled "Failed before any number was produced" and 1 of the 5 labelled "Wrong artifact measured". The coder therefore treats the boundary between those two modes more loosely than the paper's pass did.

## Open-agent baseline under the blind coder

The sample over-represents "Never launched", so the open-agent rate is reweighted by the paper's stratum sizes among the 300 labelled failing runs (76, 63, 24, 38, 46, 9, 13 and 31 for the eight modes), using each stratum's blind-coder rate of "Never launched": 13 of 13, 4 of 6, 1 of 5, and 0 of 8, 3, 6, 5 and 4 for the rest. The estimate is 13.8% (bootstrap 95% interval 7.8% to 19.7%, 5,000 resamples within strata), against 4% (3% to 7%) under the paper's labels. This is the paper-labelled runs as the blind coder reads them, with 3 unscored runs left out.

The frontier's 25% "never launched" (6 of 24, interval 12% to 45%) is 1.8 times the blind coder's own open-agent rate of 13.8%, so about half of the original gap from the paper's 4% comes from the coder and not the agents. The remaining gap does not clearly survive, because the frontier interval contains the open-agent point estimate and the two intervals overlap at 24 frontier runs.
