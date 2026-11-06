# Rebuttal plan: ICLR 2027 submission 22528 (RECLAIM)

GOAL: move YGTR from 2 (weak reject) to at least 3, and move T29u and rqBN from 3 to 4, with replies posted on OpenReview by 2026-11-14.
DONE-WHEN: four replies (general, T29u, rqBN, YGTR) are posted, every number in them traces to a file under `rebuttal/results/`, and the revised PDF compiles with the main text inside 10 pages.
MUST-NOT-CHANGE: the frozen eval-100 split, the frozen rubric and pinned auditor (claude-sonnet-5) for every grade of record, the four-agent roster of the main results, the run directories under `/work/nvme/bfvr/`, and the paused Distillation files and jobs.

Scope: the three official reviews only; the PAT feedback is set aside (Mithil, 2026-11-06). Revision 2 (2026-11-06, his answers to v1): GPU work runs on betw-dtai-gh; OpenAI budget $750 and Meta budget $500; Haochen and Samridhi take no tasks, so agents do their work and Mithil checks it; the frontier arms use the GPT-6 series and Muse Wonder (v1 named gpt-5.6-sol because the price lookup matched only names starting with gpt-5 and missed GPT-6); the 6 cells that failed outside the agent are rerun; the human-grader item is parked because the original labels exist. Revision 3 (same day): the OpenAI arms run on OpenAI's flex tier, its low-priority service at half the standard price, which grows the OpenAI subset from 12 to 24 papers.

## 0. Where we stand and how a score moves

The three reviewers agree that the task design is sound and carefully disclosed. Their objections fall into four groups: the agents are weak and the harness is thin (YGTR), one run per cell gives point estimates (T29u, YGTR), the auditor's validation is a single F1 and the agent can edit the logs the auditor reads (T29u, rqBN), and some failures may come from the environment (YGTR, rqBN). YGTR's rating rests on the first group, and its Informativeness score of 1 says the reviewer does not believe our failure modes describe the agents people actually use.

Recommendation: run current frontier models from two labs in production harnesses on the same stratified papers. OpenAI's GPT-6 series supplies gpt-6.1-sol and gpt-6.1-terra in both our harness and Codex CLI on 24 papers, plus the flagship gpt-6-astra in Codex CLI on 8, all on the half-price flex tier. Meta's Muse Wonder runs in our harness and in mini-SWE-agent, and since Muse Spark 1.2 is already in the paper, it also gives a same-family comparison on the same papers. Whichever way the results fall they answer YGTR: if frontier agents still fail in the same ways, the taxonomy generalizes; if a production harness lifts the rate, the paper gains a measured harness effect that no other reproduction benchmark reports. T29u and rqBN mostly want the auditor and the logs measured, which existing data and short analyses answer. What would change this: if the first runs show any model costing more than 1.5 times its estimate, or flex refuses so often that runs fall back to standard prices, gpt-6-astra drops to 4 papers before anything else shrinks.

**Simulated reception of v1 (2026-11-06).** Three agents read v1 as the reviewers would. YGTR would move from 2 to 3 (Informativeness 1 to 2) if the frontier and harness arms come with a paired test and a human check of the failure-mode labels, and stays below 4 while the headline numbers come from the four weaker models; v2's wider frontier set raises the chance of 3. T29u would move to 4 if the 7/8 boundary table and the repeat runs come back clean. rqBN would move to 4 given a full confusion matrix, inter-human agreement and a real tamper check on the logs. Their requested fixes are folded in below.

## 1. Every reviewer concern, grouped

Legend: **NEW** needs new evidence (Section 2), **SURFACE** existing evidence we only need to state, **TEXT** a wording fix.

### A. Agent strength and harness (YGTR W1, Q1)

| Concern | Type | What answers it |
| :- | :- | :- |
| No frontier model; tested models are weak, so findings may not generalize | NEW | E1 (gpt-6.1-sol, gpt-6.1-terra, gpt-6-astra) and E2 (Muse Wonder) on a stratified subset |
| The ReAct harness is too minimal; a researcher would use Claude Code, Codex or mini-SWE-agent | NEW | E1 Codex CLI arms paired with our harness on the same papers; E2 mini-SWE-agent arm |
| Why a thin harness at all | TEXT | Section 5.1 already argues fairness across models; add that the thin loop is the fixed baseline and the appendix measures two production harnesses against it |

Memory limits: `baseline-harness-stays-thin` holds, because the production harnesses are comparison arms and the main results keep the thin loop. `paper-model-roster` keeps the main results at four agents; the frontier arms go in a new appendix subsection plus one main-text paragraph, and Laguna and GLM-5.2 stay out. The roster decision lists "the strongest closed agent is added" as its own revisit trigger.

### B. One run per cell (T29u W1, YGTR W2)

| Concern | Type | What answers it |
| :- | :- | :- |
| Rates are point estimates; stochasticity could change rankings and tier gaps | NEW + SURFACE | E3: two more DeepSeek-V4-Flash runs on the 12-paper subset; 95% Wilson intervals on the main rates now |
| Failures may be transient | NEW | E3 per-paper flip rate across three runs |

