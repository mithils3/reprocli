# Predicted response of Reviewer rqBN

Paths: `rqBN_1.md` and `general.md` are in `rebuttal/post/`, `paper.txt` is the PDF text, others are under `rebuttal/`.

## 1. Verdict

The reviewer keeps the rating at 3 (weak accept), with Soundness likely moving from 2 to 3, because the confusion matrix and the database log comparison answer most of both weaknesses. It does not reach 4 because three requests still have no human evidence: agreement between humans on grades, agreement between annotators on targets, and any human reproduction. A second blind human label on a stratified sample of runs and targets would move it most.

## 2. Likely follow-up

"Thank you for the confusion matrix and the database comparison, which resolve most of my evidence concerns. Three points remain. First, each run still has one human label, so I cannot judge how reliable the reference is. Second, Appendix E.6 shows that only 55 of 100 targets pass all four checks, while the reply reports 92. What happens to the results on the other 45, and why is no annotator agreement reported? Third, I asked for a stratified human baseline, which need not cover all 100 papers, and PaperBench used a small subset. Could a few papers per tier be done? I am keeping my score for now."

## 3. Surviving objections

**1. Targets and annotator agreement (Q2).**
(a) "Only 55 of 100 targets pass all four of your checks, 16 have a wrong setting and stay uncorrected, the checker saw the frozen target, and no human agreement is reported."
(b) High.
(c) rqBN_1.md:21: "It confirmed our value for 92 of the 100 claims (Appendix E), which is the agreement between our targets and an independent reader." PDF E.6 (paper.txt:3825, 3833, 3809): "All four 55"; "the number is right but a setting or label is off on 16"; "Because the model saw the frozen target, this ... does not re-derive it." PDF E.5 (paper.txt:3791): "no second reviewer, so we report no annotator agreement".
(d) Reproduction rates on the 55 papers that pass, the effect of the 16 setting errors, and a second human check on a sample of targets.
(e) Partly. No file holds these rates. Computed here from results/e7/comparison.csv and results/e6/table.csv, grades as submitted: 38 of 220 cells reproduced on the 55 papers (17.3%) against 35 of 180 on the other 45 (19.4%), and the best agent on the 55 reproduces 9 of 19 Run, 3 of 13 Retrain and 4 of 23 Reimplement, so the tier order holds. The 16 are in mithil/e7_merged.md:15, with no rescore found. Second human check: not found.

**2. Human baseline (Q1).**
(a) "Stratified means a sample, so 4,800 hours is not the cost I asked about. Author-reported numbers were not produced in your environment, and 68 papers have no evidence of being reproducible there."
(b) High.
(c) rqBN_1.md:13: "our 100 papers would take about 4,800 expert-hours". rqBN_1.md:16: "Each target is technically an expert result already". The rerun covers "3 partial runs" (rqBN_1.md:17), none at Reimplement. STATUS.md:105 notes that the PaperBench 41.4% comes from a 3-paper subset.
(d) Two or three papers per tier reproduced by a person in the same container and budget.
(e) Human baseline: not found. Frontier runs reproduce 2 of the 12 sampled papers that no open agent reproduced (results/frontier/same_paper_baselines.md:60), which lifts that count above 32.

**3. One human label per run (W1).**
(a) "I asked for multi-human adjudication. One label per run gives no agreement between humans, and the reply does not say who the graders were."
(b) High.
(c) rqBN_1.md:5: "Three human graders scored the runs, one grader per run". PDF Appendix D (paper.txt:3537): "does not measure agreement between humans."
(d) A second blind label on 40 to 60 runs stratified by verdict, with kappa, and one line on whether the graders are authors.
(e) Not found. results/e4/README.md:3 says no per-run label file is on disk.

**4. Anti-cheat flags (W1).**
(a) "Agreement on score 0 does not validate the flags. Score 0 mixes several conditions, and your scan found two reproduced runs with downloaded checkpoints that the auditor passed."
(b) Medium.
(c) rqBN_1.md:5: "both graders gave a 0 to 42 of them". PDF Appendix D (paper.txt:3590): "A score of 0 covers a high-severity integrity flag and three related conditions". general.md:14 removes 2 reproduced cells after the checkpoint check.
(d) Per-flag precision on a human-read sample of the 53 auditor zeros, and the scan's miss rate, 2 of 42 reproduced Retrain and Reimplement runs (4.8%).
(e) Partly. results/e9/README.md has the 2 of 42. Per-flag human check: not found.

**5. Scope of the log check (W2).**
(a) "The comparison covers command text and exit codes in two files. The numbered step logs that hold the measured numbers stay writable."
(b) Medium.
(c) PDF A.5 (paper.txt:2779): "mounts commands.log and trajectory.jsonl read-only on top of the read-write evidence/ directory". rqBN_1.md:9: "have the same text, no exit code differs".
(d) A comparison of the result text stored in the database with the step logs for the reproduced runs.
(e) Not found. results/e5/README.md:12 records agent writes into evidence/ in 360 of 372 runs.

## 4. Mismatches

One sentence that Appendices D and F use grades as submitted (paper.txt:4192) settles the first and last.

- Tolerance: rqBN_1.md:21 "9, 12, 14 and 14 of 34 at Run" against general.md:17 "13 of 34 Run" and PDF 5.2 (paper.txt:554) "13 of 34".
- Exit codes: rqBN_1.md:9 "the 30,790 commands ... have the same text, no exit code differs" against PDF A.5 (paper.txt:2764) "30,739 match ... on command and return code, and another 51 match on command".
- Targets: general.md:6 "It supports 92 of the 100, and the other 8 are corrected" against PDF Table 15 "All four 55" and 16 uncorrected setting errors; rqBN_1.md:21 "an independent reader" against PDF "the model saw the frozen target".
- Flags: rqBN_1.md:5 "a high-severity flag sets a run's score to 0" against PDF "three related conditions" also scored 0.
- Reproduced count: rqBN_1.md:5 "64/73" against general.md:9 "from 73 to 70 of 400".
