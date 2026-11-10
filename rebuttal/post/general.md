We thank the three reviewers for their careful reading. They found the task important and the evaluation design unusually careful (T29u), the design sound and reusable (YGTR), and the methodological disclosure excellent (rqBN). The revision adds these analyses:
- **Frontier models in production harnesses** (Section 5.1, Appendix B). gpt-6.1-sol reproduces [4 of 11] papers in our loop and [2 of 18] in Codex CLI, where the submitted runs of DeepSeek-V4-Flash reproduce [4 of 11] and [6 of 18] of the same papers.
- **Uncertainty** (Section 5.2). Every rate has a 95% Wilson interval, and three runs of DeepSeek-V4-Flash on 12 papers give the same verdict on [k] of the 12.
- **Auditor validation** (Appendix D). Against a human grade on 372 runs, the auditor's reproduced verdict has precision 88% and recall 77%.
- **Log integrity** (Appendix A). Of the 45,861 entries in the agent-writable logs, 45,673 match a transcript kept on the host exactly, and the other 188 differ only in bookkeeping.
- **Targets and tolerance** (Appendices E and F). A check by a model from another lab supports 92 of the 100 frozen targets, the other 8 are corrected, and Reimplement stays the lowest tier at every tolerance from 1% to 10%.
- **Failures outside the agent** (Sections 5.2 and 5.3). Removing every build failure moves no best-agent rate by more than one percentage point.

With every new grade applied, 70 of the 400 agent-paper cells are reproduced (73 at submission), the best agent reproduces 38% of Run, 27% of Retrain and 15% of Reimplement papers, and the ordering of the tiers is unchanged.
