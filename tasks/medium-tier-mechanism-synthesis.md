# Prompt: medium-tier mechanism synthesis

Paste this prompt to an Opus agent (or run it as a session) to produce the medium-tier
counterpart of `notes/Analysis/2026-08-11 Mechanism Synthesis (easy tier, cross-model).md`.

---

You are synthesizing ReproBench medium-tier results across models, mechanism-first.

GROUND TRUTH. The frozen eval-100 dataset is host-probed by the benchmark owner: every
artifact is retrievable. There are no availability walls in the dataset. Any run that
reported an artifact as unreleased, unavailable, or a wall reflects the agent failing to
locate, retrieve, or correctly use released artifacts. Attribute every run-level failure
to the agent. The central question is why agents cannot reproduce papers.

INPUTS.
- Sweeps: DeepSeek-V4-Flash `slurm-2896059`, MiniMax-M2.7 `slurm-2690187`,
  Qwen3.6-27B `slurm-2698678` (+ its continuation `slurm-2759663`).
- Fresh metadata: `source <(grep -E 'SUPABASE_SERVICE_KEY' ~/.bashrc)` then
  `python3 .claude/skills/analyze-sweep/driver.py --batch <id> --out ~/sweeps/<id>`
  (add `--no-events` if you only need scores). Exclude `status=running` rows.
- Use `audit_score`/`audit_verdict` only where `audit_model` is `claude-sonnet-5`.
  If a sweep's rows carry another audit_model, say so and hold that sweep out of the
  headline table rather than mixing graders (2896059 was self-graded as of 08-09;
  check whether a pinned re-audit has landed).
- Per-run dissections: the rewritten analyses JSONs in `notes/Analysis/`
  (`medium-sweep-2690187-minimax-analyses.json`, `medium-sweep-2698678-qwen3-analyses.json`,
  `medium-sweep-2896059-dsv4-analyses.json`), post the 2026-08-11 narrative rewrite.

DIRECTIVES.
1. No wall narrative anywhere. No availability-wall labels, no unavailability prose.
   Relabel any residue from the run's own evidence to an agent-side mechanism.
2. Claimed and audited counts are background data. One factual line each, no honesty
   framing, no claim-gap section.
3. Mechanism-first synthesis. Use the seven easy-tier mechanisms as the template
   (validation discipline, shipped-code defects, artifact provenance, protocol
   reconstruction, compute non-bindingness, report serialization, environment
   adaptation). For each: does it appear on medium, with what per-model counts, and
   what is the single strongest transcript-cited example. Name any genuinely new
   medium-tier mechanism with evidence from at least two runs.
4. Group every number by budget band within the tier. Never average across bands.
5. Keep all audit scores, verdicts, and flags exactly as stored. Never edit raw dumps.

OUTPUT.
- Vault note `notes/Analysis/<date> Mechanism Synthesis (medium tier, cross-model).md`
  mirroring the easy-tier note's structure: provenance block, headline table
  (model, n, mean audit score, audited reproduced), the mechanisms, stability if
  measurable, a short "For the paper" close.
- House register: plain declaratives, no em dashes, no contrast frames.
- Single-file additive write into the vault. Do not run git in `notes/`.
- Reply with the headline table and the per-mechanism one-liners.
