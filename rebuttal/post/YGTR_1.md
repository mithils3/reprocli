Thank you for the detailed review and for recognising the benchmark design as sound and reusable. We ran the frontier models and production harnesses you asked for and measured each confound you named.

**W1 and Q1: Frontier models and production coding harnesses.**

We agree that stronger models and production harnesses make the benchmark more informative. [The benchmark remains challenging for them: gpt-6.1-sol reproduces 5 of 12 papers in our loop, where DeepSeek-V4-Flash and Muse Spark 1.2 each reproduce 4 of the same 12, and the frontier runs reproduce the claim in 2 of 20 runs at the Retrain tier. In Codex CLI, gpt-6.1-sol and gpt-6-astra reproduce 4 of 23 and 2 of 8, where DeepSeek-V4-Flash reproduces 8 of 23 and 4 of 8.] Each row covers a small set of papers, so the last two columns give our two best agents on exactly those papers, under the same auditor (Section 5.1, Appendix B).

| Model | Harness | Papers | Reproduced | DeepSeek-V4-Flash | Muse Spark 1.2 |
| :- | :- | -: | -: | -: | -: |
| gpt-6.1-sol | our loop | [12] | [5] | [4] | [4] |
| gpt-6.1-sol | Codex CLI | [23] | [4] | [8] | [7] |
| gpt-6-astra | Codex CLI | [8] | [2] | [4] | [3] |
| gpt-6-astra | our loop | [6] | [1] | [4] | [3] |
| Muse Wonder | mini-SWE-agent | [6] | [4] | [3] | [2] |

The papers come from every tier and were fixed before any of these runs. Half were drawn from papers that some open agent had reproduced, which favours the open-agent columns. Within one model only the harness changes, and the sandbox, task text, GPU grant and auditor are those of the main runs. On the [11] papers that gpt-6.1-sol finished in both harnesses, the counts are comparable, [4] in our loop and [3] in Codex CLI.

We also noticed that the frontier runs stop early. They used a median of [5.1]% of their GPU grant, against [14.3]% for the open agents on the same papers. A variant that prompts Codex to continue, up to three times, whenever it stops with under half of its grant used reproduces [2 of 3] papers, with the same score as the unprompted run on all three. We ran Codex CLI and mini-SWE-agent and left out Claude Code, because our auditor is Claude Sonnet 5 and would grade a model of its own family.

**Whether the failure modes and findings change.**

The mix of failures shifts in the frontier runs, and Run is again the easiest tier. An annotator that saw neither the verdict nor the harness labelled the main failure of each of the [41] failing frontier runs with the Appendix G definitions. Failures that report a number without a valid measurement are rarer in the frontier runs, [8 of 41 = 20%] against 110 of 300 = 37% for the open agents, and [16 of 41] ended before producing a number. On 2506.08898 (32 H100-hour grant), all [5] frontier runs stopped within one H100-hour because no matching checkpoint is released, while Muse Spark 1.2 retrained the model with 27 H100-hours under the same prompt and reproduced the claim (Section 5.3). The frontier runs reproduce [12 of 20] at Run, [2 of 20] at Retrain and [4 of 19] at Reimplement (Appendix B).
