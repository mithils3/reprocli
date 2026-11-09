# Fact-check of contradictions 8, 9 and 10 (followups.md)

Checked 2026-11-08 against the files named in each item. Nothing was edited except this file.

## Item 8: agent ranking rule against "DeepSeek-V4-Flash is the strongest agent"

Verdict: CONFIRMED (the rule is stated for rates, but the paper's "strongest" sentence cites the Run rates that the rule forbids comparing).

Quotes:
- rebuttal/drafts/replies.md:56 (T29u part 1): "The revision compares two agents only where their intervals, widened by this rate of change, do not overlap, and it says that the measurement covers one agent."
- paper_latex/iclr2027_conference.tex:463-466: "DeepSeek-V4-Flash is the strongest agent. It recovers the pinned number on 14 of 34 Run-tier papers, 9 of 33 at Retrain, and 4 of 33 at Reimplement, and the four agents span a factor of 1.7 in mean audit score, from 5.13 for DeepSeek-V4-Flash to 3.03 for MiniMax-M2.7."
- paper_latex/iclr2027_conference.tex:121: "DeepSeek-V4-Flash, the strongest agent we evaluate, reproduces 41\% of Run-tier papers".

On disk, rebuttal/results/e8/bound.csv (row 2, dsv4 run, 14/34) gives 0.2637 to 0.5778, and row 8 (muse run, 9/34) gives 0.146 to 0.4312. The intervals overlap before any widening, so the Run-tier comparison that the paper's sentence rests on is one the reply's rule excludes. The 5.13 and 3.03 mean audit scores appear in the paper only; no file under rebuttal/results/ holds them, and no interval is given for them.

Smallest edit to replies.md (line 56, replace the sentence):
- Old: "The revision compares two agents only where their intervals, widened by this rate of change, do not overlap, and it says that the measurement covers one agent."
- New: "The revision compares two agents' reproduction rates only where their intervals, widened by this rate of change, do not overlap, and it says that the measurement covers one agent. It calls DeepSeek-V4-Flash the strongest agent on mean audit score, which the intervals do not test."

Author decision: whether "strongest" stays in the paper (lines 121 and 463, and the sentence at lines 618-619). Option A keeps the word and names mean audit score as its basis, which is a paper edit. Option B replaces "strongest" with "highest mean audit score" in all three places and drops the rank claim from the abstract's Run-tier sentence.

## Item 9: tolerance range, General reply against T29u part 2

Verdict: CONFIRMED (both replies quote numbers that match rebuttal/results/e6/README.md, but they state different ranges, and the General reply leaves out the 1% row where the Run count falls furthest).

Quotes:
- rebuttal/drafts/replies.md:29 (General): "Moving the default tolerance from 5% to 2% or 10% changes the best agent's count by at most 2 papers at Run, 3 at Retrain and 0 at Reimplement, and the ordering of the tiers holds at every setting we tried."
- rebuttal/drafts/replies.md:83 (T29u part 2): "The ordering of the tiers holds at every tolerance we tried, from 1% to 10%, and the best agent's count moves by at most 5 papers at Run (14 at 5% against 9 at 1%), 3 at Retrain and 1 at Reimplement"

From rebuttal/results/e6/README.md (best agent per tier): Run is 9 at 1%, 12 at 2%, 14 at 5% and 14 at 10%. Retrain reaches 12 at 10% against 9 at 5%, a move of 3. Reimplement is 4 at 1% against 5 at 5%, a move of 1.

Smallest edit to replies.md (line 29, replace the first sentence's range):
- Old: "Moving the default tolerance from 5% to 2% or 10% changes the best agent's count by at most 2 papers at Run, 3 at Retrain and 0 at Reimplement"
- New: "Moving the default tolerance anywhere from 1% to 10% changes the best agent's count by at most 5 papers at Run (14 at 5% against 9 at 1%), 3 at Retrain and 1 at Reimplement"

No author decision is needed.

## Item 10: harness arms, "each model ran in both harnesses"

Verdict: CONFIRMED (the reply says each named model ran in both harnesses, but the plan has gpt-6-astra in Codex CLI only, and frontier_cells.csv has no thin-harness gpt-6-astra row).

Quotes:
- rebuttal/drafts/replies.md:212 (YGTR part 1): "Each model ran in our ReAct-style harness and in a production harness, Codex CLI for the OpenAI models and mini-SWE-agent for Muse Wonder."
- rebuttal/drafts/replies.md:23 (General): "Each model ran in our ReAct-style harness and in a production harness (Codex CLI for the OpenAI models, mini-SWE-agent for Muse Wonder), with the same sandbox, task text, GPU grant and auditor as the main runs."
- rebuttal/drafts/replies.md:207 (YGTR part 1 list): "[gpt-6-astra and gpt-6.1-sol] in Codex CLI and in our harness"
- rebuttal/PLAN.md:115: "gpt-6-astra in Codex on the first 8 papers, at least two per tier (8 runs, $247)". The arms list has no thin gpt-6-astra entry.

frontier_cells.csv arms, counted: codex-gpt-6-astra 4 rows, codex-gpt-6.1-sol 12, thin-gpt-6.1-sol 7, miniswe 1. There is no thin-harness gpt-6-astra row and no gpt-6.1-terra row at all. The thin and Codex gpt-6.1-sol arms are both partly run, so the sentence for gpt-6.1-sol is true of the plan but not yet of the data.

Smallest edits to replies.md:
- Line 212. Old: "Each model ran in our ReAct-style harness and in a production harness, Codex CLI for the OpenAI models and mini-SWE-agent for Muse Wonder." New: "gpt-6.1-sol and Muse Wonder ran in our ReAct-style harness and in a production harness (Codex CLI for gpt-6.1-sol, mini-SWE-agent for Muse Wonder), and gpt-6-astra ran in Codex CLI only."
- Line 23. Old: "Each model ran in our ReAct-style harness and in a production harness (Codex CLI for the OpenAI models, mini-SWE-agent for Muse Wonder)," New: "gpt-6.1-sol and Muse Wonder ran in our ReAct-style harness and in a production harness (Codex CLI for gpt-6.1-sol, mini-SWE-agent for Muse Wonder), and gpt-6-astra ran in Codex CLI only,"
- Line 207. Old: "[gpt-6-astra and gpt-6.1-sol] in Codex CLI and in our harness" New: "gpt-6.1-sol in Codex CLI and in our harness, and [gpt-6-astra] in Codex CLI"

Separate from this item: replies.md never names gpt-6.1-terra, which PLAN.md:115 and the E1 row at PLAN.md:189 include. The author should decide whether terra is reported or dropped from the plan.

No author decision is needed for the astra edit, since PLAN.md:115 already fixes the arm.
