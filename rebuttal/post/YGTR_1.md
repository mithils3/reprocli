Thank you for the review. We ran the frontier models and production harnesses you asked for and measured each confound you named. For your points the revision adds:
- Section 5.1 and Appendix B: gpt-6.1-sol and gpt-6-astra in Codex CLI and in our loop, and Muse Wonder in mini-SWE-agent and in our loop, on papers fixed before any of these runs.
- Section 5.3: the failure modes of the frontier runs beside those of the open agents, and the bound on hardware build failures with an x86 replay.
- Section 5.2: a 95% Wilson interval on every rate, three runs of one agent on 12 papers, a trace of all 28 cells with no graded run, and a transcript scan for downloaded checkpoints.

**W1 and Q1: Frontier models and production coding harnesses.**

[On the same papers, gpt-6.1-sol in our loop reproduces 4 of 11, as many as DeepSeek-V4-Flash and Muse Spark 1.2. In Codex CLI, gpt-6.1-sol and gpt-6-astra reproduce 2 of 15 and 1 of 7 (95% Wilson intervals 4% to 38% and 3% to 51%), where DeepSeek-V4-Flash reproduces 6 of 15 and 3 of 7.] Each row below is one model in one harness, and the last two columns give DeepSeek-V4-Flash and Muse Spark 1.2, our two best agents, on exactly the papers of that row. A run counts as reproduced at an audit score of 8 or more out of 10, graded by the same auditor as the main runs.

| Model | Harness | Papers | Reproduced | Mean score | DeepSeek-V4-Flash, same papers | Muse Spark 1.2, same papers |
| :- | :- | -: | -: | -: | -: | -: |
| gpt-6.1-sol | our loop | [11] | [4] | [5.45] | [4, mean 5.91] | [4, mean 5.73] |
| gpt-6.1-sol | Codex CLI | [15] | [2] | [4.53] | [6, mean 6.13] | [4, mean 5.27] |
| gpt-6-astra | Codex CLI | [7] | [1] | [3.14] | [3, mean 5.57] | [2, mean 5.14] |
| gpt-6-astra | our loop | [n] | [a] | [s] | [d] | [m] |
| Muse Wonder | mini-SWE-agent | [n] | [a] | [s] | [d] | [m] |
| Muse Wonder | our loop | [n] | [a] | [s] | [d] | [m] |

The papers come from every tier, drawn with a fixed seed so that half had been reproduced by at least one open agent. Because that draw used the open agents' submitted results, we also compare against fresh runs: in two new runs on the 12 core papers, the set that every arm starts from, DeepSeek-V4-Flash reproduces [r2] and [r3] (W3).

*The harness.* Between the two harnesses of one model, the tools, system prompt and context handling change, while the sandbox, task text, GPU grant, GPU metering and auditor stay those of the main runs. On the [9] papers that gpt-6.1-sol has finished in both, our loop reproduces [3] and Codex CLI [2], with mean scores of [5.11] and [4.56]. The harness changes the verdict on [3] of these [9] papers, and repeated runs of one agent in one harness change it on [f] of 12 (W3), so the harness effect is [within / larger than] run-to-run variation.

*Early stops.* A Codex run ends when Codex ends its own turn, as in our loop, and the frontier runs used a median of [2.1]% of their GPU grant, against [17.5]% for the open agents on the same papers. To test whether Codex stops too soon, we added a variant that prompts it to continue, up to three times, whenever it stops with under half of its grant used. PaperBench uses similar prompts to keep agents from ending early. With these prompts gpt-6.1-sol in Codex CLI reproduces [c] of [n] papers.

Of the harnesses you name, we ran Codex CLI and mini-SWE-agent. We left out Claude Code because our auditor is Claude Sonnet 5, so a Claude agent would be graded by a model of its own family, and because our API budget for the new runs covered OpenAI and Meta models. We keep our loop for the main results so that every model runs under one harness, and Section 5.1 now reports the production-harness arms beside it, with each run's exit reason and each count's 95% interval in Appendix B.