The intervals for the best agent per tier are 14/34 = 41% [26%, 58%] at Run, 9/33 = 27% [15%, 44%] at Retrain and 5/33 = 15% [7%, 31%] at Reimplement, and 73/400 = 18% [15%, 22%] overall (Wilson score interval at 95%). The paper already prints the DeepSeek-V4-Flash two-proportion z (Run versus Reimplement 2.7, Run versus Retrain 1.2).

### C. Auditor validity (T29u W2, Q1; rqBN W1)

| Concern | Type | What answers it |
| :- | :- | :- |
| Confusion matrix between auditor and humans, the 7/8 boundary, high-severity flags, precision, recall, per-tier errors, full 0 to 10 scale | SURFACE (parked) | E4: computed from the original per-run human labels, which Mithil confirmed exist (2026-11-06); parked until he supplies the file |
| Multi-human adjudication | TEXT | Answer from the original protocol once the labels are in hand |
| commands.log and trajectory.jsonl are writable by the agent; no tamper-evident log | NEW + TEXT | E5: compare every run's logs with the host-side transcript the agent cannot reach; hash-chained host logs for all new runs |

How the code handles the logs today (checked 2026-11-06): the harness process writes both files (`src/reprocli_repro/evidence.py:78-84`), but `sandbox.py:301-302` binds `evidence/` read-write, so the agent's shell could rewrite them, and the paper says so (`appendix/a_harness.tex:131-132`). The live transcript `agent.full.log` sits in the run directory above `evidence/`, which the sandbox does not bind (`live_log.py:71-75`, `sandbox.py:296-305`), so the agent cannot reach it. The auditor prompt never tells the auditor to distrust the logs (`prompts/prompt_audit.txt:55-73`); the instruction to treat the bundle as unverified claims appears only in the paper (`appendix/a_harness.tex:133-134`). rqBN read the paper as saying the auditor was told this, so the reply admits the mismatch and the revision corrects the sentence.

### D. Tolerance and targets (T29u Q2; rqBN Q2)

| Concern | Type | What answers it |
| :- | :- | :- |
| Sensitivity of conclusions to the match target and the default 5% relative tolerance | NEW (analysis) | E6: rescore at 1%, 2%, 5% and 10% relative and at 1 and 2 absolute points; rescore 30 papers against independently derived targets; count claims under the default |
| How claims, configurations, target tuples and tolerances were validated, and annotator agreement | NEW | Stage III (`appendix/e_construction.tex:80-92`) audited availability calls only and never validated targets, so the reply says so; E7 has a model from another lab re-derive all 100 targets blind and Mithil settles every disagreement |

The default is defined at `appendix/f_dataset.tex:116-118` and `rubric_audit.md:50-58` at the repo root (the copy the code loads, `src/reprocli_vllm/config/config.py:33`). Memory `lockfile-is-audited-selection` notes the auditor restates the target tuple at grade time, so E7 compares the re-derived tuple with the tuple the auditor actually used.

### E. Environment and attribution (YGTR W2, Q2, Q3; rqBN Q1)

| Concern | Type | What answers it |
| :- | :- | :- |
| How many failures come from hardware differences (GH200, aarch64) | SURFACE + NEW | Surface: 5 of MiniMax-M2.7's 8 Run-tier build failures trace to missing aarch64 wheels (`iclr2027_conference.tex:539-540`), and the eval set was host-probed. E8: upper bound removing every build-and-dependency failure |
| Did agents fetch checkpoints over the network instead of training | NEW | E9: transcript scan for downloads at Retrain and Reimplement |
| How many failures were not the agent's fault | NEW | E8: name and rerun the 6 cells that failed outside the agent (approved 2026-11-06) |
| Stratified human-expert reproduction baseline | TEXT + NEW (scoped) | Decline plainly; E10 re-executes faithful pipelines with two new seeds as an environment check. Raff (2019) stays out because it measures a different setting |

Memory limits: `reprobench-validity-defenses` (Threat 1) records that Mithil accepts a bounded version of the agent-versus-paper confound with no human reproduction, so E10 is scripted re-execution and the reply says a full human baseline is out of scope. `baseline-harness-stays-thin` and the 2026-08-11 instruction "there is no block do not mention any blockages" mean the reply treats aarch64 issues as part of the environment every agent faced and gives the bound while still counting those runs. `paper-missing-cells-accounting` keeps the 28 empty cells at score 0 with no per-cell table in the paper; the rerun answers YGTR Q3 directly, and the 19 runs that ended without a final report stay counted as agent failures under the protocol.

### F. Presentation (rqBN 2, YGTR 2)

Neither reviewer names a passage. The revision states each new measurement where the claim it supports is made, in plain sentences, with every new term defined at first use.

## 2. New evidence: what we run, where, cost and what changes the reply

### Shared setup

