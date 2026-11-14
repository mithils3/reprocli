Thank you for the detailed review and for recognising the benchmark design as sound and reusable. To test each confound you named, we ran three frontier models in two production harnesses.

**W1 and Q1: Frontier models and production coding harnesses.**

We agree that a benchmark is most useful when it is tested on the strongest models, in the harnesses people use them with. Our new runs show that RECLAIM remains challenging for these models. [Over the 57 frontier runs, 18 are reproduced (32%, 95% interval 21% to 44%), where DeepSeek-V4-Flash and Muse Spark 1.2 reproduce 23 and 20 on the same papers.] The last two columns give our two best agents on exactly the papers of each row, under the same auditor and with their grades at submission (Section 5.2, Appendix B.3). "Our harness" is the ReAct loop of the main runs. The two OpenAI models ran at reasoning effort high in both harnesses, and Muse Wonder ran at xhigh, the setting of Muse Spark 1.2 in the main runs.

| Model | Harness | Papers | Reproduced | DeepSeek-V4-Flash | Muse Spark 1.2 |
| :- | :- | -: | -: | -: | -: |
| gpt-6.1-sol | our harness | [12] | [5] | [4] | [4] |
| gpt-6.1-sol | Codex CLI | [23] | [4] | [8] | [7] |
| gpt-6-astra | Codex CLI | [8] | [3] | [4] | [3] |
| gpt-6-astra | our harness | [6] | [1] | [4] | [3] |
| Muse Wonder | mini-SWE-agent | [6] | [4] | [3] | [2] |
| Muse Wonder | our harness | [2] | [1] | [0] | [1] |
| All frontier runs | | [57] | [18] | [23] | [20] |

**How the papers were chosen.** The 24 papers were preselected, in a fixed order, and come from every tier. Within each tier we drew half from the papers that at least one of our four agents had reproduced and half from the papers that none had. We chose this split to ask two questions separately: whether frontier models still reproduce what the open agents can, and whether they reproduce what the open agents cannot.

- On the 12 papers that an open agent had reproduced, the frontier runs reproduce [14 of 33], against [23] and [20] for DeepSeek-V4-Flash and Muse Spark 1.2.
- On the 12 papers where all four open agents had failed, [4 of the 24] frontier runs succeed, and they reproduce [2] papers that no open agent had.

Each row follows the fixed order: gpt-6.1-sol covers the first 12 papers in our harness and [23] of the 24 in Codex CLI, gpt-6-astra the first 8 in Codex CLI, and the other rows the first papers graded so far.

**Runs where only the harness differs.** gpt-6.1-sol finished the same [11] papers in both harnesses, with the sandbox, task text, GPU grant and auditor of the main runs. It reproduces [4] in our harness and [3] in Codex CLI, with the same verdict on [8], so the harness moves the result by one paper.

We did not evaluate Claude Code because our auditor is Claude Sonnet 5, and an auditor grading a model from its own family could be biased. Including it would require an independent auditor from another provider, validated against human grades as in Appendix D, which we leave to future work.
