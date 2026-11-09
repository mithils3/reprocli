# Revised paper text promised by the rebuttal replies

Drafted 2026-11-08 for the revised PDF due Sat 2026-11-14 (PLAN.md Section 4). Nothing under `paper_latex/` was edited. Each section below quotes the reply sentence that makes the promise (with its `rebuttal/drafts/replies.md` line), gives the paper location as file:line, the old text, and the replacement LaTeX, ready to paste. Every quote and line number was rechecked on 2026-11-08 against `replies.md` at commit 9bcf851, the shortened replies, which replaced the longer version of commit 33a989c. A section whose promise no longer appears in the current replies carries the label "not promised in current replies" at its top and stays in the file. Paper line numbers refer to the files before any of these edits, so paste from the bottom of each file upward or search for the old text.

Conventions used in the LaTeX:

- `\todo{...}` marks a number or sentence that is not in yet. Add this line to the preamble of `iclr2027_conference.tex` (xcolor is already loaded, since line 114 uses `\textcolor`), and delete it before the final upload so that any leftover slot fails to compile:
  `\newcommand{\todo}[1]{\textcolor{red}{[#1]}}`
- A comment `% src:` on a line names the file under `rebuttal/results/` that holds its numbers.
- A comment `% moves with:` names the pending item that can still change a number that is filled in now. The pending items are E8 reruns (the 20 rerun cells), E7 (the author's verdicts on the 45 flagged targets), and the regrade decision (whether the two new Muse Spark grades and the two checkpoint corrections enter the counts, which decides 73 against 72, or 70 if the E7 corrections also enter).

Two findings from drafting were settled by the current replies:

1. **Section 5.2 gives each agent's mean audit score with no ranking word** (`replies.md:56`: "The scores run from 5.13 for DeepSeek-V4-Flash and 5.00 for Muse Spark 1.2 down to 3.03 for MiniMax-M2.7"). The earlier worry that Muse Spark 1.2 could pass DeepSeek-V4-Flash after the two new grades (5.00 + 14/100 = 5.14 against 5.13) no longer decides any wording, because no sentence ranks the agents by mean score. The means in Table 5 still need recomputing before the paper is final.
2. **The Stage III scope now agrees between the paper and the replies.** `replies.md:188` says Stage III "checked which artifacts each paper's authors released and settled each compute estimate", which matches the paper (`iclr2027_conference.tex:326`, `:364-365`). The author also reviewed every extracted field (`replies.md:188`, paper_revisions.md:11), so Variant A of Section 10a is the one that goes in and `iclr2027_conference.tex:668` stays as written.

---

## 1. Frontier models and production harnesses (Section 5.1, Section 5.2, Appendix B, Limitations)

**Promise.**
- replies.md:12: "Frontier agents and production harnesses (Section 5.1 and a new appendix section): gpt-6.1-sol in our loop and in Codex CLI, [gpt-6-astra] in Codex CLI, and Muse Wonder in our loop and in mini-SWE-agent, on papers from every tier frozen before any run."
- replies.md:229: "Section 5.1 and a new appendix section: gpt-6.1-sol in Codex CLI and in our loop, [gpt-6-astra] in Codex CLI, and Muse Wonder in mini-SWE-agent and in our loop, on papers frozen before any run."
- replies.md:238: "A Codex run ends when Codex ends its own turn, the same stopping rule as our loop, and the appendix table gives each run's exit reason."
- replies.md:244: "We keep the thin loop for the main results so that every model runs under one harness, and the new appendix section measures how Codex CLI and mini-SWE-agent change the results."

### 1a. Section 5.1, Models paragraph

**Location.** `paper_latex/iclr2027_conference.tex:441-446`.

**Old.**
```latex
\paragraph{Models.} We evaluate four models:
DeepSeek-V4-Flash~\citep{deepseekai2026deepseekv4highlyefficientmilliontoken,deepseekai2026flashcard},
Qwen3.6-27B~\citep{qwen3.6-27b}, MiniMax-M2.7~\citep{minimax2026m2}, and
Muse Spark 1.2~\citep{meta2026musespark}. The first three are open-weight and
run on our cluster with vLLM~\citep{kwon2023vllm}, and we reach Muse Spark 1.2 through the Meta
Model API. All use the same harness, prompts, and budgets.
```

**New.**
```latex
\paragraph{Models.} We evaluate four models:
DeepSeek-V4-Flash~\citep{deepseekai2026deepseekv4highlyefficientmilliontoken,deepseekai2026flashcard},
Qwen3.6-27B~\citep{qwen3.6-27b}, MiniMax-M2.7~\citep{minimax2026m2}, and
Muse Spark 1.2~\citep{meta2026musespark}. The first three are open-weight and
run on our cluster with vLLM~\citep{kwon2023vllm}, and we reach Muse Spark 1.2 through the Meta
Model API. All use the same harness, prompts, and budgets. To test whether the
results hold for frontier models in the harnesses they ship with, we also ran
\todo{gpt-6-astra and gpt-6.1-sol}\todo{cite} from OpenAI on \todo{n} papers and
Muse Wonder\todo{cite} from Meta on \todo{m} papers, drawn with a fixed seed from
every tier and frozen before any run. gpt-6.1-sol ran in our harness and in
Codex CLI\todo{cite}, gpt-6-astra in Codex CLI only, and Muse Wonder in our
harness and in mini-SWE-agent~\citep{yang2024sweagent}. The production
harnesses keep their own tools, system prompts, and context handling, and every
run gets the same sandbox, task text, GPU grant, and auditor as the main runs,
so within one model only the harness changes.\footnote{Appendix~\ref{app:frontier}
gives the sample, the runs, and their grades.}
% src: rebuttal/PLAN.md:115 and results/databook/frontier_cells.csv (gpt-6-astra has no thin-harness arm); sample from rebuttal/subset.json, seed 22528
```

Notes. The arm list follows the replies. `results/frontier/run_usage_summary.md` also lists a gpt-6.1-terra arm (7 runs), which the replies do not mention, so the model list stays a slot. The mini-SWE-agent cite to `yang2024sweagent` (already in the bib through `\nocite`) assumes the mini-SWE-agent README asks users to cite the SWE-agent paper; check its cite-as block. gpt-6.1-sol, gpt-6-astra, Muse Wonder, and Codex CLI need new bib entries from their own cite-as blocks or model cards.

### 1b. Section 5.2, result paragraph for the frontier arms

**Location.** New paragraph after `paper_latex/iclr2027_conference.tex:500` (the paragraph ending "DeepSeek-V4-Flash claims 19 and the auditor confirms 27."), before `\subsection{Failure mechanisms}`.

**New.**
```latex
\todo{In the frontier arms, gpt-6-astra in Codex CLI reproduces a of n papers,
gpt-6.1-sol b of n in our harness and c of n in Codex CLI, and Muse Wonder d of m
in our harness and g of m in mini-SWE-agent (Table~\ref{tab:frontier}). Within
gpt-6.1-sol the two harnesses differ by k papers (exact McNemar $p = x$), which
is within / larger than the run-to-run change of DeepSeek-V4-Flash, and the
frontier runs spend a median of u\% of their GPU grant.}
% src when frozen: results/frontier/grades.jsonl, results/databook/frontier_cells.csv, results/frontier/run_usage_summary.md
```

### 1c. Appendix B, new subsection

**Location.** `paper_latex/appendix/b_models.tex`, after the Table 5 longtable (line 189, `}`) and before the closing `\FloatBarrier` at line 191. A subsection of Appendix B keeps the letters of Appendices C to J, which the replies cite as D, E, and F. A new `\section` would have to go after Appendix J to keep them.

**New.**
```latex
\subsection{Frontier models and production harnesses}
\label{app:frontier}

The frontier arms use the 12 core papers of a sample drawn with seed 22528,
four per tier, two of which some main agent had reproduced and two of which
none had, and the 12 extension papers drawn the same way. We froze the
sample before any frontier run and excluded 2510.20725, whose main-roster
cells never started. Each run gets the paper's band ceiling as its GPU grant,
the task text of the main runs, the same sandbox and \texttt{run\_gpu} tool, and
the pinned auditor. In Codex CLI and mini-SWE-agent the agent keeps the
harness's own tools, system prompt, and context handling, and a run ends when
the agent ends its own turn, which is the stopping rule of our harness.
Table~\ref{tab:frontier} gives the results beside DeepSeek-V4-Flash and Muse
Spark 1.2 on the same papers, and Muse Spark 1.2 against Muse Wonder compares
two models from one family. % src: results/subset/README.md (counts per tier and band; 2510.20725 excluded)

\begin{table}[ht]
\centering
\small
\begin{tabular}{@{}llrrrrr@{}}
\toprule
Model & Harness & Run & Retrain & Reimplement & Mean score & Grant spent (\%) \\
\midrule
gpt-6-astra & Codex CLI & \todo{} & \todo{} & \todo{} & \todo{} & \todo{} \\
gpt-6.1-sol & ours & \todo{} & \todo{} & \todo{} & \todo{} & \todo{} \\
gpt-6.1-sol & Codex CLI & \todo{} & \todo{} & \todo{} & \todo{} & \todo{} \\
Muse Wonder & ours & \todo{} & \todo{} & \todo{} & \todo{} & \todo{} \\
Muse Wonder & mini-SWE-agent & \todo{} & \todo{} & \todo{} & \todo{} & \todo{} \\
\midrule
DeepSeek-V4-Flash & ours & \todo{} & \todo{} & \todo{} & \todo{} & \todo{} \\
Muse Spark 1.2 & ours & \todo{} & \todo{} & \todo{} & \todo{} & \todo{} \\
\bottomrule
\end{tabular}
\caption{Reproduced papers by tier, mean audit score, and median share of the
GPU grant spent for each frontier arm and for two main agents on the same papers.}
\label{tab:frontier}
\end{table}

\todo{Failure modes: we labeled the frontier runs with the procedure of
Appendix~\ref{app:taxonomy}, and Reimplemented but did not check the result
occurs in k of the m failing frontier runs. An author labeled 20 randomly drawn
frontier runs blind to the model labels and agrees with them on x of 20.}

\begin{longtable}{@{}lllllrl@{}}
\caption{Every frontier run with its model, harness, paper, tier, graded
verdict, share of the GPU grant spent, and exit reason.}
\label{tab:frontier-runs}\\
\toprule
Model & Harness & Paper & Tier & Verdict & Grant spent (\%) & Exit reason \\
\midrule
\endhead
\todo{one row per frontier run} & & & & & & \\
\bottomrule
\end{longtable}
% src when frozen: results/frontier/grades.jsonl, results/frontier/early_stop.md (replies.md:238 promises the exit reason of each run)

\todo{Early stopping: the frontier runs spend a median of u\% of their grant,
and v of them end with the agent reporting that it could not run the
experiment. Queue wait per GPU request: median w hours.}
% current partial values, not frozen: results/frontier/run_usage_summary.md (medians 0.06% to 1.40% over 11 runs);
% results/frontier/early_stop.md (24 graded runs, most stops classed "missing artifact")
```

Note. The first ten frontier runs mostly stop with a "missing artifact" report while spending under 2% of the grant (Risk 4 in replies.md, `results/frontier/early_stop.md`). The frozen eval-100 is host-probed wall-free, so in the paper's protocol such a report is the agent's failure, and the early-stopping paragraph should say so in the paper's own terms once the numbers are final.

### 1d. Limitations, Agents paragraph

**Location.** `paper_latex/iclr2027_conference.tex:596-602`.

**Old.**
```latex
\paragraph{Agents.} Each cell holds at most one run and the rates are point
estimates, so we read large gaps between agents and leave close pairs
within a tier unranked~\citep{bjarnason2026randomness}. The roster omits Claude, GPT, and Gemini
because of cost. Repeated
runs and closed frontier models are for groups with access to them, and
the harness already drives one hosted agent over its API
(Appendix~\ref{app:models}).
```

**New.**
```latex
\paragraph{Agents.} Each cell of the main roster holds one run, and the repeat
runs cover one agent on 12 papers, so we leave pairs of agents whose intervals
overlap unranked~\citep{bjarnason2026randomness}. The frontier arms cover
\todo{n} papers, and the roster omits Claude and Gemini because of cost.
```

This removes about one typeset line. It drops the sentence that repeated runs and frontier models are left to other groups, since the revision now has both.

---

## 2. Wilson intervals on every rate (Section 5.2, Table 5, Figure 4)

**Promise.**
- replies.md:13: "Uncertainty (Section 5.2): a 95% Wilson interval on every rate, and two more runs of DeepSeek-V4-Flash on 12 papers to measure run-to-run variation."
- replies.md:54: "Every rate in the revision carries a 95% Wilson interval."
- replies.md:231: "Section 5.2: a 95% Wilson interval on every rate, and repeated runs of one agent."
- replies.md:264: "Every rate now carries a 95% Wilson interval in Section 5.2."

### 2a. Section 5.2, opening paragraph (with Sections 3 and 4 below)

**Location.** `paper_latex/iclr2027_conference.tex:461-466`.

**Old.**
```latex
The auditor confirms reproduction on 73 of the 400 agent-paper cells
(Figure~\ref{fig:main-results}).
DeepSeek-V4-Flash is the strongest agent. It recovers the pinned
number on 14 of 34 Run-tier papers, 9 of 33 at Retrain, and 4 of 33 at
Reimplement, and the four agents span a factor of 1.7 in mean audit score,
from 5.13 for DeepSeek-V4-Flash to 3.03 for MiniMax-M2.7.
```

**New.**
```latex
The auditor confirms reproduction on 73 of the 400 agent-paper cells, 18\% with
a 95\% Wilson interval~\citep{wilson1927probable} of 15\% to 22\%
(Figure~\ref{fig:main-results}). % src: results/e7/rescore_summary.md:27 (73/400 = 18.2% [14.8, 22.3]); moves with: regrade decision, E7, E8 reruns
The mean audit score on the 0 to 10 rubric is 5.13 for DeepSeek-V4-Flash and
5.00 for Muse Spark 1.2, down to 3.03 for MiniMax-M2.7. % src: replies.md:56; paper :465-466 and b_models.tex:178; moves with: E8 reruns
DeepSeek-V4-Flash recovers the pinned number on 14 of 34 Run-tier papers (41\%, interval 26\%
to 58\%), 9 of 33 at Retrain (27\%, 15\% to 44\%), and 4 of 33 at Reimplement
(12\%, 5\% to 27\%), where Muse Spark 1.2 has the best rate at 5 of 33 (15\%,
7\% to 31\%). Muse Spark 1.2 reproduces 8 of 33 at Retrain (24\%, 13\% to 41\%) after the
checkpoint scan below, so DeepSeek-V4-Flash alone has the best Retrain rate. % src: replies.md:54, :280; results/e6/summary.json settings.S0_index (dsv4/run, dsv4/retrain, dsv4/reimplement, muse/reimplement); moves with: E7 (Run 14 -> 13), E8 reruns
Table~\ref{tab:results} gives an interval for every agent and tier.
\todo{Repeat-run sentence, Section 3 below.}
We compare the reproduction rates of two agents only where their intervals,
widened by this rate of change, do not overlap, so at Run we do not rank
DeepSeek-V4-Flash above Muse Spark 1.2, which reproduces 9 of 34 (26\%, 15\% to
43\%). % src: results/e6/summary.json settings.S0_index muse/run; moves with: regrade decision (Muse Run 9 -> 10 with the 2503.23035 grade)
```

The paper uses Wilson intervals for the first time here, so it needs a bib entry. Resolved from the DOI on 2026-11-08 (`curl -sLH "Accept: application/x-bibtex" https://doi.org/10.1080/01621459.1927.10502953`), with the key renamed:
```bibtex
@article{wilson1927probable,
  title={Probable Inference, the Law of Succession, and Statistical Inference},
  author={Wilson, Edwin B.},
  journal={Journal of the American Statistical Association},
  volume={22}, number={158}, pages={209--212}, year={1927},
  doi={10.1080/01621459.1927.10502953}
}
```

### 2b. Appendix B, Table 5 (Reproduced column with intervals)

**Location.** `paper_latex/appendix/b_models.tex:137` and `:144` (both header rows), and the by-tier rows at `:154-157`, `:161-164`, `:168-171`, `:175-178`, `:182-185`.

**Old header (both places).**
```latex
Agent & Tier or measure & Reproduced & Mean score & 8 h & 32 h & 96 h \\
```
**New header.**
```latex
Agent & Tier or measure & Reproduced (95\% interval) & Mean score & 8 h & 32 h & 96 h \\
```

**New Reproduced cells** (replace only the third column of each row; the other columns stay as they are):

| Row | Old cell | New cell | Source |
| :- | :- | :- | :- |
| DeepSeek-V4-Flash, Run | `14/34 (41\%)` | `14/34 (41\%, 26--58)` | e6/summary.json S0_index dsv4/run |
| DeepSeek-V4-Flash, Retrain | `9/33 (27\%)` | `9/33 (27\%, 15--44)` | dsv4/retrain |
| DeepSeek-V4-Flash, Reimplement | `4/33 (12\%)` | `4/33 (12\%, 5--27)` | dsv4/reimplement |
| DeepSeek-V4-Flash, All tiers | `27/100 (27\%)` | `27/100 (27\%, 19--36)` | not in results/ |
| Qwen3.6-27B, Run | `5/34 (15\%)` | `5/34 (15\%, 6--30)` | qwen3/run |
| Qwen3.6-27B, Retrain | `6/33 (18\%)` | `6/33 (18\%, 9--34)` | qwen3/retrain |
| Qwen3.6-27B, Reimplement | `2/33 (6\%)` | `2/33 (6\%, 2--20)` | qwen3/reimplement |
| Qwen3.6-27B, All tiers | `13/100 (13\%)` | `13/100 (13\%, 8--21)` | not in results/ |
| MiniMax-M2.7, Run | `3/34 (9\%)` | `3/34 (9\%, 3--23)` | minimax/run |
| MiniMax-M2.7, Retrain | `5/33 (15\%)` | `5/33 (15\%, 7--31)` | minimax/retrain |
| MiniMax-M2.7, Reimplement | `2/33 (6\%)` | `1/33 (3\%, 1--15)` | replies.md:280 (CURE download counted as not reproduced, 2 -> 1); Wilson computed with the e6 formula |
| MiniMax-M2.7, All tiers | `10/100 (10\%)` | `9/100 (9\%, \todo{lo--hi})` | not in results/; 10 - 1 for the CURE run (replies.md:280) |
| Muse Spark 1.2, Run | `9/34 (26\%)` | `9/34 (26\%, 15--43)` | muse/run; moves with: regrade decision (9 -> 10) |
| Muse Spark 1.2, Retrain | `9/33 (27\%)` | `8/33 (24\%, 13--41)` | replies.md:280 (CogVLA download counted as not reproduced, 9 -> 8); Wilson computed with the e6 formula |
| Muse Spark 1.2, Reimplement | `5/33 (15\%)` | `5/33 (15\%, 7--31)` | muse/reimplement |
| Muse Spark 1.2, All tiers | `23/100 (23\%)` | `\todo{22 or 23}/100` | not in results/; 23 - 1 for the CogVLA run (replies.md:280), plus 1 if the 2503.23035 grade (score 8, replies.md:290) is a Run reproduction |
| All agents, Run / Retrain / Reimplement | `31/136`, `29/132`, `13/132` | `\todo{31 or 32}/136`, `28/132`, `12/132`, each with `\todo{lo--hi}` | not in results/; Retrain and Reimplement each fall by 1 (replies.md:280) |
| All agents, All tiers | `73/400 (18\%)` | `73/400 (18\%, 15--22)` as in replies.md:54 and :68, with a `\todo{}` | e7/rescore_summary.md:27. The replies keep 73 while they also count two checkpoint runs as not reproduced and add one reproduced grade, which gives 73 - 2 + 1 = 72 (the AUTHOR note after replies.md:58); settle before the number goes in |

The intervals in percent are rounded from the `wilson95` fields of `results/e6/summary.json`, which agree with `results/e8/bound.csv` (paper_lo, paper_hi).

### 2c. Figure 4 caption

**Location.** `paper_latex/iclr2027_conference.tex:471-472`.

**Old.**
```latex
\caption{Reproduction rate and mean audit score by agent and tier, and the share
of the granted H100-hours each agent spent.}
```
**New.**
```latex
\caption{Reproduction rate with 95\% Wilson intervals and mean audit score by
agent and tier, and the share of the granted H100-hours each agent spent.}
```
The figure needs error bars drawn by `figures/build.py`, which this text draft does not cover.

---

## 3. Repeated runs and the rule for ranking agents (Section 5.2, Limitations)

**Promise.**
- replies.md:44: "Section 5.2: a 95% Wilson interval on every rate, and two more runs of DeepSeek-V4-Flash on 12 papers."
- replies.md:52: "The revision compares the reproduction rates of two agents only where their intervals, widened by the run-to-run change these repeat runs measure, do not overlap, and it says that the measurement covers one agent."
- replies.md:264: "[...] and the revision widens the comparisons between agents by this rate."

**Location.** The `\todo{Repeat-run sentence ...}` slot in the new Section 5.2 opening paragraph (Section 2a above). The ranking sentence is already in 2a, and the "covers one agent" statement is in the Limitations paragraph of Section 1d.

**New** (replaces the slot).
```latex
To measure run-to-run variation, we ran DeepSeek-V4-Flash twice more on 12
papers drawn with a fixed seed, four per tier, two of which some agent had
reproduced and two of which none had.\footnote{Some agent reproduced 34 of the
99 papers the sample was drawn from, so the sample holds a larger share of
reproduced papers than the benchmark.} % src: results/subset/README.md (core R/N per tier 2/2; candidates R sum 13+3+0+6+5+1+6+0+0 = 34, N sum 65, of 99)
\todo{Its verdict was the same in all three runs on k of 12 papers (95\%
interval lo to hi), and the ordering Run, Retrain, Reimplement held in j of 3
runs.}
% src when frozen: repeat-run grades (jobs 3540624 to 3540633, results/sweeps/jobs.csv)
```

The footnote answers the follow-up a reviewer is likely to raise (followups.md:19), namely that half the sample was chosen because some agent reproduced it.

---

## 4. Mean audit score in place of "strongest agent" (Introduction, Section 5.2, Conclusion)

**Promise.**
- replies.md:56: "Section 5.2 had called DeepSeek-V4-Flash the strongest agent, and it now gives each agent's mean audit score on the 0 to 10 rubric instead. The scores run from 5.13 for DeepSeek-V4-Flash and 5.00 for Muse Spark 1.2 down to 3.03 for MiniMax-M2.7."
- paper_revisions.md:9 (lines 463, 121, 618-619). That line asks for "the agent with the highest mean audit score", which the current reply has replaced with no ranking word, so the wording below follows the reply.

Section 5.2 (line 463) is covered by the new paragraph in Section 2a. The other occurrences follow.

### 4a. Introduction

**Location.** `paper_latex/iclr2027_conference.tex:121`.

**Old.**
```latex
when no code is available. DeepSeek-V4-Flash, the strongest agent we evaluate, reproduces
```
**New.**
```latex
when no code is available. DeepSeek-V4-Flash reproduces
```

**Location.** `paper_latex/iclr2027_conference.tex:133-135`.

**Old.**
```latex
achieve partial reproduction at a far higher rate. On Retrain-tier
papers the strongest agent reaches a verified partial result or better on 67\% of runs
and the weakest on 27\%,
```
**New.**
```latex
achieve partial reproduction at a far higher rate. On Retrain-tier
papers DeepSeek-V4-Flash reaches a verified partial result or better on 67\% of runs
and MiniMax-M2.7 on 27\%,
```
Note. Section 5.2 (line 478) gives Muse Spark 1.2 23 of 33 partial-or-better cells at Retrain, which is 70% and above DeepSeek-V4-Flash's 67%, so "the strongest agent" at line 134 was already inaccurate on this measure. Naming the two agents states the 67% and 27% without ranking them. The paper_revisions.md list did not include this line.

### 4b. Conclusion

**Location.** `paper_latex/iclr2027_conference.tex:618-620`.

**Old.**
```latex
artifact does not. We read DeepSeek-V4-Flash's fall from 41\% at Run to 12\% at
Reimplement to mean that the strongest agent does far better when it can
run the authors' code than when it must rebuild the method from the paper. The harness, the frozen rubric, and every graded
```
**New.**
```latex
artifact does not. We read DeepSeek-V4-Flash's fall from 41\% at Run to 12\% at
Reimplement to mean that this agent does far better when it can
run the authors' code than when it must rebuild the method from the paper. The harness, the frozen rubric, and every graded
```
% moves with: E7 (41% -> 38% if the 2505.23747 correction stands, results/e7/rescore_summary.md:23)

### 4c. Remaining uses of "strongest" (no change drafted)

`iclr2027_conference.tex:157` (Figure 2 caption), `:615-617` (Conclusion), and `appendix/h_runs.tex:22` speak of "the two strongest agents" as a group, which Figure 2 defines by mean audit score. They hold as long as DeepSeek-V4-Flash and Muse Spark 1.2 remain the top two by mean score. If the author wants the definition stated, the Figure 2 caption can read "Failure counts for the two agents with the lowest and the two with the highest mean audit score." (still two lines).

---

## 5. The 28 cells with no graded run, the two new grades, and the reruns (Section 5.2, Appendix B, Appendix C, Section 5.3)

**Promise.**
- replies.md:17: "Failures outside the agent (Sections 5.2 and 5.3): the trace of all 28 cells with no graded run, the bound on build failures from our aarch64 hardware with an x86 replay, and a re-execution of missed runs with new seeds."
- replies.md:232: "Section 5.2: the trace of all 28 cells with no graded run, the missing grades added, and the two runs that evaluated a downloaded checkpoint counted as not reproduced."
- replies.md:290: "The two missing audits now have grades from the same pinned auditor, reproduced (score 8) on 2503.23035 and partial (score 6) on 2510.08177. [We reran the 4 cells of 2510.20725 and the 16 stopped cells with the same settings, and r of them reproduce.] Every rate in the revision includes these grades."
- paper_revisions.md:7 (`c_rubric.tex:126`, 25 becomes 28; see 5c).

Author decision first. Risk 2 in replies.md: this paragraph says that 16 empty cells stopped on the cluster job, which reverses the 2026-09-10 and 09-19 instructions to count all 28 as agent failures at score 0 (memory paper-missing-cells-accounting). The draft keeps the scoring rule (a cell with no graded run still scores 0) and adds the trace.

### 5a. Section 5.2, new paragraph

**Location.** New paragraph after the frontier result paragraph of Section 1b (that is, after `iclr2027_conference.tex:500`). It could instead move to Appendix B to save about five main-body lines, leaving one sentence and a footnote in Section 5.2.

**New.**
```latex
Of the 400 cells, 28 produced no graded run, and we traced each one through
the cluster's job accounting and the harness logs. Six failed outside the
agent, since the four cells of 2510.20725 never started because of a
prompt-rendering bug in our harness and two audits of Muse Spark 1.2 never
returned a verdict. Sixteen stopped before the agent finished, when the
cluster job running them reached its 48-hour limit or was cancelled, and two
ended when the agent's context filled, which our protocol counts as an agent
failure. Four finished runs had no grade from the pinned auditor, and it has
now graded the three whose files survive at 0, 2, and 0, none of them
reproduced, while the fourth lost its files and stays ungraded. The pinned
auditor has also graded the two missing audits, reproduced (score 8) on
2503.23035 and partial (score 6) on 2510.08177. \todo{We reran the 4 cells of
2510.20725 and the 16 stopped cells with the same settings, and r of them
reproduce.} Every rate in this paper includes these grades, and a cell that
still has no graded run counts as a failure at score 0.
% src: replies.md:286-290; results/e8/summary.json (empty_cells: total 28; outside_agent_cells: 6); results/e8/d_cells.md and e8/regrade_dcells.json (3 of 4 regraded at 0, 2, 0; 2510.19314 ungraded); results/e8/README.md:19-27 (B 16, A 2, D 4; TIMEOUT at the 2-day limit or CANCELLED); results/e8/regrade_muse.json (2503.23035 score 8, 2510.08177 score 6)
```

### 5b. Appendix B, scoring rule

Not promised in current replies (this clause only matters if the reruns enter).

**Location.** `paper_latex/appendix/b_models.tex:126-130`. No change is needed if the rule stays as written ("a cell without a graded run counts as a failure at score 0"). If the reruns enter, add after "at score 0," the clause:
```latex
after the reruns of Section~\ref{subsec:results},
```

### 5c. Appendix C, histogram text (paper_revisions.md item 1)

Not promised in current replies (the promise is paper_revisions.md item 1 only; the replies promise the trace in Section 5.2, not Appendix C).

**Location.** `paper_latex/appendix/c_rubric.tex:125-126`.

**Old.**
```latex
Figure~\ref{fig:score-dist} shows how the 400 cells fall across the scale, with
the 25 cells that have no graded run counted at 0. Among graded runs the
```
**New.**
```latex
Figure~\ref{fig:score-dist} shows how the 400 cells fall across the scale, with
the \todo{23} cells that have no graded run counted at 0. Among graded runs the
% src: results/e8/summary.json empty_cells.total 28; replies.md:288-290 give grades to 5 of them (2 Muse Spark audits, 3 regraded runs), so 28 - 5 = 23 before the reruns, and fewer after
```
Check the figure source before changing the number: if `figures/score_distribution` was built with 25 empty cells, the figure and the text have to change together.

### 5d. Section 5.3, unlabeled cells

Not promised in current replies (a consequence of the grades in 5a, listed in Section 15).

**Location.** `paper_latex/iclr2027_conference.tex:507-508` ("where 28 cells carry no label") and `appendix/g_taxonomy.tex:48` (No label row 13, 10, 2, 3, 28). The two newly graded runs and every rerun need dissection labels, after which the count is `\todo{28 - labeled}`, and Figures 2 and 5 need rebuilding.

---

## 6. Appendix C, runs at score 0 (paper_revisions.md item 2)

Not promised in current replies (the promise is paper_revisions.md:8 only).

**Promise.** paper_revisions.md:8: "the 55 runs the auditor zeroed" becomes "the 53 runs the auditor zeroed".

**Location.** `paper_latex/appendix/c_rubric.tex:130-131`.

**Old.**
```latex
misses the bar. Two smaller peaks of nearly equal height sit at 0 and 8, the 55 runs the
auditor zeroed for an integrity break and the 52 runs the auditor accepted as reproductions with minor caveats.
```
**New.**
```latex
misses the bar. Two smaller peaks of nearly equal height sit at 0 and 8, the 53 runs the
auditor zeroed for an integrity break and the 52 runs the auditor accepted as reproductions with minor caveats.
% src: results/e4/summary.json auditor_col_totals (score 0: 53, score 4: 72, score 6: 60, score 8: 52)
```
The mode counts at 4 (72) and 6 (60) at line 127-129 match the same field. If the two new Muse Spark grades enter, the counts become 61 at 6 and 53 at 8.

---

## 7. Scan for downloaded checkpoints (Section 5.2)

**Promise.**
- replies.md:18: "Checkpoint downloads (Section 5.2): a scan of every transcript, after which the 2 runs that evaluated a downloaded checkpoint of the claimed model count as not reproduced."
- replies.md:272: "Yes, we checked, and two reproduced runs evaluated a downloaded checkpoint of the claimed model, which the revision counts as not reproduced."
- replies.md:274: "The scan cannot see a download made inside an imported library, and Section 5.2 states this limit."
- replies.md:280: "Muse Spark 1.2's reproduced Retrain papers fall from 9 of 33 to 8 of 33 (33 is the number of Retrain papers, one cell per paper), and MiniMax-M2.7's reproduced Reimplement papers fall from 2 of 33 to 1 of 33 (Section 5.2). The best-agent rates stay at 9 of 33 at Retrain (DeepSeek-V4-Flash) and 5 of 33 at Reimplement (Muse Spark 1.2)."
- replies.md:70: "the revision counts both as not reproduced, so DeepSeek-V4-Flash alone is best at Retrain with 9 of 33"

**Location.** New paragraph after the empty-cell paragraph of Section 5a, in Section 5.2.

**New.**
```latex
The harness keeps no network log, so we scanned every transcript, including
the commands, the fetched URLs, and the code the agent wrote, for downloads of
model weights. The scan finished on 368 of the 372 graded runs, none of the
four it could not finish was reproduced, and it covered all 42 reproduced
Retrain and Reimplement runs. Of the 16 of these with a match, two evaluated a
downloaded checkpoint of the model the claim is about, Muse Spark 1.2 on
2508.21046 at Retrain and MiniMax-M2.7 on 2505.12677 at Reimplement. Because
these tiers ask the agent to train or rebuild that model, we count both runs
as not reproduced, which lowers Muse Spark 1.2 to 8 of 33 at Retrain and
MiniMax-M2.7 to 1 of 33 at Reimplement, so DeepSeek-V4-Flash alone has the best
Retrain rate, 9 of 33, and the best Reimplement rate stays 5 of 33. The scan does not detect a download made inside an imported library.
% src: results/e9/README.md:12-19 (368/372 scanned; 4 timeouts; Retrain 13 of 29 and Reimplement 3 of 13 reproduced runs with a hit, 16 in all; class c 2); results/e9/class_review.csv rows 20-24; results/e8/bound.csv (muse retrain 9/33, minimax reimplement 2/33 before the correction)
```

Note. The 4 unscanned runs were not reproduced according to the viewer index (replies.md:274); that file sits outside `rebuttal/results/`, so check it before the clause goes in. Risk 5 (whether 2508.21046 and 2505.12677 belong at Run if the authors released the claimed weights) is not addressed here. If the papers move tier, this paragraph changes.

---

## 8. Auditor against human grades (Section 4, Appendix D)

**Promise.**
- replies.md:14: "Auditor validation (Appendix D): the confusion matrix of auditor against human verdict over the 372 runs with both grades, with per-tier precision and recall, the 7/8 boundary and agreement on integrity flags."
- replies.md:45: "Appendix D: the five-by-five confusion matrix of auditor against human verdict, with the 7/8 boundary and high-severity flags."
- replies.md:135: "Appendix D: the confusion matrix of auditor against human verdict, with precision, recall, the 7/8 boundary and flag agreement, and a statement that the study gives one human label per run."
- replies.md:141: "our reply to Reviewer T29u (Q1) shows the full confusion matrix that Appendix D now gives."
- replies.md:153: "That design does not measure agreement between humans, and Appendix D now states this beside the F1."

### 8a. Section 4

**Location.** `paper_latex/iclr2027_conference.tex:412-417`.

**Old.**
```latex
Three human graders scored all 396 runs that started, one grader per run,
under the same rubric and blind to the auditor's score, and the auditor's
verdicts agree with theirs at an F1 of 0.82 on the reproduced verdict
(Appendix~\ref{app:auditor-validation}). For comparison, PaperBench reports an
F1 of 0.83 for its LLM judge against human labels on individual rubric
items~\citep{starace2025paperbench}.
```
**New.**
```latex
Three human graders scored all 396 runs that started, one grader per run,
under the same rubric and blind to the auditor's score. On the 372 of these
runs that the auditor also graded, its reproduced verdicts reach a precision of
88\%, a recall of 77\%, and an F1 of 0.82 against the human labels, and it
calls 73 runs reproduced where the humans call 83, so the auditor is the
stricter grader (Appendix~\ref{app:auditor-validation}). For comparison,
PaperBench reports an F1 of 0.83 for its LLM judge against human labels on
individual rubric items~\citep{starace2025paperbench}.
% src: results/e4/summary.json reproduced_ge8 (tp 64, auditor_pos 73, human_pos 83, precision 0.877, recall 0.771, f1 0.821)
```

### 8b. Appendix D

**Location.** `paper_latex/appendix/d_auditor_validation.tex:13-17` (replace the paragraph; lines 1-11 stay).

**Old.**
```latex
Three human graders scored all 396 runs that started, one grader per run, from
the run bundle, its pinned claim, and the rubric text of
Appendix~\ref{app:rubric}, blind to the auditor's score and verdict. Taking the
human label as the reference, the auditor's reproduced verdicts reach an F1 of
0.82.
```
**New.**
```latex
Three human graders scored all 396 runs that started, one grader per run, from
the run bundle, its pinned claim, and the rubric text of
Appendix~\ref{app:rubric}, blind to the auditor's score and verdict. Each run
has one human label, so the study measures the auditor against a human grader
and does not measure agreement between humans. The auditor graded 372 of the
396 runs, and Table~\ref{tab:auditor-confusion} compares the two verdicts on
those runs. Taking the human label as the reference, the auditor's reproduced
verdicts reach a precision of 64/73 = 88\% (95\% Wilson interval 78\% to
93\%), a recall of 64/83 = 77\% (67\% to 85\%), and an F1 of 0.82, and the two
agree on the five-way verdict for 306 of the 372 runs. On the 0 to 10 scale
they give the same score to 253 runs and scores within one point to 324, with
a mean absolute difference of 0.59 points. The disagreements lean one way. Of
the 28 runs that only one of them called reproduced, the human did in 19 and
the auditor in 9, so the auditor is the stricter grader.
% src: results/e4/summary.json (reproduced_ge8, verdict_agreement 306/372, exact_agreement 253, within_one 324, mae_0_10 0.59, auditor_yes_human_no 9, human_yes_auditor_no 19)

On the 100 runs that either grader placed at 7 or 8, the two agree on 75 about
which side of the reproduced line the run falls. A score of 0 covers a
high-severity integrity flag and three related conditions
(Table~\ref{tab:rubric}), and of the 57 runs that either grader placed at 0
they agree on 42. Table~\ref{tab:auditor-tier} gives the reproduced-verdict
agreement by tier. Recall is lowest at Reimplement, where it rests on 16 human
reproductions and its interval of 44\% to 86\% overlaps those of the other
tiers.
% src: results/e4/summary.json (boundary_7_8 100 and 75; disqualified_score0_as_high_severity either 57, both 42; per_tier_reproduced reimplement recall_wilson95 [44.4, 85.8])

\begin{table}[ht]
\centering
\small
\begin{tabular}{@{}lrrrrrr@{}}
\toprule
& \multicolumn{5}{c}{Auditor} & \\
\cmidrule(lr){2-6}
Human & Reproduced & Partial & Not reproduced & Unverifiable & Disqualified & Total \\
\midrule
Reproduced     & 64 & 15 &   2 & 0 &  2 &  83 \\
Partial        &  7 & 64 &  15 & 0 &  2 &  88 \\
Not reproduced &  2 &  6 & 130 & 3 &  5 & 146 \\
Unverifiable   &  0 &  0 &   1 & 6 &  2 &   9 \\
Disqualified   &  0 &  1 &   2 & 1 & 42 &  46 \\
\midrule
Total          & 73 & 86 & 150 & 10 & 53 & 372 \\
\bottomrule
\end{tabular}
\caption{Human verdict against auditor verdict on the 372 runs with both grades.}
\label{tab:auditor-confusion}
\end{table}
% src: results/e4/summary.json verdict_matrix_human_rows; column totals equal auditor_col_totals grouped by band (8-10: 52+16+5 = 73; 6-7: 60+26 = 86; 2-5: 47+17+72+14 = 150; 1: 10; 0: 53)

\begin{table}[ht]
\centering
\small
\begin{tabular}{@{}lrrr@{}}
\toprule
Tier & Precision & Recall & F1 \\
\midrule
Run         & 28/31 = 90\% & 28/35 = 80\% & 0.85 \\
Retrain     & 25/29 = 86\% & 25/32 = 78\% & 0.82 \\
Reimplement & 11/13 = 85\% & 11/16 = 69\% & 0.76 \\
\bottomrule
\end{tabular}
\caption{Agreement of auditor and human on the reproduced verdict, by tier.}
\label{tab:auditor-tier}
\end{table}
% src: results/e4/per_tier.csv (both, auditor_only, human_only); results/e4/summary.json per_tier_reproduced (f1 0.848, 0.82, 0.759)
```

Note. Risk 3 in replies.md: the matrix comes from the aggregate 0 to 10 table the author supplied on 2026-11-08 (`results/e4/README.md:3`), and no per-run label file is on disk. Its auditor columns match the 372 graded runs exactly. The two new Muse Spark grades are not in the matrix, since their human labels exist only inside the aggregate.

---

## 9. Appendix A, the writable logs and the log comparison

**Promise.**
- replies.md:15: "Log integrity (Appendix A): a corrected description of the two logs the agent can write, and a comparison of all 45,861 logged entries with the host transcript, which found one overwritten log, on a run the auditor had graded unverifiable."
- replies.md:134: "Appendix A: the description of the two harness logs now matches the code, and a comparison of all 45,861 logged entries with the host transcript found one overwritten log, on a run the auditor had graded unverifiable."
- replies.md:159 (After): "The auditor traces every number to the command that produced it. Because the agent could edit these two files, we compared every logged entry with the transcript the harness writes on the host, outside the sandbox."
- replies.md:165: "The comparison also found 119 commands in 65 runs that the harness ran but never wrote to commands.log, because two code paths return before writing the log. The host transcript holds all 119, and Appendix A reports the gap."
- replies.md:167: "This check catches any edit made through the agent's own commands, which the transcript records, and Appendix A states that limit."

**Location.** `paper_latex/appendix/a_harness.tex:130-134`, plus a new paragraph and table after line 134.

**Old.**
```latex
recorded alongside. We bind \texttt{evidence/} read-write, so the agent
can rewrite the harness-written \texttt{commands.log} and
\texttt{trajectory.jsonl}, and we add no integrity check that would detect such
an edit. We therefore instruct the auditor to read the bundle as unverified
claims and to trace every number to the command that produced it.
```
**New.**
```latex
recorded alongside. We bind \texttt{evidence/} read-write, so the agent
can rewrite the harness-written \texttt{commands.log} and
\texttt{trajectory.jsonl}, and the harness checks neither file while the run
is live. The auditor traces every number to the command that produced it.
Because the agent could edit these two files, we compared every logged entry
with the transcript the harness writes on the host, outside the sandbox.

\paragraph{Log comparison.} For each of the 372 graded runs we matched every
entry that an agent command produced in the two files against the host
transcript, requiring the same command and return code and, for
\texttt{run\_gpu} entries, the same cost and remaining budget.
Table~\ref{tab:log-check} gives the outcome for the 45,861 such entries, and
the other 3,724 rows of the two files are written by the harness itself. We
also searched every agent command for writes to the two files. One run wrote
to \texttt{commands.log}, where MiniMax-M2.7 on 2510.25146 replaced the file
with its own notes through a \texttt{write\_file} call, and the auditor had
graded that run 1 of 10 as unverifiable. No run wrote to
\texttt{trajectory.jsonl}. The comparison also found 119 commands in 65 runs
that the harness ran and did not write to \texttt{commands.log}, because two
early-return paths in the harness skip the log, and the host transcript holds
all of them. The host transcript is not hash-chained, so it is not
tamper-evident by construction, and its protection is that it lies outside
every directory the sandbox mounts. The comparison detects edits made through
the agent's own commands, which the transcript records, and it detects no
other kind of edit.
% src: results/e5/README.md:9-17 (372/372 matched; 45,861 of 49,585 entries checked, 3,724 host-written; 45,673 passed; 185 explained; 3 unmatched; 1 write into commands.log, run 2510.25146; 65 runs missing 119 headers, workspace_bash.py:76-77 and run_gpu.py:145); results/e5/summary.json

\begin{table}[ht]
\centering
\small
\begin{tabular}{@{}lr@{}}
\toprule
Entry & Count \\
\midrule
Matches exactly & 45,673 \\
Call refused by the harness, so no cost line & 100 \\
Remaining budget within 0.00015 H100-hours & 60 \\
First attempt of a retried call & 25 \\
Remaining budget differs by up to 0.0003 H100-hours, cost equal & 3 \\
\midrule
Total & 45,861 \\
\bottomrule
\end{tabular}
\caption{Agent-issued entries of \texttt{commands.log} and \texttt{trajectory.jsonl}
compared with the host transcript over the 372 graded runs.}
\label{tab:log-check}
\end{table}
% src: results/e5/README.md:11 and :18 (100, 60, 25 explained; 3 unmatched at 0.0002 to 0.0003 h with cost equal)
```

Notes. The replies give the budget in "GPU-hours"; the paper's unit is H100-hours, so the table uses that. Risk 8 (the evidence directory's modification time is more than 60 seconds after run end in 63 of 372 runs, cause not established, `results/e5/README.md:14`) is left out of the appendix until its cause is known. The hash-chained host log in PLAN.md Section 3 item 4 is not drafted, since Risk 6 records that no such log exists in the code.

