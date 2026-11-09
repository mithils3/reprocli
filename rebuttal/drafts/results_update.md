# Results update draft for the general reply, ICLR 2027 submission 22528 (RECLAIM)

Post under the general reply on Monday 2026-11-16. Slots in square brackets are filled from the files in the fill map. The fill map is not posted.

### Results update (one part, 3122 characters)

**Results update (all reviewers)**

These are the runs that our earlier replies said we would report, and each block names the reviewer point it answers.

**Frontier models and harnesses (YGTR W1 and Q1)**
[Result sentence: gpt-6-astra in Codex CLI reproduced a of 8 papers, gpt-6.1-sol b of 12 in our loop and c of n in Codex CLI, and Muse Wonder d of m in our loop and g of h in mini-SWE-agent], with 95% Wilson intervals in the table. A run that reached its time limit counts as not reproduced.

| Agent | Harness | Papers | Reproduced | Rate (95% interval) |
| :- | :- | :- | :- | :- |
| gpt-6-astra | Codex CLI | 8 | [a] | [rate, lo, hi] |
| gpt-6.1-sol | our loop | 12 | [b] | [rate, lo, hi] |
| gpt-6.1-sol | Codex CLI | [n] | [c] | [rate, lo, hi] |
| gpt-6.1-sol | Codex CLI with continue prompts | [p] | [q] | [rate, lo, hi] |
| Muse Wonder | our loop | [m] | [d] | [rate, lo, hi] |
| Muse Wonder | mini-SWE-agent | [h] | [g] | [rate, lo, hi] |

**Harness and continue prompts (YGTR W1 and Q1)**
[Harness sentence: on the 12 papers both harnesses ran, the paired difference is k papers for gpt-6.1-sol (exact McNemar p = x), which is within / larger than the change between repeated runs of DeepSeek-V4-Flash on the same 12 papers (repeat runs, below).] [With continue prompts after an early stop, gpt-6.1-sol in Codex CLI reproduced q of p papers, against c of n without them (difference k papers, 95% interval [lo, hi]).]

**Budget and failure modes (YGTR W1)**
[Budget sentence: the frontier runs used a median of u% of their GPU grant.] [Failure-mode sentence with the final counts: on f1 of the f failing frontier runs the main failure falls in the same Appendix G modes as the open agents', and the n0 runs that never launched an experiment are on the two Reimplement papers that released no code.] The most common failure is the main failure in [k] of the [f] failing frontier runs. [Muse Wonder d of m against Muse Spark 1.2 e of m] (95% interval for the difference [lo, hi]).

**Scope of the findings (YGTR W1, continued)**
The tier ordering and the most common failure are what we test on the frontier runs of [gpt-6-astra, gpt-6.1-sol and Muse Wonder] [outcome], with the share of papers following the ordering at [r%, lo, hi].

**Repeat runs (T29u W1, YGTR W3)**
[Its verdict was the same in all three runs on k of 12 papers (95% interval [lo, hi]), so run-to-run variation moves the best Run rate by at most j papers, and the ordering Run, Retrain, Reimplement held in every run / held in j of 3 runs.]

**Seeds on 2506.10351 (rqBN Q1)**
On 2506.10351 (Run), the target is 93.12 and the original run measured 94.19, [and the new seeds gave x and y, so the miss repeats without the agent / falls inside seed variation], a range of [lo, hi] across the three values.

**Reruns of cells outside the agent (YGTR W2 and Q3)**
[We reran the 4 cells of 2510.20725 with the same settings, and r of them reproduce] ([rate, lo, hi]). The frontier runs use the same environment, and [their results].

The revised PDF gives all of these in Section 5.1, Section 5.2 and the new appendix section on frontier agents.

### Fill map (not posted)

| Slot | Source file or job id | Line in replies.md | Ready (forecast) |
| :- | :- | :- | :- |
| Result sentence, table rows a, b, c, d, g (n, m, h) | rebuttal/results/databook/frontier_cells.csv; rebuttal/results/frontier/grades.jsonl | 240 (also 12, 229, 236) | 11-15 18:00 cutoff; per-run finish is not scheduled before it |
| Continue-prompt row (p, q) | arm codex-gpt-6.1-sol-nudge in frontier_cells.csv | none (new slot) | 11-15 18:00 cutoff; not in the forecast |
| Harness sentence (k, x) | frontier_cells.csv; McNemar script | 240 | 11-15 18:00 cutoff |
| Budget sentence (u) | rebuttal/results/frontier/run_usage.csv | 240 | 11-15 18:00 cutoff |
| Failure-mode sentence, [k], [f], Muse Wonder against Muse Spark 1.2 | rebuttal/results/frontier/failure_modes.csv and never_launched_check.md (11-09: 26 coded, 21 in the open agents' modes, 5 never launched on 2505.16927 and 2503.14698, 3 reimplement-without-validating); frontier_cells.csv | YGTR part 1, failure-mode paragraph | 11-15 18:00 cutoff |
| Scope outcome and model list | frontier_cells.csv | 268 | 11-15 18:00 cutoff |
| Repeat runs (k, j, lo, hi) | jobs 3540624 to 3540632 | 52, 264 | 11-12 01:31 (Slurm start 11-10 01:31 plus 48 h limit; 3540624 by 11-10 20:43) |
| Seeds on 2506.10351 (x, y) | jobs 3558022, 3558023; rebuttal/results/e10/results.md | 180 | 11-10 04:21 |
| Reruns of 2510.20725 (r) | jobs 3540631 (DeepSeek-V4-Flash), 3540633 (MiniMax-M2.7), 3540786 (Qwen3.6-27B) and the Muse Spark 1.2 rerun, rebuttal/results/sweeps/jobs.csv | YGTR part 3 | 11-12 01:31 (3540786 by 11-10 20:40) |
| Frontier runs in the same environment (their results) | frontier_cells.csv; rebuttal/results/e8/x86 | 258 | 11-15 18:00 cutoff |
