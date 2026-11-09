# Fact-check of the four contradictions in followups.md

Checked on 2026-11-08 against rebuttal/drafts/replies.md, paper_latex/iclr2027_conference.tex, paper_latex/appendix/e_construction.tex, and rebuttal/results/. No file was edited.

## Item 1: targets had no independent check (rqBN)

Verdict: CONFIRMED. Author decision.

- replies.md:168: "so the claims, minimal configurations and targets had no independent check and there was no annotator agreement to report."
- iclr2027_conference.tex:668: "Every extracted field was reviewed by an author before the dataset was frozen."

Stage III (iclr2027_conference.tex:372 and e_construction.tex:80 to 92) covers the availability calls only, so the reply is right about Stage III. The generative AI statement covers every extracted field, and the pinned match targets are among them. An author review of the extractor's output is a check the extractor did not make, so the two sentences conflict.

Author decision: did the author review cover the claim, minimal configuration and target fields?
- If yes, replace the replies.md:168 text "had no independent check and there was no annotator agreement" with "had only an author review of each extracted field, with no second check and no annotator agreement". Keep the paper as written.
- If no, the paper sentence at line 668 must change instead.

Also, replies.md:168 says "The revision states this in Appendix E." The Appendix E file on disk does not state it.

## Item 2: "at most 27" failed outside the agent (YGTR)

Verdict: PARTLY.

- replies.md:234: "Yes, and at most 27 of the 400 cells failed for reasons outside the agent: 6 of the 28 cells with no graded run and 21 graded runs that failed on the environment ... 16 further cells were stopped by the cluster job"
- iclr2027_conference.tex:584 to 585: "for the 76 runs that executed a faithful pipeline and landed outside tolerance we cannot separate agent error from seed and hardware variance."

The 16 cluster stops are outside the 27, and the 76 are graded runs that are also outside the 27, so the arithmetic is consistent. The problem is wording. "At most 27" reads as an upper bound on failures outside the agent, and the Limitations says the 76 cannot be attributed. The reply also says "The count is an upper bound because 3 of the 12 aarch64 installs ... also fail on x86", which does not follow, because an x86 failure leaves the cause outside the agent.

Smallest edit to replies.md:234 (three exact replacements):
1. Old: "Yes, and at most 27 of the 400 cells failed for reasons outside the agent:"
   New: "Yes, and 27 of the 400 cells failed for reasons we traced outside the agent:"
2. Old: "The count is an upper bound because 3 of the 12 aarch64 installs we replayed also fail on x86."
   New: "The count is a traced count and does not bound the failures: 3 of the 12 aarch64 installs we replayed also fail on x86, so their cause is still open."
3. Old: "(Section 5.2 and Section 5.3)."
   New: "(Section 5.2 and Section 5.3). The 76 runs that ran a faithful pipeline and missed are not in this count, and the Limitations section says we cannot attribute them."

Related: rebuttal/results/e8/x86/README.md says 2 of the 16 aarch64 builds "were not chip failures", so the 27 may be 25 (see the separate item on the aarch64 count).

## Item 3: Muse Spark Retrain 9/32 in the bound table

Verdict: CONFIRMED.

- replies.md:63 and replies.md:223 (identical table rows): "| Retrain | 6 | 9/33 = 27% [15%, 44%] | 9/32 = 28% [16%, 45%] |"
- replies.md:90: "Muse Spark's Retrain count goes from 9/33 to 8/33"
- rebuttal/results/e8/bound.csv: muse retrain bound_all is 9 of 32; dsv4 retrain bound_all is 9 of 33 with no environment runs.

The 9/32 is Muse before the checkpoint correction. Corrected, Muse is 8/32 = 25%. The best Retrain agent with the 24 runs removed is then DeepSeek-V4-Flash at 9/33 = 27%, with Wilson interval 15% to 44% (bound.csv, dsv4 retrain bound_all_lo 0.1507, hi 0.4422).

Smallest edit:
1. replies.md:63 and replies.md:223, old: "| Retrain | 6 | 9/33 = 27% [15%, 44%] | 9/32 = 28% [16%, 45%] |" new: "| Retrain | 6 | 9/33 = 27% [15%, 44%] | 9/33 = 27% [15%, 44%] |"
2. replies.md:112, old: "bound 14/34, 9/32, 5/32" new: "bound 14/34, 9/33, 5/32 (Muse Retrain corrected to 8/32 per YGTR part 2)"
3. replies.md:243, old: "Retrain 9/32, Reimplement 5/32" new: "Retrain 9/33, Reimplement 5/32"

Reimplement (5/32) is unchanged by the checkpoint correction, because the Muse Reimplement count does not change.

## Item 4: headline count 73/400 and best Run 14/34

Verdict: PARTLY. The 73 is CONFIRMED. The 14/34 depends on an author decision.

Count of 73:
- replies.md:56: "the overall count is 73/400 = 18% [15%, 22%]". This is not bracketed.
- replies.md:232 reclassifies two reproduced checkpoint runs as not reproduced.
- replies.md:234 grades two missing audits: 2503.23035 reproduced (score 8) and 2510.08177 partial (score 6). rebuttal/results/e8/regrade_muse.json confirms both. 2503.23035 is a Muse run at the Run tier.
- Arithmetic: 73 + 1 − 2 = 72. The Wilson interval for 72/400 is 14.5% to 22.1%, which still rounds to [15%, 22%].

Smallest edit:
1. replies.md:56, old: "the overall count is 73/400 = 18% [15%, 22%]" new: "the overall count is 72/400 = 18% [15%, 22%]"
2. replies.md:110, old: "14/34, 9/33, 5/33, 73/400 and their Wilson intervals" new: "14/34, 9/33, 5/33, 72/400 and their Wilson intervals"; and old: "interval for 73/400 computed" new: "interval for 72/400 computed"

Muse's Run count moves from 9/34 to 10/34 because of 2503.23035. No reply quotes Muse's Run rate, and the best Run rate is still DeepSeek's 14/34, so no edit is needed for that.

Count of 14/34:
- The 13/34 figure comes from rebuttal/results/e7/rescore_summary.md:27. It applies only if the 10 target corrections are final, and the followups file says the second pre-read pass is still running.
- replies.md:29 brackets "[k] targets the paper does not support were corrected and their runs rescored", but 14/34 appears unbracketed at replies.md:25, 37, 56, 63 and 222.
- Author decision: are the 10 target corrections final? If yes, the best Run rate becomes 13/34 = 38% and the overall count becomes 70 (73, minus 2 from the rescore, plus 1 grade, minus 2 checkpoint runs, all from files above). If no, keep the bracket as written and the 14/34 stands with k still open.

Unrelated but visible: replies.md:42 quotes "73 against 83 reproductions". That is the auditor matrix over the 372 graded runs (rebuttal/results/e4/summary.json, total row), taken before the two new grades. It is not contradicted, but it will read as stale beside the 72.
