# Project Assessment & Plan Forward

Date: 2026-06-10
Scope: full review of the vault notes, methodology LaTeX, master prompt (vault + repo
versions), reprocli source, verify app, v4 run outputs, git history, and test suite.

## What the project is

**ReproBench**: a benchmark testing whether agents can reproduce an ML paper's central
claim as released artifacts disappear and compute budgets grow — targeting the
realistic middle ground between CORE-Bench (code given, now saturated) and PaperBench
(paper-only).

Pipeline so far: NeurIPS 2025 proceedings → OpenAlex title→arXiv matching → arXiv
LaTeX + OpenReview supplements → `Mithilss/neurips-2025-paper-bundles` (3,414 papers)
→ MiniMax M2.7 on DeltaAI runs an artifact-availability classifier with a tool loop
(GitHub/HF MCP, `fetch_url`, bundle reader) → deterministic score/tier computed in
code → 500-paper v4 trial → Supabase-backed verify app for team audit → eventually a
locked 100-paper benchmark (25 per tier x 4 compute bands, 192 H100-hr cap), then the
actual reproduction agent + verification loop.

The foundation is good: the methodology doc is rigorous, score/tier moved out of the
model into code, the tool loop has sensible guards (repeat-call detection, forced
schema-constrained final pass), and the verify app's guided queue + telemetry is a
strong human-audit design. The findings below are mostly about data integrity and
what's not built yet, not about redoing anything.

## Critical findings

### 1. The corpus bug is documented but still unfixed — it gates everything

`notes/BUGS.md` records that `choose_match` (`src/reprocli_data/openalex_lookup.py:97-99`)
returns sub-threshold fuzzy matches as `batch_low_confidence` instead of dropping
them, and nothing downstream filters on `match_status`. Result: ~108 of 500 trial
papers (~22%) are *not the NeurIPS papers intended* — the wrong paper was downloaded
and analyzed. The code is unchanged as of this assessment.

The extractions are internally consistent (each record correctly describes its arXiv
ID), but the corpus claim "NeurIPS 2025" is silently ~22% wrong, and this
contamination is baked into the HF bundle dataset itself, not just the run. Until
this is fixed and the missing papers re-matched and re-run, freezing any selection
would lock in the error.

### 2. The v4 data says the Hard tier is nearly empty — the 25/25/25/25 design is at risk

Selection-tier x compute-band matrix from the 500-paper trial
(`outputs/v4/neurips_2025_minimax_m2_trial_extracted.jsonl`):

| Selection tier | 0-8 | 8-32 | 32-96 | 96-192 | >192 (OOS) | Total |
|---|---|---|---|---|---|---|
| Easy | 82 | 26 | 7 | 1 | 13 | 129 |
| Medium | 141 | 47 | 11 | 6 | 12 | 217 |
| **Hard (score 2)** | **1** | **3** | **1** | **2** | **0** | **7** |
| Hardest-Reconstructable | 39 | 17 | 7 | 12 | 6 | 81 |
| Artifact-Blocked | 37 | 9 | 5 | 6 | 7 | 64 |

Score-2 papers (code missing but weights present, or similar partial states) are only
**1.4% of the corpus**. Scaling to all 3,414 papers predicts only ~48 Hard candidates
*before* audit attrition — the methodology wants 40 audited candidates and 25
selected with specific band targets. Easy x 96-192 is similarly scarce (1 in 500).

Decision required: run the full corpus and see, redefine the Hard/Hardest boundary,
relax band targets within Hard, or supplement from ICML/ICLR 2025. The full-corpus
run is needed regardless.

### 3. 30% of rows never fully verified artifacts

70/500 rows came back `web_verification: unavailable` and 80 `partial` — those rows'
signals are partly paper-text guesses, exactly what the prompt forbids treating as
evidence. The methodology already calls for re-running low-confidence rows; that
rerun pass should be built (filter extracted JSONL for `unavailable`/`partial`/
malformed, requeue just those IDs).

