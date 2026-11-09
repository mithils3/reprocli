# Attack on the T29u reply, round 1 (as Reviewer T29u)

## 1. Read twice

- "Across the three runs the best Run rate moves by at most [j] papers." Only 4 of the 34 Run papers were rerun, so this cannot bound a 34-paper rate. Fix: report the per-paper verdict flip rate and the 34-paper spread it implies.
- "widened by these [j] papers": an ad hoc ranking rule I must work out by hand. Fix: name which agent pairs it separates.
- "24 of the 396 have a human label but no auditor grade, a different set from the 24 build failures". It never says why humans graded runs the auditor skipped, and the coincidence aside confuses. Fix: give the cause in one clause and drop the aside.
- "one Muse Spark 1.2 run graded after submission" and then "two new grades". Fix: "two runs graded after submission, one reproduced".
- "75 of the 100 runs that either placed at 7 or 8" cannot be read from a five-bin table. Fix: add a 2x2 table for those 100 runs.

## 2. Not answered

- W2 asked for "a more detailed audit of disagreements", and the reply gives counts without causes. Fix: one sentence each on what caused the 25 boundary and 15 score-0 disagreements.
- The matrix shows 2 human-reproduced runs the auditor disqualified, and the reply never mentions them. Fix: name the flag on each.
- W1 asked about rankings, which reruns of one agent cannot address. Fix: say so once and point to the interval overlap.

## 3. Unsupported

- "moves no best-agent rate by more than one percentage point". "Removing" is undefined, and the source bound of 14/34 against the current 13/34 is 2.9 points. Fix: print the bounded and current rates side by side.
- "The tiers keep their order at every tolerance": at 1% it is Run 9 against Retrain 8, and Run moves 5/34 = 15 points across the range. Fix: say the order holds by one paper at 1%.
- The tolerance table has Run at 14 while W1 has 13/34. Fix: label it "before the 2505.23747 correction".
- "no longer names a strongest agent" sits beside "our best agent at Run", "sole best at Retrain" and "Best agent" rows. Fix: use agent names.
- Means are given for three of four agents, and Qwen3.6-27B is missing. Fix: list all four.

## 4. Unasked concessions

- "the method or variant for 69 and all four for 55" says 45 targets fail and only 8 were corrected. Fix: say what the other 37 are, or move this to rqBN.
- "two reproduced runs that evaluated a downloaded checkpoint" reads as the auditor missing the very integrity flag I asked about. Fix: state plainly that the auditor missed both and that the scan now covers every run.
- On 2505.23747 the agent matched the README (51.44 against 51.13) and is now demoted, which looks like penalizing a faithful run. Fix: one clause on why the paper's number defines the claim.
- "we measured this spread for one agent only" duplicates the ranking point. Fix: cut it.

## 5. Tone

- "lean toward a strict auditor" and "slightly below" when the auditor finds 73 against the human's 83 and has 9 false positives. Fix: state "73 against 83" without the adjectives.
- "a model from another lab" is an unnamed second LLM judge, which is the dependence I raised. Fix: name it and give its agreement with a human sample.
- There are five cross-references to other replies. Fix: inline the numbers and keep one.
- The general reply promises "precision and recall per tier" that never appears here, and "reran missed runs' last commands with new seeds" is opaque. Fix: deliver the numbers or drop the promise.

## Score

Stays at 3, and Soundness rises from 2 to 3 only if the disagreement causes land. The change that would raise it most is to turn the 12-paper reruns into a stated per-paper flip rate, carried through as an interval on each tier rate and agent pair.
