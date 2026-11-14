We thank the three reviewers for their careful and constructive reviews. They found the task important and the evaluation design unusually careful (T29u), the design sound and reusable (YGTR), and the methodological disclosure excellent (rqBN). Following the reviews, the revision adds these analyses:
- **Frontier models in production harnesses** (Section 5.2, Appendix B.3). Pooled over [57] runs of gpt-6.1-sol, gpt-6-astra and Muse Wonder in our harness, Codex CLI and mini-SWE-agent, [18] are reproduced, where DeepSeek-V4-Flash and Muse Spark 1.2 reproduce [23] and [20] on the same papers, half of which were sampled because an open agent had reproduced them.
- **Uncertainty** (Section 5.2). Every rate has a 95% Wilson interval, and a second, independent run of Muse Spark 1.2 on 10 Reimplement papers reaches the same reproduced verdict on 9 of the 10.
- **Auditor validation** (Appendix D). Against a human grade on 372 runs, the auditor's reproduced verdict has precision 88% and recall 77%.
- **Log integrity** (Appendix A). During each run the harness sends every tool call to a database outside the cluster, which the sandbox cannot reach. The 30,790 commands present in both that record and the agent-writable logs have the same text, and no exit code differs. The harness now mounts both logs read-only inside the sandbox.
- **Targets and tolerance** (Appendices E and F). A check by a model from another lab supports 92 of the 100 target values, the other 8 are corrected, and Reimplement stays the lowest tier at every tolerance from 1% to 10%.
- **Failures outside the agent** (Sections 5.2 and 5.3). Removing every build failure moves no best-agent rate by more than one percentage point.

**Grade changes since submission.** Counts in our replies that are marked "at submission" use the 73 reproduced cells of the submitted paper. The revision applies three changes to them:

| Change | Cells | Reproduced cells |
| :- | :- | -: |
| Submission | | 73 of 400 |
| Corrected targets (Appendix E) | DeepSeek-V4-Flash and MiniMax-M2.7 on 2505.23747 (Run) | -2 |
| Checkpoint check (Section 5.2) | Muse Spark 1.2 on 2508.21046 (Retrain), MiniMax-M2.7 on 2505.12677 (Reimplement) | -2 |
| Two audits that had not returned | Muse Spark 1.2 on 2503.23035 (Run, reproduced) and 2510.08177 (Reimplement, partial) | +1 |
| Revision | | 70 of 400 |

The best agent then reproduces 13 of 34 Run papers (38%), 9 of 33 Retrain papers (27%) and 5 of 33 Reimplement papers (15%), and the ordering of the tiers is unchanged. Papers reproduced by at least one agent go from 34 to 32. Three analyses use the grades at submission: the auditor validation (Appendix D), the tolerance tables (Appendix F) and the failure-mode labels (Appendix G).

We would be glad to answer further questions.
