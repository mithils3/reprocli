# Reply plan, ICLR 2027 submission 22528 (RECLAIM)

Reviews: Reviewer 1 (T29u) 3, Reviewer 2 (rqBN) 3, Reviewer 3 (YGTR) 2 (4-point scale). The posted replies keep the OpenReview IDs, since that is how reviewers see each other. Replies are in `rebuttal/drafts/replies.md`, the paper text for each change is in `rebuttal/drafts/paper_revision_text.md`, and the open choices are in `rebuttal/mithil/decisions_monday.md`.

## When we post

| Day | What goes up |
| :- | :- |
| Thu 11-12 | Wave 1: replies to T29u (2 parts) and rqBN (3 parts) |
| Sat 11-14 | Wave 2: reply to YGTR (3 parts), the general reply, and the revised PDF |
| Mon 11-16 | Results update with the runs that finished after the waves |
| Wed 11-18 | Discussion closes. Runs stop at Sun 11-15 18:00. |

Every post stays under 4,800 characters. An unfinished result stays a bracketed slot, and `export_replies.py` will not mark a part READY while it holds one. A slot still open on its posting day moves to the next post.

## Changes to the paper

| # | Change | Where | Answers | What it still needs |
| -: | :- | :- | :- | :- |
| 1 | Frontier models (gpt-6.1-sol, gpt-6-astra, Muse Wonder) in production harnesses (Codex CLI, mini-SWE-agent) beside the thin harness | 5.1, 5.2, new subsection of App. B, Limitations | YGTR W1 | 34 of 58 runs graded; the rest wait on GPUs and stop by Sun 18:00 at the latest |
| 2 | 95% Wilson interval on every rate | 5.2, Table 5, Figure 4 | T29u, YGTR | Figure 4 rebuild with error bars |
| 3 | Repeat runs of DeepSeek-V4-Flash on 12 papers and a rule for ranking agents | 5.2, Limitations | T29u, YGTR | Repeat runs, due Thu morning at the latest |
| 4 | Mean audit score in place of "strongest agent" | Intro, 5.2, Conclusion | T29u | Done |
| 5 | The 28 cells with no graded run, the two new grades, and the 20 reruns | 5.2, App. B, App. C | YGTR W2, Q3 | E8 reruns (one running, one starts Tue) |
| 7 | Scan for downloaded checkpoints | 5.2 | T29u, YGTR | Done |
| 8 | Auditor against human grades, with the confusion matrix | Section 4, App. D | T29u Q1, rqBN | Done |
| 9 | Writable logs and the log comparison | App. A | rqBN | Done |
| 10 | What Stage III checked, and the AI-use statement | App. E | rqBN | Done |
| 11 | Every frozen target checked against its paper (55 of 100 pass all four questions) | App. E | T29u Q2, rqBN Q2 | Decision 1: 10 or 8 corrected targets |
| 12 | Tolerance table | App. F | T29u Q2, rqBN | Done |
| 13 | Bound on build failures from the aarch64 hardware | 5.3 | T29u, YGTR | Done |
| 14 | Missed runs re-executed with new seeds | 5.3, Limitations | YGTR, rqBN | E10 seeds, due Tue afternoon |
| 15 | Counts that change if the target corrections enter | across the paper | T29u, YGTR | Follows decision 1 |
| 16 | Scope of the claims | Limitations | YGTR | Done |

Item 6 (Appendix C, runs at score 0) is in the paper revisions but no reply promises it.

## Cut from the plan

- The author read of the 45 papers with a failed target question (rqBN part 3). Cut 11-09, since rqBN did not ask for it.
- The hash-chained host log, since no such log exists in the code.

## Waiting on you

- The Monday decisions in `decisions_monday.md` (1, 2, 4 to 8, 10, 15, 18, 19, 20) and the 9 E7 items.
- A new laptop Anthropic key in `~/.bashrc.secrets`; the current one returns 401, so coding runs go through DeltaAI for now.