**Stratified subset (24 papers in priority order, frozen before any run; the first 12 are the core set every arm runs).** Four papers per tier with band shares matching each tier (Run 27/7/0 papers in the 0-8/8-32/32-96 H100-hour bands, Retrain 16/13/4, Reimplement 16/9/8): Run takes 3 from 0-8 and 1 from 8-32; Retrain and Reimplement each take 2, 1 and 1. Within each tier, two papers at least one agent reproduced and two none did. Drawn by a seeded random choice per cell and listed in priority order in `rebuttal/subset.json`, committed before the first run, so the first k papers always form a smaller stratified set. Papers 13 to 24 repeat the same per-tier recipe on the next draws, so the full list is two stratified sets of 12. Granted GPU hours are 344 per agent for the core 12 (Run 3x8 + 32 = 56, Retrain 2x8 + 32 + 96 = 144, Reimplement 144) and about 688 for all 24, the band ceiling per paper as in the main runs.

**GPU account: betw-dtai-gh** (Mithil, 2026-11-06: "run it on BETW"; balance 6,168 of 40,000 hours that day). The brain and orchestrator `.sbatch` headers already carry `#SBATCH -A betw-dtai-gh`, so they need no change. The agent's `run_gpu` holds charge the account in `src/reprocli_repro/cluster.py:73`, which is `bfvr-dtai-gh` (168 hours left). The change is one line plus tests: `account=os.environ.get("REPROCLI_SLURM_ACCOUNT", "bfvr-dtai-gh")`, with a case for the override in `tests/repro/test_cluster.py` and `test_slurm.py`, and the rebuttal launch scripts export `REPROCLI_SLURM_ACCOUNT=betw-dtai-gh`. Run directories stay under `/work/nvme/bfvr/msalunkhe/reprocli/agent_runs`, because the storage allocation is independent of the Slurm account. Check: `squeue -u $USER -o "%.10i %.14a %.14q %.10T"` shows betw-dtai-gh in both the account and QOS columns (memory `deltaai-slurm-account-qos`). The cluster checkout `/u/msalunkhe/reprocli` named in that memory no longer exists, so day 1 locates or re-clones it and pulls. Nine queued Distillation jobs also charge betw-dtai-gh; they are left alone, and the plan's ceiling (below) leaves room for them.

**API keys.** Runs execute on DeltaAI, so the keys go there, in `~/.bashrc` beside `META_MODEL_KEY`, where the Muse Spark sweep already finds its key (`scripts/reproduce/muse_spark/muse_spark_sweep.sh:47-62`):

```bash
ssh delta
nano ~/.bashrc          # add one line:  export OPENAI_API_KEY=sk-proj-...
```

Use a project key from platform.openai.com (API keys, under a new project "reclaim-rebuttal"), and set that project's budget to $750 under Settings, Limits. The rebuttal launch script reads the key with `source <(rg OPENAI_API_KEY ~/.bashrc)`, exports it as `OPENAI_API_KEY` for Codex CLI and as `REPROCLI_API_KEY` for our harness, and forces it over any inherited `REPROCLI_API_KEY`, because DeltaAI login shells export an OpenRouter key under that name (memory `meta-model-api-reprocli-wiring`). The existing `META_MODEL_KEY` serves Muse Wonder; set a $500 limit in the Meta developer console if it offers one. No key is needed on claude-vps.

**Grading.** Every new run is graded by the pinned auditor (claude-sonnet-5, frozen rubric) on the Anthropic key. The audit records keep no token counts (`paper-cost-accounting`), so grading cost is first run, no baseline; the smoke audits give the per-run figure.

### How the API cost was estimated

Muse Spark 1.2, the paper's one API-served agent, used 1,494.6M prompt tokens and 33.53M completion tokens over its 99 started runs, at $724.91 (`appendix/b_models.tex`, tab:cost). Solving its price card (1.25 uncached, 0.15 cached, 4.25 completion, per million) against that total gives 325.7M uncached and 1,168.9M cached prompt tokens, a 78% cache share, in line with memory `agent-token-cost-cache-read-dominated` (80 to 95% in other runs). Per run: 3.29M uncached, 11.81M cached, 0.339M completion tokens.

Worked example, gpt-6.1-sol on the flex tier, which OpenAI's pricing page (developers.openai.com/api/docs/pricing, read 2026-11-06) lists at $1.00 input, $0.05 cached and $5.00 output per million for prompts up to 272k tokens: 3.29 x 1.00 = $3.29, plus 11.81 x 0.05 = $0.59, plus 0.339 x 5.00 = $1.69, for **$5.58 per run**, half the $11.15 standard price. The same profile at the other prices:

| Model | Released | Flex $/M (input / cached / output) | Flex per run | Standard per run | Source |
| :- | :- | :- | :- | :- | :- |
| gpt-6-astra (OpenAI flagship) | 2026-09-04 | 5.00 / 0.50 / 25.00 | $30.82 | $61.64 | developers.openai.com/api/docs/pricing |
| gpt-6.1-sol | 2026-09-29 | 1.00 / 0.05 / 5.00 | $5.58 | $11.15 | same |
| gpt-6.1-terra | 2026-10-26 | 0.50 / 0.025 / 2.50 | $2.79 | $5.57 | same |
| muse-wonder-1.0 | not stated | no flex tier listed | | $22.29 (4.00 / 0.20 / 20.00) | dev.meta.ai/models/muse-wonder |

Release dates are from openrouter.ai/api/v1/models.

