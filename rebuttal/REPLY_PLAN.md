# Reply plan, ICLR 2027 submission 22528 (RECLAIM)

Reviews: Reviewer 1 (T29u) 3, Reviewer 2 (rqBN) 3, Reviewer 3 (YGTR) 2 (4-point scale). The posted replies keep the OpenReview IDs, since that is how reviewers see each other. Replies are in `rebuttal/drafts/replies.md` (rewritten 11-09, the earlier draft is `rebuttal/drafts/replies_pre_fable_2026-11-09.md`), the paper text for each change is in `rebuttal/drafts/paper_revision_text.md`, and the decisions are in `rebuttal/mithil/decisions_monday.md`.

## When we post

| Day | What goes up |
| :- | :- |
| Thu 11-12 | Wave 1: Reviewer 1 (2 parts) and Reviewer 2 (3 parts) |
| Sat 11-14 | Wave 2: Reviewer 3 (3 parts), the general reply, and the revised PDF |
| Mon 11-16 | Results update with the runs that finished after the waves |
| Wed 11-18 | Discussion closes. Runs stop at Sun 11-15 18:00. |

Proposed change, needs Mithil's yes: post Reviewer 3 and the general reply on Thu 11-12 with wave 1, using the frontier rows graded by then, and post the remaining rows as a short update on Sat 11-14 with the PDF. Reviewer 3 holds the only score below the accept line, and under the current dates gets four days to read and respond, the fewest of the three. The reply already stands on graded rows (40 on 11-09: gpt-6.1-sol 4 of 11 in our loop and 2 of 15 in Codex CLI, against 4 of 11 and 6 of 15 for DeepSeek-V4-Flash on the same papers), and a second author post with new numbers is one of the features that goes with raised scores in the iclr-review corpus (rule 18).

Every post stays under 4,800 characters. An unfinished result stays a bracketed slot, and `export_replies.py` will not mark a part READY while it holds one. A slot still open on its posting day is cut or moved to the next post. On 11-09 three parts are READY (T29u part 2, rqBN parts 1 and 2).

## What changed in the 11-09 rewrite

| Reply | Change | Why |
| :- | :- | :- |
| General | Each bullet carries its main number. | The earlier version listed changes and sent the reader to the reviewer replies for every number. |
| T29u W1 | Per-agent, per-tier table with intervals and an "at least one agent" row; z tests between tiers; agent ranking stated as two pairs. | The reviewer asked whether rankings and tier comparisons survive one run per cell. The earlier answer said "the tiers keep their order" beside a table where Retrain's mean score exceeded Run's. The data separate Run from Reimplement (z = 2.46 and 2.81) and do not separate Run from Retrain (z = 0.96), which Section 5.2 of the submission already says. |
| T29u W2, Q1 | Direction of disagreement stated at the 7/8 line (15 against 7) and at score 0 (auditor alone 11, human alone 4). | The reviewer asked for an audit of disagreements; the direction is the finding. |
| T29u Q2, rqBN Q2 | Target answer opens with the 8 wrong values and the two changed verdicts; "55 of 100 pass all four" follows. | The earlier order led with the number that reads worst. |
| rqBN W1 | One labelled paragraph per item the reviewer listed. | The reviewer gave a list; each item is now findable. |
| rqBN Q1 | Opens with the papers reproduced by at least one agent as a lower bound on an expert baseline, then the re-execution, then the cost. | The earlier answer opened with a statistic that did not address the question until the second paragraph. |
| YGTR W1 | Frontier table gains mean score and the two best open agents on the same papers; a sentence on the fresh DeepSeek-V4-Flash runs; a row-free slot for the continue-prompt variant; the Claude Code reason. | The earlier table gave reproduced counts with nothing to compare them to, and did not say why Claude Code, the first harness the reviewer named, was left out. |
| YGTR W1 (part 2) | Failure-mode table, frontier beside open agents, with the grouped comparison (3 of 27 against 37%, and 46% under the blind coder). | The reviewer predicted the failure modes would change. The earlier answer said every label was an Appendix G mode, which the coder's fixed label set guarantees. The table shows what shifts and what does not. |
| YGTR W1 (part 2) | A paragraph on why the early stops are the models' judgment: the task prompt allows an early stop only when a trained artifact is neither released nor retrainable in the grant, and on 2506.08898 all 5 frontier runs stopped under one H100-hour while Muse Spark 1.2 retrained with 27 of 32 and reproduced. Median grant use 2.1% against 17.5%. | A reviewer can read the early stops as an effect of our prompt. The open agents had the same prompt. |
| YGTR W2 | Opens with "at most 14 of 372". | Direct answer to "how many failures are due to hardware". |
| YGTR Q2 | The 16 hand-read matches as a three-row table. | Shorter and easier to check. |
| T29u Q1, rqBN W1 | The 25 runs on opposite sides of the 7/8 line: 18 are one point apart. Quadratic weighted kappa 0.89 on the full scale. | Two checks by agents reading as each reviewer asked what the boundary disagreements look like and why the full-scale statistic was missing. |
| All | Tier definitions removed from the YGTR reply (the review states them); "the tiers keep their order" replaced by "Reimplement is the lowest tier" wherever it appeared. | Length, and the point above. |

