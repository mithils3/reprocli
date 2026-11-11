Thank you for the detailed review and for recognising the benchmark design as sound and reusable. We ran the frontier models and production harnesses you asked for and measured each confound you named.

**W1 and Q1: Frontier models and production coding harnesses.**

We agree that stronger models and production harnesses make the benchmark more informative. [On the same papers, gpt-6.1-sol in our loop reproduces 4 of 11, as many as DeepSeek-V4-Flash and Muse Spark 1.2. In Codex CLI, gpt-6.1-sol and gpt-6-astra reproduce 2 of 18 and 1 of 7, where DeepSeek-V4-Flash reproduces 6 of 18 and 3 of 7.] Each row covers a small set of papers, so the last two columns give our two best agents on exactly those papers, under the same auditor (Section 5.1, Appendix B).

| Model | Harness | Papers | Reproduced | DeepSeek-V4-Flash | Muse Spark 1.2 |
| :- | :- | -: | -: | -: | -: |
| gpt-6.1-sol | our loop | [11] | [4] | [4] | [4] |
| gpt-6.1-sol | Codex CLI | [18] | [2] | [6] | [4] |
| gpt-6-astra | Codex CLI | [7] | [1] | [3] | [2] |
| gpt-6-astra | our loop | [4] | [1] | [2] | [2] |
| Muse Wonder | mini-SWE-agent | [4] | [2] | [1] | [1] |
| Muse Wonder | our loop | [n] | [a] | [d] | [m] |

The papers come from every tier and were fixed before any of these runs. Half were drawn from papers that some open agent had reproduced, so we also ran DeepSeek-V4-Flash twice more on the 12 core papers, where it reproduces [r2] and [r3]. Within one model only the harness changes, and the sandbox, task text, GPU grant and auditor are those of the main runs. On the [10] papers that gpt-6.1-sol finished in both harnesses, the counts are comparable, [3] in our loop and [2] in Codex CLI.

We also noticed that the frontier runs stop early. They used a median of [2.4]% of their GPU grant, against [17.2]% for the open agents on the same papers. A variant that prompts Codex to continue, up to three times, whenever it stops with under half of its grant used reproduces [c] of [n] papers. We ran Codex CLI and mini-SWE-agent and left out Claude Code, because our auditor is Claude Sonnet 5 and would grade a model of its own family.

**Whether the failure modes and findings change.**

The mix of failures shifts in the frontier runs, and Run is again the easiest tier. An annotator that saw neither the verdict nor the harness labelled the main failure of each of the [34] failing frontier runs with the Appendix G definitions. Failures that report a number without a valid measurement are rarer in the frontier runs, [6 of 34 = 18%] against 110 of 300 = 37% for the open agents, and [14 of 34] ended before producing a number. On 2506.08898 (32 H100-hour grant), all [5] frontier runs stopped within one H100-hour because no matching checkpoint is released, while Muse Spark 1.2 retrained the model with 27 H100-hours under the same prompt and reproduced the claim. The frontier runs reproduce [7 of 14] at Run, [0 of 13] at Retrain and [3 of 17] at Reimplement (Section 5.3).
