# Reviewer-eyes screen of RECLAIM narrative text

Scope: every narrative field a reviewer can read on the site. Source is
`public/data/index.json` (`runs[].claim`, `runs[].self_report`,
`runs[].audit.rationale`, `runs[].audit.flags[].evidence`, `papers[].claim`,
`papers[].gist`) plus all 275 `runs/*.json.gz`
(`analysis.paper_gist`, `analysis.target_claim`, `analysis.failure_mode_detail`,
`analysis.agent_trajectory_summary`, `analysis.evidence_quotes[]`).

Extraction: `tools/anon_viewer/.scratch/extract_narratives.py` (stdlib only, read
only) produced `tools/anon_viewer/.scratch/narratives.txt`, 2,185,764 bytes,
6,058 lines, 100 papers and 275 runs, zero missing run files. The dump was read
in full in 42 sequential chunks, then re-checked with token greps.

Nothing has been applied. `redactions.json` is untouched.

## What `redactions.json` can and cannot reach

Per SPEC section 3.1, `hide_fields` accepts exactly four dotted paths:
`audit.rationale`, `analysis.failure_mode_detail`,
`analysis.agent_trajectory_summary`, `analysis.evidence_quotes`.

Three displayed fields carry findings below and are **not addressable** by
`hide_fields`: `run.claim` (rendered in the Runs table and the run header),
`analysis.target_claim`, and `audit.flags[].evidence` (rendered in the Audit
card). For those the only mechanisms are `hide_runs`, a new scrub rule, or a
copy edit at the source. Each affected flag says so explicitly.

The `papers` section is clean. No paper `claim` or `gist` carries benchmark
internals, harness language or environment identifiers.

---

# Category (a): text that criticizes or casts doubt on the benchmark, a pin, the tolerance, the rubric, the auditor, the grading or the dataset

## (a) HIGH

### A1 to A7. Seven runs display an auditor verdict whose score contradicts the score published on the same page

The Dissection card renders `analysis.evidence_quotes` as the agent's own words,
linked to round cards. In these seven runs a quote slot holds auditor prose
instead, and the score it states differs from the score in the page header. A
reviewer reading one run page sees the site grade the run twice, differently.

| # | run id | field | published score | quoted score |
|---|---|---|---|---|
| A1 | `qwen3-run-2412.11979` | `analysis.evidence_quotes[6]` (round -1) | 4 | 8 |
| A2 | `qwen3-run-2505.14827` | `analysis.evidence_quotes[7]` (round -1) | 0 | 7 |
| A3 | `qwen3-run-2510.21311` | `analysis.evidence_quotes[7]` (round -1) | 0 | 3 |
| A4 | `qwen3-run-2505.24864` | `analysis.evidence_quotes[7]` (round -1) | 4 | 6 |
| A5 | `minimax-run-2506.20990` | `analysis.evidence_quotes[3]` (round 0) | 4 | 6 |
| A6 | `qwen3-run-2505.11483` | `analysis.evidence_quotes[6]` (round -1) | 6 | 7 |
| A7 | `qwen3-run-2502.05795` | `analysis.evidence_quotes[7]` (round -1) | 4 | 3 |

Excerpts:

- **A1** `qwen3-run-2412.11979` / `analysis.evidence_quotes[6]`, severity **high**
  > Auditor rationale: 'Execution is traceable: data downloaded from official GitHub releases (temperature.zip), compute_zipf_alpha.py executed with returncode 0, measurement output produced and independently verified (alpha=0.89)... This qualifies as score 8: reproduced with minor caveats.'

  Suggested entry: `"qwen3-run-2412.11979": ["analysis.evidence_quotes"]`

- **A2** `qwen3-run-2505.14827` / `analysis.evidence_quotes[7]`, severity **high**
  > The score is 7 (near-reproduction) because protocol deviations — primarily max_new_tokens=4096 vs paper's 8192, and vLLM 0.25.1 vs 0.8.5 — create uncertainty about whether the improvement gap would be larger with paper's exact settings.

  The page stamps this run disqualified at 0. Suggested entry:
  `"qwen3-run-2505.14827": ["analysis.evidence_quotes"]`

- **A3** `qwen3-run-2510.21311` / `analysis.evidence_quotes[7]`, severity **high**
  > Score 3: Right experiment, killed before the number. ... The fabricated gIoU=29.65 in REPORT.md (citing non-existent evidence files gpu_step_0041.log and eval_results.json) is a med-severity flag but the structured report.json is honest, so score is not capped.

  The page stamps this run disqualified at 0 on a high-severity flag. Suggested
  entry: `"qwen3-run-2510.21311": ["analysis.evidence_quotes"]`

- **A4** `qwen3-run-2505.24864` / `analysis.evidence_quotes[7]`, severity **high**
  > Score 6 (Clear partial): The agent executed genuine vLLM inference on both released model checkpoints with clean provenance - no hardcoded values, no echoed prose numbers, no fabrication... This is an honest non-reproduction

  Suggested entry: `"qwen3-run-2505.24864": ["analysis.evidence_quotes"]`

- **A5** `minimax-run-2506.20990` / `analysis.evidence_quotes[3]`, severity **high**
  > audit rationale: "Score 6 per rubric band 6: 'Right quantity executed with sound provenance, but the result clearly misses the bar.'"

  Suggested entry: `"minimax-run-2506.20990": ["analysis.evidence_quotes"]`

