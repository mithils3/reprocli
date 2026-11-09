# Pending slots in the rebuttal drafts

Scope: `rebuttal/drafts/replies.md` (R rows, slots in square brackets, [AUTHOR: ...] notes excluded) and `rebuttal/drafts/paper_revision_text.md` (P rows, `\todo{}` slots). Values come from `rebuttal/results/databook/databook.md`, the e-folder READMEs, `rebuttal/results/subset/README.md`, and the counts already printed in the drafts. Wilson 95% intervals are computed from the counts (stdlib check, matches the databook where both exist). Job state from `squeue` on 2026-11-08: 3540624 and 3540786 RUNNING; 3540625 to 3540633, 3540787, 3558022, 3558023 PENDING.

Grouping: a table row whose cells are all `\todo{}` is one P row, and its cells are listed in the slot column. Citation slots (`\todo{cite}`) are not numbers and are listed under fillable now only because a bib key is a lookup.

Known gaps: the frontier sweeps are not in the squeue output, so their status comes from the databook only. The DeepSeek-V4-Flash and Muse Spark rows on the frontier subset (P15, P16) and the All-four-by-tier row (P32) need per-run files that the read list does not cover; they are marked fillable now with the file to open.

## Fillable now

| id | file:line | slot text | what fills it | status | value and arithmetic |
| :- | :- | :- | :- | :- | :- |
| R2 | replies.md:23 | [n] papers, OpenAI | databook/frontier_cells.csv planned count; subset/README.md (core 12 + extension 12) | fillable now | 24 (gpt-6.1-sol planned 24; gpt-6-astra planned 8, a subset) |
| R3 | replies.md:23 | [m] papers, Muse Wonder | databook/frontier_cells.csv, thin-muse-wonder-1.0 planned | fillable now | 12 |
| R6 | replies.md:25 | [26%, 58%] (DSv4 Run) | e6/README.md 5% row; databook sec. 2 | filled 11-08 | 14/34 = 41.2%, Wilson 26.4 to 57.8, shown [26%, 58%] |
| R12 | replies.md:63 | [26%, 58%], [15%, 44%], [7%, 31%], [15%, 22%] | e6/README.md 5% table; 73/400 from databook sec. 2 | fillable now | 14/34 = 41.2% [26.4, 57.8]; 9/33 = 27.3% [15.1, 44.2]; 5/33 = 15.2% [6.7, 30.9]; 73/400 = 18.25% [14.8, 22.3] |
| R10 | replies.md:37 | [26%, 58%] (Run table row) | same as R6 | filled 11-08 | 14/34 = 41.2% [26.4, 57.8] |
| R13 | replies.md:69 | [26%, 58%] x2 (Run, as graded and env removed) | e6/README; databook sec. 2 (E8 Run) | filled 11-08 | 14/34 = 41.2% [26.4, 57.8] in both columns (env removal leaves DSv4 Run unchanged) |
| R14 | replies.md:70 | [15%, 44%] x2 (Retrain) | e6/README; databook sec. 2 (E8 Retrain) | filled 11-08 | as graded 9/33 = 27.3% [15.1, 44.2]; env removed: databook says Muse 9/32 = 28.1% [15.6, 45.4], not 9/33. CONFLICT, see notes |
| R15 | replies.md:71 | [7%, 31%] and [7%, 32%] (Reimplement) | e6/README; databook sec. 2 (E8 Reimplement) | filled 11-08 | as graded 5/33 = 15.2% [6.7, 30.9]; env removed 5/32 = 15.6% [6.9, 31.8] |
| R21 | replies.md:227 | [n] papers, OpenAI (sec. 5.1 copy) | same as R2 | fillable now | 24 |
| R22 | replies.md:227 | [m] papers, Muse Wonder (sec. 5.1 copy) | same as R3 | fillable now | 12 |
| R28 | replies.md:237 | [26%, 58%] x2 (Run row) | same as R6 | filled 11-08 | 14/34 = 41.2% [26.4, 57.8] |
| R29 | replies.md:238 | [15%, 44%] x2 (Retrain row) | same as R14 | filled 11-08 | 9/33 = 27.3% [15.1, 44.2] (as graded); env column conflict, see notes |
| R30 | replies.md:239 | [7%, 31%], [7%, 32%] (Reimplement row) | same as R15 | filled 11-08 | 5/33 = 15.2% [6.7, 30.9]; 5/32 = 15.6% [6.9, 31.8] |
| R34 | replies.md:262 | [26%, 58%] (sources table) | same as R6 | filled 11-08 | 14/34 = 41.2% [26.4, 57.8] |
| R35 | replies.md:262 | [7%, 31%] (sources table) | same as R15 | filled 11-08 | 5/33 = 15.2% [6.7, 30.9] |
| P2 | paper_revision_text.md:49 | \todo{cite} after the OpenAI model names | bib key for OpenAI models | fillable now | not a number: bib key lookup |
| P3 | paper_revision_text.md:49 | \todo{n} papers | same as R2 | fillable now | 24 |
| P4 | paper_revision_text.md:50 | \todo{cite} Muse Wonder | bib key | fillable now | not a number: bib key lookup |
| P5 | paper_revision_text.md:50 | \todo{m} papers | same as R3 | fillable now | 12 |
| P6 | paper_revision_text.md:52 | \todo{cite} Codex CLI | bib key | fillable now | not a number: bib key lookup |
| P9 | paper_revision_text.md:89 | \todo{and the 12 extension papers drawn the same way} | subset/README.md extension column | filled 11-08 | 12 = extension R 6 + N 6 (1+1+0+1+0+1+2+0+0 = 6 reproduced; 2+0+0+1+1+0+0+1+1 = 6 not) |
| P15 | paper_revision_text.md:113 | frontier table, DeepSeek-V4-Flash ours, five cells | e6/table.csv, restricted to the 24 subset papers (file not opened) | fillable now | not computed; needs the per-run file |
| P16 | paper_revision_text.md:114 | frontier table, Muse Spark 1.2 ours, five cells | same as P15 for Muse | fillable now | not computed; needs the per-run file |
| P19 | paper_revision_text.md:156 | \todo{n} papers in the frontier sentence | same as R2 | fillable now | 24 |
| P21 | paper_revision_text.md:234 | DSv4 All tiers lo--hi | counts sum of per-tier rows 14+9+4 of 34+33+33 (e6 per tier) | filled 11-08 | 27/100 = 27.0%, Wilson 19.3 to 36.4 |
| P22 | paper_revision_text.md:238 | Qwen3.6-27B All tiers lo--hi | 5+6+2 of 100 | filled 11-08 | 13/100 = 13.0%, Wilson 7.8 to 21.0 |
| P23 | paper_revision_text.md:242 | MiniMax-M2.7 All tiers lo--hi | 3+5+2 of 100 | fillable now | 10/100 = 10.0%, Wilson 5.5 to 17.4 |
| P24 | paper_revision_text.md:246 | Muse Spark 1.2 All tiers lo--hi | 9+9+5 of 100 | fillable now | 23/100 = 23.0%, Wilson 15.8 to 32.2 |
| P25 | paper_revision_text.md:247 | All agents Run / Retrain / Reimplement lo--hi (3 slots) | per-tier sums: 14+5+3+9 of 136; 9+6+5+9 of 132; 4+2+2+5 of 132 | fillable now | 31/136 = 22.8%, Wilson 16.5 to 30.5; 29/132 = 22.0%, 15.8 to 29.8; 13/132 = 9.8%, 5.8 to 16.1 |
| P28 | paper_revision_text.md:407 | the \todo{28} cells with no graded run | databook sec. 2, E8 empty cells | fillable now | 28 of 400 (4 + 2 + 3 + 2 + 3 + 14 = 28 by cause); moves to 26 if decision 4 counts the two Muse grades |
| P31 | paper_revision_text.md:727 | \todo{cite} gpt-6.1-sol target check | bib key | fillable now | not a number: bib key lookup |
| P32 | paper_revision_text.md:753 | All four, Run / Retrain / Reimplement (3 slots) | e7 step3 per-paper all-four flag by tier (file not opened) | fillable now | not computed; the README gives only per-question tier counts |

