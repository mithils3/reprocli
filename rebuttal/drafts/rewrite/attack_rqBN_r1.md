# Attack on the rqBN reply, round 1 (reviewer rqBN)


## 1. Sentences I had to reread or could not follow without the paper

- "Of these, ... 3 differ ... Budget logged before the GPU release charge" and "which holds the 3 entries of the last row". Last row of which table? Fix: write "the 3 unmatched entries are all in trajectory.jsonl, and no run wrote to it".
- "Comparing the two over all 372 graded runs found one edited log". "The two" is read as the logs before they are defined in the next paragraph. Fix: define commands.log and trajectory.jsonl first, then compare.
- "using the corrected grades from our other replies, with 70 of 400 agent-paper cells reproduced". The 70, the 400 and the earlier 73 and 372 are never reconciled here. Fix: one clause: "400 cells = 372 graded runs + 28 with no run; 73 became 70 after 4 corrections".
- "the target about 0.05 ... original run measured 0.0395". Is a lower error a miss? I cannot tell which side of the target fails. Fix: state the pass direction and tolerance.

## 2. Weaknesses not answered or dodged

- Anti-cheat flags: "agree on 42 of the 57 runs ... which covers all flag types together". That is 74%, with no per-flag result, which is what I asked for. Fix: report agreement per flag type, or say plainly it was not measured per type.
- Multi-human adjudication: answered only by "does not measure agreement between humans". Fix: add a number, such as a second human on a sample of 30 runs.
- Tolerances: "tiers keep their order from 1% to 10%" shows robustness of a ranking, not that 5% was validated. Fix: say tolerances were set by one author and cite the sensitivity result as the only check.
- Q1: no human baseline, and a floor of 32 papers is substituted. Fix: say what a 3 to 5 paper human attempt would show and why it was not feasible.

## 3. Unsupported claims

- "Each of these 32 is reproducible in our setting, so the count is a floor". Auditor precision is 88%, so about 4 of the 32 may be wrong, and "best of four" selects the maximum. Fix: "at least about 28 to 32, given auditor precision".
- "We did measure how often the environment alone causes a miss." Three papers cannot measure a frequency, and two of them point opposite ways (same miss; inside seed variance). Fix: "We checked 3 papers where this was possible."
- "The errors do not concentrate in one tier." Precision falls 90, 86, 85 and recall 80, 78, 69 with the tier; overlapping intervals at n=16 show low power, not absence. Fix: "the tier differences are within sampling error".
- The 2510.07501 example (seed spread 0.28 against a target of -0.20) undercuts the 5% tolerance and is presented as support. Fix: say what it implies for tolerance.

## 4. Concessions I did not raise, or defensive tone

- "119 commands in 65 runs ... two code paths return before writing the log". A volunteered harness bug. Fix: keep it, but fold it in as one clause of the log-completeness result.
- "Recall is lowest at Reimplement, but it rests on 16 ... overlaps". Pre-emptive and defensive. Fix: give the table and one neutral clause.
- "The paper supports ... all four for 55". Presents 45 flawed targets with no human review of the 37 not tied to the 8 corrections. Fix: report a human check on a sample of the flags.

## 5. Tone

"RECLAIM is meant to track agents' reproduction ability as it grows, possibly past what an expert achieves in the same budget, so each task is anchored to the authors' own reported result." This is not modest: it is a forward-looking ambition used as a reason to skip my question, and the "so" does not follow. Fix: "RECLAIM measures whether an agent reaches the authors' reported result under a fixed budget; it does not compare with experts, which we did not run."

## Cut caveats

- "does not fit in the discussion period": the loss hurts slightly. The 2,552 H100-hour sentence now ends without a conclusion. Restore one clause.
- "The checking model saw the frozen target": the loss hurts a lot. I asked for independent validation; a model shown the answer and asked "is it supported?" is leading. Restore, and say whether a second pass hid the target.

## Score after this reply: 3

The numbers are consistent and the log work answers W2 well. The one change that raises it most: have a human check a random sample of the 45 targets the model flagged (and 10 it passed) and report the confirmation rate, so Q2 has independent evidence.