---

## 10. Appendix E, what Stage III checked, and the AI-use statement

**Promise.**
- replies.md:136: "Appendix E: what the final construction stage checked, and a check of every frozen target (the target tuple and minimal configuration fixed before any agent ran) against its paper."
- replies.md:188: "One author reviewed every extracted field before the dataset was frozen and no second person did, so there is no annotator agreement to report. Appendix E now states this."
- paper_revisions.md:11 (`iclr2027_conference.tex:668` stays as written).

### 10a. Appendix E, Stage III subsection

**Location.** `paper_latex/appendix/e_construction.tex:91`, appended to the end of the Stage III paragraph (after "papers stayed eligible because one agent found one.").

**New.** The author reviewed every extracted field (replies.md:188), so this is the text that goes in.
```latex
Stage III checked the availability calls and the compute estimates. The
claim, the minimal configuration, and the match target of each paper come from
the Stage I classifier, and an author reviewed each of these fields before the
freeze with no second reviewer, so we report no annotator agreement for them.
Appendix~\ref{app:target-check} checks each frozen target against its paper.
```
The "and the compute estimates" clause follows the paper (`iclr2027_conference.tex:326`, `:364-365`) and matches replies.md:188 ("settled each compute estimate"). The last sentence is a cross-reference sentence. If the author prefers the footnote form, it becomes `\footnote{Appendix~\ref{app:target-check} checks each frozen target against its paper.}` on the sentence before.