Risks that push cost up: reasoning tokens bill as output; flex prices hold only up to 272k input tokens, so OpenAI arms cap agent input at 256k; a flex request that falls back to standard costs double; and Codex CLI's and mini-SWE-agent's token use is unmeasured. Smoke runs replace each estimate with a measured cost before the arms are sized. Muse Wonder keeps the window Meta documents (1M tokens), matching how Muse Spark ran, so the two Muse models compare directly.

### E1. OpenAI frontier models in two harnesses, flex tier ($750 OpenAI budget)

- **What.** Each model at reasoning effort high. (a) Our thin harness, a config change since it already drives API models. (b) Codex CLI, run non-interactively inside the same Apptainer sandbox with the same task text, the same evidence directory and a `run_gpu` command on its PATH that calls our `tools/run_gpu.py`, so GPU access and budget metering are identical. Codex keeps its stock tools, system prompt and context handling. Its JSON event stream is written outside the sandbox and converted into `commands.log` and `trajectory.jsonl` for the unchanged auditor.
- **Flex tier.** Every OpenAI request sends `service_tier: "flex"`, which OpenAI bills at Batch API rates, half of standard. Our harness gets it from a new `REPROCLI_SERVICE_TIER` variable that `client.py` adds to the body beside `reasoning_effort` (same pattern as `apply_reasoning_effort`, `src/reprocli_vllm/vllm/client.py:54-63`), with the client timeout raised to 15 minutes as OpenAI's flex guide advises. OpenAI says flex brings slower responses and occasional `429 Resource Unavailable` errors, which are not charged; the client retries those with exponential backoff for up to 10 minutes and then sends that one request at standard, logging each fallback so the bill can be reconciled. Codex CLI's config has a `service_tier` key (learn.chatgpt.com config reference) whose documented values are `fast` or another tier the model advertises; flex is not named, so the Codex smoke run checks the `service_tier` field in the API response, and if Codex cannot send flex, the Codex arms run at standard and shrink to fit (sizing rule below).
- **Latency cost to the agent.** The harness charges the agent's GPU grant for the whole time an allocation is held, model thinking included (`tools/run_gpu.py:378`), so slower flex replies spend more of the grant while a GPU is held. Agents used 10 to 26% of their grants in the main runs, so the grant rarely binds, but the smoke runs measure mean seconds per model call on flex against a few standard calls, and the appendix reports both.
- **Arms.** gpt-6.1-sol, thin and Codex, all 24 papers (48 runs, $268). gpt-6.1-terra, thin and Codex, all 24 papers (48 runs, $134). gpt-6-astra in Codex on the first 8 papers, at least two per tier (8 runs, $247), as the strongest model in the configuration a researcher would actually use. Smoke: the wiring is the same for every OpenAI model, so smoke runs use gpt-6.1-terra once per harness on a development paper (2 runs, $6). Expected total $655, leaving $95 for standard-price fallbacks and overruns.
- **Sizing rule.** The core 12 papers launch first for every arm, papers 13 to 24 next, gpt-6-astra last. If measured cost projects the total above $700, gpt-6-astra drops to 4 papers, then papers 13 to 24 are dropped from gpt-6.1-terra's Codex arm. A spend check runs after each finished run and stops launches at $700.
- **Log conversion check.** The auditor was validated on thin-loop logs, so the Codex smoke runs are graded twice, once from the raw event stream and once from the converted logs, and must get the same verdict.
- **Fixed in advance (written into `subset.json` before launch).** The harness effect is the paired difference in reproduced papers per model, tested with an exact McNemar test and read against the flip rate E3 measures; a difference below that flip rate is reported as no measured effect. Every failing frontier run gets its failure mode from the same labeling pass that produced the paper's labels, so the comparison with the open agents is like for like, and Mithil labels a random 20 of those runs himself, blind to the pass's labels, to report how often he agrees with it. "Same failure modes" means the share of the paper's top three modes falls inside the 95% interval of the open agents' shares. We report how many runs per arm hit the input cap or Codex's own compaction.
- **GPU-hours.** Muse Spark used 21.8% of its grant, so expect 0.218 x 688 = 150 per 24-paper arm: four such arms 600, plus astra about 50, about 650 in all, more if flex latency lengthens GPU holds. Ceiling about 3,010.
- **Time.** Codex wrapper, thin-harness configs and the flex field 1.5 days, smoke half a day, runs up to 48 hours plus flex delays. Any run still going at 2026-11-12 18:00 CT is stopped, graded on what it produced, and reported as stopped.
- **What changes the reply.** If the frontier models land inside or near the open models' range per tier and fail in the same modes by the rule above, the reply says the taxonomy holds for current frontier agents. If Codex beats our harness by more than the flip rate, the reply reports the harness effect with its p-value and which modes it removed. If gpt-6-astra in Codex reproduces most of its papers, the abstract changes to say frontier agents close much of the gap, and the reply leads with that.

### E2. Muse Wonder in two harnesses ($500 Meta budget)