## Changes to the paper

| # | Change | Where | Answers | What it still needs |
| -: | :- | :- | :- | :- |
| 1 | Frontier models (gpt-6.1-sol, gpt-6-astra, Muse Wonder) in production harnesses (Codex CLI, mini-SWE-agent) beside the thin harness, with DeepSeek-V4-Flash and Muse Spark 1.2 on the same papers | 5.1, 5.2, new subsection of App. B, Limitations | YGTR W1 | 40 of 58 planned runs graded; the rest wait on GPUs and stop by Sun 18:00 at the latest |
| 2 | 95% Wilson interval on every rate | 5.2, Table 5, Figure 4 | T29u, YGTR | Figure 4 rebuild with error bars |
| 3 | Repeat runs of DeepSeek-V4-Flash on 12 papers and a rule for ranking agents | 5.2, Limitations | T29u, YGTR | Repeat runs, due Thu morning at the latest |
| 4 | Mean audit score in place of "strongest agent"; agents ranked as two pairs | Intro, 5.2, Conclusion | T29u | Done |
| 5 | The 28 cells with no graded run, the two new grades, and the 20 reruns | 5.2, App. B, App. C | YGTR W2, Q3 | E8 reruns (one running, one starts Tue) |
| 7 | Scan for downloaded checkpoints | 5.2 | T29u, YGTR | Done |
| 8 | Auditor against human grades, with the confusion matrix and the direction of disagreement | Section 4, App. D | T29u Q1, rqBN | Done |
| 9 | Writable logs and the log comparison | App. A | rqBN | Done |
| 10 | What Stage III checked, and the AI-use statement | App. E | rqBN | Done |
| 11 | Every frozen target checked against its paper (8 wrong values corrected) | App. E | T29u Q2, rqBN Q2 | Done |
| 12 | Tolerance table | App. F | T29u Q2, rqBN | Done |
| 13 | Bound on build failures from the aarch64 hardware | 5.3 | T29u, YGTR | Done |
| 14 | Missed runs re-executed with new seeds | 5.3, Limitations | YGTR, rqBN | E10 seeds, due Tue afternoon |
| 15 | Counts that change with the target corrections | across the paper | T29u, YGTR | Done (70 of 400, 13 of 34) |
| 16 | Scope of the claims | Limitations | YGTR | Done |
| 17 | Tier tests at the corrected counts: z = 2.46 and 0.96 replace 2.7 and 1.2; per-agent, per-tier table with the "at least one agent" row | 5.2 | T29u W1, rqBN Q1 | Text; numbers in `rebuttal/results/tiers/tier_tests.md` |
| 18 | Frontier failure modes beside the open agents', and the blind coder's calibration on 50 open-agent runs | 5.3, App. G | YGTR W1 | Text; numbers in `rebuttal/results/frontier/failure_modes.md` and `coder_calibration_groups.md` |

Item 6 (Appendix C, runs at score 0) is in the paper revisions but no reply promises it.

## Runs, in the order they matter

The ghx4 GPU queue is the limit on every arm: 41 GPU requests were pending on 11-09 13:26, all on priority. Nothing below needs a new launch.

