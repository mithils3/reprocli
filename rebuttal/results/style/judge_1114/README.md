# Blind ranking and audit of the reply to Reviewer 3 (2026-11-14)

Asked by Mithil on 2026-11-14 before posting. 37 agents in one workflow (`workflow.js`).

Comparison set: 240 ICLR 2025 threads from the style corpus (120 where the reviewer moved from 5 or lower to 6 or higher, 120 where the reviewer replied and stayed at 5 or lower), drawn with seed 22528 from the 418 threads whose first-round author reply is 1,500 to 22,000 characters. Each packet holds the review and the authors' first-round reply (posts before the first reviewer follow-up), plus the general response as context. Ratings and sub-scores are stripped, score-change sentences are redacted, and file names are random ids (`build.py`, `key.json`).

Blind rank: 30 Claude Haiku 5.5 judges, each with 4 raised threads, 4 unchanged threads and our reply (two comments of 4,834 and 4,876 characters, the text of commit a1f8df7), in shuffled order. Judges did not know that one reply was special or how any thread ended.

Result (`analysis.txt`, from `analyze.py` over `result.json`):
- Validity: the judges' overall score separates raised from unchanged threads with AUC 0.685 (probability-convinced 0.681, rank 0.689). The scores carry some signal about the real outcome, and the signal is modest.
- Ours ranks first of nine in 27 of 30 shards and second in the other 3. Mean overall 8.8 of 10 (raised threads 6.25, unchanged 5.24), above 98% of the 240 real replies.
- By dimension: evidence 9.77 (above every real reply's shard mean but one), coverage 9.0 (94%), tone 8.37 (97%), clarity 6.17 (53%, below the raised threads' 6.51).
- All 30 judges name density as the biggest weakness, and 23 of 30 name the absence of Claude Code.

Limits: the judges are Claude models and the reply was written with Claude, so a preference for its style cannot be ruled out; the judges reward evidence volume, which the reply has more of than a typical 2025 reply; the comparison threads are a year older and on a 10-point scale.

Head to head (3 Fable judges, ours against 5 of the 15 top-scored real replies each, blind): ours ranks 1st, 2nd and 1st of six, and all three expect a reviewer just below the line to move.

Audits (Fable, not blind): `audit_reviewer.md` reads as Reviewer YGTR (would move from 2 to 3 "by a small margin"; the deciding risk is whether early stopping is read as caused by the task text) and `audit_ac.md` reads as the area chair across all five replies. Pointer check (2 Haiku workers): 33 number-and-pointer pairs, 1 problem (the 2506.08898 sentence against Section 5.3).

Edits applied after the audits are listed in rebuttal/STATUS.md under 2026-11-14 11:40.