- **What.** `muse-wonder-1.0` on the Meta Model API in our thin harness on all 12 papers (12 runs, $267) and in mini-SWE-agent 2.4.6 on the first 6 papers (6 runs, $134), its bash environment pointed at our sandbox, `run_gpu` on the PATH, and its litellm client aimed at Meta's OpenAI-compatible endpoint. The Distillation project already runs mini-SWE-agent on DeltaAI GH200 in Apptainer (`~/Alingment/Distillation/lead/runs/qwen38-five/swe-mini/mini_apptainer.py`); we copy the pattern into this repo and change nothing there. Smoke: one development paper per harness ($45). Expected total $446 plus $7 for the Muse Spark cell of E8, leaving about $47.
- **Wiring pitfalls** (memory `meta-model-api-reprocli-wiring`): force `META_MODEL_KEY` over the inherited `REPROCLI_API_KEY`; pass reasoning effort through `REPROCLI_REASONING_EFFORT`, since the hosted API ignores chat-template kwargs; set `REPROCLI_CONTEXT_LENGTH` only to the 1M window Meta documents for this model.
- **Why.** A second lab's newest model, a third harness, and a same-family comparison: Muse Spark 1.2's existing results on the same 12 papers against Muse Wonder's.
- **GPU-hours.** About 0.218 x 344 = 75 for the thin arm and about 38 for mini-SWE-agent, about 113. Ceiling about 550.
- **What changes the reply.** Same rules as E1, plus one sentence on Muse Spark versus Muse Wonder.

### E3. Run-to-run variance (GPU only)

- **What.** Two more DeepSeek-V4-Flash runs in the thin harness on all 12 papers, giving three per paper with the original.
- **Reported.** Per-paper verdict flip rate with its 95% interval, the spread of the mean score, and whether the tier ordering holds in every run. The flip rate widens the main-result comparisons, and the revision ranks two agents only where the widened intervals do not overlap. It measures one agent's spread, and the reply says so.
- **GPU-hours.** Agent steps 2 x 0.262 x 344 = 180 (DeepSeek-V4-Flash used 26.2% of its grant). Serving: 24 runs at six concurrent agents per two-GPU brain is four brain jobs of 2 GPUs x 48 hours = 384. Ceiling 688 + 384.
- **What changes the reply.** At least 10 of 12 papers with the same verdict in all three runs supports "single-run verdicts are stable at the paper level"; more flips get reported with the widened uncertainty.

### E4. Auditor against human labels (parked)

Mithil confirmed on 2026-11-06 that the per-run human labels behind the F1 of 0.82 exist, and parked this item. When he supplies the file, an agent computes in under an hour: the five-by-five confusion matrix of auditor verdict against human verdict, precision, recall and F1 on reproduced, the same by tier, mean absolute difference on the 0 to 10 scale, a two-by-two table at the 7/8 boundary, and agreement on high-severity flags. Without it the T29u Q1 and rqBN W1 answers have no numbers, so the file is needed by 2026-11-10 for wave 1.

### E5. Log integrity (CPU analysis plus a harness change)

- **What.** For every one of the 396 started runs, parse `agent.full.log` (host-only) and check that every command and tool result in `commands.log` and `trajectory.jsonl` appears there unchanged, and that no agent command wrote to those two paths (redirects, `write_file` calls or edits targeting them).
- **Limit.** This catches edits the agent made through its own commands, which `agent.full.log` records; the reply states the limit.
- **Harness change for all new runs.** The harness writes each step to a host directory outside the sandbox as it happens, chaining each entry to the hash of the previous one in `evidence.py`, and copies the logs into `evidence/` read-only for the auditor. The auditor prompt for new runs gains the cross-check instruction the paper described. Old grades are untouched.
- **Where and time.** Delta CPU through `delta cpu` (`/work/nvme` is shared between Delta and DeltaAI), charged to bgnp-delta-cpu (7,317 hours). Half a day to write and check, under an hour to run.
- **What changes the reply.** No edits gives the count, 0 of 396, plus the fix. Any edit means re-grading those runs from the host transcript and reporting corrected numbers.

### E6. Tolerance sensitivity (CPU analysis)

- **What.** For each graded run, take the measured value and target tuple from the audit record and recompute the match at 1%, 2%, 5% and 10% relative, and for percentage metrics at 1 and 2 absolute points; count claims under the default; rescore every paper whose E7 target differs from the frozen one against the target Mithil settles on.
- **Limit.** Tightening can move a reproduced run to partial and loosening a number-only partial to reproduced; runs that failed for other reasons do not move.
- **Where and time.** Delta CPU or claude-vps (about 400 rows), half a day including pulling audit rows.
- **What changes the reply.** Small movement at 2% and 10% supports "conclusions are insensitive to the default"; a collapse at 1% goes in as a table with the argument from E3's run-to-run spread.

### E7. Target validation (model re-derivation, Mithil settles disagreements)

