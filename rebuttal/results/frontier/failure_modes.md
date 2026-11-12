# Frontier failure modes (partial: 39 of 58 planned)

Coded 39 failing frontier runs (verdict not_reproduced, partial or unverifiable) of the 58 planned. The coder is claude-sonnet-5 with the Appendix G definitions, one run per call, and it never saw the verdict, score, flags or arm. It returned a true or false for each of the nine modes and one primary mode. This is a partial read and will change as runs finish.

## Primary mode, frontier counts beside the open agents

Open-agent share is the primary-mode count over the 300 labeled open-agent cells that were not graded reproduced (400 cells, minus 72 Reproduced, minus 28 with no label), with a Wilson 95% interval. Frontier cells are runs, not shares, so the interval for a frontier share is Wilson on that arm's N.

| Mode | Open agents | Open share (95% interval) | codex-gpt-6-astra (N=6) | codex-gpt-6.1-sol (N=17) | codex-gpt-6.1-sol-nudge (N=1) | miniswe (N=2) | thin-gpt-6-astra (N=5) | thin-gpt-6.1-sol (N=7) | thin-muse-wonder-1.0 (N=1) | All frontier |
|---|---|---|---|---|---|---|---|---|---|---|
| Ran, outside tolerance | 76 | 25% (21% to 31%) | 0 | 4 | 1 | 0 | 1 | 2 | 0 | 8 of 39 (21%, 11% to 36%) |
| Reimplemented but did not check the result | 63 | 21% (17% to 26%) | 0 | 3 | 0 | 0 | 1 | 1 | 0 | 5 of 39 (13%, 6% to 27%) |
| Build and dependency failures | 24 | 8% (5% to 12%) | 1 | 2 | 0 | 0 | 0 | 1 | 0 | 4 of 39 (10%, 4% to 24%) |
| Wrong artifact measured | 38 | 13% (9% to 17%) | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 2 of 39 (5%, 1% to 17%) |
| Wrong experiment | 46 | 15% (12% to 20%) | 1 | 1 | 0 | 1 | 0 | 1 | 0 | 4 of 39 (10%, 4% to 24%) |
| Echoed a shipped number | 9 | 3% (2% to 6%) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 of 39 (0%, 0% to 9%) |
| Never launched an experiment | 13 | 4% (3% to 7%) | 2 | 3 | 0 | 0 | 2 | 2 | 0 | 9 of 39 (23%, 13% to 38%) |
| Failed before any number was produced | 31 | 10% (7% to 14%) | 2 | 3 | 0 | 1 | 0 | 0 | 1 | 7 of 39 (18%, 9% to 33%) |

The open agents' three most common non-reproduced modes are Ran, outside tolerance, Reimplemented but did not check the result, Wrong experiment.

## Any-mode counts (a run can show several modes)

| Mode | codex-gpt-6-astra | codex-gpt-6.1-sol | codex-gpt-6.1-sol-nudge | miniswe | thin-gpt-6-astra | thin-gpt-6.1-sol | thin-muse-wonder-1.0 | All frontier |
|---|---|---|---|---|---|---|---|---|
| Reproduced | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 of 39 |
| Ran, outside tolerance | 0 | 7 | 1 | 0 | 2 | 3 | 0 | 13 of 39 |
| Reimplemented but did not check the result | 0 | 3 | 0 | 1 | 1 | 1 | 1 | 7 of 39 |
| Build and dependency failures | 2 | 6 | 1 | 0 | 2 | 1 | 1 | 13 of 39 |
| Wrong artifact measured | 0 | 3 | 0 | 1 | 1 | 2 | 0 | 7 of 39 |
| Wrong experiment | 2 | 1 | 0 | 1 | 1 | 1 | 0 | 6 of 39 |
| Echoed a shipped number | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 of 39 |
| Never launched an experiment | 2 | 3 | 0 | 0 | 2 | 3 | 0 | 10 of 39 |
| Failed before any number was produced | 2 | 5 | 0 | 1 | 0 | 0 | 1 | 9 of 39 |

## Method notes

The paper's labels came from a language model reading each transcript against the Appendix G definitions and also seeing the audit verdict. The original coder prompt was not saved (the dissection ran as a Sonnet subagent fan-out under the analyze-sweep skill), so the prompt here is rebuilt from the Appendix G definitions. The coder here is blind to the outcome, which the paper's pass was not, and the paper's counts also went through two relabel passes by hand. A transcript is cut to its timestamped commands, the agent's messages, error lines and the final report, at most 70,000 characters. Script: `rebuttal/scripts/frontier_failure_modes.py`; a rerun codes only run ids missing from `failure_modes.csv`.
