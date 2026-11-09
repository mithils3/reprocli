# Consistency check of replies.md (2026-11-08)

Read only. replies.md was not edited and nothing was committed. Extraction script: /tmp/claude-1000/-home-mithil-PyCharmProjects-reprocli/6dbe9a0b-b0fd-4784-933b-d978a99d9c41/scratchpad/check_numbers.py. Every number with 8 words of context per side, with a slot flag: /tmp/claude-1000/-home-mithil-PyCharmProjects-reprocli/6dbe9a0b-b0fd-4784-933b-d978a99d9c41/scratchpad/numbers.tsv. Line numbers refer to replies.md.

## Flags

### Flag 1. Best-agent Retrain movement across 1% to 10% is 4, not 3

Quoted places:
- line 29: "moves by at most 5 at Run (9 at 1%, 14 at 5% and 10%), 3 at Retrain and 1 at Reimplement"
- line 90: "moves by at most 5 of the 34 Run papers (14 at 5% against 9 at 1%), 3 at Retrain and 1 at Reimplement"
- line 39 (Sources, General): "so at most 14 - 9 = 5, 12 - 9 = 3 and 5 - 4 = 1"
- line 125 (Sources, T29u): "at most 5, 3 and 1 papers of movement"

Supported value: rebuttal/results/e6/README.md tolerance table. The best Retrain count is 8 at 1% (DeepSeek and Muse tie), 9 at 2% and 5%, and 12 at 10% (Muse alone). The 1% to 10% range is 12 - 8 = 4. The figure of 3 only comes from comparing 10% with 5%. At 10% the best Retrain agent is Muse, so the "best agent" is not the same agent at both ends.

Suggested fix: change "3 at Retrain" to "4 at Retrain (8 at 1%, 12 at 10%)" in lines 29 and 90, and change the Sources rows at lines 39 and 125 to "12 - 8 = 4".

### Flag 2. The all-agent count of 73 of 400 still counts two runs that the revision says are not reproduced

Quoted places:
- line 63: "Over all four agents, 73 of the 400 agent-paper cells are reproduced, 73/400 = 18% [15%, 22%]"
- line 27: "of those 372 runs it marks 73 reproduced" and "these 73 are the reproductions that Section 5.2 reports as 73 of the 400 cells"
- line 96 (tolerance table, 5% row): "73"; line 124 (Sources): "56/65/73/82"; line 46 (Sources, General)
- Against these: line 31 "The revision counts both as not reproduced" and line 88 "the revision counts both as not reproduced"

Supported value: the two checkpoint runs are Muse Spark 1.2 on 2508.21046 (Retrain, 9 to 8 per line 247) and MiniMax-M2.7 on 2505.12677 (Reimplement, 2 to 1 per line 247). Removing both gives 73 - 2 = 71 of 400, which is 17.8% with a Wilson 95% interval of 14% to 22% (computed). The AUTHOR note in line 63 gives 72 after the 2503.23035 grade is added, which is consistent with this.

Suggested fix: use 71 of 400 (18%, [14%, 22%]) for the state before the new grades, or 72 after them, and change every use listed above. Recompute the all-agent column of the tolerance table (56, 65, 73, 82) with the same two runs removed.

### Flag 3. "Every rate includes these grades" does not match the 372 base

Quoted places:
- line 249: "Every rate in the revision includes these grades."
- line 31: "The two missing audits and 3 of those 4 runs are now graded"
- line 27, line 75, line 145, line 153, and Sources lines 49, 132, 199, 210 all use 372 graded runs. Line 31 gives 368 of 372 for the download scan, and line 88 gives "372 runs" for the log check.

Supported value: rebuttal/results/e4/summary.json has n_runs 372, which is the count before the regrades. The grades added since are the two missing audits (rebuttal/results/e8/regrade_muse.json: 2503.23035 reproduced at 8, 2510.08177 partial at 6) and three regraded finished runs (rebuttal/results/e8/regrade_dcells.json: scores 0, 2, 0). That makes 372 + 5 = 377 graded runs. The counts of 73, 83, 368, and 45,861 all predate those grades.

Suggested fix: either recompute every count over 377 graded runs, or change line 249 to say the rates are over the 372 runs graded before 2026-11-08 and list the five later grades separately.

### Flag 4. Muse Retrain counts appear with two denominators and no label

Quoted places:
- line 247: "Muse Spark 1.2's reproduced Retrain papers fall from 9 of 33 to 8 of 33"
- line 119 (Sources, T29u): "Muse Retrain 9/32 less the CogVLA checkpoint run is 8/32"
- line 262 (Sources, YGTR): "Muse 9/32 becomes 8/32 after the checkpoint correction"
- line 271 (Sources, YGTR): "Muse Retrain 9 to 8"

Supported value: rebuttal/results/e8/bound.csv, row muse,retrain: paper_den 33 and reproduced 9, with bound_all_den 32 after removing one build failure. Both denominators are correct for their own purpose. The corrected figures are 8 of 33 as graded and 8 of 32 with build failures removed. The bound.csv file predates the CogVLA correction.

Suggested fix: write "as graded" or "with build failures removed" beside each Muse Retrain count in lines 119, 247, 262, and 271.

### Flag 5. Muse Spark 1.2 mean audit score of 5.00 has no source, and it predates the new grades

