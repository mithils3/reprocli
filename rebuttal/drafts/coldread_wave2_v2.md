# Cold read as Reviewer YGTR (score 2 of 4), wave 2 v2

Read: my review, general.md, YGTR_1, YGTR_2, YGTR_3. Bracketed slots are treated as unknown.

## 1. Does the response answer each point

- W1, no frontier models: Answered in structure, empty in substance. "We ran two current OpenAI models, [gpt-6-astra and gpt-6.1-sol], and Meta's Muse Wonder on papers drawn with a fixed seed from every tier and frozen before any run ([n] papers ...)". Every outcome is a slot.
- W1, minimal ReAct harness, use Claude Code, Codex or mini-SWE-agent: Answered for Codex and mini-SWE-agent, partly for Claude Code. "Both gpt-6.1-sol and Muse Wonder ran in our thin ReAct-style loop and in a production harness (Codex CLI and mini-SWE-agent respectively)". Claude Code is declined: "a Claude agent would be graded by its own model family".
- W1, success and failure modes would change with a better harness: Depends on slots. "[Failure-mode sentence: ... or Codex CLI removes mode X in k runs.]" and "[Harness sentence: the paired difference ... is k papers for gpt-6.1-sol (exact McNemar p = x)]".
- W1, findings may not generalize: Answered by scoping. "The findings are scoped to the 100 NeurIPS 2025 papers and the agents we tested, and we do not claim more."
- W2, hardware confounds: Answered with numbers. "Build failures on our hardware move no best-agent rate by more than one percentage point." and "14 on a package with no build for the aarch64 CPUs of our GH200 nodes".
- W3, single runs: Answered by method, outcome is a slot. "we measured its size by running DeepSeek-V4-Flash twice more on 12 papers ... [Its verdict was the same in all three runs on k of 12 papers ...]".
- Q1, repeat with frontier models and coding harnesses: Same as W1; slots.
- Q2, checkpoint cheating: Fully answered. "we scanned the transcripts of all 372 graded runs", "two reproduced runs evaluated a downloaded checkpoint of the claimed model, which the revision counts as not reproduced."
- Q3, failures not the agent's fault: Answered. "Across the 400 cells, 27 failed for reasons we traced outside the agent ... so 6 + 14 + 7 = 27."

## 2. Unclear on a first read

1. "which is within / larger than the run-to-run change we measured (W3)". Two alternatives left in, and W3 sits in a different file I read second. Also undefined: run-to-run change in what unit.
2. "Muse Spark 1.2 from our main runs gives a same-family comparison". I have not been told what Muse Spark 1.2 is or why it is the same family as Muse Wonder.
3. "Our reply to Reviewer rqBN (Q1) re-runs the last commands of missed runs ... both Retrain papers miss again on both seeds." A pointer to another reviewer's reply I would not open, and "both Retrain papers" has no antecedent (which two, out of how many missed runs).
4. "details in our reply to Reviewer T29u, W1". Same problem; the setup of the key experiment lives elsewhere.
5. "the revision widens the comparisons between agents by this rate". Unclear what is widened, and by what number.
6. "9 of the 12 build and import (95% Wilson interval 47% to 91%)". Grammar hides the claim, and the interval is wide enough that "hardware is the cause" for these 9 reads as weak.
7. "Removing all 24 from the denominators ... since it had none of these failures there". I cannot tell which 24 (all agents, all tiers) are removed from which denominators; the DeepSeek line has no change shown.
8. "The agent most affected is MiniMax-M2.7 at Run, which goes from 3/34 to 3/26." Eight removals look large next to the claim that nothing moves, and it is unstated that this agent is not a best agent.
9. "the pinned auditor" and "graded the 3 whose files survive". Pinned auditor is never defined in this thread, and "Four finished runs had no grade" sits next to "Two ended when the agent's context filled" without saying why they differ.
10. "the 16 stopped cells ... a stopped job does not show whether the agent would have succeeded, so we reran them". Reads as an excuse for leaving 16 of 28 out of the 27, and the sentence before already said they were reran in a slot, so the paragraph repeats itself.
11. "It leaves out the 76 runs that followed the released pipeline and still missed". 76 has no base (out of how many runs, which tier) and "released pipeline" is undefined.
12. "Claude Code is the one harness you name that we did not run, because our auditor is Claude Sonnet 5". Reads as an excuse, because a different auditor for those runs is an obvious fix.
13. "The tier ordering and the most common failure are what we test on those runs [outcome]". "Tier ordering" is not defined for a reader who skipped the paper, and the claim to be tested is not stated.
14. "(33 is the number of Retrain papers, one cell per paper)" next to "14/34" at Run. The 34 versus 33 base is never explained.

