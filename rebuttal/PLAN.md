# Rebuttal plan: ICLR 2027 submission 22528 (RECLAIM)

GOAL: move YGTR from 2 (weak reject) to at least 3, and move T29u and rqBN from 3 to 4, with replies posted on OpenReview by 2026-11-14.
DONE-WHEN: four replies (general, T29u, rqBN, YGTR) are posted, every number in them traces to a file under `rebuttal/results/`, and the revised PDF compiles with the main text inside 10 pages.
MUST-NOT-CHANGE: the frozen eval-100 split, the frozen rubric and pinned auditor (claude-sonnet-5) for every grade of record, the four-agent roster of the main results, the run directories under `/work/nvme/bfvr/`, and the paused Distillation files and jobs.

Scope: this plan answers the three official reviews only. The PAT pre-submission feedback is set aside on Mithil's instruction (2026-11-06).

## 0. Where we stand and how a score moves

The three reviewers agree that the task design is sound and carefully disclosed. Their objections fall into four groups: the agents are weak and the harness is thin (YGTR), one run per cell gives point estimates (T29u, YGTR), the auditor's validation is a single F1 with no confusion matrix and the logs it reads can be edited by the agent (T29u, rqBN), and some failures may come from the environment (YGTR, rqBN). YGTR's rating rests almost entirely on the first group, and its Informativeness score of 1 says the reviewer does not believe our failure modes describe the agents people actually use. The single most valuable result we can produce this week is therefore a run of the strongest OpenAI model inside both our harness and Codex CLI on the same stratified papers, because whichever way it falls it answers YGTR: if the frontier agent still fails in the same ways, the taxonomy generalizes; if Codex lifts the rate, the paper gains a measured harness effect that no other reproduction benchmark reports. T29u and rqBN are already positive and mostly ask for measurements of the auditor; a new human-graded sample with a confusion matrix, a check that no agent edited its logs, and a tolerance sensitivity table answer nearly all of their soundness points.

Recommendation: spend the OpenAI budget on gpt-5.6-sol in two harnesses on the same papers, spend GPU hours on DeepSeek-V4-Flash repeats and a mini-SWE-agent arm, run a fresh two-grader human study, and answer the attribution questions with scans of the 400 existing runs. What would change this: if the first smoke run of gpt-5.6-sol costs more than about $45, the paired design shrinks to 6 papers and the mini-SWE-agent arm becomes the main harness evidence.

Second recommendation, and the one that decides whether T29u and rqBN trust anything else in the reply: **withdraw the F1 of 0.82 and replace it with the new study.** Its per-run labels are gone, so it cannot be audited, and rqBN asked specifically for the matrix behind it. Both simulated reviewers below said they would accept a plain disclosure and would distrust every other number if the figure stayed and its source later proved missing.

**Simulated reception (2026-11-06).** Three agents read this plan as the reviewers would. YGTR would move from 2 to 3, with Informativeness from 1 to 2, if E1 and E2 are delivered with a paired test and human failure-mode labels; YGTR would not reach 4 while the headline numbers come from the four weaker models. T29u would move to 4 if the 7/8 boundary table and the repeat runs come back clean. rqBN would move to 4 given a full confusion matrix, inter-human agreement, a real tamper check on the logs and an adjudication blind to the auditor. The fixes they asked for are folded into Sections 1 to 5 below.

## 1. Every reviewer concern, grouped

Legend: **NEW** needs new evidence (Section 2), **SURFACE** existing evidence we only need to state, **TEXT** a wording fix.

### A. Agent strength and harness (YGTR W1, Q1)

| Concern | Type | What answers it |
| :- | :- | :- |
| No frontier model; tested models are weak, so findings may not generalize | NEW | E1: gpt-5.6-sol as the agent in our harness on a stratified subset |
| The ReAct harness is too minimal; a researcher would use Claude Code, Codex or mini-SWE-agent, and failure modes would change | NEW | E1 Codex CLI arm (same model, same papers) and E2 mini-SWE-agent arm (DeepSeek-V4-Flash, same papers) |
| Why a thin harness at all | TEXT | Section 5.1 already argues fairness across models; add one sentence that the thin loop is a fixed baseline and that Appendix X now measures two production harnesses against it |

Memory limit: `baseline-harness-stays-thin` says the baseline harness stays minimal and failures are charged to the model by default. The new harnesses run as separate comparison arms, and the main results keep the thin loop, so this memory holds. `paper-model-roster` fixes the main results at four agents; the frontier arms go in a new appendix subsection and one main-text paragraph, and Laguna and GLM-5.2 stay out. The settled decision `paper-model-roster-2026-09` lists "the strongest closed agent is added" as its own revisit trigger, so adding gpt-5.6-sol is the planned path.

### B. One run per cell (T29u W1, YGTR W2)

| Concern | Type | What answers it |
| :- | :- | :- |
| Rates are point estimates; stochasticity could change rankings and tier gaps | NEW + SURFACE | E3: two more DeepSeek-V4-Flash runs on the 12-paper subset; add 95% Wilson intervals to the main rates now (no runs needed) |
| Failures may be transient | NEW | E3 gives per-paper verdict agreement across three runs |

