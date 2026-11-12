Thank you for the thoughtful review and for your kind words about the methodological disclosure.

**W1: Validation of the auditor.**

We compared the auditor (Claude Sonnet 5) with human grades on 372 runs. Three human graders scored the runs, one grader per run, without seeing the auditor's score. On the reproduced verdict, the auditor's precision is $\frac{64}{73}$ = 88% and its recall is $\frac{64}{83}$ = 77% (F1 0.82). When the two disagree, the LLM auditor tends to be the stricter one. Of the 28 runs that only one of them marked as reproduced, 19 were from the human grader and 9 from the LLM auditor. On the full 0 to 10 scale, the two differ by at most one point on 324 of the 372 runs (quadratic weighted $\kappa$ = 0.89). For the anti-cheat flags, where a high-severity flag sets a run's score to 0, 57 runs received a 0 from at least one grader, and both graders gave a 0 to 42 of them (full matrix in Appendix D).

**W2: Agent-writable logs without an integrity check.**

Our harness wrote commands.log and trajectory.jsonl into a folder that the sandbox mounted read-write, so we checked whether any agent had modified them. During each run, the harness also sends every tool call to a database outside the cluster. The sandbox holds no credentials for this database, and the database stamps each row with its own clock. Across the 372 graded runs, the 30,790 commands present in both the logs and the database have the same text, no exit code differs, and their timestamps agree within 9 seconds. The only entries found on one side are 221 calls that ended without an exit code (mostly because no GPU could be allocated) and 79 timed-out attempts. In one run the agent overwrote commands.log, which the database shows, and the auditor had already scored that run 1 out of 10. Still, to prevent this, the harness now mounts both files read-only inside the sandbox (Appendix A).

**Q1: A stratified human-expert reproduction baseline.**

We agree that a human-expert reproduction would be the gold-standard baseline. However, the cost of this would be very high. For example, in PaperBench, ML PhDs reached 41.4% of the replication rubric after 48 hours of work on a paper. At 48 hours per paper, our 100 papers would take about 4,800 expert-hours, which is more than we are able to provide. To still address this point, our revision reports what we can measure in its place:

- **Papers known to be reproducible.** At least one of our four agents reproduced 32 of the 100 papers (95% interval 24% to 42%): 16 of 34 at Run, 11 of 33 at Retrain and 5 of 33 at Reimplement. These papers are therefore reproducible in the same environment and budget.
- **Expert targets.** Each target is technically an expert result already, since it is the number that the paper's own authors reported from the same code and data.
- **Agent results rerun by us.** To confirm that the numbers the agents report are what their code produces, we reran the final commands of 3 partial runs ourselves, with two new seeds and without the agent (Section 5.3). On two papers our reruns repeat the agent's number (on 2506.10351, 93.65% and 94.15% against the agent's 94.19%). On the third, 2510.07501, the result varies across seeds by more than the agent's original miss.

**Q2: How claims, targets and tolerances were validated, and annotator agreement.**

The revision adds an independent check of every target. We asked another model, gpt-6.1-sol, to compare each target value with its paper and to quote the passage behind each answer. It confirmed our value for 92 of the 100 claims (Appendix E), which is the agreement between our targets and an independent reader. When we correct the other 8 targets and rescore their runs, only two verdicts change, both on 2505.23747. Before the dataset was frozen, one author also reviewed every extracted field. For tolerances, 58 of the 62 point-estimate claims use the default of 5%, and the other 4 use the margin stated in their paper. When every run is rescored at 1%, 2%, 5% and 10%, Reimplement keeps the lowest reproduction rate: the best agent reproduces 4, 5, 5 and 5 of its 33 papers, against 9, 12, 14 and 14 of 34 at Run (Appendix F).

We are happy to answer any follow-up questions. Thank you again for the review.
