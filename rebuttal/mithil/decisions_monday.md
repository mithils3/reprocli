# Decisions before posting the ICLR rebuttal (Monday 2026-11-09)

Line numbers refer to rebuttal/drafts/replies.md at commit 9bcf851. Ordered by lines touched, most first.

replies.md has 5 [AUTHOR: ...] notes. Line 3 only mentions the marker. Line 60 holds the 73 note and line 62 the Muse note. Map: 60 (73 becomes 72, 14/34 becomes 13/34, Risk 5, E7) is decisions 1, 2, 4, 6, 7. 62 (Muse mean 5.14) is decision 4. Line 246 is decision 18. Line 248 is decision 15. Line 296 is decision 5. Decision 17 cites line 188, which has no note.

**1. Keep the 10 target corrections? (13 lines: 95, 24, 47, 60, 252, (cut in the 11-08 rewrite), 99, 192, 113, 194, 213, (cut in the 11-08 rewrite), 306, 307, 331)**
Question: Do the 10 corrections in rebuttal/results/e7/rescore_summary.md stand, out of the 45 targets with a failed question? yes / no
Change: best Run 14/34 = 41% becomes 13/34 = 38%. All-agent 73 becomes 70 [followups_check_1.md:75]. Brackets k at 47 and 196 take the count.
Recommended: settle decision 7 first, then keep a correction only where you agree the number itself is wrong. The second pass (e7_merged.md) finds 8 targets with a wrong number and 16 where only a setting or label is off, so the final count may be 8 rather than the 10 in rescore_summary.md.
Checked 11-08 (rebuttal/mithil/e7_ten_vs_eight.md, rebuttal/results/e7/class_d_rescore.md): the two lists share 5 targets with a wrong number, and only one of those, 2505.23747, changes verdicts (DeepSeek-V4-Flash and MiniMax-M2.7 at Run). The 3 targets the rescore never corrected (2510.04136, 2506.01511, 2505.24864) change no verdict: the one reproduced cell among them, Qwen on 2506.01511, scores 8 under both targets. So the counts are the same under either rule, and the choice only sets whether the reply names 10 corrected targets or 8.
Decision: ______

**2. Base of graded runs: 372 or 377? (12 lines: 14, 17, 36, 74, 85, 123, 126, 141, 153, 206, 217, 290)**
Question: Keep 372 as the base and say five later grades are separate, or recount over 377? keep 372 / recount 377
Change: 372 becomes 377 (five grades: 2503.23035 at 8, 2510.08177 at 6, three regraded runs at 0, 2, 0) [consistency_check.md Flag 3]. Line 290 says every rate includes these grades, which holds only for 377.
Recommended: keep 372 for the auditor-against-human table, since that study is fixed, and report the five later grades in one separate sentence. Line 290 then says the benchmark rates include them while the agreement figures do not.
Decision: ______

**3. Widen the re-execution beyond 3 papers? (9 lines: 17, 137, 177, 212, 218, 222, 258, 310, 337)**
Question: Add near-miss papers from the 8 to 32 GPU-hour band? yes / no
Change: "3 papers" (177, 212, 258) becomes a count not yet set. Spreads 0.0007 and 0.28 at 178 and 179 get new rows.
Recommended: no. The ghx4 queue is waiting 200 to 960 minutes per request, so new re-executions are unlikely to finish by 11-16. Say that 3 papers had a single clean command chain and leave it there.
Decision: ______

**4. Count the two new Muse Spark grades? (8 lines: 14, 33, 60 and 62, 99, 99, 111, 114, 118)**
Question: Count the 8 on 2503.23035 and the 6 on 2510.08177 [e8/regrade_muse.json]? yes / no
Change: all-agent 73 of 400 becomes 72 of 400 = 18% [15%, 22%] with yes, or 71 with no (the two checkpoint runs are already not reproduced) [followups_check_1.md; consistency_check.md Flag 2]. Muse mean 5.00 becomes 5.14 with yes (5.00 + 14/100, the empty cells scored 0), above DeepSeek 5.13 [paper iclr2027_conference.tex:463-466]. With no, the mean stays 5.00.
Recommended: yes. Both are grades by the pinned auditor on runs that finished, and leaving them out scores finished work as 0. This gives 72 of 400 (or 71 if you also drop the two checkpoint runs) and the mean list without a ranking word.
Decision: ______