### 4. H100 estimates drive selection but nobody audits them

Estimates range to 2.2M hours; the median is 4. Bands determine which papers get
selected, yet the verify app audits only the four binary signals — the methodology
itself lists "accepting model-generated H100 estimates without arithmetic checks" as
a failure mode. The verify app needs a fifth step: confirm the *band* (not the exact
number) and flag `needs_human_review` when the basis string has no auditable
arithmetic.

### 5. The selection pipeline doesn't exist in code

The methodology defines `selection_tier`, `selection_status`, eligibility filters,
band bucketing, constrained minimization, diversity guardrails, the lockfile schema,
and five release JSONL files — none of it is implemented. Next concrete deliverable:
a `reprocli_select` module that joins extracted rows with the Supabase audit export
and emits `reprobench_candidates/selected/reserve/artifact_blocked/
out_of_scope_compute.jsonl`. It is deterministic, easily testable, and unblocks the
lockfile.

## Smaller issues

- **Failing test**: `test_runtime_cleanup` fails because `run_arxiv_prompt_vllm.py:77`
  says "OpenAI-compatible" in the new `--vllm-server-url` help text. One-line fix
  (reword or whitelist).
- **Uncommitted work**: `kimi-k2-6-model` branch has modified verify_app files and
  `notes/BUGS.md` untracked; `main` is behind. Merge/clean before team members build
  on it.
- **Vault docs have drifted from the repo**: the vault Master Prompt still shows the
  old scoring (dataset weight 1, model outputs score/tier, "Hardest" tier) while the
  repo uses 2/3/1 deterministic scoring with no in-model score. Make the vault note
  point at `prompt.txt` as the single source of truth. `week1_report.md` in the vault
  is also empty (the PDF exists).
- **Stray file**: `src/data/get_premade.py` sits outside both packages.

## Plan going forward

### Now (gates everything)

1. Fix `choose_match` to drop sub-threshold matches, filter `match_status` in
   `arxiv_source_inputs.load_jobs`, emit the list of ~108 dropped NeurIPS titles,
   re-match them (arXiv API title search with author cross-check), rebuild the bundle
   dataset for the affected IDs, and rerun classification on just those papers.
2. Fix the failing test; commit and merge the branch state so the team has a clean
   baseline.

### Next (data completion)

3. Run the classifier over the **full 3,414-paper corpus** — required both for corpus
   completeness and because Hard-tier scarcity makes the 500-sample insufficient. Add
   the rerun pass for `unavailable`/`partial`/malformed rows.
4. Cheap quality multiplier since the Kimi K2.6 runner already exists: run a second
   model over (at least) a stratified subset and use *model disagreement* to
   prioritize the human-audit queue. Papers where two models agree are likely fine;
   disagreements go to reviewers first.

### Then (selection & lock)

5. Implement the selection pipeline + lockfile per the methodology, with tests.
6. Add the H100-band audit step to the verify app; have the team audit >=40
   candidates per tier, disagreement-first. Decide the Hard-tier scarcity question
   with full-corpus numbers in hand.
7. Freeze the 100-paper lockfile + 10 reserves per tier. Side benefit: the
   full-corpus artifact-blocked/out-of-scope statistics (12.8% artifact-blocked in
   the trial) are a publishable "state of NeurIPS 2025 reproducibility" result on
   their own.

### In parallel / after (the actual benchmark)

8. Start the reproduction-agent harness now on a few already-audited Easy papers
   rather than waiting for the lock — non-interactive task runner, sandboxed DeltaAI
   env, H100-hour budget metering, trace capture. This de-risks the second half
   (verification design, Ralph loop, metric-tolerance judging) and validates
   "reproducible in the first place" for the Easy tier, which is still an open TODO.
   With three people, the natural split is: audit ownership, selection-pipeline
   ownership, and agent-harness ownership.

The single highest-leverage action is item 1 — every week of audit work done on the
contaminated corpus is partially wasted effort.
