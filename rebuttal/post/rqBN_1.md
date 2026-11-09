Thank you for checking how runs are graded and how their logs are protected.

**W1: Validation of the auditor.**

Appendix D now reports each measure you list, on the 372 runs graded by both the auditor (Claude Sonnet 5) and a human.
- *Precision and recall.* On the reproduced verdict they are 64/73 = 88% and 64/83 = 77% (F1 0.82), and the appendix gives the full confusion matrix.
- *By tier.* Precision and recall are 90% and 80% at Run, 86% and 78% at Retrain, and 85% and 69% at Reimplement. In every tier the auditor's misses outnumber its false positives, so its errors lower the reported rates.
- *Full 0 to 10 scale.* The two give the same score to 253 of the 372 runs and differ by at most one point on 324 (quadratic weighted kappa 0.89).
- *Anti-cheat flags.* A high-severity flag forces a score of 0. The two agree on 42 of the 57 runs that either placed there, the auditor alone flagged 11 and the human alone 4.
- *Human labels.* Each run was labelled by one of three human graders, under the same rubric and blind to the auditor's score.

**W2: Agent-writable logs without an integrity check.**

The concern is sound. The harness writes commands.log and trajectory.jsonl into the folder the auditor reads, and the sandbox mounts that folder read-write, so we ran an analysis to find out whether any agent used this. The harness also writes every command to a transcript on the host, outside the sandbox, and we compared the two files with it over all 372 graded runs. Of the 45,861 entries that agent commands produced, 45,673 match exactly on the command, the return code and, for GPU jobs, the cost and remaining budget. The other 188 are bookkeeping differences that Appendix A lists by group. A search of every agent command for writes to the two files found one, on a run the auditor had already scored 1 of 10 as unverifiable. The current agents therefore left the logs alone in 371 of 372 runs, and making the logs tamper-proof is future work.

**Q1: A stratified human-expert reproduction baseline.**

The revision gives a lower bound on that baseline per tier. At least one of the four agents reproduced 32 of the 100 papers (95% Wilson interval 24% to 42%): 16 of 34 at Run, 11 of 33 at Retrain and 5 of 33 at Reimplement. These papers are reproducible in the same environment and budgets, and the best single agent reaches 13, 9 and 5 of them. To test whether misses come from the environment, we re-ran the final commands of 3 partial runs with two new seeds and no agent (Section 5.3). On 2505.17836 both seeds miss by the same amount as the agent's run (0.0400 and 0.0393 against 0.0395, target 0.05), and on 2510.07501 the seeds differ by more than the original miss. [On 2506.10351 the new seeds gave x and y.] Each task is also anchored to the authors' own reported result, which is an expert result on the same artifacts, and a separate expert pass over the 100 papers would need up to 2,552 H100-hours.

**Q2: How claims, targets and tolerances were validated, and annotator agreement.**

The revision adds an independent check of every target. OpenAI's gpt-6.1-sol, from a different lab than our auditor, compared each frozen target with its paper and quoted the passage behind each answer. The paper supports the value for 92 of the 100 claims, the metric for 95, the dataset and split for 76, and the method or variant for 69 (Appendix E). Correcting the other 8 values and rescoring their runs changes two verdicts, both on 2505.23747. Before the freeze, one author reviewed every extracted field. For tolerances, 58 of the 62 point-estimate claims use the default 5% and 4 use the margin their paper states. Rescoring every run at 1%, 2%, 5% and 10% gives the best agent 9, 12, 14 and 14 of the 34 Run papers, and Reimplement stays the lowest tier at each (Appendix F).