Existing evidence to surface: the paper already prints the DeepSeek-V4-Flash two-proportion z (Run versus Reimplement 2.7, Run versus Retrain 1.2) and leaves close pairs unranked. The intervals for the best agent per tier are 14/34 = 41% [26%, 58%] at Run, 9/33 = 27% [15%, 44%] at Retrain and 5/33 = 15% [7%, 31%] at Reimplement, and 73/400 = 18% [15%, 22%] overall. Each interval is the Wilson score interval at 95%; for example at Run, 14 reproduced of 34 papers gives 0.41 with a half-width of about 0.16 after the Wilson correction. Memory `sweep-2883229-dsv4-easy` records three papers that DeepSeek-V4-Flash ran twice with the same score both times (8 and 8); that is too small to quote alone but agrees with E3's purpose.

### C. Auditor validity (T29u W2, Q1; rqBN W1)

| Concern | Type | What answers it |
| :- | :- | :- |
| Confusion matrix between auditor and humans, especially at the 7/8 boundary and for high-severity flags | NEW | E4: fresh human study, 48 runs, two blind graders per run |
| Precision, recall, tier-conditioned errors, multi-human adjudication, full 0 to 10 scale, anti-cheat flags | NEW | E4 reports all of these |
| commands.log and trajectory.jsonl are writable by the agent; no tamper-evident log | NEW + TEXT | E5: compare every run's logs with the host-side transcript the agent cannot reach; move the harness logs out of the sandbox for all new runs |

Memory limit, and the most important constraint in this plan: `human-grader-study-lost` records that the per-run labels behind the paper's F1 of 0.82 are not on disk (the repo holding them was deleted on 2026-09-06), and a Google Drive search on 2026-11-06 found no grading sheet either. **We cannot produce a confusion matrix, precision, recall or a per-tier breakdown for the 396-run study, and the reply must not imply that we can.** The settled decision `reclaim-auditor-human-f1-not-llm-agreement-2026-09` lists "a reviewer asks for n, grader count, or the labels; or the study is redone" as its revisit trigger, and both reviewers have now asked. The first step on 2026-11-07 is for Mithil to ask Haochen and Samridhi whether either still holds their grading sheet. If a sheet turns up, its confusion matrix goes in as well. Either way, E4 runs, because it also supplies what the original design could not: two graders per run, inter-human agreement, and flag-level agreement. Recommended wording for the opening of the auditor answer, if Mithil agrees to withdraw the figure: "The per-run labels of the original human study were not retained, so its 0.82 cannot be audited, and we withdraw it. Two co-authors graded a new sample of 48 runs, committed before grading began, blind to the auditor and to each other; the revision reports this study in its place." The graders are co-authors, and the reply says so. The memory also says not to reintroduce LLM-versus-LLM agreement numbers, so the reply does not use the 2026-07-23 auditor test-retest comparison (`auditor-test-retest-instability`, 5 of 32 runs changed their high-severity flag between two identical passes while no reproduced verdict changed) unless Mithil chooses to; E4 measures the flags against humans instead.

How the code handles the logs today (checked 2026-11-06): the harness process writes both files (`src/reprocli_repro/evidence.py:78-84`), but `sandbox.py:301-302` binds `evidence/` read-write, so the agent's shell could rewrite them, and the paper says so (`appendix/a_harness.tex:131-132`). The live transcript `agent.full.log` sits in the run directory above `evidence/`, which the sandbox does not bind (`live_log.py:71-75`, `sandbox.py:296-305`), so the agent cannot reach it. The auditor prompt does not tell the auditor to distrust the logs (`prompts/prompt_audit.txt:55-73`); the instruction to treat the bundle as unverified claims appears only in the paper (`appendix/a_harness.tex:133-134`). rqBN read the paper as saying the auditor was told this, so the reply admits the mismatch and the revision corrects the paper text.

### D. Tolerance and targets (T29u Q2; rqBN Q2)

| Concern | Type | What answers it |
| :- | :- | :- |
| Sensitivity of conclusions to the match target and the default 5% relative tolerance | NEW (analysis only) | E6: rescore every graded run at 1%, 2%, 5% and 10%, and for percentage metrics at 1 and 2 absolute points; rescore 30 papers against independently derived targets; count how many claims use the default |
| How claims, minimal configurations, target tuples and tolerances were validated, and annotator agreement | NEW | Stage III (`appendix/e_construction.tex:80-92`) audited the availability calls only and never validated targets, so the reply says so; E7: a second annotator independently re-derives 30 targets and we report agreement |

The default is defined at `appendix/f_dataset.tex:116-118` and `rubric_audit.md:50-58` at the repo root (the copy the code loads, `src/reprocli_vllm/config/config.py:33`): a standalone point estimate with no stated tolerance gets 5% relative. Memory `lockfile-is-audited-selection` notes the auditor restates the target tuple at grade time from the frozen claim, so E7 should compare the second annotator against the tuple the auditor actually used.

### E. Environment and attribution (YGTR W2, Q2, Q3; rqBN Q1)

