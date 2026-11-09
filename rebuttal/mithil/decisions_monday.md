# Decisions before posting the ICLR rebuttal (Monday 2026-11-09)

Line numbers refer to rebuttal/drafts/replies.md as of 2026-11-08. Ordered by lines touched, most first.

replies.md has 5 [AUTHOR: ...] notes. Line 3 only mentions the marker. Line 63 holds two notes. Map: 63a (73 becomes 72, 14/34 becomes 13/34, Risk 5, E7) is decisions 1, 2, 4, 6, 7. 63b (Muse mean 5.14) is decision 4. Line 179 is decision 17. Line 231 is decision 15. Line 249 is decision 5.

**1. Keep the 10 target corrections? (15 lines: 29, 37, 60, 63, 65, 69, 96, 111, 119, 191, 206, 237, 261, 262, 286)**
Question: Do the 10 corrections in rebuttal/results/e7/rescore_summary.md stand, out of the 45 targets with a failed question? yes / no
Change: best Run 14/34 = 41% becomes 13/34 = 38%. All-agent 73 becomes 70 [followups_check_1.md:75]. Brackets k at 29, 60, 111, 191 take the count.
Decision: ______

**2. Base of graded runs: 372 or 377? (12 lines: 27, 31, 49, 75, 84, 129, 132, 145, 153, 199, 210, 249)**
Question: Keep 372 as the base and say five later grades are separate, or recount over 377? keep 372 / recount 377
Change: 372 becomes 377 (five grades: 2503.23035 at 8, 2510.08177 at 6, three regraded runs at 0, 2, 0) [consistency_check.md Flag 3]. Line 249 says every rate includes these grades, which holds only for 377.
Decision: ______

**3. Widen the re-execution beyond 3 papers? (9 lines: 20, 143, 177, 205, 211, 215, 241, 265, 292)**
Question: Add near-miss papers from the 8 to 32 GPU-hour band? yes / no
Change: "3 papers" (177, 205, 241) becomes a count not yet set. Spreads 0.0007 and 0.28 at 177 and 241 get new rows.
Decision: ______

**4. Count the two new Muse Spark grades? (8 lines: 27, 46, 63, 96, 99, 117, 120, 124)**
Question: Count the 8 on 2503.23035 and the 6 on 2510.08177 [e8/regrade_muse.json]? yes / no
Change: all-agent 73 of 400 becomes 72 of 400 = 18% [15%, 22%] with yes, or 71 with no (the two checkpoint runs are already not reproduced) [followups_check_1.md; consistency_check.md Flag 2]. Muse mean 5.00 becomes 5.14 with yes (5.00 + 14/100, the empty cells scored 0), above DeepSeek 5.13 [paper iclr2027_conference.tex:463-466]. With no, the mean stays 5.00.
Decision: ______

**5. Keep the 16-stopped-cells admission? (8 lines: 31, 42, 225, 249, 251, 272, 274, 287)**
Question: Admit that 16 of the 28 cells with no graded run stopped at the 48-hour limit or were cancelled? That reverses the paper's rule that all 28 are model failures. keep / cut
Change: keep: line 249 stands, and the paper's zero rule (appendix/b_models.tex:128) needs the sentence in replies_check.md item 4. Cut: the paper's count of 28 stands and the clause leaves 31 and 249.
Decision: ______

**6. Move CogVLA to Run? (7 lines: 63, 119, 247, 262, 270, 271, 290)**
Question: Move 2508.21046 from Retrain to Run because its release covers the claimed checkpoint? yes / no (CURE, 2505.12677, is Reimplement, so the rule does not move it)
Change: Muse Retrain 9 of 33 becomes 8 of 33 at 247 (and 262, 271) [e9/class_review.csv]. With yes, Run goes 34 to 35 and Retrain 33 to 32 [e6/summary.json]; rates are recomputed.
Decision: ______

