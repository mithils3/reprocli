# Paper revisions found by the rebuttal fact-checks

Paper-side fixes for paper_latex/, recorded here for a later paper edit. One line each, with the file and line and the source of the correct value.

## From the follow-up checks of 2026-11-08

- paper_latex/appendix/c_rubric.tex:126: "the 25 cells that have no graded run" becomes "the 28 cells that have no graded run" (source: rebuttal/results/e8/summary.json:110, empty_cells total 28; followups_check_2.md item 5).
- paper_latex/appendix/c_rubric.tex:130: "the 55 runs the auditor zeroed" becomes "the 53 runs the auditor zeroed", after checking the histogram source (source: rebuttal/results/e4/summary.json:17-18, auditor_col_totals 53 at score 0; followups_check_2.md item 5).
- paper_latex/iclr2027_conference.tex:463: "DeepSeek-V4-Flash is the strongest agent." becomes a sentence naming it the agent with the highest mean audit score (5.13 against 3.03 for MiniMax-M2.7, lines 463-466), with the same change at lines 121 and 618-619, because the Run intervals of DeepSeek-V4-Flash (26% to 58%) and Muse Spark (15% to 43%) overlap (source: rebuttal/results/e8/bound.csv rows dsv4 run and muse run; followups_check_3.md item 8; the T29u part 1 reply already announces this wording).
- paper_latex/iclr2027_conference.tex:668: "Every extracted field was reviewed by an author before the dataset was frozen." waits on the author's item 1 decision: it stays if that review covered the claim, configuration and target fields, and otherwise it is narrowed to the fields the review did cover (source: followups_check_1.md item 1; replies.md rqBN part 2 [AUTHOR] note).