| Concern | Type | What answers it |
| :- | :- | :- |
| How many failures come from hardware differences (GH200, aarch64) | SURFACE + NEW (analysis) | Surface: the paper already traces 5 of MiniMax-M2.7's 8 Run-tier build failures to missing aarch64 wheels (`iclr2027_conference.tex:539-540`) and the eval set was host-probed so no paper has an artifact wall. E8: an upper bound that removes every build-and-dependency failure and recomputes the rates |
| Did agents cheat by fetching checkpoints over the network instead of training | NEW (analysis) | E9: scan all transcripts for checkpoint downloads at Retrain and Reimplement, check each against the authors' released links and the run's grade |
| How many failures were not the agent's fault | SURFACE + NEW | E8 plus a plain count of cells that failed for reasons outside the agent (below) |
| Stratified human-expert reproduction baseline | TEXT + NEW (scoped) | Decline plainly; E10 is offered as an environment check that re-executes the faithful pipelines with two more seeds on Run and Retrain papers. Raff (2019) is left out of the reply because it reproduced papers by hand without our budgets and so measures a different setting |

Memory limits here. `reprobench-validity-defenses` (Threat 1) records that Mithil accepts a bounded version of the agent-versus-paper confound and has no resources for a human reproduction of the benchmark, so E10 is a scripted re-execution of commands the agents already found, run by us, and the reply says plainly that a full human baseline is out of scope. `baseline-harness-stays-thin` and the 2026-08-11 instruction "there is no block do not mention any blockages" mean the reply frames aarch64 issues as part of the environment every agent faced, and gives the bound while still counting those runs. `paper-missing-cells-accounting` keeps all 28 empty cells as model failures at score 0 in the paper and forbids a per-cell table. YGTR Q3 asks directly how many failures were not the agent's fault, and that memory records two causes that are clearly outside the agent: the 4 cells of 2510.20725, where a prompt-rendering bug fixed on 2026-09-10 stopped every agent before it started, and 2 Muse Spark cells whose audit never returned a verdict. **Decision for Mithil:** I recommend the YGTR reply names these 6 cells and that we rerun 2510.20725 for DeepSeek-V4-Flash and Muse Spark and re-audit the two Muse cells, while the 19 runs that ended without a final report stay counted as agent failures under the protocol. Omitting known harness-caused cells in an answer to a direct question would be the larger risk.

### F. Presentation (rqBN 2, YGTR 2)

Neither reviewer names a passage. Treat it as TEXT: the revision states each new measurement where the claim it supports is made, in plain sentences, and keeps every new term defined at first use.

## 2. New evidence: what we run, where, cost and what changes the reply

### Shared setup

**Stratified subset (12 papers, frozen before any run).** Four papers per tier, with band shares matching each tier (Run 27/7/0 papers in the 0-8/8-32/32-96 H100-hour bands, Retrain 16/13/4, Reimplement 16/9/8): Run takes 3 from 0-8 and 1 from 8-32; Retrain and Reimplement each take 2, 1 and 1. Within each tier, two papers that at least one agent reproduced and two that none did. Papers are drawn by a seeded random choice within each cell, listed in priority order in `rebuttal/subset.json`, and committed before the first run, so the first N papers of the list form a smaller stratified set if the budget shrinks. Granted GPU hours for the 12 papers are 344 H100-hours per agent (Run 3x8 + 32 = 56, Retrain 2x8 + 32 + 96 = 144, Reimplement 144), the band ceiling per paper as in the main runs.

**GPU account routing.** All rebuttal GPU work charges bgnp-dtai-gh (balance 1,304 of 6,367 hours on 2026-11-06), with betw-dtai-gh (6,168 hours, Mithil 2026-11-06: "you can also use betw btw") as overflow. bfvr-dtai-gh has only 168 hours left, so it cannot carry rebuttal work in any case. The change is one line plus tests: `src/reprocli_repro/cluster.py:73` becomes `account=os.environ.get("REPROCLI_SLURM_ACCOUNT", "bfvr-dtai-gh")`, with `tests/repro/test_cluster.py` and `test_slurm.py` gaining a case for the override. Brain and orchestrator jobs get `sbatch -A bgnp-dtai-gh` on the command line, which overrides the `#SBATCH -A betw-dtai-gh` header without editing the scripts. Run directories stay under `/work/nvme/bfvr/msalunkhe/reprocli/agent_runs` because the storage allocation is independent of the Slurm account. Check: `squeue -u $USER -o "%.10i %.14a %.14q %.10T"` shows bgnp-dtai-gh in both the account and QOS columns (memory `deltaai-slurm-account-qos`). The cluster checkout at `/u/msalunkhe/reprocli` named in that memory no longer exists, so day 1 locates or re-clones it and pulls this commit. Queued Distillation jobs on betw-dtai-gh are left alone.

**Unit check.** `accounts` reports hours; we treat one as one GH200 GPU-hour, which the harness bills as one H100-hour (`budget.py` multiplier 1.0). Day 1 confirms this from the charge of the first smoke job.

**OpenAI key.** No `OPENAI_API_KEY` is set on claude-vps or in DeltaAI's `~/.bashrc` (checked 2026-11-06). Mithil puts the key in DeltaAI's `~/.bashrc` and sets a hard project budget of $600 in the OpenAI dashboard before any run.

**Grading.** Every new run is graded by the pinned auditor (claude-sonnet-5, frozen rubric) on the Anthropic key, as before. The audit records keep no token counts (`paper-cost-accounting`), so grading cost is first run, no baseline; the smoke audits give the per-run figure.

### How the API cost was estimated

The only API-served agent in the paper, Muse Spark 1.2, used 1,494.6M prompt tokens and 33.53M completion tokens over its 99 started runs, at a cost of $724.91 (`appendix/b_models.tex`, tab:cost). Solving its price card (1.25 uncached, 0.15 cached, 4.25 completion, per million) against that total gives 325.7M uncached and 1,168.9M cached prompt tokens, a 78% cache share, which matches memory `agent-token-cost-cache-read-dominated` (80 to 95% in other runs). Per run that is 3.29M uncached, 11.81M cached and 0.339M completion tokens.