**5. Keep the 16-stopped-cells admission? (8 lines: 17, 29, 232, 288, 292, 317, 319, 332)**
Question: Admit that 16 of the 28 cells with no graded run stopped at the 48-hour limit or were cancelled? That reverses the paper's rule that all 28 are model failures. keep / cut
Change: keep: line 288 stands, and the paper's zero rule (appendix/b_models.tex:128) needs the sentence in replies_check.md item 4. Cut: the paper's count of 28 stands and the clause leaves 17 and 288.
Recommended: keep. The cluster's job accounting shows it, and a reviewer who finds it later would trust the rest less. State it once, plainly, with the paper's zero rule as the reason the paper counted them.
Decision: ______

**6. Move CogVLA to Run? (7 lines: 54, 113, 280, 307, 315, 316, 335)**
Question: Move 2508.21046 from Retrain to Run because its release covers the claimed checkpoint? yes / no (CURE, 2505.12677, is Reimplement, so the rule does not move it)
Change: Muse Retrain 9 of 33 becomes 8 of 33 at 280 (and 307, 316) [e9/class_review.csv]. With yes, Run goes 34 to 35 and Retrain 33 to 32 [e6/summary.json]; rates are recomputed.
Recommended: no move. The evaluation split is frozen, so keep the tier and add a footnote that the release covers the claimed checkpoint. Moving a paper between tiers during the rebuttal invites the question of what else moved.
Decision: ______

**7. Settle the nine E7 items? (6 lines: 52, 178, 218, 258, 286, 310)**
Question: Give keep or change for each item in rebuttal/mithil/e7_merged.md, "Look at these first": 1 2505.15201 variance; 2 2505.17836 GoRank near 0.05; 3 2507.02064 recall near 0 cm; 4 2505.19154 training views; 5 2505.24873 32-frame sentence; 6 2506.18896 which 84.8; 7 2402.04579 Moons dataset; 8 2510.20725 RBF curve; 9 2511.02225 FIOC 0.95.
Change: item 2 touches the 0.05 target at 178 and 218. Item 8 touches 2510.20725 at 286. Others feed decision 1 (lines 95, 47, 192, 194).
Decision: ______

**8. Other environment or agent error for the 2 "not chip" build rows? (6 lines: 252, 113, 252, 292, 304, 308)**
Question: Count them as other environment (14 aarch64, 7 other, 3 agent) or agent error (14, 5, 5)? other / agent
Change: draft reads 14, 7, 3 [followups_check_2.md item 1]. Agent error gives "6 + 14 + 5 = 25" at 292 and changes the 27.
Recommended: other environment, as drafted (14, 7, 3). The x86 replay places the cause outside the chip, and nothing in the transcripts places it in the agent's commands.
Decision: ______

**9. Cancel 13 orphaned GPU requests? (6 lines, indirect: 17, 127, 222, 286, 327, 332)**
Question: Cancel the 13 requests with no live launcher (3548889 to 3555340, rebuttal/results/spend/pending_gpu_jobs.md line 64)? yes / no
Change: no sentence changes. The requests are older than every live job, so they would start first and delay the reruns. Cancelling needs your approval.
Recommended: yes. Each would hold a GPU node with nothing attached and push the reruns back.
Decision: ______

**10. Report gpt-6.1-terra? (5 lines: 236, 28, 229, 236, 305)**
Question: Report gpt-6.1-terra or drop it from the plan? report / drop
Change: replies.md never names terra, but rebuttal/PLAN.md:115 and :189 include it. Report adds it to 236, 229, 28 and 305 with no number yet. Drop edits PLAN.md only.
Recommended: drop. No gpt-6.1-terra run exists in frontier_cells.csv, so there is nothing to report by 11-16.
Decision: ______