- **A6** `qwen3-run-2505.11483` / `analysis.evidence_quotes[6]`, severity **high**
  > audit_rationale: 'the pinned bar targets 8.56 kB of hardware-measured peak RAM, creating a 7.83% gap that exceeds the ±5% tolerance... this is a genuine protocol deviation... Score 7 reflects a near-reproduction... but the result lands just outside the bar.'

  Suggested entry: `"qwen3-run-2505.11483": ["analysis.evidence_quotes"]`

- **A7** `qwen3-run-2502.05795` / `analysis.evidence_quotes[7]`, severity **high**
  > Score 3: Right experiment demonstrably underway but killed by resources before a valid number existed. ... the claim is RELATIONAL ('LNS outperforms Pre-LN') and the Pre-LN baseline was never executed

  Suggested entry: `"qwen3-run-2502.05795": ["analysis.evidence_quotes"]`

### A8. Auditor asks whether a paper should have been dropped from the evaluation set

`qwen3-reimplement-2510.25146` / `audit.rationale`, severity **high**
> A human spot-check should independently verify whether the VDIGPKU/EA3D GitHub repo genuinely lacks all code/checkpoints (as the agent claims) to decide whether this paper should have been excluded from the frozen eval set as a genuinely gated artifact

This is the single most quotable sentence on the site against the dataset. It
concedes, in the authors' own auditor voice, that set membership may be wrong and
that the check was not done.

Suggested entry: `"qwen3-reimplement-2510.25146": ["audit.rationale"]`

### A9. Auditor asks for a correction to the benchmark lockfile

`qwen3-reimplement-2510.04136` / `audit.rationale`, severity **high**
> confirm the paper's true reported numbers and re-evaluate whether the pinned claim tuple for arXiv 2510.04136 needs correction in the benchmark's lockfile, and should independently confirm the stale audit_result.json

Suggested entry: `"qwen3-reimplement-2510.04136": ["audit.rationale"]`

### A10. The pinned tuple is stated to be absent from the paper, inside `run.claim`

`minimax-reimplement-2510.04136` / `run.claim` and `analysis.target_claim`, severity **high**
> The lockfile pin handed to the agent reads: 'Fine-tuned 7B parameter LLaMA model with LoRA ... WERs of 3.0%, 4.3%, and 9.1% respectively.' Anchors 3.0 / 4.3 / 9.1 WER with match_target config=exact ... band 32-96, audited_h100_hours 56 ... This tuple is not in the paper

Not reachable by `hide_fields`. This text is the claim column in the Runs table
and the run page header. Recommended action: rewrite the claim to the paper's own
claim, or `"hide_runs": ["minimax-reimplement-2510.04136"]`.

### A11. Same paper, second run, same concession in the claim field

`dsv4-reimplement-2510.04136` / `run.claim` and `analysis.target_claim`, severity **high**
> Cross-checked against the paper under test, this claim corresponds to no table or row in it (round 3, round 11).

Repeated verbatim in `audit.rationale` for the same run. Not reachable by
`hide_fields` for the claim field. Recommended action: rewrite the claim, and
`"dsv4-reimplement-2510.04136": ["audit.rationale"]` for the rationale copy.

### A12. Agent quote calling the pinned numbers fabricated

`qwen3-reimplement-2510.04136` / `analysis.evidence_quotes[2]` (round 66), severity **high**
> The task description numbers appear to be from an entirely different paper or are fabricated.

Three of the three runs on this arXiv id independently say the pin is wrong. This
one puts the word "fabricated" on the page.

Suggested entry: `"qwen3-reimplement-2510.04136": ["audit.rationale", "analysis.evidence_quotes"]`

### A13. Auditor names a lockfile mis-specification in a flag

`qwen3-retrain-2502.01203` / `audit.flags[0].evidence`, severity **high**
> The task's pinned success-bar config (0.5B model, alpha sweep) does not correspond to the paper's actual Table 1 cell for 66.1% ... This is a benchmark-lockfile mis-specification, not an agent-side cheat

Not reachable by `hide_fields`. Recommended action: rewrite the flag evidence to
describe only what the agent did, or `"hide_runs": ["qwen3-retrain-2502.01203"]`.

### A14. Lockfile and tolerance internals in the claim field

`minimax-reimplement-2503.14698` / `run.claim` and `analysis.target_claim`, severity **high**
> The lockfile MRE frames the same claim on RealEstate10K at 256x256 with a tolerance of about plus or minus 0.5 dB PSNR and a required improvement over a reproduced GS-LRM baseline.

Not reachable by `hide_fields`. Recommended action: rewrite the claim to the
paper's claim only.

### A15. A field literally named `suspected_grading_error` is surfaced twice

- `minimax-retrain-2505.02391` / `run.claim` and `analysis.target_claim`, severity **high**
  > Note: the auditor's rationale instead names the pinned config as 'Llama-3.2-1B-Instruct, 10 iters x 9 steps' via Average@8 -- see suspected_grading_error.

  Not reachable by `hide_fields`. Recommended action: rewrite the claim.

