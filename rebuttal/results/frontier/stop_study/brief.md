# Coding sheet: how each agent run ended

You code excerpts of AI-agent runs. Each run tried to reproduce one result of a machine-learning paper inside a sandbox with a GPU grant (H100-hours). Each excerpt gives the tier, the grant and how much was spent, the GPU commands, the last tool commands, and the last assistant messages ending with the FINAL message. You do not know which model produced a run or how it was graded; do not guess either, and ignore any model or tool name you see.

For EACH run in your shard write one JSON object on one line with exactly these keys:
- "rid": the run id, like "r017".
- "stop_reason": exactly one of
  - "claimed_done": the final message presents its result as the finished reproduction.
  - "shortfall_cost": it says the full experiment (training or evaluation at the paper's scale) was not completed because it would take too much time or compute, and reports a partial, reduced or diagnostic result instead.
  - "missing_artifact": it says a needed checkpoint, dataset or piece of code is not released or not available, and stops there.
  - "environment_block": a build, dependency, hardware or GPU-allocation failure it did not get past.
  - "handed_back": it ends by asking for instructions or by leaving the remaining work as next steps for someone else, with no cost or artifact reason given.
  - "limit": it ran out of GPU grant, context or time, or was cut off mid-work.
  - "other".
  If two apply, choose the one the final message gives as the main reason the work stopped.
- "admits_not_reproduced": true or false. True only if the final message itself says the claim was not reproduced or only partly reproduced.
- "reduced_scale": true or false. True only if the text says it ran fewer epochs, steps, samples, seeds or a smaller model than the paper's configuration.
- "estimates_full_cost": true or false. True only if a message gives a number for the time or GPU-hours the full experiment would need.
- "mentions_unused_budget": true or false. True only if a message mentions how much GPU grant remains or is unused.
- "lists_next_steps": true or false. True only if the final message lists work that would still be needed and that it did not do.
- "trained_model": true or false. True only if the GPU commands or messages show a training run of the paper's model (any scale), as opposed to evaluation only or nothing.
- "quote": at most 25 words copied exactly from the final message that best show the stop_reason.

Rules: strict booleans (true/false, never "maybe"); when the text does not show it, the answer is false. One line per run, every run in the shard, no other text in the file. Do not edit any other file. Use the Read tool on the shard (it is about 90,000 characters; read it in parts with offset and limit if needed), then Write the output file. Final reply: one line with the number of runs coded and the count of each stop_reason.