Worked example, gpt-5.6-sol at its OpenRouter list price on 2026-11-06 ($4.00 input, $0.40 cached, $20.00 output per million; openai.com returned 403 to the lookup, and the model is listed at `openrouter.ai/api/v1/models`): 3.29 x 4.00 = $13.16, plus 11.81 x 0.40 = $4.72, plus 0.339 x 20.00 = $6.78, for **$24.66 per run** ($24.65 from the unrounded token counts). For comparison gpt-5.6-terra is $13.00 and gpt-5.3-codex $12.56 per run on the same profile. Three risks push the real cost up: reasoning tokens at high effort bill as output, prompts above 272k tokens bill at $8.00 and $30.00, and Codex CLI's token profile is unmeasured. The harness caps agent input at 256k tokens for this model to stay under the long-context rate, and the smoke runs replace the estimate with a measured cost before the paired runs are sized.

### E1. Frontier model in two harnesses (OpenAI budget)

- **What.** gpt-5.6-sol, reasoning effort high, as the agent in (a) our thin harness, a config change since the harness already drives an API model, and (b) Codex CLI, run non-interactively inside the same Apptainer sandbox with the same task prompt, the same evidence directory and a `run_gpu` command on its PATH that calls our existing `tools/run_gpu.py`, so GPU access and budget metering are identical. Codex's own JSON event stream is written outside the sandbox and converted into `commands.log` and `trajectory.jsonl` for the unchanged auditor. Both arms run on the same first N papers of the subset, so each paper gives a paired comparison. Codex keeps its stock tools, system prompt and context handling; our only additions are the task text and the `run_gpu` command. We report how many runs in each arm hit the 256k input cap or Codex's own compaction.
- **Log conversion check.** The auditor was validated on thin-loop logs only, so before grading the Codex arm we grade the two smoke runs twice, once from Codex's raw event stream and once from the converted logs, and require the same verdict.
- **Fixed in advance (written into `subset.json` before launch).** The harness effect is the paired difference in reproduced papers, tested with an exact McNemar test and read against the flip rate E3 measures for one agent across reruns; a difference smaller than that flip rate is reported as no measured effect. Haochen and Samridhi label the failure mode of every failing E1 and E2 run with the paper's taxonomy, blind to the LLM labels, and "same failure modes" means the share of the top three modes falls inside the 95% interval of the open agents' shares.
- **Sizing rule.** After one smoke run per arm on a development paper, N = floor((600 - smoke spend - 50 reserve) / (measured cost per thin run + measured cost per Codex run)), capped at 12. At the $24.65 estimate for both arms, N = 10 papers and 20 runs. At 1.5 times the estimate, N = 6. A spend check runs after every finished run and stops launches when $550 is reached.
- **Where.** Agent loops run on a DeltaAI CPU-side orchestrator job, GPU steps on ghx4 through `run_gpu`, both charged to bgnp-dtai-gh.
- **GPU-hours.** Muse Spark used 21.8% of its grant, so expect about 0.218 x 344 = 75 GPU-hours per 12-paper arm, about 63 for 10 papers, so about 125 for both arms. Hard ceiling 344 per arm, 688 total.
- **Time.** Integration 1.5 days (the Codex wrapper is the only new piece; the aarch64 Codex binary is checked first), smoke half a day, runs up to 48 hours.
- **What changes the reply.** If gpt-5.6-sol in the thin harness lands inside the open models' range per tier and its runs fall into the same failure modes by the rule above, the reply says the taxonomy holds for a frontier model. If Codex beats the thin harness by more than the E3 flip rate, the reply reports a measured harness effect with the McNemar p-value and names which failure modes it removed. If both arms reproduce most of the subset, the headline becomes "frontier agents close much of the Run-tier gap and still fall at Reimplement" and the abstract changes in the revision.

### E2. Production harness on an open model (GPU only)

- **What.** DeepSeek-V4-Flash, served as in the main runs, driven by mini-SWE-agent 2.4.6 on all 12 subset papers, with its bash environment pointed at our sandbox and `run_gpu` on the PATH. The Distillation project already runs mini-SWE-agent on DeltaAI GH200 inside Apptainer (`~/Alingment/Distillation/lead/runs/qwen38-five/swe-mini/mini_apptainer.py`); we copy the pattern into this repo and change nothing there.
- **Why.** It is the one harness YGTR named that costs no API money, and we already have DeepSeek-V4-Flash's thin-harness result on the same papers, so the comparison holds the model fixed.
- **GPU-hours.** Agent steps about 0.262 x 344 = 90 (DeepSeek-V4-Flash used 26.2% of its grant). Serving is shared with E3 (below).
- **What changes the reply.** Same rule as E1: a paired difference larger than the E3 flip rate is reported as a harness effect; otherwise the reply says a standard community harness gives the same result as ours on this subset.

### E3. Run-to-run variance (GPU only)