## Waiting on the running frontier sweeps

| id | file:line | slot text | what fills it | status | value and arithmetic |
| :- | :- | :- | :- | :- | :- |
| R4 | replies.md:23 | [Result sentence: a, b, c, d] | databook/frontier_cells.csv, reproduced column per arm (gpt-6-astra Codex; gpt-6.1-sol thin and Codex; Muse Wonder) | waiting on the running frontier sweeps | now: astra Codex 0/4 graded (of 8); sol Codex 1/12 (of 24); sol thin 2/7 (of 12 planned); Muse 0/0 (of 12) |
| R5 | replies.md:23 | [Failure-mode sentence] | frontier grades and failure-mode labels (blind check of 20, decision 12) | waiting on the running frontier sweeps | not computed |
| R17 | replies.md:177 | [frontier agents ... a of n papers] | frontier_cells.csv reproduced column | waiting on the running frontier sweeps | now: sol Codex 1 of 12 graded |
| R23 | replies.md:229 | [Result sentence, sec. 5.1 copy: a, b, c, d, g, h] | frontier_cells.csv (arms as R4) | waiting on the running frontier sweeps | as R4; Codex sol 1/12, thin sol 2/7 |
| R24 | replies.md:229 | [Harness sentence: k papers, McNemar p = x] | paired sol thin vs sol Codex, frontier_cells.csv | waiting on the running frontier sweeps | not computed; needs both arms on the same papers |
| R25 | replies.md:229 | [Budget sentence: u% of GPU grant] | frontier_cells.csv spent_h100 / budget_h100 | waiting on the running frontier sweeps | now partial: median of 24 rows is not final |
| R26 | replies.md:229 | [k] of [f] failing frontier runs | frontier_cells.csv, rows with reproduced False | waiting on the running frontier sweeps | not computed |
| R27 | replies.md:229 | [Muse Wonder d of m against Muse Spark e of m] | frontier_cells.csv (Muse, 0 of 0 graded); e6 for Muse Spark | waiting on the running frontier sweeps | Muse Wonder 0 graded of 12 |
| R31 | replies.md:241 | [their results] (frontier, same environment) | frontier_cells.csv | waiting on the running frontier sweeps | not computed |
| P8 | paper_revision_text.md:69 | \todo{In the frontier arms ...} a, b, c, d, g, k, u, n, m | frontier_cells.csv, run_usage_summary.md | waiting on the running frontier sweeps | as R4 and R25 |
| P10 | paper_revision_text.md:107 | frontier table, gpt-6-astra Codex, five cells | frontier_cells.csv (Run, Retrain, Reimplement, mean score, grant spent) | waiting on the running frontier sweeps | now: 0/4 graded |
| P11 | paper_revision_text.md:108 | frontier table, gpt-6.1-sol ours, five cells | frontier_cells.csv thin arm | waiting on the running frontier sweeps | now: 2/7 graded |
| P12 | paper_revision_text.md:109 | frontier table, gpt-6.1-sol Codex, five cells | frontier_cells.csv Codex arm | waiting on the running frontier sweeps | now: 1/12 graded |
| P13 | paper_revision_text.md:110 | frontier table, Muse Wonder ours, five cells | frontier_cells.csv thin-muse arm | waiting on the running frontier sweeps | now: 0 graded |
| P14 | paper_revision_text.md:111 | frontier table, Muse Wonder mini-SWE, five cells | frontier_cells.csv miniswe arm | waiting on the running frontier sweeps | now: 0/1 graded (miniswe row) |
| P17 | paper_revision_text.md:122 | \todo{Failure modes ... k of m ... x of 20} | frontier labels, blind labels of 20 runs | waiting on the running frontier sweeps | not computed |
| P18 | paper_revision_text.md:127 | \todo{Early stopping ... u, v, w} | frontier run_usage_summary.md, early_stop.md | waiting on the running frontier sweeps | not computed; partial medians 0.06% to 1.40% over 11 runs |