- **What.** gpt-6.1-sol on flex, a different lab's model from both the auditor and the Claude model that drafted the targets, reads each of the 100 eval papers and writes the target tuple and minimal configuration from the paper alone, blind to the frozen value. A script compares metric, configuration and value with the frozen tuple. Mithil reads only the papers where they disagree and records which side the paper supports.
- **Example of one comparison.** For a paper whose frozen target is top-1 accuracy 76.4 on ImageNet at the ResNet-50 setting, a re-derived 76.1 at the same metric and setting agrees on metric and configuration and differs by 0.3/76.4 = 0.4% on value, inside the 5% default, so it needs no check; a re-derived target from a different table row goes to Mithil.
- **Cost and time.** About 30k input tokens per paper, 3M in all, about $5 on flex; one hour of agent work. Mithil's time depends on the disagreement count, about 10 minutes each, first run, no baseline.
- **What changes the reply.** The reply reports agreement on metric and configuration out of 100, the value gap, and how many disagreements Mithil resolved in favor of the frozen target. It calls the second deriver a model and says so plainly; a frozen target found wrong is corrected and its runs rescored.

### E8. Attribution bound and rerun of the 6 non-agent cells

- **Bound (CPU).** Recompute each agent's per-tier rate with every build-and-dependency run (24 across all agents) removed from its denominator, and count those citing a missing aarch64 wheel. Needs the per-run labels in `~/sweeps/paper-table-2026-09-05/resolved_modes.json`, which live only on the laptop; Mithil copies the folder to `/work/nvme/bfvr/msalunkhe/rebuttal/` on day 1.
- **Rerun (approved 2026-11-06).** Paper 2510.20725 (Retrain, 0-8 band) for all four agents, whose cells never started because of the prompt-rendering bug fixed on 2026-09-10, and re-audits of the two Muse Spark cells whose audit never returned (Run 2503.23035, Reimplement 2510.08177). DeepSeek-V4-Flash rides an E3 brain job; Qwen3.6-27B needs a one-GPU brain and MiniMax-M2.7 a two-GPU brain for about 12 hours each; Muse Spark uses the Meta API (about $7).
- **GPU-hours.** About 45 expected (36 serving plus agent steps), ceiling 70.
- **What changes the reply.** The new grades replace the four zeros and two missing verdicts in every rate, and the YGTR reply names the cause of all six. The bound goes in either way; if the best Run-tier rate rises above 50% under it, the Limitations paragraph says the hardware matters for released-code papers.

### E9. Network checkpoint scan (CPU analysis)

- **What.** Search every transcript for checkpoint downloads (`hf_hub_download`, `snapshot_download`, `huggingface-cli download`, `from_pretrained` with a repo id, `torch.hub.load`, `timm` with `pretrained=True`, `gdown`, and `wget` or `curl` of `.pt`, `.pth`, `.ckpt`, `.safetensors` or `.bin`), and for fetched result files whose numbers could be copied. For Retrain and Reimplement runs, label each hit as the authors' artifact, a base model the method starts from, or a third-party checkpoint of the claimed model, then check the run's grade. The harness keeps no network log, so the transcript is the record, and the reply says so.
- **Why.** The flag list has no named flag for a substituted third-party checkpoint, and `prompts/prompt_audit.txt:107-113` allows a sibling checkpoint unless it changes method, size or metric.
- **Where and time.** Delta CPU, half a day.
- **What changes the reply.** None among reproduced Retrain and Reimplement runs gives the count scanned; any found are re-graded and the corrected rates reported.

### E10. Environment check: re-execution of faithful pipelines (GPU)

- **What.** For up to 6 Run-tier and 4 Retrain-tier papers (0-8 band) whose faithful pipeline landed outside tolerance (24 such runs at Run, 37 at Retrain), an agent extracts the final command sequence from the best run's transcript and re-runs it with two new seeds on GH200, with no model in the loop, and Mithil checks each extracted sequence against the transcript before it is submitted. The reply calls this an environment check.
- **GPU-hours.** Run 6 x 2 x 2 = 24, Retrain up to its 8-hour grant 4 x 2 x 8 = 64, about 90; ceiling 180.
- **What changes the reply.** Misses that recur on two seeds belong to the environment or the paper, and the reply and Limitations count them; hits mean the original miss was seed variance or agent error.

### Budget summary

| Item | OpenAI $ | Meta $ | GPU-hours on betw (expected / ceiling) |
| :- | :- | :- | :- |
| Smoke runs (4 dev-paper runs) | 6 | 45 | 15 / 40 |
| E1 gpt-6.1-sol, flex, thin + Codex, 24 papers | 268 | | 300 / 1,376 |
| E1 gpt-6.1-terra, flex, thin + Codex, 24 papers | 134 | | 300 / 1,376 |
| E1 gpt-6-astra, flex, Codex, 8 papers | 247 | | 50 / 260 |
| E2 Muse Wonder, thin 12 + mini-SWE-agent 6 | | 401 | 113 / 550 |
| E3 DeepSeek-V4-Flash repeats, agents + 4 brain jobs | | | 564 / 1,072 |
| E7 target re-derivation, gpt-6.1-sol flex, 100 papers | 5 | | |
| E8 rerun of 2510.20725 (4 agents) + 2 re-audits | | 7 | 45 / 70 |
| E10 environment check | | | 90 / 180 |
| E5, E6, E8, E9 analyses | | | CPU, under 50 core-hours on bgnp-delta-cpu |
| **Total** | **660 of 750** | **453 of 500** | **about 1,477 / 4,924** |