- **What.** Two more DeepSeek-V4-Flash runs in the thin harness on all 12 subset papers, giving three runs per paper with the original.
- **Reported.** Per-paper verdict flip rate across the three runs with its 95% interval, the spread of the mean score, and whether the tier ordering of rates holds in every run. The flip rate then widens the intervals on the main results, and the revision ranks two agents only where the widened intervals do not overlap. This measures one agent's run-to-run spread; the reply says so and does not claim it for the other three.
- **GPU-hours.** Agent steps 2 x 90 = 180. Serving for E2 and E3 together: 36 agent runs at six concurrent agents per two-GPU brain is six brain jobs of 2 GPUs x 48 hours = 576 GPU-hours. This is the largest single cost in the plan and the first place to cut.
- **What changes the reply.** If at least 10 of 12 papers keep the same verdict in all three runs, the reply says single-run verdicts are stable at the paper level. If several papers flip, the reply reports the flip rate, widens the claimed uncertainty, and the paper adds the intervals to every agent comparison.

### E4. Human validation study, two graders per run (people, no GPU)

- **Sample.** 48 graded runs, 16 per tier, drawn by a fixed seed and stratified by the auditor's verdict: 14 reproduced, 8 partial, 12 not reproduced, 4 unverifiable and 10 disqualified, oversampling every run scored 7 or 8 and every run with a high-severity flag. The sample is fixed in `rebuttal/human_study/sample.json` before grading starts.
- **Protocol.** Haochen and Samridhi each grade all 48 from the run bundle in the viewer, with the frozen rubric, blind to the auditor's score and to each other, on a sheet that records the 0 to 10 score, the verdict and every flag. Mithil adjudicates disagreements after both finish, from a sheet that hides the auditor's verdict. The sample file is committed and pushed before grading starts, so its timestamp shows it was fixed in advance. A shared calibration on three development runs outside the sample comes first.
- **Reported.** A five-by-five confusion matrix of auditor verdict against the adjudicated human verdict; agreement before adjudication as well; precision, recall and F1 on reproduced, both on the sample and reweighted to the 372 graded runs by the inverse of each verdict stratum's sampling rate (the sample oversamples hard cases, so the raw figure overstates the difficulty); the same by tier; Cohen's kappa between the two humans; mean absolute score difference on the 0 to 10 scale; a two-by-two table at the 7/8 boundary; and agreement on high-severity flags.
- **Time.** Grading time per run is first run, no baseline. We time the first five runs; at 25 minutes each the study is 20 hours per grader over five days. If the first five average more than 30 minutes, the sample drops to 30 runs and keeps every boundary and flagged run.
- **What changes the reply.** If F1 on reproduced is at least 0.8 and the humans agree with each other at kappa 0.6 or above, the reply says the auditor matches humans about as well as humans match each other. If the auditor is lenient (humans reject several of its reproduced verdicts), we rescore the headline with the human labels on the sample, report the corrected rate with an interval, and say so in the general reply.

### E5. Log integrity (CPU analysis plus a harness change)

- **What.** For every one of the 396 started runs, parse `agent.full.log` (host-only) and check that every command and tool result in `commands.log` and `trajectory.jsonl` appears there unchanged, and that the agent's own shell commands never write to those two paths (search the transcripts for redirects, `write_file` calls or edits that target them).
- **Limit.** This catches only edits that `agent.full.log` records: an agent command that rewrote the logs shows up there, and the transcript itself is out of the agent's reach. The reply states the limit.
- **Harness change for all new runs.** The harness writes each step to a host directory outside the sandbox as it happens, chaining each entry to the hash of the previous one in `evidence.py`, and copies the logs into `evidence/` read-only for the auditor. The auditor prompt for new runs gains the cross-check instruction the paper described. Old grades are untouched.
- **Where.** Delta CPU partition through `delta cpu` (the run directories sit on `/work/nvme`, which Delta and DeltaAI share), charged to bgnp-delta-cpu (7,317 hours).
- **Time.** Half a day to write and check the script, under an hour to run.
- **What changes the reply.** If no run edited its logs, the reply gives the count, 0 of 396, and describes the fix. If any did, those runs are re-graded with the host transcript and the corrected numbers go in the reply.

### E6. Tolerance sensitivity (CPU analysis)

- **What.** For each graded run, take the measured value and target tuple from the audit record, recompute the match at 1%, 2%, 5% and 10% relative, and for percentage metrics at 1 and 2 absolute points; count how many of the 100 claims fall under the default. Then rescore the E7 papers against the targets the second annotator derived on their own, which tests the choice of target as T29u asked.
- **Limit.** Tightening can move a reproduced run to partial; loosening can move a partial run whose only shortfall was the number to reproduced. Runs that failed for other reasons do not move.
- **Where and time.** Delta CPU or claude-vps (about 400 rows), half a day including pulling audit rows from Supabase or the run directories.
- **What changes the reply.** If the best-agent rate per tier moves by at most a few papers at 2%, the reply says conclusions are insensitive to the default. If it collapses at 1%, the reply reports the table and argues 5% from the run-to-run spread E3 measures.

### E7. Target validation agreement (people)

- **What.** Samridhi re-derives the target tuple (metric, value, operator, tolerance) and minimal configuration for 30 eval papers, 10 per tier, from the paper alone and blind to the frozen value. We report exact agreement on the metric and configuration and the relative difference on the value.
- **Time.** About 15 minutes per paper, 7.5 hours, first run, no baseline.
- **What changes the reply.** Agreement of at least 26 of 30 lets the reply state an inter-annotator figure; lower agreement goes in as a measured limitation with the disagreeing papers named in the appendix.

