# Number check: rebuttal/drafts/followups_v4_rqBN.md

No Wilson intervals appear in the draft, so none were recomputed. Percentages and sums were recomputed with python.
Paper line numbers are file lines in paper.txt.

L5 | 92 value-only; 55 pass all four (Table 15) | MATCH | paper.txt 3819 (Value 92), 3827 (caption)
L9 | All 100, Run 30/136 = 22% | MISMATCH | e6/table.csv index_verdict reproduced Run = 31 of 129 rows; paper.txt 3699 gives 31/136; rescore_summary.md lines 16-17 flip two Run cells, giving 29
L9 | 55 subset, Run 19/76 = 25% | MATCH | ev_targets_raw.txt line 55 (per-model sum 19); 76 = 19 x 4; paper.txt 3819 (19/34)
L10 | All 100, Retrain 28/132 = 21% | MISMATCH | paper.txt 3700 (29/132); e6/table.csv reproduced Retrain = 29
L10 | 55 subset, Retrain 7/52 = 13% | MATCH | ev_targets_raw.txt line 56 (sum 7); 52 = 13 x 4; paper.txt 3819 (13/33)
L11 | All 100, Reimplement 12/132 = 9% | MISMATCH | paper.txt 3702 (13/132); e6/table.csv reproduced Reimplement = 13
L11 | 55 subset, Reimplement 10/92 = 11% | MATCH | ev_targets_raw.txt line 57 (sum 10); 92 = 23 x 4; paper.txt 3819 (23/33)
L12 | All 70/400 = 18% | MATCH (note) | ev_targets_raw.txt line 38 (70 of 400); paper.txt 547 (Section 5.2: 70 of 400). Paper Table 13 (3704) gives 73; rescore_summary.md line 27 gives 71
L12 | 36/220 = 16% | MATCH | ev_targets_raw.txt line 42
L14 | 34/180 = 19%, p = 0.51 | MATCH | ev_targets_raw.txt line 46 (34 of 180); line 62 (p = 0.5119)
L14 | 53/336 = 16% | MATCH | ev_targets_raw.txt line 50
L14 | 16 targets with setting or label off | MATCH | rebuttal/mithil/e7_merged.md line 14 (16 items); 16 distinct papers
L14 | Reimplement 12/128 = 9% | MISMATCH | e6/table.csv submitted grades: 13 Reimplement reproduced cells, none on the 16 setting-or-label papers, so 13/128 = 10%; ev_targets_raw.txt line 17 gives 57/336 on submitted grades
L16 | 36/220, 34/180, 53/336, p = 0.51 | MATCH | ev_targets_raw.txt lines 42, 46, 50, 62
L16 | per-model rows on the 55 sum to 19, 7, 10 | MATCH | ev_targets_raw.txt lines 55-57 (19, 7, 10)
L17 | recomputed 30, 28, 12; 12 of 128 | MISMATCH | e6/table.csv gives 31, 29, 13 (73 total); no named source gives 30/28/12 or 12/128; see L9-L14
L18 | 17 of 70 reproduced cells sit on setting-or-label targets | MATCH (arithmetic only) | 70 - 53 from ev_targets_raw.txt lines 38, 50. Submitted grades give 16 cells (e6/table.csv)
L18 | ...on 11 targets | MISMATCH | e7_merged.md lists 16 setting-or-label targets; e6/table.csv places reproduced cells on 7 of them; no source names 11
L18 | best agent on the 55: 9 of 19, 2 of 13, 4 of 23 | MATCH | ev_targets_raw.txt lines 43-45
L18 | other 45: Retrain 21 of 80 vs Run 11 of 60 | MATCH | ev_targets_raw.txt lines 59-60 (sums 21 and 11)
L22 | 32 of 100 papers (16, 11, 5) | MATCH | paper.txt 571-572 (Section 5.2). Note: e6 submitted grades give 34 (16/12/6), ev_targets_raw.txt line 5
L22 | 2 of the 12 papers no open agent had; both Run | MATCH | rebuttal/results/frontier/same_paper_baselines.md line 60 (2 papers, 4/24); paper.txt 3216 ("on 2 papers"); paper.txt 3242, 3247 (Run); e6/table.csv: no open agent reproduces 2505.10475 or 2506.20671
L22 | 34 = 18 Run, 11 Retrain, 5 Reimplement | MATCH | 16 + 2, 11, 5 (arithmetic)
L22 | 76 runs outside tolerance | MATCH | ev_faithful/ev_faithful.md line 11 (24, 37, 15)
L22 | 14/29 = 48%, 9/18 = 50%, 5/31 = 16% | MATCH | ev_faithful/ev_faithful.md lines 27-29 and 39 (dsv4 14 of 29; muse 9 of 18; muse 5 of 31)
L24 | Section 5.2 32 (16, 11, 5); B.3 2 papers | MATCH | paper.txt 571-572; 3216 (B.3, file lines 3166-3370)
L30 | human Table 13: 35/136, 32/132, 16/132 | MATCH | paper.txt 3699, 3700, 3702
L30 | 324/372 = 87% within one point | MATCH | rebuttal/results/e4/README.md line 14 (324 of 372); 324/372 = 87.1%
L30 | kappa = 0.89 | MATCH | rebuttal/results/e4/README.md line 14
L30 | 38 runs, none changes | MATCH | rebuttal/results/e7/rescore_summary.md line 15 (0 of 38 cells change)
L33 | 10 papers; 3 reproduced; 8 scores differ | MATCH | rescore_summary.md lines 1, 3, 13, 15 (8 of 38 integer scores differ)
L37 | Table 10: score 0 covers high-severity flag and three related conditions | MATCH | paper.txt 3590-3591
L37 | 42 of 57 agree; auditor 11 vs human 4 | MATCH | paper.txt 3592-3593 (Appendix D, 3527-3709)
L37 | 46 disqualified by humans; auditor calls none reproduced | MATCH | paper.txt 3607 (Total 46; Reproduced column 0)
L37 | 2 of 42 with downloaded checkpoint; 40/42 = 95% | MATCH | paper.txt 3134-3135 (Appendix B.2: two of 16 matches); 40/42 = 95.2%
L37 | scan covered all 42 reproduced Retrain and Reimplement runs | MATCH | paper.txt 3134 (B.2); e9/README.md lines 12-14 (2 Reimplement runs unscanned, both not reproduced in e6/table.csv)
L39 | Table 11 human Disqualified row 0, 1, 2, 1, 42 | MATCH | paper.txt 3607
L39 | Appendix D 57, 42, 11, 4 | MATCH | paper.txt 3592-3593
L40 | 42 runs (29 + 13) | MATCH | rebuttal/results/e9/README.md lines 13-14 (of 29, of 13); paper.txt 3134
L40 | 2 ready checkpoints | MATCH (count) | e9/README.md line 15 ("class c: 2")
L47 | matched 30739; matched_command_only 51 | MATCH | rebuttal/results/e5/db_check/db_summary.json lines 4, 12
L47 | 30,790 commands in total | MATCH | 30739 + 51 (arithmetic)
L47 | code refs run_gpu.py:12, :179; supabase_sink.py:38, :87-95 | MATCH | src/reprocli_repro/tools/run_gpu.py lines 12, 179; supabase_sink.py lines 38, 87-95
L48 | 4 of 6,243 write_evidence rows contain gpu_step_, each a cp | MATCH | rebuttal/results/e5/flags_all.tsv.gz recount (gzip, kind column): 6,243 rows; 4 contain gpu_step_; all 4 contain cp
L55-L59 | repeated short-reply numbers (36/220, 34/180, 19/76, 7/52, 10/92, 35/136, 32/132, 16/132, 32 of 100, 2, 18/11/5) | MATCH | as the lines above; the 32 and 34 carry the L22 note

Verdict counts (45 rows): MATCH 39, MISMATCH 6 (L9, L10, L11, L14, L17, L18), NOT FOUND 0.
Note on the "All 100" block: Table 13 (paper.txt 3699-3704) uses submitted grades (73). The draft's 70 matches Section 5.2 and ev_targets_raw.txt section B only. The rescore (rescore_summary.md line 27) gives 71.