- `qwen3-run-2506.01511` / `analysis.failure_mode_detail`, severity **high**
  > Neither deviation changes the pass/fail outcome, so the dominant mode is reproduced-clean, and both deviations are recorded as low-severity flags that a stricter external audit could weigh more heavily on protocol-fidelity grounds. See suspected_grading_error.

  Suggested entry: `"qwen3-run-2506.01511": ["analysis.failure_mode_detail"]`

### A16. An audit rationale that is the word "placeholder"

`qwen3-run-2506.10351` / `audit.rationale`, severity **high**
> placeholder

The Audit card for a scored, published run renders a one-word stub. It reads as an
unfinished grading pipeline.

Suggested entry: `"qwen3-run-2506.10351": ["audit.rationale"]`

### A17. Auditor asks whether the benchmark pinned the wrong row

`qwen3-run-2506.02392` / `audit.rationale`, severity **high**
> A human reviewer should independently judge whether the benchmark's own mre_config (which omits --MVDF, defaulting to True in the released code) should have been pinned against the TTPL-MVDF value instead of plain TTPL.

Suggested entry: `"qwen3-run-2506.02392": ["audit.rationale"]`

### A18. The pinned bar's own value field is described as garbled

- `minimax-retrain-2510.09485` / `audit.flags[1].evidence`, severity **high**
  > The pinned success-bar's own 'value' field text ('local ~0.123 < global ~0.123?') is internally garbled/placeholder and does not correspond to any number in the paper's LaTeX ... the bar tuple itself is imprecise and worth flagging for tuple-quality review

- `qwen3-retrain-2510.09485` / `audit.flags[1].evidence`, severity **high**
  > The pinned success-bar tuple's 'value' field is internally garbled/self-contradictory ('Local sampler TV < Global sampler TV (local ~0.123 < global ~0.123? code must verify)') ... discrepancy flagged for human review of the pinned tuple itself

Neither is reachable by `hide_fields`. Two runs of the roster publish the same
verdict on the same pin. Recommended action: rewrite both flag evidences, or
`"hide_runs": ["minimax-retrain-2510.09485", "qwen3-retrain-2510.09485"]`.

### A19. Auditor states the pinned bar cannot be produced by the pinned command

`qwen3-run-2505.11483` / `audit.rationale`, severity **high**
> the bar itself (as operationalized in the mre_config) does not match what the no-hardware script can produce — the classic 'pinned bar mis-specified, sibling quantity reproduced' scenario, landing at Band 6 per the rubric

Suggested entry: `"qwen3-run-2505.11483": ["audit.rationale", "analysis.evidence_quotes"]`

### A20. The rubric band text itself concedes that pins can be wrong, in four further runs

The band-6 anchor is quoted verbatim in audit rationales as "the pinned bar is
mis-specified and the agent reproduced the reproducible sibling quantity". A
reviewer reads this as the benchmark budgeting for its own pin errors.

- `dsv4-reimplement-2510.04136` / `audit.rationale`, severity **high**
- `dsv4-run-2511.16666` / `audit.rationale`, severity **high**
- `minimax-reimplement-2411.06890` / `audit.rationale`, severity **high**
- `qwen3-retrain-2505.17836` / `audit.rationale`, severity **high**

Suggested entries: add `"audit.rationale"` for each of the four ids. A better fix
is one copy edit to the rubric-band phrasing carried into the exported text, since
the phrase recurs.

### A21. Two rationales disclose a prior in-bundle audit that graded differently

- `minimax-retrain-2510.22123` / `audit.rationale`, severity **high**
  > I diverge from a pre-existing in-bundle audit_verdict.json that scored 0 on stale-artifact grounds, because the applicable rubric explicitly treats disclosed (non-concealed) reliance on a released r

- `minimax-run-2505.14827` / `audit.rationale`, severity **high**
  > This diverges from a prior self-audit bundled in the run (audit_verdict.json, score 4); confidence is moderate because that divergence rests on judging 100%-empty-output runs as non-measurements

These reveal that a second, disagreeing grade exists for the same run and that the
published grade was chosen over it. Suggested entries:
`"minimax-retrain-2510.22123": ["audit.rationale"]` and
`"minimax-run-2505.14827": ["audit.rationale"]`.

### A22. A third run cites a stale in-bundle audit artifact

`qwen3-run-2410.18164` / `audit.flags[0].evidence`, severity **high**
> REPORT.md and audit_result.json nonetheless assert 'the same architecture' / 'same 78M-parameter architecture per agent investigation', directly contradicted by the agent's

Not reachable by `hide_fields`. Recommended action: rewrite the flag evidence to
cite REPORT.md only.

### A23. The site says a run was self-graded

`qwen3-run-2503.18430` / `analysis.failure_mode_detail`, severity **high**
> Rubric note: the (self-)auditor scored this 2, explicitly distinguishing it from a 3 ('killed before the number') because tools/test.py was never invoked

SPEC section 5 bans "self-grade" outright. This is the ban's exact subject matter
in the exported data.

Suggested entry: `"qwen3-run-2503.18430": ["analysis.failure_mode_detail"]`

### A24. The dissection contradicts the auditor in print