**7. Settle the nine E7 items? (6 lines: 63, 177, 211, 241, 249, 265)**
Question: Give keep or change for each item in rebuttal/mithil/e7_merged.md, "Look at these first": 1 2505.15201 variance; 2 2505.17836 GoRank near 0.05; 3 2507.02064 recall near 0 cm; 4 2505.19154 training views; 5 2505.24873 32-frame sentence; 6 2506.18896 which 84.8; 7 2402.04579 Moons dataset; 8 2510.20725 RBF curve; 9 2511.02225 FIOC 0.95.
Change: item 2 touches the 0.05 target at 177, 211, 241, 265. Item 8 touches 2510.20725 at 249. Others feed decision 1 (lines 29, 60, 111, 191).
Decision: ______

**8. Other environment or agent error for the 2 "not chip" build rows? (6 lines: 65, 119, 233, 251, 259, 263)**
Question: Count them as other environment (14 aarch64, 7 other, 3 agent) or agent error (14, 5, 5)? other / agent
Change: draft reads 14, 7, 3 [followups_check_2.md item 1]. Agent error gives "6 + 14 + 5 = 25" at 251 and changes the 27.
Decision: ______

**9. Cancel 13 orphaned GPU requests? (6 lines, indirect: 31, 133, 215, 249, 282, 287)**
Question: Cancel the 13 requests with no live launcher (3548889 to 3555340, rebuttal/results/spend/pending_gpu_jobs.md line 64)? yes / no
Change: no sentence changes. The requests are older than every live job, so they would start first and delay the reruns. Cancelling needs your approval.
Decision: ______

**10. Report gpt-6.1-terra? (5 lines: 23, 41, 222, 227, 260)**
Question: Report gpt-6.1-terra or drop it from the plan? report / drop
Change: replies.md never names terra, but rebuttal/PLAN.md:115 and :189 include it. Report adds it to 23, 222, 227, 41, 260 with no number yet. Drop edits PLAN.md only.
Decision: ______

**11. Explain the 3 unmatched log entries? (4 lines: 170, 173, 200, 204)**
Question: Keep "we have not yet traced why" (line 173), or trace the 3 before posting? keep / trace
Change: keep: 3 of 45,861 stay unexplained. Trace: 173 gives a cause and 170, 200, 204 may change [followups_check_4.md].
Decision: ______

**12. Run a second blind grader? (4 lines: 153, 199, 229, 288)**
Question: Have a second blind grader label about 40 runs stratified by verdict, and an author label 20 frontier runs blind? yes / no
Change: yes fills the bracket at 153 and the [x] of 20 at 229. No: "one label per run" at 199 stays and no agreement figure can be reported.
Decision: ______

**13. Approve a Codex variant with fixed "continue" prompts? (3 lines: 227, 229, 289)**
Question: Run a small variant to test the early stop? yes / no
Change: the first ten frontier runs used a median under 2% of their GPU grant [rebuttal/results/frontier/run_usage_summary.md]. Yes: 229 takes the new median and 227 gets a row. No: 289 stays an open risk.
Decision: ______

**14. Trace the 63 evidence directories? (3 lines: 88, 162, 293)**
Question: Trace what touched the 63 directories modified over 60 seconds after run end? yes / no
Change: yes: 162 can say whether they were a cleanup. No: 293 stays open.
Decision: ______

**15. Keep the same-family reason for leaving out Claude Code? (2 lines: 231, 279)**
Question: Keep "our auditor is Claude Sonnet 5", use the billing reason from PLAN.md:200, or write your own? keep / billing / own
Change: 279 cites the same fact and changes with 231.
Decision: ______

**16. "Strongest" or "highest mean audit score"? (1 line: 63; paper lines 121, 463, 618-619)**
Question: Keep "strongest agent" with mean audit score as its basis (A), or write "highest mean audit score" (B)? A / B
Change: B changes 63. If decision 4 gives Muse 5.14, A is false, so B is the only option that holds [followups_check_3.md:20].
Decision: ______

**17. Did the author review cover the claim, configuration and target fields? (1 line: 179; paper line 668)**
Question: Did it? yes / no
Change: yes: 179 becomes "had only an author review of each extracted field, with no second check and no annotator agreement" [followups_check_1.md:15]. No: paper iclr2027_conference.tex:668 changes instead.
Decision: ______

---

Not decisions: Risk 6 is closed. The consistency Flag 1 was settled by the main session. Bracketed result slots that wait on runs are not decisions.