**11. Explain the 3 unmatched log entries? (4 lines: 161, 163, 207, 211)**
Question: Keep "we have not yet traced why" (old line 173; now line 161), or trace the 3 before posting? keep / trace
Change: keep: 3 of 45,861 stay unexplained. Trace: 161 gives a cause and 163, 207, 211 may change [followups_check_4.md].
Settled by the 11-08 trace (rebuttal/results/e5/traces_2026-11-08.md): each gap equals the GPU release charge logged after the entry. Lines 161 and 211 now say so.
Decision: none needed

**12. Run a second blind grader? (3 lines: 153, 206, (cut in the 11-08 rewrite), 333)**
Question: Have a second blind grader label about 40 runs stratified by verdict, and an author label 20 frontier runs blind? yes / no
Change: yes fills the bracket at 153 and the [x] of 20 (cut in the 11-08 rewrite). No: "one label per run" at 206 stays and no agreement figure can be reported.
Decision: no (Mithil, 11-08). The second-grader slot (old line 153) and the 20 blind frontier labels (old line 229) are removed; one label per run stays.

**13. Approve a Codex variant with fixed "continue" prompts? (3 lines: 236, 240, 334)**
Question: Run a small variant to test the early stop? yes / no
Change: the first ten frontier runs used a median under 2% of their GPU grant [rebuttal/results/frontier/run_usage_summary.md]. Yes: 240 takes the new median and 236 gets a row. No: 334 stays an open risk.
No decision needed: this arm is already running (gpt-6.1-sol, 8 papers, up to 3 continue prompts). Line 240 takes its median when it finishes.
Decision: ______

**14. Trace the 63 evidence directories? (3 lines: 70, 161, 338)**
Question: Trace what touched the 63 directories modified over 60 seconds after run end? yes / no
Change: yes: 161 can say whether they were a cleanup. No: 338 stays open.
Traced on 11-08: 9 directories hold the auditor's own writes, 49 changed only the directory time (38 on 2026-10-29, the cleanup day), and 5 directories with 6 files have no writer found. The replies never cite the 63, so no reply sentence changes; Risk 8 records this.
Decision: none needed

**15. Keep the same-family reason for leaving out Claude Code? (2 lines: 244, 324)**
Question: Keep "our auditor is Claude Sonnet 5", use the billing reason from PLAN.md:200, or write your own? keep / billing / own
Change: 324 cites the same fact and changes with 244.
Recommended: billing as the reason, with the same-family grading point as a second sentence. Post the reason that actually drove the choice.
Decision: ______

**16. "Strongest" or "highest mean audit score"? (1 line: 56; paper lines 121, 463, 618-619)**
Question: Keep "strongest agent" with mean audit score as its basis (A), or write "highest mean audit score" (B)? A / B
Change: B changes 56. If decision 4 gives Muse 5.14, A is false, so B is the only option that holds [followups_check_3.md:20].
Settled on 11-08: line 56 now lists each agent's mean (5.13, 5.00, 3.03) with no ranking word, so it holds under either answer to decision 4. The paper's "strongest agent" sentence (line 463) changes to match in the revised PDF.
Decision: ______

**17. Did the author review cover the claim, configuration and target fields? (1 line: 188; paper line 668)**
Question: Did it? yes / no
Change: yes: 188 becomes "had only an author review of each extracted field, with no second check and no annotator agreement" [followups_check_1.md:15]. No: paper iclr2027_conference.tex:668 changes instead.
Decision: yes (Mithil, 11-08). Line 188 now says an author reviewed every field and no second person did; paper line 668 stands.

**18. Thin-harness gpt-6.1-sol arm: 12 papers or 24? (2 lines, one note: 246, 246)**
Question: Compare the two harnesses on the 12 papers both have run, or launch thin-harness papers 13 to 24 so the arm matches Codex's 24? keep 12 / launch 12 more
Change: keep 12: the note at line 246 names 12 shared papers and the paired comparison is over 12. Launch: about 12 more OpenAI runs from the $700 budget ($157 spent), finishing only if the ghx4 queue clears before the 11-15 18:00 stop.
Recommended: keep 12. A paired comparison on the shared 12 answers YGTR's harness question, and the queue makes 12 more unlikely to finish in time.
Decision: ______

---

Not decisions: Risk 6 is closed. The consistency Flag 1 was settled by the main session. Bracketed result slots that wait on runs are not decisions.
