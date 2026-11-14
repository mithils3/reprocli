Thank you for the detailed review and for recognising the benchmark design as sound and reusable. To test each confound you named, we ran three frontier models in two production harnesses.

**W1 and Q1: Frontier models and production coding harnesses.**

We agree that a benchmark is most useful when it is tested on the strongest models, in the harnesses people use them with. Our new runs show that RECLAIM remains challenging for these models. Over the 57 frontier runs, 18 are reproduced (32%, 95% interval 21% to 44%), where DeepSeek-V4-Flash and Muse Spark 1.2 reproduce 23 and 20 on the same papers. The last two columns give our two best agents on exactly the papers of each row, under the same auditor and with their grades at submission (Section 5.2, Appendix B.3). The OpenAI models ran at high reasoning effort and Muse Wonder at xhigh.

| Model | Harness | Papers | Reproduced | DeepSeek-V4-Flash | Muse Spark 1.2 |
| :- | :- | -: | -: | -: | -: |
| gpt-6.1-sol | our harness | 12 | 5 | 4 | 4 |
| gpt-6.1-sol | Codex CLI | 23 | 4 | 8 | 7 |
| gpt-6-astra | Codex CLI | 8 | 3 | 4 | 3 |
| gpt-6-astra | our harness | 6 | 1 | 4 | 3 |
| Muse Wonder | mini-SWE-agent | 6 | 4 | 3 | 2 |
| Muse Wonder | our harness | 2 | 1 | 0 | 1 |
| All frontier runs | | 57 | 18 | 23 | 20 |

**How the papers were chosen.** We preselected 24 papers from all three tiers, half that at least one of our four agents had reproduced and half that none had, so that the two cases can be read separately. Every row takes the papers in the same fixed order, and the rows differ in how many they cover.

- On the 12 papers that an open agent had reproduced, the frontier runs reproduce 14 of 33, against 23 and 20 for DeepSeek-V4-Flash and Muse Spark 1.2.
- On the 12 papers where all four open agents had failed, 4 of the 24 frontier runs succeed, and they reproduce 2 papers that no open agent had.

**Runs where only the harness differs.** gpt-6.1-sol finished the same 11 papers in both harnesses, with every other setting as in the main runs. It reproduces 4 in our harness and 3 in Codex CLI, with the same verdict on 8, so the harness moves the result by one paper.

We did not evaluate Claude Code because our auditor is Claude Sonnet 5, and an auditor grading a model from its own family could be biased. Including it would require an independent auditor from another provider, validated against human grades as in Appendix D, which we leave to future work.

**Whether the failure modes and findings change.**

Run is also the easiest tier for the frontier models (11 of 18, against 3 of 20 at Retrain and 4 of 19 at Reimplement), but their main cause of failure is stopping early rather than reporting a number without a valid measurement. Because the sample holds equal numbers of reproduced and unreproduced papers in every tier, it narrows the gap between Retrain and Reimplement, and DeepSeek-V4-Flash is level on these papers as well (6 of 20 and 6 of 19).

Interestingly, the frontier models stop even earlier than the open agents. Over the 57 runs, the median frontier run used 5.6% of its GPU grant, against 14.3% for the open agents on the same papers, and the frontier runs that did not reproduce used 2.1%. To test the effect further, we ran a variant that prompts Codex to continue, up to three times, whenever it stops before using half of its GPU grant. On the 3 papers it finished, it spent more of its grant and received the same score as the unprompted run (8, 7 and 8).

To find the reason, we analysed the full transcripts of the 39 failing frontier runs. 27 of the 39 never ran the paper's experiment at full scale, and they decided this early, at a median of turn 9:

- 12 stopped because the code, checkpoint or data they needed is not released, 8 of them at Reimplement, where writing that code is the task. One run explains: "Without an artifact to resolve and validate these choices, I can't treat a new implementation's accuracy as a reproduction of the locked result."
- 6 timed a short probe, projected a cost above the grant and stopped. On 2506.08898 (32 H100-hour grant), three runs projected 33 to 51 hours, where Muse Spark 1.2 and Muse Wonder in our harness retrained the model within the grant and reproduced the claim (Section 5.3).
- 5 evaluated a different released checkpoint, and 4 hit build or launch errors.

The other 12 ran the experiment and missed the number. For 11 of the 27, an open agent that kept working reproduced the same paper, so stopping early cost reproductions. The failure labels agree. Failures that report a number without a valid measurement fall to 8 of 39 = 21%, against 110 of 300 = 37% for the open agents, and 14 of 39 = 36% end before producing a number, against 44 of 300 = 15% (46% and 23% when the same annotator, Claude Sonnet 5, labels a sample of 50 open-agent runs).