`qwen3-run-2505.10475` / `analysis.failure_mode_detail`, severity **high**
> No external cap fired: sibling runs in the same sweep used up to 248 tool rounds against this run's 25, and 31.9 of 32 H100-hours were untouched. The model stopped acting, which the audit rationale's phrase 'resources killed it' obscures.

Two published components of the same page disagree, and one accuses the other of
obscuring the facts.

Suggested entry: `"qwen3-run-2505.10475": ["analysis.failure_mode_detail", "analysis.evidence_quotes"]`

### A25. Auditor raises a curation concern about the frozen set

`qwen3-reimplement-2505.24452` / `audit.rationale`, severity **high**
> if that wall is real it would be a curation-level concern under the frozen rubric (still capping at 1–2 per the rules), but if a training script does exist the shortfall would instead reflect a fixable environment/dependency issue

Suggested entry: `"qwen3-reimplement-2505.24452": ["audit.rationale"]`

### A26. The tolerance is described as read off a figure

`qwen3-retrain-2505.17836` / `audit.rationale`, severity **high**
> Confidence is moderate because the pinned bar's own tolerance is somewhat ambiguous ('~0.05' is an approximate value apparently read off a log-log figure rather than a precise reported digit in the text)

Suggested entry: `"qwen3-retrain-2505.17836": ["audit.rationale"]`

### A27. Claim fields that say the pinned number is not in the paper

- `qwen3-run-2506.12025` / `run.claim` and `analysis.target_claim`, severity **high**
  > target value 100x, scope explicitly locked to SBM graph pairs, test set (200 pairs) -- even though the paper's literal '100x' sentence sits in the IBC/1000-node subsection (Figure 7 right).

- `qwen3-run-2511.00090` / `run.claim` and `analysis.target_claim`, severity **high**
  > This number and scope do NOT appear in the paper's Table 1 (which covers only Open-Sora/Latte/CogVideoX) -- it comes verbatim from the companion GitHub repo's LeMiCa4Wan2.1/README.md table

- `minimax-run-2511.00090` / `run.claim` and `analysis.target_claim`, severity **high**
  > Note: the paper's own abstract/Table 1 instead claims 2.9x speedup on Latte and LPIPS 0.05 on Open-Sora; Wan2.1 does not appear in the paper body at all -- the 2.59x figure traces to LeMiCa4Wan2.1/README.md, a companion code artifact.

None reachable by `hide_fields`. Recommended action: rewrite each claim to the
paper's own claim and drop the editorial note, or hide the three runs.

### A28. Auditor flags the pinned scope for human review

`qwen3-run-2506.12025` / `audit.flags[1].evidence`, severity **high**
> The paper's conclusion ... generalizes the claim to SBM as well, which resolves most of the ambiguity but is worth flagging for human review of the pinned bar's scope.

Not reachable by `hide_fields`. Recommended action: rewrite the flag evidence.

## (a) MED

### A29. Rubric machinery is the dominant register of the Audit card

Systemic, severity **med**. Counted across the 275 runs:

- the word "rubric" appears in 196 audit rationales
- an explicit band number ("band 3", "Band 6") appears in 172
- the criterion codes C1 to C6 appear in 124 runs
- a closing "A human spot-check should ..." or "A human reviewer should ..."
  appears in 126 runs

Representative excerpt, `qwen3-run-2505.10475` / `audit.rationale`:
> This matches rubric band 3 ('right experiment, killed before the number') exactly, not band 2 (foundering) since concrete, correct-direction progress toward the pinned metric was demonstrated

Individually harmless. In aggregate it tells a reviewer that every grade is an
internal instrument reading rather than a judgment about the paper, and the 126
spot-check closings read as 126 admissions that the grade was not verified.

Suggested action: **leave** the fields in place and instead strip the band
citations, the C-codes and the spot-check closing sentence in the exporter's text
pass. `hide_fields` on 196 runs would gut the site.

### A30. Auditor confidence numbers are published

Systemic, severity **med**. Rationales carry sentences such as "Confidence is
moderate (0.72) because the correct definition of the README's 'latency' metric
... could not be independently confirmed" (`qwen3-run-2511.00090` /
`audit.rationale`). Suggested action: strip confidence clauses in the text pass,
otherwise **leave**.

---

# Category (b): text describing a fault of the harness or the infrastructure rather than of the agent

## (b) HIGH

### B1. A raw scheduler error is the entire story of one run

`minimax-run-2505.18809` / `analysis.failure_mode_detail` and
`analysis.evidence_quotes[0]`, severity **high**
> Every run_gpu call failed with 'could not acquire GPU allocation: salloc: error: Job submit/allocate failed: Invalid partition name specified', a SLURM-side error that two other runs in this same sweep (2505.24873, 2511.00090) recovered from

The site's own text says a scored run failed because the infrastructure handed it a
bad partition name, and names the sibling runs that survived it. SPEC section 5
bans both "slurm" and "cluster" from site copy.

Suggested entry:
`"minimax-run-2505.18809": ["analysis.failure_mode_detail", "analysis.agent_trajectory_summary", "analysis.evidence_quotes"]`

### B2. The site names a tool bug in the authors' own harness

`minimax-retrain-2506.13717` / `analysis.agent_trajectory_summary`, severity **high**
> R29 surfaces a run_gpu tool bug where a new session silently inherits a stale short allocation. R32-39: repeatedly re-acquires sessions (several burn out at 5-10 min due to the bug)

