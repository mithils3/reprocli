# V4 Output Evaluation: Stronger Model vs. Filter Down?

Date: 2026-06-10
Scope: quality audit of `outputs/v4/neurips_2025_minimax_m2_trial_extracted.jsonl`
(500 papers, MiniMax M2) to decide whether reaching the 100-paper benchmark requires
a stronger classifier model or whether the existing output can be filtered down.

**Verdict: neither. The model's judgment is not the bottleneck (~1% demonstrated
error), but filtering v4 down cannot reach 100 papers either — the losses are
infrastructure failures and corpus contamination, which stack to empty out the Hard
tiers. The fix is tool hardening + rerun pass + the full-corpus run, not a stronger
model.**

## How this was measured

1. **Positive audit**: sampled 15 Easy-tier rows with `code_available=true`;
   HTTP-checked every `verified_links.code` URL.
2. **Negative audit (deterministic, full coverage)**: extracted every GitHub URL
   cited inside the `code_available` evidence text of all 131 Hard/Artifact-Blocked
   rows with `code_available=false` and HTTP-checked them; inspected resolving repos'
   contents via the GitHub API.
3. **Negative audit (sampled search)**: for 25 random negative rows, searched GitHub
   repositories for the arXiv ID in README/description (official repos almost always
   cite their arXiv ID).
4. **Contamination cross-check**: compared the `title:` in each of the 500 run
   prompts (from the trace file) against authoritative arXiv titles
   (`tools/verify_app/arxiv_meta.json`), flagging similarity < 0.75.
5. Internal-consistency profiling of all 500 rows (schema, links vs. signals,
   verification status, H100 estimates).

## Finding 1: model judgment quality is genuinely good

- **Positives**: 15/15 sampled code links resolve (HTTP 200).
- **Negatives**: across all 131 "no code" rows, exactly **1 demonstrated false
  negative** — `2510.19040` (repo `optimal-uoft/Empowering-DTs-via-Shape-Functions`,
  full code, existed since 2025-09-30). The evidence text shows the model *found* the
  URL in the paper but its GitHub tooling errored ("repo inspection returned a parse
  error"), so this is a tool failure, not a reasoning failure.
- Every other resolving URL in negative evidence was a **correct** negative on
  inspection:
  - `2510.13245` CymbaDiff — repo exists but is README-only ("will be released soon")
  - `2504.02433` OmniTalker — repo is a project page (HTML/static only)
  - `2502.01755` RoLoRA — repo exists but is literally empty (model verified this)
  - `2512.03276` vlm-two-hop — empty repo (409 "Git Repository is empty")
  - `2509.15607` — cited repos are a *different paper's* baseline code
  - `2506.01748` — LLaMA-Factory is a third-party training framework, not the
    paper's code
  - `2411.16034` VisualLens — repo has only `data_proc/`; README says "no models
    will be released" (Artifact-Blocked is defensible)
  - The model even noticed an OpenReview supplement contained the wrong paper's code.

A stronger model would re-run 3,414 papers at higher cost to fix a ~1% judgment-error
rate while leaving the actual yield-killers (below) untouched.

## Finding 2: the real losses are infrastructure and corpus, and they stack

- **30% of rows (150/500) have `web_verification` = `partial` (80) or `unavailable`
  (70)**, concentrated exactly where it hurts:

  | Tier | available | partial | unavailable | unverified % |
  |---|---|---|---|---|
  | Easy | 117 | 7 | 5 | 9% |
  | Medium | 194 | 16 | 7 | 11% |
  | Hard | 21 | 43 | 24 | **76%** |
  | Artifact-Blocked | 16 | 14 | 34 | **75%** |

  The negative signals that define the hard tiers are the least-verified ones.
- **117/500 prompts are title-mismatched** (recomputed independently from the v4
  traces; matches `notes/BUGS.md` — ~108 genuinely wrong papers, 9 harmless retitles).
- Smaller requeue list: 2 malformed rows (no extracted JSON), 29 rows claiming
  `code_available=true` with no verified code link (14 with no links at all),
  50 rows with `h100_hours_estimate = 0`.

## Finding 3: filtering v4 down cannot produce the benchmark

Keeping only clean (non-contaminated) + fully-verified (`available`) rows:

| Score/tier | 0-8 | 8-32 | 32-96 | 96-192 | >192 | Total |
|---|---|---|---|---|---|---|
| 0 Easy | 59 | 20 | 7 | **0** | 8 | 94 |
| 1 Medium | 101 | 34 | 8 | 3 | 4 | 150 |
| **2 Hard** | **0** | **0** | **0** | **0** | **0** | **0** |
| 3 Hardest-Recon | 7 | 7 | 1 | 2 | 1 | 18 |
| Artifact-Blocked | 7 | 1 | 1 | 1 | 1 | 11 |

Zero usable Hard papers, 18 Hardest-Reconstructable against a 40-candidate audit
target, and Easy x 96-192 is empty. This is corpus scarcity, not model noise — no
filter on 500 rows fixes it.

## Recommended path to 100 papers

1. **Fix the corpus bug first** (`choose_match` drops sub-threshold matches,
   re-match the ~108, rebuild bundles) — still gates everything.
2. **Harden the tool loop instead of upgrading the model**: retry/fallback on GitHub
   API errors, plus a deterministic code-level backstop — extract any artifact URL
   the paper text mentions and HTTP-check it outside the LLM. (The negative audit
   above *is* that check; it runs in minutes and caught the only false negative.)
3. **Requeue the union of**: 150 partial/unavailable, 2 malformed, 29
   code-true-without-link, 50 zero-estimate rows (~190 rows, heavily overlapping).
4. **Run the full 3,414-paper corpus with the same MiniMax setup.** Scaled estimates
   from clean+verified rates: Hardest-Recon ≈ 120 candidates corpus-wide (more after
   the rerun pass) — workable. **Score-2 Hard ≈ 48 raw candidates corpus-wide before
   any attrition** — the 25-target is likely unreachable as defined; that is a
   tier-boundary / ICML-ICLR-supplement decision, not a model decision.
5. Optional quality multiplier (already planned in `notes/ASSESSMENT.md`): the Kimi
   K2.6 runner as a *second opinion* for disagreement-first audit ordering — not as
   a replacement for M2.