Quoted places:
- line 63: "5.00 for Muse Spark 1.2"
- line 120 (Sources, T29u) cites only "5.13 and 3.03 mean audit score" (paper_latex/iclr2027_conference.tex:463-466)

Supported value: the paper text at lines 463 to 466 gives 5.13 for DeepSeek-V4-Flash and 3.03 for MiniMax-M2.7 and nothing for Muse. A search of rebuttal/results/e4, e6, and e8 found no 5.00 mean. The AUTHOR note in line 63 says the two new Muse grades (8 and 6) would make it 5.14, so 5.00 is the pre-grade value.

Suggested fix: add the Sources row that produces 5.00, or remove the Muse number. State that the value is over the 372 runs, as in Flag 3.

## Items checked that match

- Every fraction with a Wilson interval recomputes correctly: 14/34 [26%, 58%], 9/33 [15%, 44%], 5/33 [7%, 31%], 5/32 [7%, 32%], 73/400 [15%, 22%], 9/12 [47%, 91%], 64/73 [78%, 93%], 64/83 [67%, 85%], 11/16 [44%, 86%].
- Precision, recall and F1 by tier in line 145 match the counts (28/31, 28/35, 25/29, 25/32, 11/13, 11/16). F1 0.82 overall is 2 x 64 / (2 x 64 + 9 + 19) = 0.82.
- The 5-by-5 confusion matrix in lines 77 to 84 sums correctly on every row and column to 372. The diagonal sums to 306. The 28 disagreements split as 19 and 9. The 57 at zero split as 42 agreeing (53 + 46 - 42).
- Log-entry split in lines 166 to 171 sums to 45,861. rebuttal/results/e5/summary.json and e5/README.md agree.
- Empty cells: 28 = 6 + 16 + 2 + 4. rebuttal/results/e8/empty_cells_traced.csv has 16 class B rows and 4 class D rows. The 6 outside-agent cells match e8/summary.json outside_agent_cells.
- Build failures: 24 = 13 + 6 + 5 by tier and 14 + 7 + 3 by cause. Matches e8/summary.json.
- 27 = 6 + 14 + 7 (line 251). 2,552 = 10,208 / 4 (line 177). 6.9% = 6.7 / 97.3 (line 99). 0.0007 and 0.28 (line 177) recompute from the listed values.
- Claims: 62 = 58 + 4 point estimates; 38 = 21 + 14 + 3 (matches e6/summary.json lockfile_kinds). Target parts 92, 95, 76, 69, 55 and 45 failures match Risk 1.
- Scan: 368 = 127 + 118 + 123, and 372 = 129 + 118 + 125 (e9/summary.json runs_scanned). 42 = 29 + 13, and 16 = 10 + 4 + 2.

Not checked: the 100 at 7 or 8 with 75 agreeing (line 86), 253 and 324 agreement counts (line 145, matched to e4 but not recounted), and the 70 and 72 totals at 1 and 2 points (line 99).

## Heading counts (text under each ### heading, up to the next # line)

| Part | Stated | Measured, with AUTHOR notes | Measured, AUTHOR notes removed | Result |
| :- | -: | -: | -: | :- |
| General reply (line 9) | 4,561 | 4,561 | 4,561 | match |
| Reply to T29u, part 1 (line 54) | 3,030 | 3,564 | 3,068 | off by 38, heading stale |
| Reply to T29u, part 2 (line 73) | 4,669 | 4,669 | 4,669 | match |
| Reply to rqBN, part 1 (line 137) | 4,975 | 4,975 | 4,975 | match |
| Reply to rqBN, part 2 (line 175) | 4,219 | 4,676 | 4,249 | off by 30, heading stale |
| Reply to YGTR, part 1 (line 219) | 4,972 | 5,138 | 4,973 | over 5,000 as drafted; off by 1 without notes |
| Reply to YGTR, part 2 (line 245) | 3,599 | 3,762 | 3,600 | off by 1 |

The stated counts appear to exclude AUTHOR notes, since four of them match exactly on that basis. Fix the two stale headings (T29u part 1 and rqBN part 2). The YGTR part 1 part is under 5,000 only once its AUTHOR note is resolved, and its heading should then be 4,973. The one-character gaps on YGTR parts 1 and 2 are probably a trailing newline difference.

All seven parts are under 5,000 characters once AUTHOR notes are removed.

## Style checks

- Em dashes (U+2014): none in replies.md. En dashes (U+2013): none.
- Experiment codes E3 to E10 in reply text: none. The one hit is "E7" at line 63, inside an [AUTHOR] note ("if the E7 target corrections are final" and "the E7 verdicts"). It is not posted text, but if the note stays, write "the target-correction check" instead.
- The "24" in line 65 (build failures among 372 graded runs) and in line 75 (human labels with no auditor grade, out of 396) are different quantities in the same reviewer reply. Both denominators are stated, so no change is needed.

## Resolved by the main session, 2026-11-08

- 73 against 71 of 400: left for the author (Risk 5 and the [AUTHOR] note on item 4); the replies stay at 73 until he decides.
- "3 at Retrain": rejected. The movement is measured from the 5% count (9): 8 at 1% and 12 at 10%, so at most 3, the same way Run's 5 is 14 against 9 (e6/README.md table).
- Muse 5.00 mean: source added to the T29u Sources table (b_models.tex:178).
- Heading counts for T29u part 1 (3,066) and rqBN part 2 (4,248) updated; counts exclude [AUTHOR] notes, which come out before posting.