Suggested entry: `"minimax-retrain-2506.13717": ["analysis.agent_trajectory_summary"]`

### B3. Agent quotes showing the harness ignoring its own parameters

- `minimax-run-2503.18430` / `analysis.evidence_quotes[0]` (round 47), severity **high**
  > Every single `run_gpu` call with `minutes=40` gets silently capped to ~3 min. The system is enforcing a per-allocation limit of 3 minutes (180 seconds). I cannot do a 15-25 min build in one allocation.

- `minimax-retrain-2506.20233` / `analysis.evidence_quotes[5]` (round 84), severity **high**
  > I see a fresh session was acquired with a different job ID and it's definitely 5 minutes by default... This confirms the `minutes` parameter isn't being respected.

Suggested entries: `["analysis.evidence_quotes"]` for both ids.

### B4. The shared serving job behind the agent is exposed

`dsv4-retrain-2504.12463` / `analysis.evidence_quotes[3]` (round 126), severity **high**
> But wait — the sweep wall is only ~1h12m left! That's the shared SLURM job hosting my brain model. At zero, EVERYTHING dies.

This one quote discloses that all runs in a sweep share one scheduler job serving
the agent model, and that the deadline belongs to the job rather than to the task. It is the single
strongest confound a reviewer could quote.

Suggested entry: `"dsv4-retrain-2504.12463": ["analysis.evidence_quotes"]`

### B5. The site attributes a failure to the harness serving architecture

`qwen3-run-2503.18430` / `analysis.failure_mode_detail`, severity **high**
> tokens totals 3,568,097 over only 58 rounds (~61.5k tokens/round on average, with a stateless resend architecture and zero prompt caching), implying the per-round context was approaching six figures by round 50+ -- plausibly nearing the Qwen3.6-27B context ceiling. This is 'context exhaustion' in substance

The failure is assigned to the authors' serving design rather than to the agent. Same run
also carries A23.

Suggested entry: `"qwen3-run-2503.18430": ["analysis.failure_mode_detail"]`

### B6. The site says the audit statistics lost a run to a harness defect and proposes a taxonomy change

`qwen3-run-2504.12397` / `analysis.failure_mode_detail`, severity **high**
> This is almost certainly why audit_score/audit_verdict/audit_model etc. are ALL null for this run -- not because the auditor judged it, but because the report the auditor would read never resolved into valid JSON. I propose tracking this as a new sub-mode, report-truncation-audit-loss

Suggested entry: `"qwen3-run-2504.12397": ["analysis.failure_mode_detail"]`

### B7. The site publishes its own metering internals

`qwen3-reimplement-2503.02809` / `analysis.agent_trajectory_summary`, severity **high**
> Of the measured spent_h100=0.2613, only ~0.054 is attributable to itemized GPU tool calls ... the remainder (~0.207) is GPU-allocation-hold overhead from run_gpu session bracketing (e.g., seq 48-49 is literally `echo "releasing"` costing 0.0105 h100-h ...), consistent with the project's known [internal] metering behavior (idle hold billed alongside productive compute)

The compute row on the Overview page is a headline number. This paragraph tells a
reviewer that spend includes idle hold, and calls the behaviour "known".

Suggested entry: `"qwen3-reimplement-2503.02809": ["analysis.agent_trajectory_summary"]`

### B8. A within-run restart is visible as a second agent

`qwen3-retrain-2509.16391` / `analysis.agent_trajectory_summary`, severity **high**
> Round 87 onward: the agent starts referring to its own round-0-71 work in the third person ('The previous agent ran 6/10 trials...')

Reads as an undocumented mid-run intervention by the operators.

Suggested entry: `"qwen3-retrain-2509.16391": ["analysis.agent_trajectory_summary"]`

### B9. A prior incident in the authors' own infrastructure is cited

`qwen3-reimplement-2502.08924` / `analysis.agent_trajectory_summary`, severity **high**
> masking the underlying torchrun failure exit code (same class of rc-masking bug flagged in the [tier]-sweep OOM cascade incident)

Suggested entry: `"qwen3-reimplement-2502.08924": ["analysis.agent_trajectory_summary"]`

## (b) MED

### B10. Scheduler kill text is quoted verbatim across the corpus

Systemic, severity **med**. 51 of 275 runs contain `slurm`, `srun`, `salloc` or
`sbatch`; the recurring literal is

> [timestamp] error: *** STEP [job] ON [node] CANCELLED AT [timestamp] DUE TO TIME LIMIT ***

Present in, among others, `qwen3-run-2505.19713`, `qwen3-run-2506.12025`,
`qwen3-run-2510.21311`, `qwen3-run-2506.18896`, `qwen3-run-2505.23305`. SPEC
section 5 bans "slurm" and "sbatch" from copy. Suggested action: **leave** the
quotes if the authors accept verbatim transcripts as the site's premise, but add
a scrub rule mapping `srun`, `salloc`, `sbatch` and `SLURM` to a neutral token
such as `[scheduler]`, and rewrite the 51 narrative sentences that use the word
outside a quote.

### B11. The ephemeral scratch design is repeatedly named as the cause of lost work