### 10b. AI-use statement

Not promised in current replies. The author reviewed every extracted field (replies.md:188), so `paper_latex/iclr2027_conference.tex:666-669` stays as written, and the Variant B rewording that was drafted here is dropped.

---

## 11. Appendix E, the check of every frozen target against its paper

**Promise.**
- replies.md:16: "Targets and tolerances (Appendices E and F): every frozen target checked against its paper by a model from a different lab than our auditor, and every graded run rescored at 1%, 2%, 5% and 10% relative tolerance."
- replies.md:47: "Appendix E: every frozen target (the value, metric, dataset and configuration fixed for each claim before any agent ran) checked against its paper by a model from a different lab than our auditor[, with k targets corrected and their runs rescored]."
- replies.md:190: "A model from a different lab than our auditor (OpenAI's gpt-6.1-sol) read each of the 100 papers and answered four yes-or-no questions about the frozen target, quoting the passage behind each answer."
- replies.md:194: "The dataset and method questions check the minimal configuration, the value and metric questions check the target, and the choice of claim rests on construction alone, which Appendix E now states. The checking model saw the frozen target when it answered, so we describe this as a check of each target against its paper."

**Location.** New subsection in `paper_latex/appendix/e_construction.tex`, after the Stage III subsection (after line 91) and before `\subsection{The evaluation and development splits}` at line 93.

