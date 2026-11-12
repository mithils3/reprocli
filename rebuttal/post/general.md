We thank the three reviewers for their careful and constructive reviews. They found the task important and the evaluation design unusually careful (T29u), the design sound and reusable (YGTR), and the methodological disclosure excellent (rqBN). Following the reviews, the revision adds these analyses:
- **Frontier models in production harnesses** (Section 5.1, Appendix B). gpt-6.1-sol reproduces [5 of 12] papers in our loop and [4 of 23] in Codex CLI, where the submitted runs of DeepSeek-V4-Flash reproduce [4 of 12] and [8 of 23] of the same papers.
- **Uncertainty** (Section 5.2). Every rate has a 95% Wilson interval, and a second, independent run of Muse Spark 1.2 on 10 Reimplement papers reaches the same reproduced verdict on 9 of the 10.
- **Auditor validation** (Appendix D). Against a human grade on 372 runs, the auditor's reproduced verdict has precision 88% and recall 77%.
- **Log integrity** (Appendix A). During each run the harness sends every tool call to a database outside the cluster, which the sandbox cannot reach. The 30,790 commands present in both that record and the agent-writable logs have the same text, and no exit code differs. The harness now mounts both logs read-only inside the sandbox.
- **Targets and tolerance** (Appendices E and F). A check by a model from another lab supports 92 of the 100 target values, the other 8 are corrected, and Reimplement stays the lowest tier at every tolerance from 1% to 10%.
- **Failures outside the agent** (Sections 5.2 and 5.3). Removing every build failure moves no best-agent rate by more than one percentage point.

With every new grade applied, 70 of the 400 agent-paper cells are reproduced (73 at submission), the best agent reproduces 38% of Run, 27% of Retrain and 15% of Reimplement papers, and the ordering of the tiers is unchanged.

We would be glad to answer further questions.
