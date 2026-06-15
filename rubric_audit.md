# ReproBench Audit Rubric (v1)

Generic, paper-agnostic rubric an LLM auditor applies to ONE agent reproduction
attempt. The auditor is given (a) the paper's central claim + reference number(s)
and (b) the agent's full run bundle (code it wrote, commands, stdout/stderr,
output files, env). It instantiates this rubric for the specific paper, grades
each criterion **from cited evidence in the bundle**, and returns the structured
verdict in `audit_schema.py`.

The auditor NEVER trusts a number just because the agent printed it. Every graded
quantity must be traced to *how it was produced* in the run.

## Prior

Default to **not_reproduced / unverifiable**. A claim is only `reproduced` when
positive, cited evidence clears every criterion below. Absence of evidence is a
fail, not a pass.

## Criteria

### C1 — Target identified
Restate the central claim as a checkable target: metric, reference value(s),
dataset/split, model/config, and what counts as a match (op + tolerance). If the
claim has no re-scorable scalar, mark `unverifiable` and stop.

### C2 — Execution verified
Find evidence the agent actually *ran code that computed the metric*: training/eval
logs, non-trivial runtime, output files created during the run, library/version
banners. A number that appears only as an assertion, a comment, or prose — with no
execution trace — fails C2 → verdict `unverifiable`. Cite the evidence.

### C3 — Measured value located
Find the agent's reproduced value for the C1 metric. Cite the exact file + line or
log snippet. If several candidates exist, pick the one matching the claim's
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
Any HIGH-severity flag caps the verdict at `not_reproduced` regardless of value match.

### C5 — Value matches claim
Apply the C1 op/tolerance to (measured, reference). Report the comparison
explicitly. A match here only counts if C2–C4 are clean.

### C6 — Methodological fidelity
Did the run reproduce the *actual experiment* of the claim (right benchmark,
protocol, ablation arm)? Note deviations even when the number matches.

## Verdict mapping
- `reproduced` — C2 execution clean, C4 no high flag, C5 within tolerance, C6 faithful.
- `partial` — executed and on the right experiment, but value off / minor flag /
  only some of a multi-metric claim met.
- `not_reproduced` — executed but value misses, or a high anti-cheat flag.
- `unverifiable` — no execution evidence, no re-scorable scalar, or bundle too thin.

Always emit: the restated target, measured value + citation, every flag with
evidence, and a one-paragraph rationale. The verdict must be reconstructable from
the cited evidence alone.
