We thank the three reviewers for their careful and constructive reviews. They found the task important and the evaluation design unusually careful (T29u), the design sound and reusable (YGTR), and the methodological disclosure excellent (rqBN). Following the reviews, the revision adds these analyses:
- **Frontier models in production harnesses** (Section 5.2, Appendix B.3). Pooled over 57 runs of gpt-6.1-sol, gpt-6-astra and Muse Wonder in our harness, Codex CLI and mini-SWE-agent, 18 are reproduced, where DeepSeek-V4-Flash and Muse Spark 1.2 reproduce 23 and 20 on the same papers, half of which were sampled because one of our four agents had reproduced them.
- **Uncertainty** (Section 5.2). Every rate has a 95% Wilson interval, and repeated runs keep the reproduced verdict on 23 of 27 model and paper pairs, including 9 of the 10 Reimplement papers that Muse Spark 1.2 ran a second time.
- **Auditor validation** (Appendix D). Against a human grade on 372 runs, the auditor's reproduced verdict has precision 88% and recall 77%.
- **Log integrity** (Appendix A). During each run the harness sends every tool call to a database outside the cluster, which the agents have no credentials to access. The 30,790 commands present in both that record and the agent-writable logs have the same text, and no exit code differs. To be sure, the harness now also mounts both logs read-only inside the sandbox.
- **Targets and tolerance** (Appendices E and F). We used gpt-6.1-sol to check every target value against its paper. It supports 92 of the 100, and the other 8 are corrected. Reimplement stays the lowest tier at every tolerance from 1% to 10%.
- **Failures outside the agent** (Sections 5.2 and 5.3). Removing every build failure moves no best-agent rate by more than one percentage point.

**Grade changes since submission.** Three changes take the reproduced cells from 73 to 70 of 400:

| Change | Cells | Reproduced cells |
| :- | :- | -: |
| Corrected targets (Appendix E) | DeepSeek-V4-Flash and MiniMax-M2.7 on 2505.23747 | -2 |
| Checkpoint check (Section 5.2) | Muse Spark 1.2 on 2508.21046, MiniMax-M2.7 on 2505.12677 | -2 |
| Two audits that had not returned | Muse Spark 1.2 on 2503.23035 (reproduced) and 2510.08177 (partial) | +1 |

The best agent then reproduces 13 of 34 Run, 9 of 33 Retrain and 5 of 33 Reimplement papers, the ordering of the tiers is unchanged, and papers reproduced by at least one agent go from 34 to 32.

We would be glad to answer further questions.