**New.**
```latex
\subsection{Target check}
\label{app:target-check}

We checked every frozen target against its paper with gpt-6.1-sol\todo{cite},
a model from a different lab than the auditor. Given the paper text, the
claim sentence, and the frozen metric, dataset and split, configuration, and
value, it answered four yes-or-no questions with a supporting quotation each,
whether the paper reports this value within rounding, for this metric, on this
dataset and split, and for this method or variant. Implementation details of
the released code, such as checkpoint names, step counts, seeds, and hardware,
were out of scope. Because the model saw the frozen target, this checks each
target against its paper and does not re-derive it. The value and metric
questions check the target, the dataset and method questions check the
minimal configuration, and the choice of claim rests on construction alone.
Table~\ref{tab:target-check} gives the counts.
% src: results/e7/README.md:3-5 (gpt-6.1-sol, reasoning high, pdftotext of the arXiv PDF; four questions; out-of-scope details)

\begin{table}[ht]
\centering
\small
\begin{tabular}{@{}lrrrrr@{}}
\toprule
The paper supports the frozen & Of 100 & 95\% interval & Run & Retrain & Reimplement \\
\midrule
Value          & 92 & 85--96 & 32/34 & 29/33 & 31/33 \\
Metric         & 95 & 89--98 & 32/34 & 30/33 & 33/33 \\
Dataset and split & 76 & 67--83 & 24/34 & 25/33 & 27/33 \\
Method or variant & 69 & 59--77 & 22/34 & 18/33 & 29/33 \\
\midrule
All four       & 55 & 45--64 & \todo{} & \todo{} & \todo{} \\
\bottomrule
\end{tabular}
\caption{Frozen targets whose paper supports each part, by tier.}
\label{tab:target-check}
\end{table}
% src: results/e7/summary.json step3 (by_question yes and wilson95; by_tier Easy/Medium/Hard a-d; all_four_yes 55, wilson95 [0.4524, 0.6439]); all-four by tier is not in summary.json

The most common failure is the method question alone, on 18 papers. On
2506.18890, for example, the frozen value of 27.443 PSNR appears in the paper
for 24 input views, while the frozen configuration says 12.
% src: results/e7/README.md:9-10; results/e7/v3_failures.csv
```

