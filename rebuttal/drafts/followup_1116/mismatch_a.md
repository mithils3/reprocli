# Mismatch check, five items

Paths: comments in rebuttal/post/. PDF = scratchpad followup_1116/paper.txt (line numbers are paper.txt lines). Data in rebuttal/results/.

## 1. Run tier tolerance row. Class: SAME

- Comment rqBN_1.md:21: "against 9, 12, 14 and 14 of 34 at Run (Appendix F)". Comment general.md:17: "reproduces 13 of 34 Run". PDF Section 5.2, paper.txt:554: "13 of 34 Run-tier papers". PDF E.6, paper.txt:2567-2568: "DeepSeek-V4-Flash then reproduces 13 of 34 Run papers where the submission reported 14".
- PDF Table 18 note, paper.txt:2803: "The table uses the grades as submitted".
- Data, submitted grades: rebuttal/results/e6/README.md (table) gives Run 9, 12, 14, 14 at 1%, 2%, 5%, 10%. e6/table.csv has dsv4 Run reproduced at 5% = 14 rows.
- Data, revised grades: rebuttal/results/e7/rescore_summary.md:23 gives "dsv4 14 = 41.2%" against "dsv4 13 = 38.2%" after the 2505.23747 correction.
- Both are right for their set. The rqBN 14 is as submitted and does not say so, while the same paragraph describes the corrections. The fact a reader needs: 14 is as submitted, 13 is after the 2505.23747 correction.

## 2. Commands in the log comparison. Class: COMMENT-WRONG

- Comment rqBN_1.md:9: "the 30,790 commands present in both the logs and the database have the same text, no exit code differs".
- PDF A.5, paper.txt:2764-2765: "Of these, 30,739 match a commands.log entry on command and return code, and another 51 match on command while their result row did not reach the database".
- Data: rebuttal/results/e5/db_check/db_summary.json: matched 30739, matched_command_only 51, db_result_row_missing 51, runs_with_rc_differs 0. rebuttal/results/e5/README.md:33 defines the 51 as "matched on command, result row never reached the database (best-effort sink)".
- The 51 are calls whose database result row (seq+1) is absent. The database holds no exit code for them, so "no exit code differs" was not compared for them. The rc = 0 difference count covers only the 30,739. The comment applies the exit-code claim to all 30,790. The PDF wording is accurate.

## 3. Target check. Class: COMMENT-WRONG (general.md:6)

- Comment general.md:6: "It supports 92 of the 100, and the other 8 are corrected." Comment rqBN_1.md:21: "confirmed our value for 92 of the 100 claims". PDF E.6, paper.txt:2549-2563 (Table 15 and text): 55 pass all four; "the frozen number is wrong on 8, the number is right but a setting or label is off on 16, and the target is correct or the paper is ambiguous on 21"; "We corrected the 8 numbers to the paper's value and rescored their runs".
- Data, rebuttal/results/e7/summary.json: step3 by_question a.yes = 92 (paper reports this value within rounding); all_four_yes = 55.
- Data, rebuttal/mithil/e7_merged.md (45 items): "wrong / wrong / number" = 8 (2505.23747, 2510.04136, 2511.00090, 2506.01511, 2506.18896, 2505.16927, 2505.24864, 2510.10480); "setting or label" = 16; "none" = 21.
- 92 counts question (a) alone. The 8 that fail (a) (comparison.csv v3_a_yes=False) are 2505.23747, 2510.04136, 2511.00090, 2505.15201, 2505.17836, 2510.09485, 2510.05874, 2507.02064. Only three of these are in the 8 number-wrong list. So "the other 8 are corrected" does not hold.
- Corrections: the PDF says the 8 numbers were corrected and rescored. On disk, rebuttal/results/e7/corrected_targets.jsonl and rescore_summary.md cover 10 different targets, sharing five with the 8. The three remaining number-wrong targets were checked in results/e7/class_d_rescore.md and change no verdict. The paper does not say what was done about the 16; it only classifies them.

## 4. Score 0. Class: UNCLEAR

- Comment rqBN_1.md:5: "a high-severity flag sets a run's score to 0".
- PDF Appendix D, paper.txt:3589-3590: "A score of 0 covers a high-severity integrity flag and three related conditions (Table 10)".
- Table 10, paper.txt:3442-3446: "Any high-severity anti-cheat flag, a report whose verdict contradicts its own evidence, a proxy substituted into the target slot, or a retrieved benchmark answer the graded value runs through." The three related conditions are the second, third and fourth items.
- Data: rebuttal/results/e4/README.md:16 gives "Score 0 (high-severity flag) | human 46, auditor 53, both 42, either 57". Per-run severity is not on disk (e4 has only the aggregate matrix; e5 flag files have no severity field). High-severity count for auditor score 0: not on disk.
- Closest per-run file: rebuttal/results/e6/table.csv. 53 rows have index_score 0, and all 53 have cheat_flags_med_high > 0. That column merges medium and high, so it does not isolate high.

## 5. Reproduced count. Class: SAME

- Comment rqBN_1.md:5: "$\frac{64}{73}$ = 88%" and "$\frac{64}{83}$ = 77%". Comment general.md:9: "Three changes take the reproduced cells from 73 to 70 of 400".
- Data, rebuttal/results/e4/README.md:15: "Reproduced (8 or more): auditor 73, human 83, both 64 | precision 64/73 = 88%, recall 64/83 = 77%". So 73 is the auditor's count and 83 is the human's, both at submission, on the 372 runs both graded.
- The 73 is not the human count. The human comparison uses 83 as the human side and 73 as the auditor side.
- Grade set: PDF paper.txt:291 says "it calls 73 of the submitted runs reproduced where the humans call 83". PDF Table 13 caption, paper.txt:3706: "Reproduced cells under the auditor's and the human grade as submitted". The 70 of 400 is after three post-submission changes (general.md:9-15). Both 73s are the submitted auditor count, since cells with no run count as not reproduced.