### E8. Attribution bound and non-agent cells (CPU analysis)

- **What.** Recompute each agent's per-tier rate after removing every run labeled build and dependency failure (24 runs across all agents) from its denominator, and separately count the runs among them that cite a missing aarch64 wheel. Report the 6 cells that failed outside the agent (4 never started because of the fixed prompt bug, 2 audits that never returned) and, if Mithil agrees, rerun 2510.20725 for DeepSeek-V4-Flash and Muse Spark and re-audit the two Muse cells.
- **Data.** The per-run labels in `~/sweeps/paper-table-2026-09-05/resolved_modes.json` live only on the laptop. Mithil copies that folder to `/work/nvme/bfvr/msalunkhe/rebuttal/` on day 1.
- **Cost.** The rerun adds two runs on one paper: about 15 GPU-hours and a few dollars of Muse API time.
- **What changes the reply.** The reply gives the bound either way. If the best Run-tier rate rises above 50% under the bound, the general reply says the hardware matters for released-code papers and the Limitations paragraph says it.

### E9. Network checkpoint scan (CPU analysis)

- **What.** Search every transcript for checkpoint downloads (`hf_hub_download`, `snapshot_download`, `huggingface-cli download`, `from_pretrained` with a repo id, `torch.hub.load`, `timm` with `pretrained=True`, `gdown`, and `wget` or `curl` of `.pt`, `.pth`, `.ckpt`, `.safetensors` or `.bin`), and for fetched result files (results JSON or CSV, leaderboard pages) whose numbers could be copied. The harness keeps no host-side network log, so the transcript is the record and the reply says so. For Retrain and Reimplement runs, where the authors released no weights for the claimed model, compare each URL with the paper's verified release links and label it as the authors' artifact, a base model the method starts from, or a third-party checkpoint of the claimed model. Then check the run's grade.
- **Why it matters.** The auditor's flag list has no named flag for a substituted third-party checkpoint, and `prompts/prompt_audit.txt:107-113` allows a sibling checkpoint unless it changes method, size or metric. A scan settles whether this ever produced a reproduced verdict.
- **Where and time.** Delta CPU, half a day.
- **What changes the reply.** If no reproduced Retrain or Reimplement run rests on a third-party checkpoint of the claimed model, the reply says so with the count of runs scanned. If some do, we re-grade them, report the corrected rates, and add the flag for future versions.

### E10. Environment check: re-execution of faithful pipelines (GPU, scoped)

- **What.** For up to 6 Run-tier and 4 Retrain-tier papers (0-8 band) whose faithful pipeline landed outside tolerance (24 such runs at Run and 37 at Retrain), Haochen extracts the final command sequence from the best run's transcript and re-runs it with two new seeds on GH200, without an agent. This is an environment check and the reply calls it that; it is no substitute for a human-expert baseline.
- **GPU-hours.** Run: 6 x 2 x 2 = 24. Retrain retrains, so up to its 8-hour grant: 4 x 2 x 8 = 64. About 90 in all, ceiling 180.
- **What changes the reply.** If the authors' own pipeline also lands outside tolerance on two seeds, those misses belong to the environment or the paper, and the reply and Limitations say how many. If it lands inside, the original miss was seed variance or agent error, and we say which.

### Budget summary

| Item | OpenAI $ (expected / cap) | GPU-hours (expected / ceiling) | Machine |
| :- | :- | :- | :- |
| Smoke runs, 1 dev paper per arm | 50 / 75 | 30 / 60 | DeltaAI |
| E1 thin + Codex, N = 10 (20 runs x $24.65) | 493 / 500 (launches stop at $550 total) | 125 / 688 | DeltaAI |
| E2 mini-SWE-agent, 12 papers | 0 | 90 / 344 | DeltaAI |
| E3 two repeats, 12 papers | 0 | 180 / 688 | DeltaAI |
| E2 + E3 brain serving | 0 | 576 / 576 | DeltaAI |
| E8 rerun of 2510.20725 (Retrain, 0-8 band, 2 agents; Muse on the Meta key) | 0 | 15 / 16 | DeltaAI |
| E10 environment check | 0 | 90 / 180 | DeltaAI |
| E5, E6, E8, E9 analyses | 0 | CPU, under 50 core-hours | Delta CPU |
| **Total** | **about 543 of 600** | **about 1,106 / 2,552** | |

The expected GPU total of 1,106 fits in bgnp-dtai-gh's 1,304 hours; the ceiling would need betw-dtai-gh. Grading on the Anthropic key is extra and measured at smoke.

Claude Code as a harness is not in the plan: it bills to the Anthropic key, outside the OpenAI budget, and Codex CLI is the same kind of agent. If Mithil wants it, it reuses the Codex wrapper and runs on the same N papers.

## 3. Paper revisions (from the three reviews)

Load `m-paper` before any edit under `paper_latex/`. Main text may grow to 10 pages at rebuttal; it currently ends with the Conclusion on page 9, so the new main-text material is at most one page and the rest goes to the appendix. Every new number enters only after its result file is frozen in `rebuttal/results/`.

