# Number check: followups_v4_T29u.md

L5 | 10 Muse papers; 5 Reimplement reproduced; 4 again | MATCH | e12/README.md lines 7-18 (run 8+ on 5 Reimplement papers; 4 repeats 8+)
L9 | Muse 10 Reimplement, keep 9 | MATCH | e12/README.md line 20
L10 | DSv4 1 Run, 6 Retrain, 5 Reimplement; keep 1, 6, 3 | MATCH | e13/README.md lines 9-24, 36-40, 50-62 (recount: keep 1+6+3 = 10 of 12)
L11 | gpt-6.1-sol, gpt-6-astra: 8 pairs, keep 7 | MATCH | e13/README.md line 28 and line 63 ("8 x86 pairs (7 keep)"); paper.txt 3231 gives 4 of 8 reproduced on x86, a different count
L12 | 26/30 = 87% [70%, 95%] | MATCH | e13/README.md line 63 (Wilson 70% to 95%); recomputed 0.867, Wilson 70.3% to 94.7%
L14 | 20 runs, 17 keep the verdict; Section 5.2 reports first 16 | MATCH | e13/README.md lines 42, 63; paper.txt 563 (16 runs, 9 papers)
L14 | each of 4 changing pairs has every run at 7, 8 or 9 | NOT FOUND | DSv4 pairs 2503.02809 and 2505.19087 verified (e13/README.md lines 17-20); Muse 2503.02809 (e12 line 10); 4th pair (gpt) has no per-run file on disk
L16 | 9 of 10 Muse keep; 5 at 8+; 4 again | MATCH | e12/README.md line 20 and table lines 9-18
L17 | 4 of 12 DSv4 papers in subset.json | MATCH | rebuttal/subset.json (recount: 2506.20671, 2503.02809, 2505.19087, 2506.06991)
L17 | 18 of 38 opened repeats stopped ungraded | MATCH | rebuttal/STATUS.md line 135
L17 | e12 says completion favours shorter runs | MATCH | e12/README.md line 22
L21 | 18 runs scored 7 and 8 | MATCH | e4/matrix_0_10.csv: human7/auditor8 = 7, human8/auditor7 = 11; sum 18
L21 | 22 runs with lower score 6 or 7 | MATCH | matrix recount, 28 verdict-split runs: min score 6 or 7 = 22
L21 | 9 auditor-only runs; human 7 to seven, 5 to two | MATCH | matrix: auditor>=8 and human<8 = 9; by human 7 = 7, human 5 = 2
L21 | 28 split runs | MATCH | matrix recount (verdict differs) = 28; paper.txt 3624
L25 | Human grade: Run 35 = 26%, Retrain 32 = 24%, Reimplement 16 = 12% | MATCH | paper.txt 3700-3702 (Table 13); recomputed 35/136, 32/132, 16/132
L26 | Auditor: 31 = 23%, 29 = 22%, 13 = 10% | MATCH | paper.txt 3699-3702 (Table 13); recomputed 31/136, 29/132, 13/132
L28 | 38 re-graded, no reproduced verdict changed | MATCH | e7/rescore_summary.md line 15 (0 cells change)
L28 | "mean score difference was 0.39" | MISMATCH | e7/rescore_summary.md line 15 gives "mean absolute difference 0.39 points"; value matches, but the draft drops "absolute" (signed mean would differ)
L35 | 92 count the value question alone | MATCH | paper.txt 3819 (Table 15, Value 92)
L35 | 55 pass all four | MATCH | paper.txt 3825 (Table 15); ev_targets/ev_targets.md line 6
L35 | 36/220 = 16%; 34/180 = 19% | MATCH | ev_targets/ev_targets.md line 14 (revision B column; 36 of 220, 34 of 180)
L39 | All 100: Run 13/34, Retrain 9/33, Reimplement 5/33 | MATCH | tiers/tier_tests.md lines 7-11 (dsv4 13/34, 9/33; muse 5/33 is the tier best at Reimplement; dsv4 is 4/33)
L40 | Without the 16: 10/29, 6/23, 5/32 | NOT FOUND | ev_targets/ev_targets.md has per-agent tables only for the 55 and 45 groups; the 84 group has cell totals (53 of 336) only
L41 | 55 pass all four: 9/19 = 47%, 2/13 = 15%, 4/23 = 17% | MATCH | ev_targets/ev_targets.md line 25 (revision B: dsv4 9 of 19; 2 of 13; muse 4 of 23)
L43 | Retrain 13 papers, 15% [4%, 42%] | MATCH | ev_targets/ev_targets.md line 25 (2 of 13 = 15.4% [4.3, 42.2])
L52-58 | z table (15 values) | MATCH | tiers/tier_tests.md lines 7-11
L60 | two-sided p = 0.014 (DSv4), p = 0.005 (at least one) | MATCH | recomputed from z 2.46 -> 0.0139 and z 2.81 -> 0.0050
L62 | z values 2.46, 0.96, 2.81, 1.15 at paper.txt 579-581 | MATCH | paper.txt lines 579 and 581
L67 | 57 runs with a 0; 42 both; 11 auditor only; 4 human only | MATCH | matrix recount; paper.txt 3592
L67 | auditor-only 11: human 1-5 seven, 6-7 two, 8-9 two | MATCH | matrix human rows h1..h10 in column a0 (2+2+1+1+1 = 7; 1+1 = 2; 1+1 = 2)
L67 | no human-0 run counts as reproduced | MATCH | matrix human-0 row, auditor >= 8 sums to 0
L69 | auditor-0 column 42, 7, 2, 2; human-0 row 1, 2, 4, 6 | MATCH | matrix recount; paper.txt 3590-3594, Table 11 at 3610
L74 | 3,414 NeurIPS 2025 papers; 1,000-paper sample; 687 verified | MATCH | paper.txt 375-376, 389
L74 | 100 papers from an audit pool stratified by tier and compute band | MATCH | paper.txt 411 (200-paper audit pool, stratified) and 416-417 (100-paper benchmark)
L74 | Section 6 | MATCH | paper.txt 796 ("6 LIMITATIONS AND FUTURE WORK")
L82 | 10 of 12 DSv4 papers; 7 of 8 gpt pairs | MATCH | e13/README.md line 63; e13 line 28
L84 | 18 of 28 are 7 and 8; Reimplement 16 of 132 (12%); Run 35 of 136 (26%) | MATCH | matrix; paper.txt 3700-3702
L86 | 36/220 = 16%; 34/180 = 19%; 9 of 19 (47%); 13 Retrain papers | MATCH | ev_targets/ev_targets.md lines 14, 25
L16 | paper.txt 563 (16 repeat runs, 9 papers) | MATCH | paper.txt 563

Tally (39 rows): MATCH 36 rows, MISMATCH 1 (L28 wording), NOT FOUND 2 rows (L14 fourth pair scores; L40 three values). Also NOT FOUND: the L21 sub-split "15 + 7" cannot be reproduced from the matrix (the total 22 matches).
