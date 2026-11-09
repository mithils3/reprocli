# Never launched an experiment: check of the six frontier labels

Source: agent.full.log and report.json in each run_dir on DeltaAI (read only), plus frontier_cells.csv (rebuttal/results/databook/). Line numbers are lines of agent.full.log. Every run ended with exit_reason natural. The two runs the brief called miniswe muse-wonder-1.0 are the two thin-harness gpt-6.1-sol runs (arm thin-gpt-6.1-sol) in failure_modes.csv; no muse-wonder run carries this label there.

Definitions (paper_latex/appendix/g_taxonomy.tex, lines 138 to 149): "Never launched an experiment" means the agent spends its rounds reading, downloading and probing, never runs the pinned pipeline, and stops with most compute unused. "Failed before any number was produced" means the environment and artifacts work, the pipeline runs, and the run ends before the graded command produces a value.

| run_id | arm | paper | launched | why it stopped | deciding lines | spent_h100 / budget | my mode |
|---|---|---|---|---|---|---|---|
| codex-gpt-6-astra-20261107T101517Z-62f1c5 | codex-gpt-6-astra | 2505.16927 | no | Missing artifact (no STaPLe code, checkpoint or training data exists), then the model chose to end with a report | l.2344: "no runnable scripts, checkpoin[ts]"; l.2380: "The released material is insufficient to validate a faithful end-to-end port"; report.json what_ran: "No training, policy generation, judge inference or benchmark scoring ran." | 0.039 / 32 | Never launched an experiment |
| codex-gpt-6-astra-20261109T010623Z-6cef06 | codex-gpt-6-astra | 2510.21363 | yes (diagnostic only) | The model chose to end with a report after one smoke run, because the development-selection sweep was not recoverable (20 development prompts in the paper, 30 in the release) | l.3246: "The unmodified author entrypoint completed a FairImagen smoke run, including image generation and DeepFace/CLIP/MUSIQ scoring"; l.3308: "smoke run scored gender fairness 0.500 for the CEO prompt ... only a diagnostic result, not the 100-prompt target"; l.3608: "The full sweep and test evaluation were not run" | 0.3946 / 8 | Failed before any number was produced |
| codex-gpt-6.1-sol-20261107T010540Z-d345e4 | codex-gpt-6.1-sol | 2505.16927 | no | Missing artifact (no code or checkpoint), then the model chose to end with a report | l.2161: "no code or weights ... I can't establish a faithful scoring path ... I'm winding down with no benchmark score"; report.json: "No mining, training, benchmark inference, or scoring ran." | 0.0546 / 32 | Never launched an experiment |
| codex-gpt-6.1-sol-20261108T023042Z-ae78cc | codex-gpt-6.1-sol | 2503.14698 | no | Missing artifact (project page 404, no code or checkpoint), then the model chose to end with a report | l.1929: "found no runnable Fuse-and-Refine code, target checkpoint, or same-method sibling checkpoint"; l.1931: "I have no measured PSNR to report ... an unvalidated port would not test the locked target" | 0.0308 / 96 | Never launched an experiment |
| core-a-2503.14698-a56492 | thin-gpt-6.1-sol | 2503.14698 | no | Missing artifact, then the model chose to end with a report at round 30 | l.1716: "Without a trained method artifact ... a baseline run or custom implementation would not test the locked claim. I'm stopping before spending on an incomparable experiment"; l.2097: FINAL (round 30) exit=natural | 0.0027 / 96 | Never launched an experiment |
| core-a-2505.16927-eed0ff | thin-gpt-6.1-sol | 2505.16927 | no | Missing artifact (no checkpoint or implementation), then the model chose to end with a report | l.2126: "The benchmark experiment was not executed ... I stopped at the documented artifact and validation blocker rather than manufacture a substitute measurement"; l.2139: FINAL (round 26) exit=natural | 0.0669 / 32 | Never launched an experiment |

None of the six stopped because of a budget or wall limit, an API or harness error, or waiting on a GPU (the GPU waits of several hours before the first CUDA check are queue time, not the stop cause). Five of the six stopped because the paper ships no code or checkpoint for a reimplement-tier claim, so the stop is an artifact gap followed by a voluntary report. That is still the Appendix G description of the label, since the pinned pipeline was never run and almost all compute was left unused.

Five of the six are truly never launched; the sixth (6cef06) ran the authors' own entrypoint on a single prompt and belongs under "Failed before any number was produced". The corrected frontier count is 5 of 24 (20.8 percent, Wilson 95 percent interval 9.2 to 40.5 percent), down from 6 of 24 (25.0 percent, 12.0 to 44.9 percent).

## Same papers, open agents

Open-agent labels come from resolved_modes.json (`~/sweeps/paper-table-2026-09-05/resolved_modes.json`, local; `mode` field) and the score and verdict columns of rebuttal/results/databook/frontier_cells.csv. Frontier rows are the "my mode" labels above; failure_modes.csv still lists all five as procrastination/wall-kill and should be corrected. Scores are on the 0 to 4 scale.

| paper | agent | tier | verdict (score) | failure mode label |
|---|---|---|---|---|
| 2505.16927 (STaPLe) | DeepSeek-V4-Flash | reimplement | not_reproduced (4) | reimplement-without-validating |
| 2505.16927 | MiniMax-M2.7 | reimplement | disqualified (0) | artifact-provenance-mismatch |
| 2505.16927 | Muse Spark 1.2 | reimplement | not_reproduced (4) | scope-substitution |
| 2505.16927 | Qwen3.6-27B | reimplement | not_reproduced (4) | reimplement-without-validating |
| 2505.16927 | frontier gpt-6-astra | reimplement | unverifiable (1) | Never launched an experiment |
| 2505.16927 | frontier gpt-6.1-sol | reimplement | unverifiable (1) | Never launched an experiment |
| 2505.16927 | frontier thin-gpt-6.1-sol | reimplement | unverifiable (1) | Never launched an experiment |
| 2503.14698 | DeepSeek-V4-Flash | reimplement | unverifiable (1) | killed-before-the-number |
| 2503.14698 | MiniMax-M2.7 | reimplement | not_reproduced (2) | reimplement-without-validating |
| 2503.14698 | Muse Spark 1.2 | reimplement | unverifiable (1) | procrastination/wall-kill (relabeled from unavailability-concluded-from-prose) |
| 2503.14698 | Qwen3.6-27B | reimplement | unverifiable (1) | killed-before-the-number |
| 2503.14698 | frontier gpt-6.1-sol | reimplement | not_reproduced (2) | Never launched an experiment |
| 2503.14698 | frontier thin-gpt-6.1-sol | reimplement | unverifiable (1) | Never launched an experiment |

None of the eight open-agent runs on these papers carries the never-launched label, but on 2503.14698 they stopped early under other labels, spending 0.02 to 1.3 H100 hours of a 96 hour budget, while on 2505.16927 they spent 7.3 to 31.5 of 32 hours. Excluding these two papers, 0 of 19 failing frontier runs are never-launched (0.0%, Wilson 95% interval 0.0 to 16.8%), so the overall frontier share of 5 of 24 (20.8%, 9.2 to 40.5%) comes entirely from these two papers.