1. **Section 5.1 and Limitations ("Agents" paragraph).** Replace "The roster omits Claude, GPT, and Gemini because of cost" with one paragraph on the E1 and E2 arms and a pointer to a new appendix subsection with a table of arm by tier (reproduced, mean score, cost, GPU-hours) and their failure-mode counts beside the main agents'.
2. **Section 5.2.** Add the 95% Wilson intervals to the main rates and the E3 agreement figure in one sentence.
3. **Section 4 and Appendix D.** Report E4: the confusion matrix, agreement before adjudication, precision, recall, F1 on the sample and reweighted, per-tier F1, inter-human kappa, boundary table and flag agreement. On Mithil's decision (Section 1C and the decisions below), the "three graders scored all 396 runs" sentences and the 0.82 are replaced by the new study.
4. **Appendix A (run bundle) and the auditor prompt figure.** Correct `appendix/a_harness.tex:133-134` so it no longer implies the auditor prompt told the auditor to distrust the logs, report E5 with its limit, and describe the hash-chained host logs used for the new runs.
5. **Appendix C or F.** E6 tolerance table and the count of claims under the default.
6. **Appendix E (Stage III).** E7 agreement.
7. **Section 5.3 and Limitations ("Attributing a miss").** E8 bound, the aarch64 count, E9 result and E10 re-execution result, each stated where the claim is made.
8. **Section 5.1, harness paragraph.** One sentence that the thin loop is the fixed baseline and the appendix measures two production harnesses against it.

Compile, then read every rendered page for split floats, early page ends and uneven spacing before upload. Upload the revised PDF only if the OpenReview revision button is open for this venue.

## 4. Schedule, 2026-11-07 to 2026-11-14

Owners: **M** Mithil, **H** Haochen, **S** Samridhi. "Agents" means Claude workers launched by Mithil's session; Mithil checks each result.

| Day | M | H | S |
| :- | :- | :- | :- |
| Sat 11-07 | Ask H and S for old grading sheets. OpenAI key on DeltaAI and $600 project cap. Locate DeltaAI checkout, land the account override, confirm the unit on a tiny job. Copy `~/sweeps/paper-table-2026-09-05/` to `/work/nvme/bfvr/msalunkhe/rebuttal/`. Agents freeze `subset.json` and `human_study/sample.json`, check the Codex aarch64 binary, start E5, E6, E9 scripts | Read the rubric; calibration on 3 dev runs with S | Same calibration |
| Sun 11-08 | Agents build the thin-harness gpt-5.6-sol config, the Codex wrapper and the mini-SWE-agent wrapper; smoke run per arm on a dev paper; size N from measured cost. Review E5, E6, E9 outputs | Grade 12 sample runs | Grade 12 sample runs |
| Mon 11-09 | Launch E1 (N papers, both arms), E2 and E3 brain jobs, E8 rerun. Start drafting T29u and rqBN replies | Grade 12; extract commands for E10 | Grade 12 |
| Tue 11-10 | Monitor runs and spend; audit finished runs with the pinned auditor | Grade 12 (done, 48); run E10 | Grade 12 (done, 48); start E7 |
| Wed 11-11 | Adjudicate E4 disagreements; build confusion matrix. **Post wave 1: T29u and rqBN replies** with E4, E5, E6, E7 and intervals, saying frontier results follow | Check E10 results | Finish E7 (30 papers) |
| Thu 11-12 | Runs finish (48-hour limit); audit remaining; E8 bound; McNemar test and flip-rate comparison. Start paper revisions under `m-paper` | Label failure modes of failing E1/E2 runs, blind to LLM labels | Same labeling, independently |
| Fri 11-13 | Tables and appendix for E1 to E3; compile; page read. Draft YGTR and general replies | Review YGTR reply against the numbers | Review general reply |
| Sat 11-14 | **Post wave 2: YGTR reply, general reply, revised PDF.** Reply to any wave-1 follow-ups | | |

Posting in two waves gives T29u and rqBN three days to respond before the deadline, which matters more than holding every answer for one post.

**Cut list if we fall behind** (cut from the top):

1. E8 rerun of 2510.20725 and the two re-audits (state the 6 cells in the reply anyway).
2. The second E3 repeat (keep one, giving two runs per paper), which saves about 290 GPU-hours.
3. E10 down to the 6 Run-tier papers.
4. E7 down to 15 papers.
5. E4 down to 30 runs, keeping every 7/8 boundary and flagged run.
6. E2 mini-SWE-agent arm, if the Codex arm has run.

Never cut: E1 (both arms, at least 6 papers), E4 confusion matrix, E5 log check, E9 checkpoint scan. YGTR's score depends on E1, and the other three are the direct answers to soundness questions.

## 5. Reply outlines

Each reply opens by thanking the reviewer in one sentence and naming what changed, answers concerns in the reviewer's order, and gives a number with its denominator wherever one exists. Square brackets mark values that the runs fill in.

### General reply (posted wave 2)

1. We thank the reviewers; all three found the task design sound, and the main requests were a frontier agent, a production harness, repeated runs and a fuller validation of the auditor.
2. Key sentence: "We ran gpt-5.6-sol as the agent in our harness and in Codex CLI on the same [N] stratified papers, DeepSeek-V4-Flash in mini-SWE-agent on 12 papers, and two repeat runs of DeepSeek-V4-Flash on the same 12; the frontier agent reproduced [a/N] in our harness and [b/N] in Codex, and its failures fall into the same modes as the open agents [or: Codex removes mode X in k runs]."
3. "The per-run labels of our original human study were not retained, so we withdraw its F1 of 0.82. Two co-authors graded a new sample of 48 runs, fixed before grading, blind to the auditor and to each other; the auditor matches their adjudicated verdicts at F1 [x] on reproduced ([x'] reweighted to all graded runs), the two graders agree at kappa [y], and Appendix D gives the full confusion matrix."
4. "No agent edited its harness logs in any of the 396 runs that started, checked against a host-side transcript the agent cannot reach; new runs write a hash-chained log on the host."
5. List of revisions by section.