1. Repeat runs of DeepSeek-V4-Flash (jobs 3540624 to 3540633). They fill T29u W1, YGTR W3 and the fresh-run baseline in YGTR W1, so three answers wait on them.
2. gpt-6.1-sol in Codex CLI on the 12 core papers (3 not graded) and gpt-6-astra in our loop (2 of 8 graded, 4 running). These complete the two paired harness comparisons.
3. E10 seeds on 2506.10351 and the E8 reruns of 2510.20725. Each fills one sentence.
4. Muse Wonder in mini-SWE-agent (2 graded, 2 waiting on GPUs) and in our loop (0 graded, 4 started on 11-06). The reply reads complete without these rows; they are added if graded.
5. gpt-6.1-sol in Codex CLI on the 12 extension papers. Our loop did not run these papers, so they add to one count and to no comparison.
6. The continue-prompt Codex variant. The two runs started on 11-07 still wait on GPUs, and the other six core papers were started in parallel on 11-09 13:41 (tmux `rb-codex-nudge-c` on gh-login04). The old dispatcher on gh-login01 is paused with SIGSTOP (pid 15878) so it cannot start those six a second time. A hostile read of the Reviewer 3 reply names this variant as the result most likely to move the score, because it tests whether the early stops survive being told to continue.
7. The two gpt-6-astra cells in Codex CLI that ended at the old 48-hour wall (2505.10475, 2504.20571) were restarted on 11-09 13:41 under the current rule (tmux `rb-codex-astra-rerun` on gh-login03). When a rerun is graded, the old run gets a VOID file and the rerun is the row of record.
8. The x86 arms on Delta. In the first pass 15 of 21 runs had a GPU request refused at submit ("job submit limit"), so the pass was stopped on 11-09 13:54 and every bundle except astra-x86-2505.16927-8dbd30 (no refusal, finished) carries a VOID file. Commit f7ca417 makes `run_gpu` resubmit a refused request every 2 minutes for up to 6 hours. Both arms were relaunched under the same tags at lower concurrency (7 and 6). The allocation expires Fri 11-13.

## Paper revision

First pass committed 11-09 (348e89b) and pushed to the Overleaf repo. It applies the drafted text of `paper_revision_text.md` and adds the tier tests at the corrected counts, the frontier baselines, the frontier failure-mode subsection (Appendix G.4), mean-score intervals in Table 5 and the rebuilt Figure 4 with intervals. The conclusion ends on page 10. Open: every red `\todo` slot (frontier arms, repeat runs, 2506.10351 seeds, 2510.20725 reruns, x86 arm), Figures 2, 5 and 6 and the dissection counts in Section 5.3, which are still at the submission counts, bib entries for the frontier models and Codex CLI, and the fixes from the page read and the adversarial review. `rebuttal/scripts/frontier_tex.py` regenerates the two frontier tables from the databook.

## Cut from the plan

- The author read of the 45 papers with a failed target question (rqBN part 3). Cut 11-09, since rqBN did not ask for it.
- The hash-chained host log, since no such log exists in the code.
- "The tiers keep their order" as a claim. Replaced 11-09 by the Run against Reimplement comparison.

## Decided on 11-09

- The `paper_latex/` edits for the revised PDF are approved ("yes"). Items 1 to 18 above go in, with slots for the results that have not landed.
- The two Codex gpt-6-astra cells that ended at the 48-hour wall with a GPU request pending (a54ff7 on 2505.10475, 9f613b on 2504.20571) are rerun under the current rule, which has no wall and stops at Sun 11-15 18:00. The reruns are the rows of record. His word was "whatever you think is the best"; a row that ended waiting in the queue measures the queue.
- The x86 arms: `run_gpu` is patched to wait and retry when Slurm refuses a GPU request, the papers whose runs never got a GPU are relaunched before the allocation ends on Fri 11-13, and a run with any refused or ungranted GPU request stays out of the replies.
- The weekly usage cap is 85% this week.

## Waiting on you

- Posting Reviewer 3 on Thu 11-12 (proposal above). Until you say yes the dates in the table stand.
- The Claude Code sentence in YGTR part 1, which gives both reasons (same-family auditor, API budget).
- A new laptop Anthropic key in `~/.bashrc.secrets`; the current one returns 401, so coding runs go through DeltaAI for now.
