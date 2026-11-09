**W2: Agent-writable logs without an integrity check.**

The harness does keep an external log, and we have now checked every graded run against it. Besides the two logs in the agent's workspace, the harness (the program that runs the agent) writes every command to a second transcript on the host, outside the sandbox, where the agent cannot reach it. Comparing the workspace logs with this transcript over all 372 graded runs found one edited log, and the edit did not raise that run's score.

Your reading of the submission is correct for the two workspace files. The harness writes commands.log and trajectory.jsonl into each run's evidence directory, the folder the auditor reads, and the sandbox mounts that folder read-write. Appendix A now reads:
> "The auditor traces every number to the command that produced it. Because the agent could edit these two files, we compared every logged entry with the transcript the harness writes on the host, outside the sandbox."

*The comparison.* We matched each of the 45,861 entries that agent commands produced in the two files against the host transcript, requiring the same command and return code and, for GPU jobs, the same cost and remaining GPU-hour budget. Of these, 45,673 match exactly. The other 188 are bookkeeping differences in four groups (Appendix A):

| Group | Entries |
| :- | -: |
| Calls the harness refused, which have no cost line | 100 |
| Remaining budget differs by at most 0.00015 GPU-hours | 60 |
| First attempts of a call the agent then retried | 25 |
| Budget logged before the GPU release charge, same cost, differs by at most 0.0003 GPU-hours | 3 |

*Edits.* A search of every agent command for writes to the two files found one. On 2510.25146, MiniMax-M2.7 replaced commands.log with its own notes through a write_file call, and the auditor scored that run 1 of 10, the rubric's grade for an unverifiable run. The 3 entries in the last group are all in trajectory.jsonl, and no run wrote to that file.

*Omissions.* Two early-return code paths left 119 commands in 65 runs out of commands.log. The host transcript holds all 119, and Appendix A reports them.

The host transcript is not hash-chained. It is protected by lying outside every directory the sandbox mounts, so the comparison catches any edit made through the agent's commands, and Appendix A states this.