## Waiting on a job

| id | file:line | slot text | what fills it | status | value and arithmetic |
| :- | :- | :- | :- | :- | :- |
| R7 | replies.md:25 | [verdict same in all three runs on k of 12] | repeat-run grades, jobs 3540624 to 3540633 (sweeps/jobs.csv) | waiting on job 3540624 (9 more repeat jobs) | not computed |
| R32 | replies.md:243 | [Its verdict ... k of 12 ... [lo, hi]] | same as R7; Wilson of k of 12 | waiting on job 3540624 | not computed |
| R9 | replies.md:31 | [16 stopped cells and 4 prompt-bug cells rerun, r reproduced] | E8 rerun grades | waiting on job 3540786 (and 3540787) | not computed; decision 5 governs whether the 16 stay admitted |
| R33 | replies.md:249 | [reran 4 cells of 2510.20725 and 16 stopped cells, r reproduce] | same as R9 | waiting on job 3540786 | not computed |
| P20 | paper_revision_text.md:196 | \todo{Repeat-run sentence, Section 3} | repeat-run grades, jobs 3540624 to 3540633 | waiting on job 3540624 | not computed |
| P26 | paper_revision_text.md:286 | \todo{verdict same in all three runs on k of 12; lo to hi; j of 3} | same as R7 | waiting on job 3540624 | not computed |
| P27 | paper_revision_text.md:382 | \todo{reran the other 20 cells ... r reproduce} | E8 rerun grades, jobs 3540786 and 3540787 | waiting on job 3540786 | not computed; 20 = 4 + 16 |
| P29 | paper_revision_text.md:414 | \todo{28 - labeled} | dissection labels after the reruns, job 3540786 | waiting on job 3540786 | not computed |
| P34 | paper_revision_text.md:898 | \todo{On 2506.10351 both seeds ...} | E10 seed runs, jobs 3558022 and 3558023 | waiting on job 3558022 and 3558023 | not computed |
| P37 | paper_revision_text.md:938 | \todo{} rerun and regrade costs (\$4,835 and \$12.21 and \$66) | run costs, jobs 3540624 and 3540786 | waiting on job 3540786 | not computed |
| P38 | paper_revision_text.md:939 | \todo{} dissection counts (58 of 73, 72, 45 of 73) | dissection records after reruns | waiting on job 3540786 | not computed |
| P41 | paper_revision_text.md:943 | \todo{} Reproduced 72 and No label 28 after labeling | dissection records | waiting on job 3540786 | not computed |

