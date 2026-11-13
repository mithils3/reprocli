# Frontier failure modes (partial: 40 of 58 planned)

Coded 40 failing frontier runs (verdict not_reproduced, partial or unverifiable) of the 58 planned. The coder is claude-sonnet-5 with the Appendix G definitions, one run per call, and it never saw the verdict, score, flags or arm. It returned a true or false for each of the nine modes and one primary mode. This is a partial read and will change as runs finish.

## Primary mode, frontier counts beside the open agents

Open-agent share is the primary-mode count over the 300 labeled open-agent cells that were not graded reproduced (400 cells, minus 72 Reproduced, minus 28 with no label), with a Wilson 95% interval. Frontier cells are runs, not shares, so the interval for a frontier share is Wilson on that arm's N.

| Mode | Open agents | Open share (95% interval) | codex-gpt-6-astra (N=5) | codex-gpt-6.1-sol (N=19) | codex-gpt-6.1-sol-nudge (N=1) | miniswe (N=2) | thin-gpt-6-astra (N=5) | thin-gpt-6.1-sol (N=7) | thin-muse-wonder-1.0 (N=1) | All frontier |
|---|---|---|---|---|---|---|---|---|---|---|
| Ran, outside tolerance | 76 | 25% (21% to 31%) | 1 | 5 | 1 | 0 | 1 | 2 | 0 | 10 of 40 (25%, 14% to 40%) |
| Reimplemented but did not check the result | 63 | 21% (17% to 26%) | 0 | 3 | 0 | 0 | 1 | 1 | 0 | 5 of 40 (12%, 5% to 26%) |
| Build and dependency failures | 24 | 8% (5% to 12%) | 1 | 2 | 0 | 0 | 0 | 1 | 0 | 4 of 40 (10%, 4% to 23%) |
| Wrong artifact measured | 38 | 13% (9% to 17%) | 0 | 2 | 0 | 0 | 1 | 0 | 0 | 3 of 40 (8%, 3% to 20%) |
| Wrong experiment | 46 | 15% (12% to 20%) | 1 | 1 | 0 | 1 | 0 | 1 | 0 | 4 of 40 (10%, 4% to 23%) |
| Echoed a shipped number | 9 | 3% (2% to 6%) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 of 40 (0%, -0% to 9%) |
| Never launched an experiment | 13 | 4% (3% to 7%) | 2 | 3 | 0 | 0 | 2 | 2 | 0 | 9 of 40 (22%, 12% to 38%) |
| Failed before any number was produced | 31 | 10% (7% to 14%) | 0 | 3 | 0 | 1 | 0 | 0 | 1 | 5 of 40 (12%, 5% to 26%) |

The open agents' three most common non-reproduced modes are Ran, outside tolerance, Reimplemented but did not check the result, Wrong experiment.

## Any-mode counts (a run can show several modes)

| Mode | codex-gpt-6-astra | codex-gpt-6.1-sol | codex-gpt-6.1-sol-nudge | miniswe | thin-gpt-6-astra | thin-gpt-6.1-sol | thin-muse-wonder-1.0 | All frontier |
|---|---|---|---|---|---|---|---|---|
| Reproduced | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 of 40 |
| Ran, outside tolerance | 1 | 9 | 1 | 0 | 2 | 3 | 0 | 16 of 40 |
| Reimplemented but did not check the result | 0 | 3 | 0 | 1 | 1 | 1 | 1 | 7 of 40 |
| Build and dependency failures | 1 | 7 | 1 | 0 | 2 | 1 | 1 | 13 of 40 |
| Wrong artifact measured | 1 | 4 | 0 | 1 | 1 | 2 | 0 | 9 of 40 |
| Wrong experiment | 2 | 1 | 0 | 1 | 1 | 1 | 0 | 6 of 40 |
| Echoed a shipped number | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 of 40 |
| Never launched an experiment | 2 | 3 | 0 | 0 | 2 | 3 | 0 | 10 of 40 |
| Failed before any number was produced | 0 | 5 | 0 | 1 | 0 | 0 | 1 | 7 of 40 |

## Method notes

The paper's labels came from a language model reading each transcript against the Appendix G definitions and also seeing the audit verdict. The original coder prompt was not saved (the dissection ran as a Sonnet subagent fan-out under the analyze-sweep skill), so the prompt here is rebuilt from the Appendix G definitions. The coder here is blind to the outcome, which the paper's pass was not, and the paper's counts also went through two relabel passes by hand. A transcript is cut to its timestamped commands, the agent's messages, error lines and the final report, at most 70,000 characters. Script: `rebuttal/scripts/frontier_failure_modes.py`; a rerun codes only run ids missing from `failure_modes.csv`.