Author decision. Whether the corrected targets replace the frozen ones as the grades of record (so 14/34 becomes 13/34 everywhere, and the abstract's 41% becomes 38%) or are reported as a sensitivity check beside the frozen grades. The replies (line 47) are written for the first reading. Section 15 lists every line that changes under it.

---

## 12. Appendix F, tolerance table

**Promise.**
- replies.md:46: "Appendix F: every graded run rescored at 1%, 2%, 5% and 10% tolerance."
- replies.md:95: "The best agent's count of reproduced papers moves by at most 5 of the 34 Run papers (14 at 5% against 9 at 1%), 3 at Retrain and 1 at Reimplement."
- replies.md:99: "All agents together reproduce 56, 65, 73 and 82 of the 400 cells, with 70 or 72 at an absolute tolerance of 1 or 2 points on percentage metrics (Appendix F)."
- replies.md:198: "the ordering of the tiers holds from 1% to 10% (our reply to Reviewer T29u, Q2, and Appendix F)."

**Location.** `paper_latex/appendix/f_dataset.tex:113-119`, the "Match targets and tolerance" paragraph, extended in place, with a table after it (before the `\newpage` at line 121).

**Old.**
```latex
\paragraph{Match targets and tolerance.} For 62 of the 100 evaluation papers
the match bar is a point estimate, for 21 a stated baseline the run must beat,
for 14 a reported threshold it must clear, for 1 the size of a reported delta,
and for 1 a reported range it must fall inside. A run matches a
point estimate when its measured value lies within the authors' stated
tolerance, or within 5\% relative when the paper states none
(Figure~\ref{lst:rubric-text}).
```
**New.**
```latex
\paragraph{Match targets and tolerance.} For 62 of the 100 evaluation papers
the match bar is a point estimate, for 21 a stated baseline the run must beat,
for 14 a reported threshold it must clear, for 1 the size of a reported delta,
and for 1 a reported range it must fall inside. A run matches a
point estimate when its measured value lies within the authors' stated
tolerance, or within 5\% relative when the paper states none
(Figure~\ref{lst:rubric-text}), and 58 of the 62 point estimates use the 5\%
default. To measure how much the default decides, we rescored every graded run
at relative tolerances of 1\%, 2\%, and 10\% (Table~\ref{tab:tolerance}). The
ordering of the tiers holds at every setting, and the best agent's count moves
by at most 5 papers at Run, 3 at Retrain, and 1 at Reimplement. Tightening to
1\% moves 17 of the 73 reproduced runs to partial, and loosening to 10\% moves
up 9 partial runs whose only failed criterion was the number. For example,
DeepSeek-V4-Flash measured 90.6 on 2511.19808 against a frozen target of 97.3,
a gap of $6.7 / 97.3 = 6.9\%$, so that run is partial at 5\% and reproduced at
10\%. With an absolute tolerance of 1 or 2 points on percentage metrics, 70 or
72 of the 400 cells reproduce.
% src: results/e6/summary.json (claims: 62 point estimates, point_estimate_default_5pct 58, point_estimate_stated_margin 4; falls_by_setting rel1 17; number_only_partials 9; settings abs1, abs2); results/e6/README.md:13-24 (worked run; best-agent table)

\begin{table}[ht]
\centering
\small
\begin{tabular}{@{}lrrrr@{}}
\toprule
Relative tolerance & Run, best of 34 & Retrain, best of 33 & Reimplement, best of 33 & All agents, of 400 \\
\midrule
1\%           &  9 &  8 & 4 & 56 \\
2\%           & 12 &  9 & 5 & 65 \\
5\% (default) & 14 &  9 & 5 & 73 \\
10\%          & 14 & 12 & 5 & 82 \\
\bottomrule
\end{tabular}
\caption{Reproduced cells at four relative tolerances, for the best agent in
each tier and over all agents.}
\label{tab:tolerance}
\end{table}
% src: results/e6/README.md:19-24 (best agent per tier); results/e6/summary.json cells summed per setting (56, 65, 73, 82)
% moves with: E7 and the regrade decision (the 5% row becomes the post-correction counts); rerun rel1/rel2/rel10 if the counts of record change
```

Note. The table is at the frozen targets and the submission's graded runs. If the E7 corrections or the regrades become the grades of record, the E6 rescore has to be rerun on them (PLAN.md Section 4, Tue 11-10) so that the 5% row matches Section 5.2.

---

## 13. Section 5.3, the bound on build failures from the aarch64 hardware

**Promise.**
- replies.md:17: "the bound on build failures from our aarch64 hardware with an x86 replay"
- replies.md:48: "Section 5.3: how much build failures on the aarch64 hardware move the best-agent rates."
- replies.md:230: "Section 5.3: the bound on build failures with an x86 replay, and a re-execution of missed runs with new seeds."
- replies.md:256: "Removing all 24 from the denominators leaves DeepSeek-V4-Flash, the best agent at Run and Retrain, at 14/34 = 41% [26%, 58%] and 9/33 = 27% [15%, 44%], since it had none of these failures there, and moves Muse Spark 1.2, the best at Reimplement, from 5/33 = 15% [7%, 31%] to 5/32 = 16% [7%, 32%] (Section 5.3)."

**Location.** `paper_latex/iclr2027_conference.tex:538-541`.

**Old.**
```latex
differs from the one the paper reports. The build failures
depend on the host as well as the agent. Five of MiniMax-M2.7's eight Run-tier
cases trace to packages without aarch64 wheels on our GH200 nodes, and
DeepSeek-V4-Flash met the same packaging gaps and adapted in two ways. On
```
**New.**
```latex
differs from the one the paper reports. The build failures
depend on the host as well as the agent. Our reading of the 24 transcripts
traces 14 to a package with no build for the aarch64 CPUs of our GH200 nodes,
including five of MiniMax-M2.7's eight Run-tier cases, 7 to other environment
problems, and 3 to agent error, and 9 of the 12 aarch64 installs we could
replay build and import on x86 nodes (95\% interval 47\% to 91\%). Removing all
24 runs from the denominators moves no best-agent rate by more than one
percentage point and leaves the best Run rate at 14 of 34, since
DeepSeek-V4-Flash has none of them at Run.
DeepSeek-V4-Flash met the same packaging gaps and adapted in two ways. On
% src: results/e8/summary.json build_dependency_runs (total 24; class_counts A 16, O 5, E 3; explicit_aarch64_minimax_run 5); results/e8/x86/README.md:3-4 (2 of the 16 not chip failures, so 14 aarch64 and 5 + 2 = 7 other; 12 replayed, 9 build, Wilson 0.47 to 0.91); results/e8/bound.csv (dsv4 env_runs 0, 0, 1; best Run 14/34 unchanged; Reimplement 5/33 -> 5/32 = 15.2% -> 15.6%; Retrain best stays dsv4 9/33 after the CogVLA correction, Muse 8/32)
```

---

## 14. Section 5.3 and Limitations, the re-execution of missed runs with new seeds

**Promise.**
- replies.md:137: "Section 5.3 and Limitations: a re-execution of missed runs with new seeds, and the bound on build failures."
- replies.md:175: "For papers where an agent followed the released pipeline and still landed outside tolerance, we extracted the final command sequence from its transcript and re-ran it on the same GH200 nodes with two new seeds and no model in the loop."
- replies.md:258: "Our reply to Reviewer rqBN (Q1) re-runs the last commands of missed runs on the same nodes with new seeds and no agent, and both Retrain papers miss again on both seeds."

### 14a. Section 5.3, end of "Where the failures occur"

**Location.** `paper_latex/iclr2027_conference.tex:543`, after "it replaced the package with an unvalidated port the auditor disqualified." and before `\paragraph{What the successful runs do.}`.

**New.**
```latex
To test whether a run outside tolerance misses because of the environment, we
re-ran the final command sequence of three such runs on the same nodes with
two new seeds and no model in the loop.\footnote{We took runs labeled Ran,
outside tolerance at the Run and Retrain tiers in the 0--8 H100-hour band, and
only three had a single command chain that ran without code the agent had
edited by hand or several GPU sessions.} On 2505.17836 both seeds miss again
and the measured value repeats within 0.0007, so that miss recurs without the
agent. On 2510.07501 the value moves by 0.28 across seeds against a target of
$-0.20$, which puts the original near miss inside seed variation.
\todo{On 2506.10351 both seeds ... .}
% src: results/e10/results.md (2505.17836: 0.0395, 0.0400, 0.0393, spread 0.0400 - 0.0393 = 0.0007; 2510.07501: -0.2241, -0.1308, +0.0566, spread 0.0566 - (-0.2241) = 0.28, target -0.20; 2506.10351 pending); results/e10/README.md:3-14 (selection rule; Run 1 of 6, Retrain 2 of 4)
```

### 14b. Limitations, Attributing a miss

**Location.** `paper_latex/iclr2027_conference.tex:583-586`.

**Old.**
```latex
\paragraph{Attributing a miss to the agent.} RECLAIM has no human
reproduction on our cluster, so for the 76 runs that executed a faithful
pipeline and landed outside tolerance we cannot separate agent error from
seed and hardware variance. An exhaustive human reproduction of these papers
```
**New.**
```latex
\paragraph{Attributing a miss to the agent.} RECLAIM has no human
reproduction on our cluster, so for the 76 runs that executed a faithful
pipeline and landed outside tolerance we cannot separate agent error from
seed and hardware variance, beyond the three runs we re-executed
(Section~\ref{subsec:mechanisms}). An exhaustive human reproduction of these papers
```
The rest of the paragraph stays, which already answers rqBN Q1 ("the Limitations section says so", replies.md:169). The paragraph grows by less than one line.

---

## 15. Counts that change if the corrections enter (propagation list)

Not promised in current replies by line. The replies promise the grades (replies.md:290, "Every rate in the revision includes these grades") and the two checkpoint corrections (replies.md:280), and this list follows from them. The checkpoint corrections now count as promised, so the Muse Spark Retrain (8/33) and MiniMax-M2.7 Reimplement (1/33) entries are no longer conditional.

No reply promises these lines by name, but replies.md:54 and :290 ("Every rate in the revision includes these grades") commit the revision to them once the regrade decision is made. Arithmetic, from the files cited in Sections 5, 7, and 11: the regrade decision gives 73 + 1 (Muse Spark, 2503.23035, Run) - 1 (Muse Spark, 2508.21046, Retrain) - 1 (MiniMax-M2.7, 2505.12677, Reimplement) = 72. The E7 corrections then remove 2 more Run cells (DeepSeek-V4-Flash and MiniMax-M2.7 on 2505.23747), giving 70, and the reruns can add r.

| Location | Current text | After the regrade decision | After E7 as well |
| :- | :- | :- | :- |
| Abstract, `iclr2027_conference.tex:80` | "41\% of Run-tier papers" | unchanged | 38\% (13/34) |
| Intro, `:122` | "41\% of Run-tier papers" | unchanged | 38\% |
| `:461` | "73 of the 400" | 72 | 70 |
| `:478` | "Muse Spark 1.2 on 23 of 33" (partial or better, Retrain) | `\todo{}` if the CogVLA run's score falls below 6 | same |
| `:481-482` | "$z = 2.7$", "$z = 1.2$" | unchanged | `\todo{}` (DeepSeek-V4-Flash Run 13/34) |
| `:490` | "13 of 132 cells reproduce there" | 12 | 12 |
| `:497-500` | "against 73 audited reproductions"; "the auditor confirms 10 of its runs" (MiniMax-M2.7); "confirms 27" (DeepSeek-V4-Flash) | 72; 9; 27 | 70; 8; 26 |
| `:494-496` | "\$4{,}835", "\$12.21 per run and \$66 per confirmed reproduction" | `\todo{}` with the rerun and regrade costs | same |
| `:547`, `:552` | "58 of the 73", footnote "72 Reproduced runs", "45 of the 73 successful runs" | `\todo{}` from the dissection records | same |
| Conclusion, `:611`, `:618` | "41\%" | unchanged | 38\% |
| `appendix/b_models.tex:154-185` | Table 5 counts and means | Muse Spark Run 10/34, Retrain 8/33, All `\todo{}`; MiniMax-M2.7 Reimplement 1/33, All 9/100; all agents 32/136, 28/132, 12/132, 72/400; every mean `\todo{}` | DeepSeek-V4-Flash Run 13/34, All 26/100; MiniMax-M2.7 Run 2/34, All 8/100; all agents Run 30/136, 70/400 |
| `appendix/c_rubric.tex:126-131` | 28 (Section 5c), 53 at 0, 60 at 6, 52 at 8 | 26; 53; 61; 53 | `\todo{}` from the E7 regrades |
| `appendix/g_taxonomy.tex:38`, `:48` | Reproduced 72, No label 28 | `\todo{}` after labeling | same |
| Figures 2, 4, 5, 6, score distribution | built at the submission counts | rebuild | rebuild |

The DeepSeek-V4-Flash Run count after E7 (13/34) is from `results/e7/rescore_summary.md:23`. The Muse Spark and MiniMax-M2.7 changes are from `results/e8/regrade_muse.json` and `results/e9/class_review.csv`. The Muse Spark Run interval at 10/34 and every changed interval are not in `rebuttal/results/` and stay slots.

---

## 16. Limitations, scope of the claims

**Promise.**
- replies.md:268: "Section 5 and the Limitations section state the scope, and the revision adds that the claims hold for these papers and agents and that other venues, years and models remain untested."

**Location.** `paper_latex/iclr2027_conference.tex:592` (the Scope paragraph of Limitations).

**Old.**
```latex
\paragraph{Scope.} The 100 papers come from one venue and year, have a pinned experiment under a 96 H100-hour cap, and exclude papers that need a paid or closed API (15 in the audit pool, Figure~\ref{fig:funnel}).
```

**New.**
```latex
\paragraph{Scope.} The 100 papers come from one venue and year, have a pinned experiment under a 96 H100-hour cap, and exclude papers that need a paid or closed API (15 in the audit pool, Figure~\ref{fig:funnel}). Our claims hold for these papers and the agents we tested, and other venues, years, and models remain untested.
```
This adds about one typeset line. The Section 5 half of the promise is met by the frontier paragraph of Section 1b.

---

## Promises not drafted, and why

1. **Error bars on Figure 4** (Section 2c). The figure is built by `figures/build.py` from HTML, so it needs a figure build, a DOM audit, and a render check, none of which a text draft covers. Only the caption is drafted.
2. **Every number of the frontier arms** (Section 1b, 1c). The runs are still going and only 15 to 24 runs are graded (`results/frontier/README.md`, `results/databook/frontier_cells.csv`). The paragraph and table structure are drafted with slots.
3. **Repeat-run result, E10 on 2506.10351, the 20 reruns, E7 author verdicts and rescore, and the 73 or 72 count.** These are drafted as `\todo{}` slots, as the brief asks.
4. **Recomputed mean scores, Wilson intervals for the All-tiers rows of Table 5, and the dissection counts after the regrades** (Section 15). These are derived from per-cell data that is not summarized under `rebuttal/results/`, so they stay slots. The mean scores matter for Table 5 and the Section 5.2 sentence that gives them (finding 1).
5. **Bib entries for gpt-6.1-sol, gpt-6-astra, Muse Wonder, and Codex CLI.** They need the vendors' own cite-as text, which is not in the repo. The Wilson entry is drafted from its DOI.
6. **Hash-chained host log** (PLAN.md Section 3 item 4). Not promised any more (Risk 6), since no such log exists in the code.
7. **The 27 cells traced outside the agent** (replies.md:237 cites "Section 5.2 and Section 5.3"). The parts are in Sections 5a (6 cells) and 13 (14 aarch64 and 7 other environment runs), and no separate sentence sums them, to save main-body lines. If the author wants the sum, it fits as one clause at the end of Section 13: "so we traced 27 of the 400 cells to causes outside the agent".

## Main-body growth estimate

At about 95 characters per typeset line in the ICLR column, the main-body edits add roughly:

| Edit | Lines |
| :- | -: |
| 1a frontier sentences in Section 5.1, with footnote | +7 |
| 1b frontier result paragraph in Section 5.2 | +4 |
| 1d Limitations, Agents | -1 |
| 2a and 3, Section 5.2 opening with intervals, ranking rule, repeat runs, footnote | +9 |
| 4a, 4b wording | 0 |
| 5a empty-cell paragraph | +7 |
| 7 checkpoint paragraph | +7 |
| 8a Section 4 | +2 |
| 13 aarch64 bound | +3 |
| 14a re-execution, with footnote | +7 |
| 14b Limitations | +1 |
| **Total** | **about +46 lines** |

That is about 0.8 of a page at roughly 55 lines per page. The main body now ends at the bottom of page 9 (checked with pdftotext on the current PDF), and the rebuttal limit is 10 pages (PLAN.md:204, `iclr_threads/lit.md:35`), so the edits fit with about 10 lines to spare before floats move. If it runs over, the cheapest cuts are to move Section 5a to Appendix B with a one-sentence pointer (about -5 lines) and to move the selection footnote of Section 14a into Appendix G beside the definition of Ran, outside tolerance (about -2 lines).