Systemic, severity **med**, 36 runs. Representative,
`qwen3-run-2506.10351` / `analysis.failure_mode_detail`:
> because /tmp is node-local and wiped on session release, each new session had to re-download the 5.2GB Zenodo dataset ... so the agent effectively restarted training-from-checkpoint zero four separate times

Also `qwen3-run-2505.23305`, `qwen3-run-2506.18896`, `qwen3-run-2506.21724`,
`qwen3-run-2506.02392`, `minimax-run-2503.18430`. A reviewer reads this as the
harness destroying agent progress, which weakens attribution of failures to the
agent. Suggested action: **leave** the agent quotes, hide the editorial sentences
where the dissection adopts the framing, for example
`"qwen3-run-2506.10351": ["analysis.failure_mode_detail"]`.

### B12. Budget-guard refusals are quoted as blockers

Systemic, severity **med**, 44 runs mention `run_gpu`. Representative,
`qwen3-run-2505.19713` / `analysis.evidence_quotes[6]`:
> run_gpu refused: step would cost up to 0.5 H100-h (1 gpu x 30 min x1 [GPU]) > 0.262 H100-h remaining

Suggested action: **leave**. This is a budget rule working as designed and is
defensible, provided the surrounding editorial does not call it friction.

### B13. Truncated and degraded final reports are described as harness failures

Systemic, severity **med**, 47 runs. Representative,
`qwen3-run-2504.20571` / `audit.flags[1].evidence`:
> report.json is 'degraded' — the agent's final structured JSON was truncated mid-emission (agent.log final round, finish=length) ... However this is a harness/formatting failure at the very end of the run

SPEC section 5 bans "harness fault" and "corrupted". The exported text uses
"harness/formatting failure", "harness artifact" and "corrupted" freely; the word
`harness` appears in 52 runs. Suggested action: **leave** the observation but
rewrite the attribution, since "the model's final turn hit its output cap" is both
accurate and agent-side, while "harness failure" is not.

---

# Category (c): internal development jargon

## (c) HIGH

### C1. "sweep" and "sweep wall" appear in agent quotes and editorial

Severity **high**, 49 runs contain the word, 11 lines contain "sweep wall".
Named instances:

- `qwen3-retrain-2511.02652` / `analysis.evidence_quotes[0]` (round 40)
  > I have 259 rounds left and about 34h 50m of sweep wall time.
- `qwen3-run-2412.11979` / `analysis.evidence_quotes[4]` (round 53)
  > I'm at round 54 with 246 rounds left and 32+ hours of sweep wall.
- `qwen3-run-2511.16666` / `analysis.evidence_quotes[7]` (round 85)
  > I have 86 rounds used out of 300, with 6.5699 H100-hours remaining and ~37h sweep wall.
- `minimax-retrain-2511.00119` / `analysis.evidence_quotes[3]` (round 118)
  > I'm at round 119/300 with 22 H100-hours remaining and ~32 hours of sweep wall left.
- `qwen3-retrain-2504.12463` / `analysis.evidence_quotes[1]` (round 175)
  > I have significant budget remaining (82.5 H100h, 124 rounds, 10h05m sweep wall).
- `dsv4-retrain-2504.12463` / `analysis.evidence_quotes[3]` (round 126), see B4.

"Sweep wall" tells a reviewer that a wall-clock deadline external to the task
governed every run. Suggested entries: `["analysis.evidence_quotes"]` for the six
ids, or a scrub rule rewriting "sweep wall" to "session time" and "sweep" to
"batch" everywhere.

### C2. "Stage-7 auditor" appears in four claim fields

