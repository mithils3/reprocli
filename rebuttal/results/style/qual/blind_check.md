# Blind check of the qualitative features of author replies

**What this is.** Four readers each compared 10 ICLR 2025 threads where the reviewer moved from 5 or lower to 6 or higher ("raised") with 10 where the reviewer replied and stayed at 5 or lower ("unchanged"), and each proposed features of the authors' text that differed (reader_1 to reader_4 in this folder). The readers knew the outcomes, so their lists were merged into 15 yes/no tests (blind_coder_brief.md) and applied to the 361 threads no reader had seen: 204 raised and 157 unchanged. The coders (Claude Haiku, 36 shards of about 10 threads with both groups mixed) saw the review and the authors' text only, with scores, groups and reviewer follow-ups removed. Every answer other than "no" carries a verbatim quote, and 1,725 of 1,730 quotes occur in their thread file.

**How to read the table.** The gap is the raised share minus the unchanged share in percentage points, with a Newcombe 95% interval. For "asks the reviewer to spell out a criticism" it is 12/204 = 6% minus 37/157 = 24%, which gives -18. About 20 rows were tested, so one interval that excludes zero is expected by chance. Every gap is a correlation: authors with strong results can afford modest words.

| feature | raised | unchanged | gap (points) | 95% interval |
|---|---|---|---|---|
| asks_to_specify | 12/204 = 6% | 37/157 = 24% | -18 | -25 to -10 * |
| correction bare (of threads that correct the reviewer) | 85/148 = 57% | 84/113 = 74% | -17 | -28 to -5 * |
| location_only | 64/204 = 31% | 26/157 = 17% | +15 | +6 to +23 * |
| modest_size_word | 72/204 = 35% | 34/157 = 22% | +14 | +4 to +23 * |
| correction fixed (all threads) | 63/204 = 31% | 29/157 = 18% | +12 | +3 to +21 * |
| cited_paper_specifics (of threads citing a paper as evidence) | 118/160 = 74% | 73/119 = 61% | +12 | +1 to +23 * |
| correction bare (all threads) | 85/204 = 42% | 84/157 = 54% | -12 | -22 to -1 * |
| evidence_limit | 78/204 = 38% | 42/157 = 27% | +11 | +2 to +21 * |
| decline bare (of threads that decline a request) | 52/68 = 76% | 54/62 = 87% | -11 | -24 to +3 |
| decline bare (all threads) | 52/204 = 25% | 54/157 = 34% | -9 | -18 to +1 |
| promise_for_result | 47/204 = 23% | 45/157 = 29% | -6 | -15 to +3 |
| sends_elsewhere | 41/204 = 20% | 23/157 = 15% | +5 | -3 to +13 |
| worked_case | 51/204 = 25% | 32/157 = 20% | +5 | -4 to +13 |
| own_shortfall | 97/204 = 48% | 69/157 = 44% | +4 | -7 to +14 |
| self_praise | 89/204 = 44% | 74/157 = 47% | -4 | -14 to +7 |
| decline with substitute (all threads) | 16/204 = 8% | 8/157 = 5% | +3 | -3 to +8 |
| asks_for_score | 38/204 = 19% | 31/157 = 20% | -1 | -10 to +7 |
| shared_limitation | 17/204 = 8% | 12/157 = 8% | +1 | -5 to +6 |
| grants_main | 66/204 = 32% | 51/157 = 32% | -0 | -10 to +9 |

* interval excludes zero. With about 20 rows tested, one such row is expected by chance.

## Features that hold in both halves of the shards

| Feature | Shards 1 to 18 | Shards 19 to 36 |
|---|---|---|
| Asks the reviewer to spell out a criticism already made | 7% against 23% (-16) | 5% against 24% (-19) |
| A correction of the reviewer with no change to the paper and no owned wording, among threads that correct | 67% against 77% (-10) | 48% against 71% (-23) |
| A correction that owns the wording or names the fix | 23% against 17% (+7) | 39% against 20% (+18) |
| A modest size word for an own result (marginal, slight, comparable, small) | 36% against 17% (+19) | 35% against 27% (+8) |
| Names a limit on what a cited result covers and leaves it standing | 38% against 22% (+16) | 39% against 32% (+7) |
| A new result mentioned by its location only | 26% against 15% (+11) | 37% against 18% (+19) |

The last row runs against the reader's guess that a bare pointer costs the authors. It most likely tracks having new results in the revised PDF at all, which the regex counts already found (a pointer to revised text, 75% against 63%).

## Features that did not hold

- A cited paper's specific finding: +23 in the first half and +2 in the second.
- An own shortfall stated in a named setting: 10 of 10 against 3 of 10 for the reader, +4 (-7 to +14) blind.
- Granting the main objection, praising one's own conduct, a worked case, sending the reviewer to another post, asking for the score, a limitation shared with named prior work, a promise in place of a result, and a decline with or without a substitute result: no interval excludes zero.

## Not testable blind

Whether a point the reviewer raised a second time received new content. The blind copies have no reviewer follow-ups, so this remains a reader's observation (1 of 3 raised against 4 of 6 unchanged).

## Applied to the RECLAIM replies (2026-11-09)

- No draft and no prepared follow-up asks a reviewer to spell out a criticism, and none tells a reviewer that a point was already in the paper. Rule for the discussion: answer the most likely reading of a vague point and say which reading was answered.
- Reviewer YGTR, part 1: "Each row covers a small set of papers, so the last two columns give our two best agents on exactly those papers".
- Reviewer YGTR, part 1: "the counts are comparable, [3] in our loop and [2] in Codex CLI".
- Reviewer rqBN, W1: "so its errors lower the reported rates slightly" (73 against 83 of 400).
- Unchanged on purpose: the wording of the rqBN W2 answer, and every pointer to an appendix.
