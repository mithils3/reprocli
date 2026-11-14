# Why frontier runs stop early (2026-11-13)

Question: the frontier runs spend a median of 5.6% of their GPU grant against 14.3% for the open agents on the same papers. Why?

Data: the 57 pooled frontier runs (continue-prompt and x86 runs left out) and the 45 DeepSeek-V4-Flash and Muse Spark 1.2 runs on the same 24 papers, from the scrubbed transcripts in tools/anon_viewer/public/data.

Pass 1 (endings_coded.jsonl, sheet brief.md): 11 Claude Haiku 5.5 coders, each given 10 runs in mixed order with no model name, arm or grade, read the last messages and the GPU commands of each run and coded the stated reason for stopping. Among runs not reproduced: frontier 16 of 39 stop on a missing artifact (41%, 27% to 57%) against 6 of 30 open-agent runs (20%, 10% to 37%); frontier 12 of 39 present the result as finished (31%) against 17 of 30 (57%). Full tallies: summary.md.

Pass 2 (deep_all.json, sheet deep_brief.md): 13 coders, 3 runs each, read a condensed full transcript of each of the 39 failing frontier runs, again without model or grade. Reason the run did not reproduce: artifact not released 12 (8 at Reimplement, 3 at Retrain, 1 at Run; median 0.2% of grant), ran the experiment and missed 10 plus 2 coded other that also ran it, projected cost above the grant after a timed probe 6, evaluated a different released checkpoint 5, build or launch failure 4. So 27 of 39 did not run the paper's experiment at full scale; the decision turn has a median of 9 over the 24 runs with a stated decision. GPU trouble is given as a reason for stopping in 2 of 39 and a time or session limit in 1. The final report says plainly that the result was not reproduced in 33 of 39 (the other 6 final messages are cut off in the excerpt or do not say it).

Agreement: on "ran the experiment or did not", pass 1 and pass 2 agree for 37 of 39 runs.

Mechanical checks (frontier_cells.csv and the bundles): failing frontier runs take a median of 15 assistant turns and 55 tool calls, failing open-agent runs 91 and 102.5; 56 of 57 frontier runs end by the agent's own turn or submission and 1 by budget; frontier runs whose GPU requests waited 30 minutes or less spend a median of 6.5% of the grant (29 runs), the others 4.1% (28 runs); 28 of the 39 failing runs spent under 10% of the grant, and on 14 of those some open agent reproduced the paper; of the 27 runs of pass 2 that did not run the experiment, some open agent reproduced the paper on 11. By model: failing under 10% of grant, gpt-6.1-sol 18 of 35 runs, gpt-6-astra 8 of 14, Muse Wonder 2 of 8.

Projected costs in the six cost stops: 2506.08898 (grant 32): 33.2, 50.4 and 51 GPU-hours, where Muse Spark 1.2 (27.1 H100-h) and Muse Wonder in our harness (27.5 H100-h) retrained and scored 8; 2505.16927 (grant 32): 36 and 40; 2505.18809 (grant 8): about 480.

Limits: one LLM coder per run in each pass; the coders are Claude models; excerpts truncate long messages.
