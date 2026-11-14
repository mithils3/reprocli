Thank you for the detailed review and for recognising the benchmark design as sound and reusable. To test each confound you named, we ran three frontier models in two production harnesses.

**W1 and Q1: Frontier models and production coding harnesses.**

We agree that a benchmark is most useful when it is tested on the strongest models, in the harnesses people use them with. Our new runs show that RECLAIM remains challenging for frontier models. Over the 57 frontier runs, 18 are reproduced (32% [21%, 44%]), against 23 and 20 for DeepSeek-V4-Flash and Muse Spark 1.2 on the same papers (Section 5.2, Appendix B.3). The OpenAI models ran at high reasoning effort and Muse Wonder at xhigh.

Papers reproduced:

| Model | Harness | Papers | Reproduced | DeepSeek-V4-Flash | Muse Spark 1.2 |
| :- | :- | -: | -: | -: | -: |
| gpt-6.1-sol | our harness | 12 | 5 | 4 | 4 |
| gpt-6.1-sol | Codex CLI | 23 | 4 | 8 | 7 |
| gpt-6-astra | Codex CLI | 8 | 3 | 4 | 3 |
| gpt-6-astra | our harness | 6 | 1 | 4 | 3 |
| Muse Wonder | mini-SWE-agent | 6 | 4 | 3 | 2 |
| Muse Wonder | our harness | 2 | 1 | 0 | 1 |
| All frontier runs | | 57 | 18 | 23 | 20 |

**How the papers were chosen.** We preselected 24 papers from all three tiers, half that at least one of our four agents (the open agents below) had reproduced and half that none had, so that the two cases can be read separately.

- On the 12 papers that an open agent had reproduced, the frontier runs reproduce 14 of 33, against 23 and 20 for DeepSeek-V4-Flash and Muse Spark 1.2.
- On the 12 papers where all four open agents had failed, 4 of the 24 frontier runs succeed, and they reproduce 2 papers that no open agent had.

**Runs where only the harness differs.** gpt-6.1-sol finished the same 11 papers in both harnesses, with every other setting as in the main runs. It reproduces 4 in our harness and 3 in Codex CLI, with the same verdict on 8 of the 11, so the two harnesses differ by one reproduced paper.

Of the three harnesses you suggested, we ran Codex CLI and mini-SWE-agent. We did not evaluate Claude Code because our auditor is Claude Sonnet 5, and an auditor grading a model from its own family could be biased. Including it would require an independent auditor from another provider, validated against human grades as in Appendix D, which we leave to future work.

**Whether the failure modes and findings change.**

Two of our findings carry over to the frontier models, and the main failure mode changes. Run remains the easiest tier (11 of 18, against 3 of 20 at Retrain and 4 of 19 at Reimplement), and most of the GPU grant again goes unused. The main cause of failure becomes stopping early, and reporting a number without a valid measurement becomes less common. Retrain and Reimplement are close here because the sample holds equal numbers of reproduced and unreproduced papers in every tier, and DeepSeek-V4-Flash is level on these papers as well (6 of 20 and 6 of 19).

Interestingly, the frontier models stop even earlier than the open agents. Over the 57 runs, the median frontier run used 5.6% of its GPU grant, against 14.3% for the open agents on the same papers, and the frontier runs that did not reproduce used 2.1%. To test the effect further, we ran a variant that prompts Codex to continue, up to three times, whenever it stops before using half of its GPU grant. On 3 papers it spent more of its grant and received the same scores as the unprompted runs (8, 8 and 7).

To find the reason, we analysed the full transcripts of the 39 failing frontier runs (Appendix G.3). 27 of the 39 never ran the paper's experiment at full scale, and they decided this early, at a median of turn 9:

- 12 stopped because the code, checkpoint or data they needed is not released, 8 of them at Reimplement, the tier where the agent writes that code.
- 6 timed a short probe, projected a cost above the grant and stopped. On 2506.08898 (32 H100-hour grant), three runs projected 33 to 51 hours of retraining and stopped, while Muse Spark 1.2 and Muse Wonder in our harness retrained the model within the grant and reproduced the claim (Section 5.3).
- 5 evaluated a different released checkpoint, and 4 hit build or launch errors.

The other 12 ran the experiment and missed the number. For 11 of the 27, an open agent given the same task text kept working and reproduced the paper, so these papers were within reach of the grant. Failures that report a number without a valid measurement fall to 8 of 39 = 21%, against 110 of 300 = 37% for the open agents, and 14 of 39 = 36% end before producing a number, against 44 of 300 = 15% (46% and 23% for the open agents when Claude Sonnet 5, the same annotator, labels a sample of 50 of their runs).
