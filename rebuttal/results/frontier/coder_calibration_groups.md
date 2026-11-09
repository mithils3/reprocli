# Open-agent share of two mode groups, blind-coder reweighting

Each group is scored as the share of the 300 labelled failing open-agent cells, using the paper's eight failing-mode sizes as strata. Within each stratum the share is the fraction of the coded sample rows that the blind coder labels in the group, and the estimate is sum(size x fraction) / 300, with a stratified bootstrap (5,000 resamples, seed 20261109). Frontier counts are the failing frontier runs in failure_modes.csv under the blind coder, with one hand relabel applied and a Wilson 95% interval.

| Group | Open agents, paper labels (count/300, %, Wilson 95%) | Open agents, blind coder (reweighted %, bootstrap 95%) | Frontier runs, blind coder (count/N, %, Wilson 95%) |
|---|---|---|---|
| A. Number without a valid measurement | 110/300, 36.7%, 31.4% to 42.3% | 46.2%, 34.8% to 58.3% | 3/27, 11.1%, 3.9% to 28.1% |
| B. Ended without a number | 44/300, 14.7%, 11.1% to 19.1% | 22.8%, 14.4% to 33.3% | 11/27, 40.7%, 24.5% to 59.3% |

Worked example, Group A: 76 x 2/8 (near-miss-partial) + 63 x 3/3 (reimplement-without-validating) + 24 x 2/5 (environment-fights) + 38 x 3/5 (artifact-provenance-mismatch) + 46 x 2/6 (scope-substitution) + 9 x 4/4 (stale-artifact-reliance) + 13 x 0/13 (procrastination/wall-kill) + 31 x 0/6 (killed-before-the-number) = 138.73, and that divided by 300 is 46.2%.

Sanity check: the same code on Never launched alone gives 13.8%, matching the 13.8% in coder_calibration.md.

Frontier check: Group A 3 + Group B 11 + other modes 13 = 27 failing rows in failure_modes.csv. The 6cef06 run is counted as killed-before-the-number. Sample: 50 coded open-agent runs.
