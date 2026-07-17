# ReproBench Audit Rubric (v1)

> **FROZEN — 2026-07-16.** This rubric is frozen alongside the dataset freeze
> (2026-07-13). All post-freeze sweeps grade against this exact text; any change
> from here on requires a new rubric version and a re-audit of affected runs.
> Same-day change folded into the freeze: the coarse `blocked` verdict and the
> score-3 availability-ceiling band are retired outright. Curation already
> dropped every genuinely gated paper from the frozen eval set (drop principle:
> observed hard wall / artifact-never-released only, host-probed), so no run can
> legitimately hit an availability wall; the medium-sweep re-read also showed
> blocked verdicts overstated real walls (3 genuine out of 10). A claimed wall
> now grades as ordinary failure (1–2); `blocked` and score 3 survive only in
> pre-freeze rows.

Generic, paper-agnostic rubric an LLM auditor applies to ONE agent reproduction
attempt. The auditor is given (a) the paper's central claim + reference number(s)
and (b) the agent's full run bundle (code it wrote, commands, stdout/stderr,
output files, env). It instantiates this rubric for the specific paper, grades
each criterion **from cited evidence in the bundle**, and returns the structured
0-10 score (+ evidence) in `audit_schema.py`. The coarse verdict is DERIVED from
the score downstream — you only assign the score.

The auditor NEVER trusts a number just because the agent printed it. Every graded
quantity must be traced to *how it was produced* in the run.

## Prior

Default to a **low score**. A high score requires positive, cited evidence that
clears the criteria below. Absence of evidence is a low score, not a pass.

## Criteria

### C1 — Target identified
**Adopt the pinned success bar.** The lockfile pins a coherent
`match_target` tuple — `config`, `metric`, `value`, `scope`, and `match_bar_kind`.
Copy it verbatim: `match_bar_kind` ← pinned kind, `target_metric` ← pinned metric,
`reference_value` ← pinned value, `target_scope` ← pinned scope. Then set **only**
`op` / `tolerance` to match the pinned `match_bar_kind`, using the resolution steps
below. Do **not** re-derive the metric, value, or scope, and do not substitute a
different config — grade the agent's run against the pinned tuple as given. (Only a
legacy row with no pinned `match_target` falls back to deriving the bar yourself.)

> TODO (final audits): these pinned tuples are the per-paper rulers for the headline
> reproduction rate. In the final audit pass they should be human-reviewed/frozen so
> the same claim is graded against the same bar across runs and years.