Count of unclear sentences: 14.

## 3. Score

Keep 2 on the text as posted. I would raise to 3 if the slots show the following; I would not go above 3 because the single-harness main results remain.

The one thing that decides it: whether frontier agents in Codex CLI or mini-SWE-agent reproduce papers at a rate that is distinguishable from the open agents, together with the failure-mode sentence. If gpt-6.1-sol and gpt-6-astra reproduce a meaningful share and their failures still fall in the paper's three modes inside the open agents' 95% intervals, my generalization concern is answered and I raise. If Codex CLI removes the dominant failure mode in many runs, the central finding is harness-specific and I lower to 1 or keep 2 depending on how the paper reframes it. With [n] and [m] small (for example a of 8), the intervals will overlap everything, and I keep 2.

Slots my score depends on: [n], [m], a (of 8), b, c, d, g, h (reproduced counts), k and x in the harness sentence, u% GPU grant, the failure-mode sentence, k of f, d of m against e of m, the W3 k of 12, and r for the 20 reruns. The Q2, Q3 and W2 answers need no slot and already satisfy me.

## 4. Editor fixes (quote old, give new; all numbers kept)

1. Old: "which is within / larger than the run-to-run change we measured (W3)"
   New: "which is within / larger than the change between repeated runs of DeepSeek-V4-Flash on the same 12 papers (W3 below)"
2. Old: "Muse Spark 1.2 from our main runs gives a same-family comparison, [Muse Wonder d of m against Muse Spark e of m]."
   New: "Muse Spark 1.2, the Meta model in our main runs, gives a comparison within one model family: [Muse Wonder d of m against Muse Spark 1.2 e of m]."
3. Old: "Our reply to Reviewer rqBN (Q1) re-runs the last commands of missed runs on the same nodes with new seeds and no agent, and both Retrain papers miss again on both seeds."
   New: "We also re-ran the last commands of the missed runs on the same nodes with new seeds and no agent. The [n] Retrain papers tested miss again on both seeds." (state the count in this reply)
4. Old: "(details in our reply to Reviewer T29u, W1)"
   New: "(DeepSeek-V4-Flash, the agent with the highest Run and Retrain rates, three runs per paper)"
5. Old: "and the revision widens the comparisons between agents by this rate."
   New: "and every comparison between agents in the revision states the 95% interval."
6. Old: "and 9 of the 12 build and import (95% Wilson interval 47% to 91%)."
   New: "and 9 of the 12 build and import on x86 (95% Wilson interval 47% to 91%)."
7. Old: "Removing all 24 from the denominators leaves DeepSeek-V4-Flash ..."
   New: "Dropping those 24 runs from every agent's denominator leaves DeepSeek-V4-Flash ..."
8. Old: "The agent most affected is MiniMax-M2.7 at Run, which goes from 3/34 to 3/26."
   New: "The agent most affected is MiniMax-M2.7 at Run, which goes from 3/34 to 3/26 and is not a best agent at any tier."
9. Old: "Four finished runs had no grade from the pinned auditor"
   New: "Four finished runs had no grade from our auditor (Claude Sonnet 5, the same model for every graded run)"
10. Old: "because a stopped job does not show whether the agent would have succeeded, so we reran them"
    New: "because a stopped job gives no outcome to attribute, so we reran them"
11. Old: "It leaves out the 76 runs that followed the released pipeline and still missed"
    New: "It leaves out the 76 graded runs (of 372) that followed the released code, data and weights and still missed"
12. Old: "because our auditor is Claude Sonnet 5 and a Claude agent would be graded by its own model family."
    New: "because our auditor is Claude Sonnet 5; a Claude agent graded by its own family would be a self-grade, so we ran the other two named harnesses."
13. Old: "The tier ordering and the most common failure are what we test on those runs [outcome]."
    New: "We test two main-run findings on those runs: that Run is reproduced more often than Retrain and Reimplement, and that the most common failure is writing the method without checking its output against the paper [outcome]."
14. Old: "(33 is the number of Retrain papers, one cell per paper)"
    New: "(each tier has one cell per paper per agent: 34 papers at Run, 33 at Retrain, 33 at Reimplement)"
