# ReproBench Audit Rubric (v1)

Generic, paper-agnostic rubric an LLM auditor applies to ONE agent reproduction
attempt. The auditor is given (a) the paper's central claim + reference number(s)
and (b) the agent's full run bundle (code it wrote, commands, stdout/stderr,
output files, env). It instantiates this rubric for the specific paper, grades
each criterion **from cited evidence in the bundle**, and returns the structured
0-5 score (+ evidence) in `audit_schema.py`. The coarse verdict is DERIVED from
the score downstream — you only assign the score.

The auditor NEVER trusts a number just because the agent printed it. Every graded
quantity must be traced to *how it was produced* in the run.

## Prior

Default to a **low score**. A high score requires positive, cited evidence that
clears the criteria below. Absence of evidence is a low score, not a pass.

## Criteria

### C1 — Target identified
**If the record supplies a pinned `match_bar`**, adopt it verbatim as the bar — it
is the frozen lockfile target (`kind`, `op`, `reference_value`, `tolerance`) and
echo it into your `op`/`reference_value`/`tolerance`. The resolution steps below
apply only when no `match_bar` is given (older rows, or `kind` = "none").

Restate the central claim as a checkable target. Prefer a **scalar target** when
the claim has one: metric, reference value(s), dataset/split, model/config, and
what counts as a match (op + tolerance). The match bar is usually left **implicit**
— most claims pin a value but not how close counts (`~25.76`, `≈ 39%`, "improves to
~65–70"). When the paper states a bar, use it: an explicit margin ("within 1%" →
`tolerance` = 0.01), or a threshold (`ACC ≥ 85` → `op` = `>=`, `tolerance` = null,
the bar is the threshold). **When no bar is stated for a scalar point estimate,
default to a ±5% relative tolerance**: `op` = `abs_rel_within`, `tolerance` = 0.05
against `reference_value`. This default is the *starting* bar — note in the
rationale if the claim's own precision clearly warrants a tighter or looser one.
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
  (e.g. train not test; 7B when the claim is 1.5B; public split not the sealed one).
- **cherry-picked metric** — reports an easier sibling metric, not the central claim.
- **stale artifact** — number read from a shipped `result*/metrics*` file the agent
  did not regenerate this run.
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

## Score scale (0–5)

Assign one integer. Each level is an anchor; pick the highest whose conditions
are fully met by cited evidence.

- **5 — Faithful reproduction.** Right experiment, executed, result meets the C1
  criterion (scalar within tolerance, or the relation/property clearly holds),
  clean provenance (no flags), correct protocol/split/scale.
- **4 — Reproduced, minor deviations.** Central claim clearly supported; value
  within a slightly loose margin (or the relation holds with a minor caveat), or a
  single low-severity caveat.
- **3 — Partial.** Right experiment executed, but the result falls just short of
  the C1 criterion (scalar close yet outside tolerance, or the relation holds only
  weakly/partially), or only some of a multi-metric/multi-arm claim is met.
- **2 — Weak attempt.** Executed, but the value is substantially off or there is a
  significant (non-cheating) methodological deviation.
- **1 — Off-target / failed.** Code ran but did not address the claim's experiment
  (wrong task/benchmark) or crashed before producing the metric.
- **0 — Unverifiable or disqualified.** No execution evidence, no checkable target
  at all (neither a re-scorable scalar nor a verifiable relation), bundle too thin,
  OR a HIGH-severity anti-cheat flag. Cheating is 0.

Downstream, score ≥ 4 counts as a reproduction; 3 → partial; 0 with no execution
→ unverifiable; everything else → not reproduced. You assign only the score.

Always emit: the restated target, measured value + citation, every flag with
evidence, the score, a 0–1 confidence, and a one-paragraph rationale. The score
must be reconstructable from the cited evidence alone.
