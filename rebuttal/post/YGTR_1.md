Thank you for the detailed review and for recognising the benchmark design as sound and reusable. We ran three frontier models in two production harnesses and measured each confound you named.

**W1 and Q1: Frontier models and production coding harnesses.**

We agree that stronger models and production harnesses make the benchmark more informative. [The benchmark remains challenging for them. Pooled over the 57 frontier runs, 18 are reproduced (32%, 95% interval 21% to 44%), where DeepSeek-V4-Flash and Muse Spark 1.2 reproduce 23 and 20 on the same papers, and changing the harness moves gpt-6.1-sol by one paper.] The last two columns give our two best agents on exactly the papers of each row, under the same auditor and with their grades at submission (Section 5.2, Appendix B.3).

| Model | Harness | Papers | Reproduced | DeepSeek-V4-Flash | Muse Spark 1.2 |
| :- | :- | -: | -: | -: | -: |
| gpt-6.1-sol | our loop | [12] | [5] | [4] | [4] |
| gpt-6.1-sol | Codex CLI | [23] | [4] | [8] | [7] |
| gpt-6-astra | Codex CLI | [8] | [3] | [4] | [3] |
| gpt-6-astra | our loop | [6] | [1] | [4] | [3] |
| Muse Wonder | mini-SWE-agent | [6] | [4] | [3] | [2] |
| Muse Wonder | our loop | [2] | [1] | [0] | [1] |
| All frontier runs | | [57] | [18] | [23] | [20] |

The 24 papers come from every tier and were fixed, in order, before any of these runs. Each row follows that order: gpt-6.1-sol covers the first 12 papers in our loop and [23] of the 24 in Codex CLI, gpt-6-astra the first 8 in Codex CLI, and the other rows the first papers graded so far. In each tier, half are papers that some open agent had reproduced and half are papers that none had, so the open-agent columns can only score on the first half. On those 12 papers the frontier runs reproduce [14 of 33], against [23] and [20] for DeepSeek-V4-Flash and Muse Spark 1.2. On the 12 papers that no open agent reproduced they reproduce [4 of 24], which adds [2] papers that none of our four agents reproduced. Within one model only the harness changes, and the sandbox, task text, GPU grant and auditor are those of the main runs. On the [11] papers that gpt-6.1-sol finished in both harnesses, it reproduces [4] in our loop and [3] in Codex CLI, with the same verdict on [8].

The frontier runs also stop early. Over the [57] runs, the median frontier run used [5.6]% of its GPU grant, against a median of [14.3]% for the open agents on the same papers, and the frontier runs that did not reproduce used a median of [2.1]%. The three rows with 12, 23 and 8 papers have medians of [8.5]%, [3.2]% and [3.8]%. A variant that prompts Codex to continue, up to three times, whenever it stops with under half of its grant used spent more of its grant on each of the [3] papers it finished and received the same score as the unprompted run ([8, 7 and 8]). These runs are left out of the pooled counts. We ran Codex CLI and mini-SWE-agent and left out Claude Code, because our auditor is Claude Sonnet 5 and would grade a model of its own family. A Claude Code arm would need a second auditor from another lab, validated against the human grades as ours is in Appendix D.

**Whether the failure modes and findings change.**

Run is again the easiest tier, and the failures shift toward stopping early. The frontier runs reproduce [11 of 18] at Run, [3 of 20] at Retrain and [4 of 19] at Reimplement. This sample cannot order Retrain and Reimplement, because it takes equal numbers of reproduced and unreproduced papers from every tier, and DeepSeek-V4-Flash is level on it as well, at [6 of 20] and [6 of 19]. At Retrain a run has to train the model again, which is where stopping early costs most. On 2506.08898 (32 H100-hour grant), [5 of 6] frontier runs stopped within one H100-hour because no matching checkpoint is released. [The sixth, Muse Wonder in our loop, retrained the model with 27 H100-hours and reproduced the claim, as Muse Spark 1.2 did under the same prompt] (Section 5.3).

Claude Sonnet 5, shown neither the verdict nor the harness, labelled the main failure of each of the [39] failing frontier runs with the Appendix G definitions. Failures that report a number without a valid measurement are rarer in the frontier runs, [8 of 39 = 21%] against 110 of 300 = 37% for the open agents, and [14 of 39 = 36%] ended before producing a number, against 44 of 300 = 15%. When the same annotator labels a sample of 50 open-agent runs, the two shares are 46% and 23% (Appendix G). The 300 are the open-agent runs with a failure label at submission: the 299 that were not reproduced, and one reproduced run that the taxonomy labels as measuring the wrong artifact.