Expected GPU use is 24% of betw-dtai-gh's 6,168 hours; the worst case, every run spending its full grant, is 80%, which would crowd the queued Distillation jobs, so a GPU check after the core 12 papers decides whether papers 13 to 24 launch. Grading on the Anthropic key is extra and measured at smoke. Claude Code as a harness stays out: it bills to Anthropic, and Codex CLI and mini-SWE-agent already cover the production-harness question.

## 3. Paper revisions (from the three reviews)

Load `m-paper` before any edit under `paper_latex/`. Main text may grow to 10 pages at rebuttal and now ends with the Conclusion on page 9, so new main-text material is at most one page; the rest goes to the appendix. Every new number enters only after its result file is frozen in `rebuttal/results/`.

1. **Section 5.1 and Limitations ("Agents").** Replace "The roster omits Claude, GPT, and Gemini because of cost" with one paragraph on the frontier arms and a new appendix subsection: a table of model by harness by tier (reproduced, mean score, cost, GPU-hours) and failure-mode counts beside the main agents'.
2. **Section 5.2.** Wilson intervals on the main rates and the E3 flip rate in one sentence; rates updated for the six rerun cells.
3. **Section 4 and Appendix D.** E4 confusion matrix and boundary table, once Mithil supplies the labels.
4. **Appendix A and the auditor prompt figure.** Correct `appendix/a_harness.tex:133-134` so it no longer implies the auditor prompt told the auditor to distrust the logs; report E5 with its limit; describe the hash-chained host logs used for new runs.
5. **Appendix C or F.** E6 tolerance table and the count of claims under the default.
6. **Appendix E (Stage III).** State that Stage III audited availability, and report E7.
7. **Section 5.3 and Limitations ("Attributing a miss").** E8 bound and aarch64 count, E9 scan, E10 re-execution, each where the claim is made.
8. **Section 5.1, harness paragraph.** The thin loop is the fixed baseline, and the appendix measures Codex CLI and mini-SWE-agent against it.

Compile, then read every rendered page for split floats, early page ends and uneven spacing. Upload the revised PDF only if the OpenReview revision button is open for this venue.

## 4. Schedule, 2026-11-07 to 2026-11-14

Mithil is the only person working on the rebuttal; Haochen and Samridhi take no tasks (Mithil, 2026-11-06). "Agents" means Claude workers launched from Mithil's session, and Mithil checks each result. His own hands-on time is the key setup, the E4 label file, E7 disagreements, the 20 blind failure-mode labels, checking E10 command sequences, and approving each reply.

| Day | Mithil | Agents |
| :- | :- | :- |
| Sat 11-07 | Set the $750 OpenAI project budget and a Meta limit. Copy `~/sweeps/paper-table-2026-09-05/` to `/work/nvme/bfvr/msalunkhe/rebuttal/` | Locate the DeltaAI checkout, land the account override, confirm the hour unit on a tiny betw job; freeze `subset.json`; check the Codex aarch64 binary; write and run E5, E6, E9; start E7 re-derivation; pick E10 papers |
| Sun 11-08 | Review E5, E6, E9 outputs; check E10 command sequences | Build the OpenAI and Meta thin-harness configs with the flex field, the Codex wrapper and the mini-SWE-agent wrapper; 4 smoke runs; size arms from measured cost; extract E10 sequences; finish E7 comparison |
| Mon 11-09 | Approve launches; settle E7 disagreements | Launch E1, E2, E3 brain jobs, the E8 rerun and E10; draft T29u and rqBN replies |
| Tue 11-10 | Supply the E4 label file; read the T29u and rqBN drafts | Monitor runs and spend; audit finished runs; E6 rescore on settled E7 targets |
| Wed 11-11 | **Post wave 1: T29u and rqBN replies** | E4 matrix; label failure modes on finished frontier runs with the paper's labeling pass; draw Mithil's random 20 |
| Thu 11-12 | Label the 20 frontier runs blind | Runs finish or stop at 18:00 CT; audit the rest; E8 bound and rerun grades; McNemar tests; start paper revisions under `m-paper` |
| Fri 11-13 | Read the revised PDF and the YGTR and general drafts | Frontier tables and appendix; compile; one agent per page reads spacing; one reader agent per reply with no context checks every number against `rebuttal/results/` |
| Sat 11-14 | **Post wave 2: YGTR reply, general reply, revised PDF.** Answer wave-1 follow-ups | |

Two waves give T29u and rqBN three days to respond before the deadline.

**Cut list if we fall behind** (cut from the top):

1. E2 mini-SWE-agent arm (Codex already covers the production harness).
2. The second E3 repeat (two runs per paper), saving about 280 GPU-hours.
3. Papers 13 to 24 for gpt-6.1-terra (both harnesses), then for gpt-6.1-sol's Codex arm.
4. E10 down to the 6 Run-tier papers.
5. Mithil's blind check of the frontier labels down to 10 runs.

Never cut: gpt-6.1-sol in both harnesses on the core 12, gpt-6-astra in Codex, the E8 rerun, E5 and E9. YGTR's score depends on the first two, the rerun is approved, and the last two directly answer soundness questions.

## 5. Reply outlines

