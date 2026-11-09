# Fact-check of followups.md contradictions 5, 6 and 7

Read only. No file was edited and nothing was committed.

## Item 5: no auditor grade and empty cells

Verdict: CONFIRMED, with a second mismatch in the paper.

Quotes:
- rebuttal/drafts/replies.md:68: "(the other 24 runs that started have no auditor grade)"
- rebuttal/drafts/replies.md:31: "We traced all 28 cells that produced no graded run."
- paper_latex/appendix/c_rubric.tex:126: "the 25 cells that have no graded run counted at 0."
- paper_latex/appendix/c_rubric.tex:130: "the 55 runs the auditor zeroed for an integrity break"

What the files show:
- rebuttal/results/e8/summary.json:110 gives "total": 28 empty cells.
- The replies are internally consistent: 396 started minus 372 graded is 24, and 4 never-started cells plus 24 is 28.
- rebuttal/results/e8/README.md:27 says 4 of the empty cells (minimax 2506.18896, qwen3 2511.19808, qwen3 2510.25529, qwen3 2510.19314) finished with a report, score or verdict on disk. So "no auditor grade" is wrong for those 4, though they are outside the 372-run matrix.
- rebuttal/results/e4/summary.json:17-18 gives auditor_col_totals with 53 at score 0. The paper says 55 zeros, so the 55 does not match the matrix.

Smallest replies.md edit (removes the 24 versus 28 wording clash and the no-grade claim):
- Old: "(the other 24 runs that started have no auditor grade)"
- New: "(the other 24 runs that started are not in the graded set)"

This does not fix Appendix C, which must change too. c_rubric.tex:126 "25" should read "28" (matches e8/summary.json:110), and c_rubric.tex:130 "55" should read "53" (matches e4/summary.json:18), after checking the histogram source. Those edits are in the paper, not in replies.md.

Not checked: the replies' split of the 28 (16 job limit, 4 unknown) differs from e8/summary.json's categories (17 with no run directory or orphan launch, 3 with run finished and no entry). Not resolved here.

## Item 6: 16 aarch64 failures

Verdict: CONFIRMED.

Quotes:
- rebuttal/drafts/replies.md:58: "our reading of their transcripts traces 16 of them to a package that has no build for the aarch64 CPUs of our GH200 nodes"
- rebuttal/drafts/replies.md:218: "traces 16 of them to a package with no build for the aarch64 CPUs of our GH200 nodes"
- rebuttal/results/e8/x86/README.md:4: "The other 4 rows are excluded: 2 were not chip failures (MiniMax's vLLM install returned 0 on aarch64; Qwen's spconv failed on the cp312 ABI tag), and 2 have no install command in the transcript."
- rebuttal/results/e8/x86/results.csv lines 14-15 mark minimax 2504.20571 and qwen3 2506.20671 as "not_arch".

The 16 is a label count (e8/x86/README.md:1 says "Of the 16 build failures labelled aarch64-caused"). Only 12 rows are aarch64 by replay (results.csv lines 2-13).

Smallest replies.md edit (line 58; line 218 needs the same change):
- Old: "traces 16 of them to a package that has no build for the aarch64 CPUs of our GH200 nodes"
- New: "traces 14 of them to a package that has no build for the aarch64 CPUs of our GH200 nodes"

Author decision: the 2 excluded rows move to the "5 other environment" class, so the split becomes 14 aarch64, 7 other environment, 3 agent error. The same change applies at replies.md:112, :218, :234 (the "6 + 16 + 5 = 27" sum becomes "6 + 14 + 7 = 27") and :242. The author should confirm that the 2 "not chip" rows count as other environment and not as agent error.

## Item 7: all three reviewers agree the design is sound

Verdict: CONFIRMED.

Quotes:
- rebuttal/drafts/replies.md:11: "They agree that the task and the grading design are sound and well documented"
- rebuttal/reviews-2026-11-06.md:35 (rqBN): "Evaluator and evidence validity are also material concerns."
- rebuttal/reviews-2026-11-06.md:19 (T29u): "The evaluation and diagnostic design is unusually careful."
- rebuttal/reviews-2026-11-06.md:45 (YGTR): "The task and evaluation design is sound, explained in detail and reusable."

Only YGTR says "sound". T29u says "unusually careful" and rqBN raises a material concern about evaluator validity.

Smallest replies.md edit (line 11):
- Old: "They agree that the task and the grading design are sound and well documented"
- New: "Two reviewers praise the task and evaluation design, T29u calling it unusually careful and YGTR calling it sound, and rqBN calls evaluator validity a material concern"

No author decision needed.