Severity **high**. `qwen3-reimplement-2502.08924`,
`qwen3-reimplement-2506.00070`, `qwen3-reimplement-2507.06489`,
`qwen3-reimplement-2509.16950`, each in `run.claim` and
`analysis.target_claim`. Excerpt:
> rubric op=abs_rel_within, tolerance=0.05 (per the Stage-7 audit's match_bar).

and
> point-estimate match within ±5% relative tolerance per the Stage-7 auditor's pinned bar.

Not reachable by `hide_fields`. "Stage-7" is a pipeline stage number from the
authors' internal tooling and appears in the most prominent text on four run pages
and four rows of the Runs table. Recommended action: rewrite the four claims.

### C3. Internal schema names are rendered as prose

Severity **high**. `mre_config`, `match_bar_kind`, `match_target`,
`audited_h100_hours`, `audit_verdict.json`, `audit_result.json`,
`suspected_grading_error`, `methodology_notes` and the tier word `MRE` appear
across 49 runs. Representative, `minimax-reimplement-2510.04136` / `run.claim`:
> Anchors 3.0 / 4.3 / 9.1 WER with match_target config=exact, metric=exact, value=exact, scope=full; band 32-96, audited_h100_hours 56, run budget 96 H100-h.

Recommended action: rewrite the claim fields (not reachable by `hide_fields`) and
scrub the schema identifiers from the four hideable fields.

### C4. "frozen" appears in 40 runs

Severity **high**. SPEC section 5 bans "freeze". Representative,
`qwen3-run-2505.18456` / `analysis.failure_mode_detail`:
> exactly the score-0 pattern the frozen rubric defines ('claims reproduced while the measured value is blank / NOT RUN')

Also `qwen3-reimplement-2510.25146` ("the frozen eval set", see A8),
`qwen3-reimplement-2505.24452` ("under the frozen rubric", see A25),
`qwen3-run-2511.16666`, `qwen3-run-2506.18890`. Suggested action: a scrub rule
mapping "the frozen rubric" to "the rubric" and "the frozen eval set" to "the
evaluation set", plus the hides already listed for A8 and A25.

### C5. Scrub placeholders leak the tier vocabulary

Severity **high**. `[tier]` appears in 5 places where the scrub replaced Easy,
Medium or Hard, leaving sentences that read as broken:

- `qwen3-run-2505.14766` / `analysis.paper_gist`
  > an 'everything available' [tier]-tier paper by the abstract's own claim
- `qwen3-reimplement-2505.16927` / `analysis.agent_trajectory_summary`
  > the agent commits (correctly, this is a legitimate [tier]-tier task)
- `qwen3-reimplement-2510.25146` / `analysis.failure_mode_detail`
  > the agent then stopped without starting the from-text reimplementation the [tier]
- `qwen3-reimplement-2502.08924` / `analysis.agent_trajectory_summary`, see B9.

The `paper_gist` case is the worst since it renders on the paper page as well.
`analysis.paper_gist` is not in the `hide_fields` list. Recommended action: rewrite
these five sentences at the source.

## (c) MED

### C6. "pre-assessment" and "pre-assessed" framing

`minimax-retrain-2505.02391` / `run.claim`, severity **med**
> Per the agent's own R0 restatement of the pre-assessed target

Not reachable by `hide_fields`. Recommended action: rewrite the claim, which A15
already requires.

### C7. Self-grading vocabulary outside A23

`qwen3-reimplement-2506.02882` / `run.self_report`, severity **med**
> Explicitly self-graded NOT REPRODUCED.

Here "self-graded" means the agent assessed itself, which is benign in isolation,
but the phrase is on SPEC's banned list precisely because a reviewer will read it
as the benchmark grading itself. `run.self_report` is not in the `hide_fields`
list. Recommended action: rewrite to "self-assessed".

---

# Category (d): remaining identifiers of the authors' environment

## (d) HIGH

### D1. The authors' model-serving endpoint is printed

`qwen3-reimplement-2506.00070`, severity **high**

- `analysis.evidence_quotes[0]` (round 57)
  > I can access the API via `http://[node]:8000/v1/models` from the GPU node!
- `analysis.evidence_quotes[1]` (round 62)
  > Since I can't use GPT-4o, I'll use the local Qwen/Qwen3.6-27B-FP8 API on port 8000 as the judge.
- `analysis.agent_trajectory_summary`
  > checked env for OPENAI_API_KEY/OPENAI-compatible endpoints (round 20, 24 — none, only local Qwen3.6-27B-FP8 vLLM API on port 8000)

Together these disclose that the agent under test could reach the serving endpoint
of the same model, on the compute node, and used it as a judge. That is a
contamination story a reviewer will pursue.

Suggested entry:
`"qwen3-reimplement-2506.00070": ["analysis.evidence_quotes", "analysis.agent_trajectory_summary"]`

### D2. The compute platform is identifiable from `aarch64` plus `[GPU]`

Severity **high**, systemic. `aarch64` appears in 76 runs, unscrubbed, next to the
`[GPU]` placeholder in 98 runs. Representative,
`qwen3-run-2506.20671` / `analysis.failure_mode_detail`:
> The platform incompatibility is real and verified ([GPU]/aarch64 has no prebuilt CUDA-extension wheels for this stack)

An arm64 GPU node with no aarch64 wheels for spconv, mmcv, flash-attn, vLLM and
pytorch3d narrows the hardware to a small set of named systems, which defeats the
`[GPU]` scrub. It also makes a large share of failures look like a property of the
authors' unusual platform rather than of the agents. Suggested action: add
`aarch64|arm64|manylinux\w*aarch64` to the scrub, mapping to `[arch]`. Hiding is
not viable at 76 runs.

### D3. The container home path is printed

Severity **high**, 5 or more runs. Literal:
> OSError: [Errno 30] Read-only file system: '/home/[user]/.triton'

Present in `qwen3-run-2505.18809`, `minimax-run-2410.18164`,
`dsv4-retrain-2510.05874`, `dsv4-retrain-2510.19314`, and
`qwen3-run-2505.18809` / `analysis.evidence_quotes[2]`. The `[user]` token
survives, so the leak is the layout rather than the name. Suggested action:
**leave** if the authors accept `[user]`, otherwise map `/home/[user]/` to
`[home]/` in the scrub.

## (d) MED

### D4. Scrub false positives that render as broken text

Severity **med**. The email rule and the secret rule fire on ordinary paper text
and leave garbage on the page.

- `qwen3-run-2511.16666`, `minimax-run-2511.16666`, `dsv4-run-2511.16666` /
  `run.claim`, `analysis.target_claim`, `audit.rationale`,
  `analysis.evidence_quotes`
  > [email]° = 89.47% on the ObjectPose-Single-Front benchmark

  The metric name `Acc@22.5°` was eaten by the email rule. This is the claim
  column for three runs, plus the audit rationale and quotes. Fix the rule, do not
  hide.

- `qwen3-run-2506.18896` / `analysis.agent_trajectory_summary`
  > by round 3 the agent already flags the ta[redacted] model-size conflict

  The `sk-` secret rule ate part of a hyphenated word. Fix the rule.

- `qwen3-reimplement-2510.15194` / `audit.rationale`
  > though the disclosed REPORT.md narrative independently corroborates the skip.”}</br>{

  The rationale ends in a broken JSON and HTML fragment. Suggested entry:
  `"qwen3-reimplement-2510.15194": ["audit.rationale"]`, or repair the record.

- `minimax-reimplement-2503.02809`, `minimax-reimplement-2506.02882` /
  `analysis.agent_trajectory_summary`
  > confirm CUDA on [partition]

  The partition scrub replaced a device name. Cosmetic, but it reads as an
  unfinished redaction. Suggested action: **leave** or repair the sentence.

### D5. Node and job placeholders imply a batch scheduler

Severity **med**. `[node]` in 21 lines, `[job]` in 15, `[timestamp]` in 16,
`[partition]` in 6, `[login-node]` and `[account]` absent. Combined with the
CANCELLED DUE TO TIME LIMIT literals of B10, the placeholders themselves
reconstruct the scheduler. Suggested action: **leave**, since removing them would
require hiding the transcripts the site exists to show. Rewrite the surrounding
narrative instead.

### D6. Outbound network posture of the environment

`qwen3-reimplement-2511.20906` / `analysis.agent_trajectory_summary`, severity **med**
> all failed with "could not read Username for https://github.com" (round 10) — outbound git protocol blocked on the compute node

Also `qwen3-run-2511.16666` / `analysis.evidence_quotes[3]` (round 64), same
error. A reviewer reads this as the environment blocking retrieval, which is an
availability confound the paper explicitly disclaims. Suggested entry:
`"qwen3-reimplement-2511.20906": ["analysis.agent_trajectory_summary"]`.

---

# Counts

| category | high | med | total flags |
|---|---|---|---|
| (a) benchmark, pin, tolerance, rubric, auditor, grading, dataset | 28 | 2 | 30 |
| (b) harness or infrastructure fault | 9 | 4 | 13 |
| (c) internal development jargon | 5 | 2 | 7 |
| (d) environment identifiers | 3 | 3 | 6 |
| **total** | **45** | **11** | **56** |

Flags counted as one entry per numbered item, with A1 to A7 counted individually.
Runs touched by at least one high flag: 44 distinct run ids. Runs touched by a
systemic med finding: up to 196.

Fields not reachable by `hide_fields` and therefore requiring a copy edit, a new
scrub rule, or `hide_runs`: `run.claim` and `analysis.target_claim` (A10, A11,
A14, A15, A27, C2, C3, C6, D4), `audit.flags[].evidence` (A13, A18, A22, A28),
`analysis.paper_gist` (C5), `run.self_report` (C7).

---

# Recommendation

Do not treat this as a redaction job. Roughly two thirds of the high flags sit in
fields `redactions.json` cannot touch, and the ones it can touch are load-bearing
narrative that the site exists to show, so blanking them run by run would leave a
visibly gutted supplement that raises its own questions. Do three things instead,
in order. First, fix the eight items that are simply wrong on the page rather than
merely unflattering: the seven runs whose evidence-quote panel publishes an
auditor score that contradicts the score in the header (A1 to A7), and the run
whose audit rationale is the word "placeholder" (A16); a reviewer who finds any
one of these stops trusting the grades entirely, and these are the only findings
that are defects rather than disclosures. Second, run one text pass over the
exported strings rather than 44 per-run hides: strip rubric band citations, C1 to
C6 codes, auditor confidence numbers and the "a human spot-check should" closing
from audit rationales; map "sweep wall" to "session time", "the frozen rubric" to
"the rubric", "Stage-7 auditor" to "the auditor", and the schema identifiers
(`mre_config`, `match_target`, `audit_verdict.json`, `suspected_grading_error`,
`audited_h100_hours`) to plain English; add `aarch64` to the scrub and repair the
email and secret rules that are eating `Acc@22.5°` and hyphenated words. Third,
hand-rewrite the eleven claim fields that currently argue against their own pin
(A10, A11, A14, A15, A27, C2, C3) so that each states the paper's claim and
nothing else; the observation that a pin does not match its paper belongs in the
authors' own notes; the Runs table is the first thing a reviewer
reads. After that, reserve `hide_fields` for the small residue that survives:
`minimax-run-2505.18809` and `dsv4-retrain-2504.12463` for the scheduler and
shared serving job (B1, B4), `qwen3-run-2503.18430` for the self-grading note and
the serving-architecture attribution (A23, B5), `qwen3-reimplement-2506.00070` for
the judge endpoint (D1), and the four rationales that concede a mis-specified pin
or a disagreeing prior audit (A8, A9, A17, A21). One caveat the authors should
weigh before any of this: every one of these passages is true, and several are the
kind of self-criticism that earns credit if the paper raises it first. The honest
move is to put the pin-quality question in the paper's limitations in the authors'
own words, then clean the site so that a reviewer finds the argument where the
authors made it rather than assembling it from seven inconsistent run pages.