## Waiting on an author decision

| id | file:line | slot text | what fills it | status | value and arithmetic |
| :- | :- | :- | :- | :- | :- |
| R1 | replies.md:23 | [gpt-6-astra and gpt-6.1-sol] model names | frontier_cells.csv model column; terra would add gpt-6.1-terra | waiting on an author decision (10, report gpt-6.1-terra?) | names as in frontier_cells.csv |
| R19 | replies.md:222 | [gpt-6-astra] | same as R1 | waiting on an author decision (10) | gpt-6-astra |
| R20 | replies.md:227 | [gpt-6-astra and gpt-6.1-sol] | same as R1 | waiting on an author decision (10) | as R1 |
| R8 | replies.md:29 | [k] targets corrected | e7 corrected_targets (count of lines) | waiting on an author decision (1, keep the 10 target corrections) | candidate 10 per decisions_monday item 1; not final |
| R11 | replies.md:60 | [k targets corrected and rescored] | same as R8 | waiting on an author decision (1) | candidate 10 |
~~R16 | replies.md:111 | [45 papers read; k targets; v verdicts; w papers per tier] | e7 v3_failures.csv (45 flagged) and author review | waiting on an author decision (7, settle the nine E7 items) | 45 flagged; k, v, w not final~~ cut 11-09, author decision: rqBN did not ask for the 45-paper read |
~~R18 | replies.md:191 | [each of 45 papers read; k of 45; v verdicts] | same as R16 | waiting on an author decision (7) | k of 45 not final~~ cut 11-09, author decision: rqBN did not ask for the 45-paper read |
| P1 | paper_revision_text.md:49 | \todo{gpt-6-astra and gpt-6.1-sol} model names | same as R1 | waiting on an author decision (10) | as R1 |
| P30 | paper_revision_text.md:540 | \todo{Optional: second author labeled n, agrees on k} | blind second grader labels | waiting on an author decision (12, run a second blind grader) | not computed |
~~P33 | paper_revision_text.md:765 | \todo{An author read all 45 papers ... k ... v} | same as R16 | waiting on an author decision (7) | k and v not final; candidate Run 14 to 13~~ cut 11-09, author decision: rqBN did not ask for the 45-paper read |
| P35 | paper_revision_text.md:934 | ':478' Muse Spark 1.2 on 23 of 33 (CogVLA) | CogVLA run score in e8 regrades | waiting on an author decision (6, move CogVLA to Run) | 23/33 holds unless the CogVLA score falls below 6 |
| P36 | paper_revision_text.md:935 | ':481-482' z = 2.7 and z = 1.2 | E7 rescore, DSv4 Run 13/34 candidate | waiting on an author decision (7) | z values unchanged if Run stays 14/34 |
| P39 | paper_revision_text.md:941 | Table 5 Muse Run/Retrain, All, means | Muse counts after regrades (2503.23035, CogVLA) | waiting on an author decision (4, count the two new Muse grades) | Muse Run 10/34 candidate (9 now); Retrain 8/33 candidate (9 now) |
| P40 | paper_revision_text.md:942 | c_rubric 28, 53, 60, 52 to 26, 53, 61, 53 | E7 regrades | waiting on an author decision (7) | candidate values only |

