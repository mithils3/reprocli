# Mismatch check, items 6 to 11

PDF line numbers are paper.txt file lines, with the manuscript margin number in brackets where one exists.

## Item 6. 2506.08898, projections and checkpoint stops

- YGTR_1.md line 37: "three runs projected 33 to 51 hours of retraining and stopped"
- paper.txt 709-710 [462-463]: "5 of 6 frontier runs stopped under one H100-hour of a 32-hour grant because no matching checkpoint is released"
- Data: same_paper_baselines.md 66 gives six frontier runs, five under 1 H100-h (0.18, 0.17, 0.29, 0.61, 0.46) and Muse Wonder in our harness at 27.49.
- early_stop.md 59 says the three cost projections belong to miniswe, codex-gpt-6-astra and codex-gpt-6.1-sol, which are also coded missing artifact at lines 20-22.
- stop_study/README.md 15 gives projected costs 33.2, 50.4 and 51 GPU-hours.
- Class: SAME. The same three runs both projected a cost and stopped with a missing checkpoint. Caveat: stop_study/summary.md 82-103 (11-13, later) codes miniswe and codex-gpt-6.1-sol as shortfall_cost, so the "because no matching checkpoint" cause for all five runs is contested inside the data.

## Item 7. Ungraded cells

- YGTR_2.md 23: "6 cells with no graded run"; paper.txt 618-622 [398-403]: "Of the 400 cells, 28 produced no graded run"; general.md 15: two audits.
- e8/README.md 11 and 17-21; e8/empty_cells_traced.csv (22 data rows: A 2, B 16, C 0, D 4).
- 6: the first six. Four cells of 2510.20725 never started (prompt-rendering bug) and two Muse Spark 1.2 audits never returned (e8/README.md 11; paper.txt 3116-3122 [2093-2095]).
- 28: all cells with no graded run at the e8 build (README 11).
- 5: cells graded since. Three finished runs (PDF text: 0, 2, 0; these grades are not in the e8 files) plus the two audits (paper.txt 3121-3122).
- 2: the two Muse Spark 1.2 audits, 2503.23035 (reproduced) and 2510.08177 (partial), general.md 15.
- 22: the 28 minus the first six, the rows of empty_cells_traced.csv (README 17-19).
- Class: SAME. The comment and the PDF agree; the comment's 6 is the first six only.

## Item 8. Repeat runs

- general.md 3: "repeated runs keep the reproduced verdict on 23 of 27 model and paper pairs" cited to Section 5.2.
- YGTR_2.md 11: "7 keep their verdict" (the 8 x86 pairs).
- paper.txt 359-360 [358-360]: "9 of the 10"; paper.txt 362 [361-362]: "7 of the 9". The string "23 of 27" does not appear in paper.txt, and no x86 repeat count appears there.
- e13/README.md 28: 23 of 27 = 7 of 9 DeepSeek papers + 9 of 10 Muse pairs + 7 of 8 x86 pairs. e13/README.md 46 says Section 5.2 of the second revised PDF prints the figure; the paper.txt here is not that build.
- Class: COMMENT-WRONG on the citation only. The number is correct per e13, but the cited section in this PDF text prints only the 9 of 10 and 7 of 9 parts.

## Item 9. Frontier coverage

- PDF paper.txt 316-317 [315-317]: "we also ran gpt-6-astra and gpt-6.1-sol (OpenAI, 2026e;d) from OpenAI on 24 papers and Muse Wonder (Meta, 2026) from Meta on 6 of them".
- YGTR_1.md 11-17 rows (papers, reproduced): gpt-6.1-sol our harness 12 (5); gpt-6.1-sol Codex CLI 23 (4); gpt-6-astra Codex CLI 8 (3); gpt-6-astra our harness 6 (1); Muse Wonder mini-SWE-agent 6 (4); Muse Wonder our harness 2 (1); total 57 (18).
- frontier/databook frontier_cells.csv (68 rows, the 57 plus nudge and x86 rows) gives distinct papers: gpt-6.1-sol 24 across both harnesses; gpt-6-astra 8 (the six our-harness papers are a subset of the eight Codex papers); Muse Wonder 6. The table rows match the data.
- Class: PDF-WRONG if read per model. The sentence gives 24 for both models. The data gives 24 for gpt-6.1-sol and 8 for gpt-6-astra. The union of both is 24.

## Item 10. Reruns of partial runs

- rqBN_1.md 17: "On two papers our reruns repeat the agent's number (on 2506.10351, ...)"; the third is 2510.07501.
- YGTR_2.md 32: "In all three, the agent's number is what the released pipeline gives".
- e10/results.md 5-7: 2505.17836 repeats within 0.0007 (0.0395 original, 0.0400 and 0.0393 seeds); 2506.10351 seeds 93.65 and 94.15 against 94.19; 2510.07501 seeds -0.1308 and +0.0566 against -0.2241, a spread of 0.28.
- "two" in rqBN means 2505.17836 and 2506.10351 (rqBN names only one; the other is implied). "three" in YGTR_2 counts all reruns, and it includes 2510.07501, which does not repeat the agent's number.
- Class: COMMENT-WRONG for YGTR_2 line 32. rqBN is consistent with the data.

## Item 11. 96-hour band in the PDF

- paper.txt 137-138 [85-86]: "the 48 cells in the 96 H100-hour band spend 6.2% ... and 1 of them reproduces its claim (Section 5.4)".
- paper.txt 727-728 [476-477]: "while none of them reproduces its claim".
- Data: tools/anon_viewer/public/data/index.json, papers with band 32-96 (12 papers), 42 graded runs. Before the revision's corrections, one reproduced run (muse-retrain-2508.21046, score 9). tiers/tier_tests.md lists that run among the four removed. After removal, 0 of 42 reproduce.
- Class: PDF-INTERNAL. The data supports Section 5.4 ("none"). The introduction's "1" is the figure before the checkpoint correction.