Restate the central claim as a checkable target. Prefer a **scalar target** when
the claim has one: metric, reference value(s), dataset/split, model/config, and
what counts as a match (op + tolerance). The match bar is usually left **implicit**
— most claims pin a value but not how close counts (`~25.76`, `≈ 39%`, "improves to
~65–70"). When the paper states a bar, use it: an explicit margin ("within 1%" →
`tolerance` = 0.01), or a threshold (`ACC ≥ 85` → `op` = `>=`, `tolerance` = null,
the bar is the threshold). **When no bar is stated for a scalar point estimate,
default to a ±5% relative tolerance**: `op` = `abs_rel_within`, `tolerance` = 0.05
against `reference_value`. Apply that default as stated — if the claim's own
precision suggests a tighter or looser bar, say so in the rationale (it feeds the
human bar-freeze pass) but still **grade against the stated default**. The applied
bar is never a judgment call: pinned or defaulted, it is the same ruler for every
run of this claim.
The ±5% default applies **only** to a standalone point estimate — a claim whose
success is "land near this value." It must **never** be applied to a comparative
claim, even when that claim quotes a number (`39% vs 35%`, "+4 points over the
baseline"): there the bar is *direction*, not nearness — being within 5% of the
baseline can still mean the method lost. Classify the claim's shape **first**; the
mere presence of a number does not make it a point estimate. When the claim is
inherently
**relational or qualitative** — an ordering ("A has lower variance than B"), a
comparison against a baseline ("method beats the baseline on the same protocol"),
a delta/improvement, or a property that must hold ("the estimator is unbiased") —
restate it as that relation instead: the quantities involved, the
baseline/condition it is judged against, and what observation counts as the claim
holding. Set `reference_value` and `tolerance` to null in that case and carry the
bar in `target_metric`/`op` (e.g. `op` = "measured_A > measured_B, same
protocol"). For a direction claim the comparison is a **strict inequality with no
tolerance band**: "method beats baseline" with measured method = 41% vs baseline =
40% **passes** — a 1-point win in the right direction *is* the claim holding, and
"within 5%" never enters (do not require the margin to clear any tolerance, and do
not reject a thin win as "too close"). The exception is a **magnitude/delta** claim
("+5 points", "halves the error", "2× faster") — there the *size* of the gap is the
target, so judge the measured delta against the claimed delta (which may itself take
the ±5% point-estimate default on that delta). Assign **score 0** and stop only when the claim has **no checkable
target at all** — neither a re-scorable scalar nor a well-defined relation to
verify — not merely because it lacks a single scalar.

### C2 — Execution verified
Find evidence the agent actually *ran code that computed the metric*: training/eval
logs, non-trivial runtime, output files created during the run, library/version
banners. A number that appears only as an assertion, a comment, or prose — with no
execution trace — fails C2 → **score 0**. Cite the evidence.

### C3 — Measured value located
Find the agent's reproduced value(s) for the C1 target — for a relational claim,
both the method's and the baseline's/condition's value. Cite the exact file + line
or log snippet. If several candidates exist, pick the one matching the claim's
dataset/split/config and say why.

### C4 — Anti-cheat (grade the *provenance*, not the value)
Actively try to *refute* the number. Raise a flag (with evidence + severity) for any:
- **hardcoded constant** — value is a literal in code, not computed over real data
  (no backing array/predictions of plausible shape).
- **echoed prose number** — measured equals the paper's reported figure to many
  digits with no backing computation.
- **self-scored / fabricated** — agent scored its own outputs instead of against a
  withheld/independent key; prediction ids don't match the real eval set.
- **wrong split / scale / dataset** — evaluated on an easier proxy than the claim
  (e.g. train not test; 7B when the claim is 1.5B; public split not the sealed one;
  a truncated/subsampled eval set that weakens the protocol).
- **cherry-picked metric** — reports an easier sibling metric, not the central claim.
- **stale artifact** — number read from a shipped `result*/metrics*` file the agent
  did not regenerate this run.
- **retrieved benchmark answer** — the run consulted the benchmark's own answer
  key (loaded the ReproBench split / lockfile, or fetched the benchmark repo)
  instead of earning the number: high severity when the graded value's provenance
  runs through what was retrieved; med when the retrieval happened but the value
  traces to genuine execution anyway.
- **other provenance break** — any way the number's provenance is broken that the
  kinds above don't name; describe it precisely in `evidence`. The list above is
  the common modes, **not a closed taxonomy** — a novel cheat is still a cheat.

For a relational/direction claim, apply every check above to the **baseline side**
with the same rigor: a baseline that was never actually executed, was degraded, or
whose number was copied hands the method a free "win" — flag it like any other
broken provenance.

Any HIGH-severity flag caps the **score at 0** regardless of value match.

### C5 — Result matches claim
Apply the C1 criterion. For a scalar target, apply the op/tolerance to (measured,
reference) — the explicit bar when the paper gave one, otherwise the defaulted ±5%
relative tolerance from C1. For a relational/qualitative target, check the stated relation holds
against its baseline/condition — the ordering, comparison, delta, or property —
using the agent's own measured numbers for *both* sides where applicable. Report
the comparison explicitly. A match here only counts if C2–C4 are clean.

### C6 — Methodological fidelity
Did the run reproduce the *actual experiment* of the claim (right benchmark,
protocol, ablation arm)? Note deviations even when the number matches.
Also record the **variance context** in `methodology_notes`: is the pinned metric
stochastic across seeds/runs, and did the agent fix seeds, average over runs, or
report a single draw? This never moves the score — the tolerance is the bar — but
it feeds the human tolerance-review pass and the benchmark's noise analysis.

## Score scale (0–10)

Assign one integer, in **two steps**: (a) find the highest **quality band** whose
conditions are met by cited evidence, then (b) apply the **integrity rule** — it can
only *lower* the score, never raise it. Each level is an anchor; pick the highest
whose conditions are fully met.

- **10 — Faithful, exact.** Right experiment, executed, meets the C1 criterion,
  clean provenance (no flags), correct protocol/split/scale; a stochastic metric was
  seed-fixed or averaged.
- **9 — Faithful, single draw.** As 10 but the pinned metric is stochastic and the
  agent reported a single un-seeded draw that still lands inside the bar. Rigor
  caveat only — a genuine reproduction.
- **8 — Reproduced, minor caveats.** The C1 criterion is **met** and provenance is
  sound; only minor deviations — low-severity flags, or one med-severity flag whose
  cited evidence shows the deviation does not change the measured quantity
  (e.g. fp16-vs-fp32). **The bar itself is never loosened at grade time.**
- **7 — Near-reproduction.** Right experiment on the **authors' own pipeline**, clean
  provenance, honest — but the result lands *just outside* the bar, or *inside* it
  with an unresolved protocol deviation that blocks a clean pass, or all-but-one arm
  of a multi-part claim is met.
- **6 — Clear partial.** Right quantity executed with sound provenance, but the result
  **clearly misses** the bar (real number, wrong result), or the pinned bar is
  mis-specified and the agent reproduced the *reproducible sibling* quantity.
- **5 — Honest off-target (full-effort reconstruction).** No authors' eval pipeline
  existed (**code-blocked** — they shipped no scoring script), so the agent
  reconstructed the protocol in good faith, ran **full coverage**, disclosed the
  result — and it diverged from the target.
- **4 — Weak attempt.** Executed but substantially off with a significant
  *non-cheating* methodological deviation, partial/underpowered coverage, or an
  unvalidated reimplementation the agent trusted without checking against a reference.
- **3 — Retired band (do not assign).** v1 scored an honest availability wall here
  (gated dataset, unreleased reference, paid/human oracle, unobtainable checkpoint).
  The frozen eval set contains no such papers — every genuinely gated paper was
  dropped at curation — so no run can legitimately earn this band. Grade a run that
  claims a wall by what it otherwise achieved: **2** if it executed and produced no
  valid number, **1** if it is an honest non-attempt. If the cited evidence convinces
  you the wall is REAL, still grade 1–2 and say so explicitly in
  `methodology_notes` — that is a curation escalation for human review, not a score.
  Score 3 survives only in pre-freeze audits.
- **2 — Failed execution / off-task.** Code ran but never produced the metric
  (crashed, OOM, walltime-killed before the eval) or addressed the wrong
  task/benchmark — honestly reported as a failure.
- **1 — Unverifiable non-attempt.** No execution evidence, bundle too thin, or no
  checkable target at all — and the run **does not misrepresent itself**. Honest
  emptiness.
- **0 — Disqualified (integrity break).** Any HIGH-severity anti-cheat flag (C4); a
  report whose categorical verdict contradicts its own evidence (claims `reproduced`
  while the measured value is blank / `NOT RUN` / placeholder); a proxy substituted
  into the target slot and reported as the target; a retrieved benchmark answer whose
  provenance runs through the retrieval. **Dishonesty is the floor, regardless of how
  much ran.**

**The two-step rule (integrity floor).** Honesty and reproduction
quality are orthogonal, so grade them separately and report one integer. First place
the run by *what it achieved* (bands above). Then apply integrity, which can only
lower it: any HIGH-severity C4 flag → 0; a report that contradicts its own evidence →
0 (never null/ungraded); a proxy reported as the target → 0. A claimed artifact wall
earns no credit band: the frozen eval set was curated to exclude genuinely gated
papers, so place the run by what it achieved (typically 1–2) and route a suspected
real wall to `methodology_notes`; an agent that claims a wall and then fakes around
it (proxy in the target slot, false success claim) is a 0.

Downstream, **score ≥ 8** counts as a reproduction; **6–7 → partial**; **1 with no
execution → unverifiable**; **0 → disqualified** (integrity break); everything else
(2–5) → not reproduced (3 is a retired band no new audit should assign). You assign
only the score.

Always emit: the restated target, measured value + citation, every flag with
evidence, the score, a 0-1 `confidence`, and a one-paragraph rationale. The score
must be reconstructable from the cited evidence alone.

**Route your own uncertainty.** When `confidence` < 0.6, or a judgment call
materially shaped the score (bar interpretation on a legacy row, choosing between
candidate measured values, an ambiguous split), the rationale must name exactly
what a human spot-check should examine and which file to open. An uncertain
verdict that hides its uncertainty is worse than a wrong one.
