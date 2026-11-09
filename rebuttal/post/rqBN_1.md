Thank you for checking how runs are graded and how their logs are protected. For your points the revision adds:
- Appendix D (W1): the confusion matrix of the auditor against the human verdict, precision and recall overall and per tier, agreement on the full 0 to 10 scale, and agreement on integrity flags.
- Appendix A (W2): a description of the logs that matches the code, and a comparison of every agent-writable log entry with a transcript kept on the host.
- Section 5.3 and Limitations (Q1): the papers reproduced by at least one agent per tier, and a re-execution of missed runs with new seeds.
- Appendix E (Q2): a check of each paper's frozen target against the paper by a model from another lab.

**W1: Validation of the auditor.**

Appendix D now reports each measure this point lists. The auditor (Claude Sonnet 5) and a human graded the same 372 runs, and a run counts as reproduced at a score of 8 or higher.

*Precision and recall.* On the reproduced verdict the auditor's precision is 64/73 = 88% and its recall is 64/83 = 77%, which gives the F1 of 0.82. The five-by-five confusion matrix is in Appendix D and in our reply to Reviewer T29u (Q1).

*Errors by tier.* The tiers do not differ beyond sampling error: Run recall is 80% (95% Wilson interval 64% to 90%) and Reimplement recall is 69% (44% to 86%).

| Tier | Precision | Recall | F1 |
| :- | -: | -: | -: |
| Run (code, data and weights released) | 28/31 = 90% | 28/35 = 80% | 0.85 |
| Retrain (no weights) | 25/29 = 86% | 25/32 = 78% | 0.82 |
| Reimplement (no code) | 11/13 = 85% | 11/16 = 69% | 0.76 |

In every tier the auditor's misses outnumber its false positives (7 against 3, 7 against 4, 5 against 2), so its errors lower the reported rates.

*The full 0 to 10 scale.* The auditor and the human give the same score to 253 of the 372 runs and scores within one point to 324, with a mean absolute difference of 0.59 points and a quadratic weighted kappa of 0.89.

*Anti-cheat flags.* A high-severity integrity flag, such as a number copied from the paper, forces a score of 0. The human placed 46 runs at 0 and the auditor 53. They agree on 42 of the 57 runs that either placed there, the auditor alone flagged 11 and the human alone 4.

*Multi-human adjudication.* Three graders divided the 396 runs that started, so each run has one human label, given under the same rubric and blind to the auditor's score. This design does not measure agreement between humans, and Appendix D now says so beside the F1.