## Counts by status

| status | rows |
| :- | :- |
| fillable now | 32 |
| waiting on the running frontier sweeps | 17 |
| waiting on a job | 12 |
| waiting on an author decision | 14 |
| total | 75 |

Counts are rows, and table rows with several cells count as one row each. Citation rows (P2, P4, P6, P31) are counted as fillable now.

## Notes and conflicts

1. Thin arm sample size. frontier_cells.csv plans thin-gpt-6.1-sol on 12 papers, but replies.md:23 and 229 read "b of n in our harness" with n = 24. Either the thin arm is 24 papers (a planned change) or the sentence needs 12.
2. Env-removed Retrain column. replies.md:70 and :238 show 9/33 in the env-removed column, but databook sec. 2 gives the best env-removed Retrain as Muse 9/32 = 28.1% [15.6, 45.4]. The replies sources line also says Muse 9/32 becomes 8/32 after the checkpoint correction.
3. E10 seeds for 2505.17836. replies.md:191 quotes new-seed values 0.0400 and 0.0393, but databook sec. 3 lists both 2505.17836 seed jobs as FAILED with no completed job. Only 2510.07501 s1 (3540342) and s2 (3544919) are COMPLETED. Source needed before posting.
4. Frontier jobs. The squeue query shows no codex, thin or miniswe jobs. Frontier status here comes from frontier_cells.csv (24 rows, dated through 2026-11-08 19:52 UTC).
5. Nudge arm. codex-gpt-6.1-sol-nudge has 0 of 8 graded and no slot in the drafts. Decision 13 decides whether it gets one.
6. Sample counts. gpt-6-astra is on 8 papers while the sentence reads "from OpenAI on n papers"; n = 24 is the gpt-6.1-sol count. A reader could take n as 8 for both.


7. Resolved 11-08. Conflict 1: n is per arm (thin sol 12 planned, Codex sol 24, astra 8), AUTHOR note added at replies.md:23 and :227. Conflict 2: no change; DeepSeek-V4-Flash 9/33 is the best Retrain agent in e8/bound.csv and Muse 9/32 is a separate claim. Conflict 3: 0.0400 and 0.0393 are in e10/results.md and STATUS.md (jobs 3550825 and 3550826 finished the experiment; Slurm FAILED only at the save step); no change. Filled slots needed no text change except P9, P21, P22 and the n notes; the interval brackets in R6 to R35 were already printed and match the Wilson recomputation. Left: R2, R3, R21, R22, P3, P5, P19 (frontier counts), R12 (73/400 depends on decisions 1 and 4), P23, P24, P25, P28 (regrade decisions), P2, P4, P6, P31 (bib keys), P15, P16, P32 (not computed).