Each reply thanks the reviewer in one sentence and names what changed, answers in the reviewer's order, and gives every number with its denominator. Square brackets mark values the runs fill in.

### General reply (wave 2)

1. All three reviewers found the task design sound; the main requests were frontier agents, production harnesses, repeated runs and a fuller validation of the auditor and its evidence.
2. Key sentence: "We ran three current OpenAI models on up to 24 stratified papers and Meta's Muse Wonder on 12, each in our harness and in a production harness (Codex CLI or mini-SWE-agent): gpt-6-astra in Codex reproduced [a/8], gpt-6.1-sol [b/24] in ours and [c/24] in Codex, and Muse Wonder [d/12]; the frontier agents' failures fall into the same modes as the open agents' [or: Codex removes mode X in k runs]."
3. "No agent edited its harness logs in any of the 396 runs that started, checked against a host-side transcript the agent cannot reach; new runs write a hash-chained log on the host."
4. "The six cells that failed for reasons outside the agent have been rerun and re-graded, and every rate now includes them."
5. Revisions by section.

### Reviewer T29u

- **Single run per cell.** "We added 95% intervals to every rate (best agent at Run: 14/34, [26%, 58%]) and ran DeepSeek-V4-Flash twice more on 12 stratified papers; its verdict flipped on [k] of 12 ([interval]), and we now rank two agents only where intervals widened by that rate do not overlap. This measures one agent's spread, and the paper says so."
- **Disagreements, 7/8 boundary, high-severity flags (Q1).** "Appendix D now gives the confusion matrix of auditor against human verdicts [counts]; at the 7/8 boundary they agree on [m] of [n] runs, and on high-severity flags on [p] of [q]."
- **Tolerance and match target (Q2).** "[c] of the 100 claims use the default 5% relative tolerance. At 2% the best-agent rate changes by [d, e, f] papers at Run, Retrain and Reimplement, and at 10% by [g, h, i] (new table in Appendix F). Rescoring against targets re-derived independently changes [j] verdicts."

### Reviewer rqBN

- **Auditor metrics.** The confusion matrix, precision [x], recall [y], per-tier F1 [r/t/i] and mean absolute difference on the 0 to 10 scale [d], from the human labels.
- **Writable logs.** "You are right, and our paper overstated the safeguard: the auditor prompt never told the auditor to distrust these logs, and we correct that sentence. The harness writes both files, but the agent could rewrite them. We compared both with the host-side transcript, which lies outside the sandbox, for all 396 runs and found [0] edits; the check catches any edit the agent made through its own commands. New runs write a hash-chained log on the host."
- **Human-expert baseline (Q1).** "A human reproduction across three tiers is beyond our resources, and Limitations says so. As an environment check we re-ran the faithful agents' own pipelines with two new seeds on [n] Run and Retrain papers whose faithful run missed; [k] also miss on our hardware, which bounds how much of the gap belongs to the environment."
- **Validation of claims and targets (Q2).** "Stage III audited availability calls only, and targets had no independent check until now. A model from a different lab than our auditor re-derived all 100 targets from the papers, blind to the frozen values, and agreed on metric and configuration for [a/100]; an author read every disagreement and found the frozen target wrong in [k], which we corrected and rescored."

### Reviewer YGTR

- **Frontier models and harness (W1, Q1).** "We ran gpt-6-astra, gpt-6.1-sol and gpt-6.1-terra from OpenAI on up to 24 stratified papers and Muse Wonder from Meta on 12, each in our harness and in Codex CLI or mini-SWE-agent. [Result sentence.] The most common failure in the paper, writing the method without checking it against the paper's numbers, occurs in [k] of the frontier agents' [m] failing runs, labeled with the same procedure as the paper's runs; an author's blind labels agree with it on [x] of 20." The thin loop stays the main baseline because it treats all models alike, and the new appendix measures what a production harness adds.
- **Hardware (W2).** "We cannot fully separate the hardware from agent error, and we bound it three ways. Missing aarch64 wheels explain [k] of the 24 build-and-dependency failures; removing all 24 from the denominators moves the best Run-tier rate from 41% to at most [x]%; and re-running the faithful agents' own pipelines with two new seeds, [k2] of [n] still missed on our hardware."
- **Single run (W2).** The E3 sentence.
- **Checkpoint fetching (Q2).** "We scanned all [396] transcripts for checkpoint downloads; [n] Retrain or Reimplement runs downloaded a checkpoint, [k] of them a third-party checkpoint of the claimed model, and [none] of those were graded reproduced."
- **Failures not the agent's fault (Q3).** "Six of the 400 cells failed for reasons outside the agent: four never started because of a prompt-rendering bug in our harness, since fixed, and two audits returned no verdict. We reran and re-graded all six, [result], and every rate in the revision includes them. Beyond these, the bound above covers environment failures."
- **Closing.** Ask whether the frontier and harness results address the generalization concern behind the Informativeness score.

## Open items for Mithil

1. The E4 human-label file by 2026-11-10, so the wave-1 replies carry the confusion matrix.
2. The $750 OpenAI project budget (keys are already on DeltaAI), and the `~/sweeps/paper-table-2026-09-05/` copy, on 2026-11-07.