### Reviewer T29u

- **Single run per cell.** "We added 95% intervals to every rate (best agent at Run: 14/34, [26%, 58%]) and ran DeepSeek-V4-Flash twice more on 12 stratified papers; its verdict flipped on [k] of 12 papers ([interval]), we widened the agent comparisons by that rate, and we now rank two agents only where the widened intervals do not overlap. This measures one agent's spread, and we say so in the paper."
- **Auditor disagreements, 7/8 boundary, high-severity flags (Q1).** Opens with the withdrawal sentence from the general reply, then: "the new study oversamples every run scored 7 or 8 and every high-severity flag; Appendix D gives the confusion matrix [counts]; at the 7/8 boundary the auditor and the humans agree on [m] of [n] runs, and on high-severity flags on [p] of [q]."
- **Tolerance and match target (Q2).** "[c] of the 100 claims use the default 5% relative tolerance. At 2% the best-agent rate changes by [d] papers at Run, [e] at Retrain and [f] at Reimplement, and at 10% by [g, h, i] (new table in Appendix F). Rescoring 30 papers against targets a second annotator derived on their own changes [j] verdicts."

### Reviewer rqBN

- **Single human label, missing metrics.** The withdrawal and new-study sentences, plus "agreement before adjudication [a]; precision [x], recall [y]; per-tier F1 [r/t/i]; inter-human kappa [k]; mean absolute difference on the 0 to 10 scale [d]. The adjudicator saw neither the auditor's verdict nor its score."
- **Writable logs.** "You are right, and our paper overstated the safeguard: the auditor prompt never told the auditor to distrust these logs, and we correct that sentence. The harness writes both files, but the agent could rewrite them. We compared both with the host-side transcript, which lies outside the sandbox, for all 396 runs and found [0] edits; this check catches any edit the agent made through its own commands. New runs write a hash-chained log on the host."
- **Human-expert reproduction baseline (Q1).** "A human reproduction across all three tiers is beyond our resources, and we say so in Limitations. As an environment check we re-ran the faithful agents' own pipelines with two new seeds on [n] Run and Retrain papers whose faithful run missed; [k] also miss on our hardware, which bounds how much of the gap belongs to the environment."
- **Validation of claims and targets (Q2).** "Stage III audited the availability calls only, and the targets had no second annotator before now. A second annotator re-derived the target for 30 papers blind to the frozen value and agreed on metric and configuration for [a/30], with the value within [v]% on [b/30]."

### Reviewer YGTR

- **Frontier models and harness (W1, Q1).** "We ran gpt-5.6-sol as the agent in our harness and in Codex CLI on the same [N] stratified papers and DeepSeek-V4-Flash in mini-SWE-agent on 12. [Result sentence from E1/E2.] The most common failure in the paper, writing the method without checking it against the paper's numbers, occurs in [k] of the frontier agent's [m] failing runs." The thin loop stays the main baseline because it treats all models alike, and the new appendix measures what a production harness adds.
- **Hardware confound (W2).** "We cannot fully separate the hardware from agent error, and we bound it three ways. Missing aarch64 wheels explain [k] of the 24 build-and-dependency failures; removing all 24 from the denominators moves the best Run-tier rate from 41% to at most [x]%; and when we re-ran the faithful agents' own pipelines with two new seeds, [k2] of [n] still missed on our hardware."
- **Single run (W2).** E3 sentence.
- **Checkpoint fetching (Q2).** "We scanned all [396] transcripts for checkpoint downloads; [n] Retrain or Reimplement runs downloaded a checkpoint, [k] of them a third-party checkpoint of the claimed model, and [none] of those were graded reproduced. The auditor also traces every reported number to the execution that produced it and caps flagged runs at zero."
- **Failures not the agent's fault (Q3).** "Six of the 400 cells failed for reasons outside the agent: four never started because of a prompt-rendering bug in our harness, since fixed, and two audits returned no verdict. [We reran and re-audited them: result.] Beyond these, the bound above covers environment failures, and the re-execution of faithful pipelines shows [k] misses that the authors' own pipeline also produces on our hardware."
- **Closing.** One sentence asking whether the frontier and harness results address the generalization concern behind the Informativeness score.

## Decisions for Mithil before 2026-11-07 noon

1. **Withdraw the 0.82 F1** in the replies and the revision and replace it with the new two-grader study (Sections 0 and 1C). Recommended. This reverses the 2026-09-10 instruction recorded in memory `human-grader-study-lost`, whose revisit trigger ("a reviewer asks for n, grader count, or the labels") has now fired twice.
2. Approve gpt-5.6-sol as the frontier model. The alternative, gpt-5.6-terra at about half the cost ($13.00 per run), buys about twice the papers and a stronger paired test, at the price of not being OpenAI's top model; YGTR's read favors more papers, and I still recommend sol because "no frontier model" is the literal objection.
3. Approve naming the 6 non-agent cells in the YGTR reply (Section 1E).
