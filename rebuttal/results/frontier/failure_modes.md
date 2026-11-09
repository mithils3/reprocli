# Frontier failure modes (partial: 29 of 58 planned)

Coded 29 failing frontier runs (verdict not_reproduced, partial or unverifiable) of the 58 planned. The coder is claude-sonnet-5 with the Appendix G definitions, one run per call, and it never saw the verdict, score, flags or arm. It returned a true or false for each of the nine modes and one primary mode. This is a partial read and will change as runs finish.

## Primary mode, frontier counts beside the open agents

Open-agent share is the primary-mode count over the 300 labeled open-agent cells that were not graded reproduced (400 cells, minus 72 Reproduced, minus 28 with no label), with a Wilson 95% interval. Frontier cells are runs, not shares, so the interval for a frontier share is Wilson on that arm's N.

| Mode | Open agents | Open share (95% interval) | codex-gpt-6-astra (N=6) | codex-gpt-6.1-sol (N=13) | miniswe (N=1) | thin-gpt-6-astra (N=2) | thin-gpt-6.1-sol (N=7) | All frontier |
|---|---|---|---|---|---|---|---|---|
| Ran, outside tolerance | 76 | 25% (21% to 31%) | 0 | 3 | 0 | 0 | 2 | 5 of 29 (17%, 8% to 35%) |
| Reimplemented but did not check the result | 63 | 21% (17% to 26%) | 0 | 2 | 0 | 0 | 1 | 3 of 29 (10%, 4% to 26%) |
| Build and dependency failures | 24 | 8% (5% to 12%) | 1 | 2 | 0 | 0 | 1 | 4 of 29 (14%, 5% to 31%) |
| Wrong artifact measured | 38 | 13% (9% to 17%) | 0 | 0 | 0 | 1 | 0 | 1 of 29 (3%, 1% to 17%) |
| Wrong experiment | 46 | 15% (12% to 20%) | 1 | 1 | 1 | 0 | 1 | 4 of 29 (14%, 5% to 31%) |
| Echoed a shipped number | 9 | 3% (2% to 6%) | 0 | 0 | 0 | 0 | 0 | 0 of 29 (0%, 0% to 12%) |
| Never launched an experiment | 13 | 4% (3% to 7%) | 2 | 2 | 0 | 1 | 2 | 7 of 29 (24%, 12% to 42%) |
| Failed before any number was produced | 31 | 10% (7% to 14%) | 2 | 3 | 0 | 0 | 0 | 5 of 29 (17%, 8% to 35%) |

The open agents' three most common non-reproduced modes are Ran, outside tolerance, Reimplemented but did not check the result, Wrong experiment.

## Any-mode counts (a run can show several modes)

| Mode | codex-gpt-6-astra | codex-gpt-6.1-sol | miniswe | thin-gpt-6-astra | thin-gpt-6.1-sol | All frontier |
|---|---|---|---|---|---|---|
| Reproduced | 0 | 0 | 0 | 0 | 0 | 0 of 29 |
| Ran, outside tolerance | 0 | 4 | 0 | 0 | 3 | 7 of 29 |
| Reimplemented but did not check the result | 0 | 2 | 0 | 0 | 1 | 3 of 29 |
| Build and dependency failures | 2 | 6 | 0 | 0 | 1 | 9 of 29 |
| Wrong artifact measured | 0 | 1 | 1 | 1 | 2 | 5 of 29 |
| Wrong experiment | 2 | 1 | 1 | 1 | 1 | 6 of 29 |
| Echoed a shipped number | 0 | 0 | 0 | 0 | 0 | 0 of 29 |
| Never launched an experiment | 2 | 2 | 0 | 1 | 3 | 8 of 29 |
| Failed before any number was produced | 2 | 5 | 0 | 0 | 0 | 7 of 29 |

## Method notes

The paper's labels came from a language model reading each transcript against the Appendix G definitions and also seeing the audit verdict. The original coder prompt was not saved (the dissection ran as a Sonnet subagent fan-out under the analyze-sweep skill), so the prompt here is rebuilt from the Appendix G definitions. The coder here is blind to the outcome, which the paper's pass was not, and the paper's counts also went through two relabel passes by hand. A transcript is cut to its timestamped commands, the agent's messages, error lines and the final report, at most 70,000 characters. Script: `rebuttal/scripts/frontier_failure_modes.py`; a rerun codes only run ids missing from `failure_modes.csv`.
