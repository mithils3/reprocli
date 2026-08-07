---
name: analyze-sweep
description: Analyze a repro-agent sweep (sbatch batch) from Supabase — dump runs and event transcripts, fan out Sonnet subagents for per-run dissection, and write a paper-facing report into the notes vault. Use when asked to "analyze this sbatch/sweep", compute average audit score, or dissect model failures for the results section.
---

# Analyze a sweep (Supabase run dump → subagent dissection → vault report)

Paths are relative to the repo root. The driver is read-only against the
run-viewer Supabase project (`repro_runs` / `repro_events` / `repro_tags`).

## Prerequisites

The service key lives in `~/.bashrc` (do NOT source the whole bashrc):

```bash
source <(grep -E 'SUPABASE_SERVICE_KEY' ~/.bashrc)
```

## 1. Find the batch

```bash
python3 .claude/skills/analyze-sweep/driver.py --list
```

One line per `batch_id` (e.g. `slurm-2672018  repro_hard_qwen3 #2672018  finished=30, running=3 ...`).
If the user says "the latest sbatch", it is the newest `slurm-*` batch here.

## 2. Dump it

```bash
source <(grep -E 'SUPABASE_SERVICE_KEY' ~/.bashrc)
python3 .claude/skills/analyze-sweep/driver.py --batch slurm-2672018 --out "$SCRATCHPAD/sweep-2672018"
```

Runs with `status=running` are **excluded by default** (add `--include-running`
to keep them; usually you should not — their scores are NULL). Output:

- `runs.json` — full `repro_runs` rows (audit_score, audit_verdict, audit_rationale,
  audit_flags, exit_reason, spent_h100/budget, tokens, gpu_util_*).
- `events/<run_id>.jsonl` — the complete ordered transcript per run
  (`round_open`/`call_start`/`call_result`/`final`; stdout capped by the sink).
- `aggregates.json` + `SUMMARY.md` — mean audit score (overall and per budget
  band), verdict/exit-reason counts, cheat-flag count, spend totals, per-run table.

`--no-events` gives a fast metadata-only dump when you just need the numbers.

## 3. Fan out Sonnet subagents

Split the runs into groups of ~5 and launch one **`model: sonnet`** Agent per
group, all in a single message so they run concurrently. Each agent prompt must
include: its run_ids, the dump paths (`runs.json` entry + `events/<run_id>.jsonl`),
and ask for a per-run dissection:

- what the paper needed (code/weights/data availability) and what the agent found;
- timeline of what the agent actually did (cite round numbers, quote key events);
- failure-mode classification — use the standing taxonomy (reimplement-without-
  validating, availability wall, environment fights, procrastination/wall-kill,
  killed-before-the-number) but let agents propose new modes with evidence;
- self-claim vs audit verdict (read the `final` event's report vs `audit_verdict`
  and `audit_rationale`) — this feeds the self-claim-gap finding;
- for `disqualified` runs: which `audit_flags` fired and whether the flag looks
  legitimate from the transcript (auditor false-positives are paper-relevant);
- compute behavior: `spent_h100` vs band, GPU util fields, idle-allocation waste.

Collect every subagent's dissections into one **`analyses.json`** (a JSON array,
one object per run) so step 5 can publish it. The website + `upload.py` read this
shape per object: `run_id`, `arxiv_id`, `paper_gist`, `target_claim`,
`failure_mode` (+ `failure_mode_detail`), `artifact_availability`,
`genuine_wall{is_wall,what}`, `agent_trajectory_summary`,
`agent_final_selfclaim{claimed_outcome,claimed_numbers,honest_about_failure}`,
`self_claim_gap`, `audit_summary{score,verdict,cheat_flags[],rationale_gist}`,
`suspected_grading_error`, `compute_pattern`, `notable_insights[]`,
`evidence_quotes[{round,quote}]`.

## 4. Synthesize the report

Write the report to `notes/Analysis/Repro-Agent Runs/` (one file per sweep,
date-prefixed, e.g. `2026-07-20 Hard Sweep 2672018.md`). It must contain:

- headline numbers: mean audit score overall and **per budget band** (8h/32h/96h),
  verdict counts, disqualification rate, reproduced count;
- failure-mode table with per-run assignments and counts;
- self-claim gap: claimed-success vs audited-success counts;
- compute: spent vs budgeted H100-h, utilization, waste patterns;
- novel insights section — anything not already in the standing taxonomy;
- a "caveats for the paper" section (pre/post-freeze status — dataset froze
  2026-07-13; rubric froze 2026-07-16 — auditor model, self-grading confounds).

Commit the repo-side changes; the vault has its own git (never `git add -A`
from `notes/`).

## 5. Publish to the website (Analysis tab)

`upload.py` pushes the sweep to the run viewer's **Analysis** tab
(https://agent-logs.vercel.app/) so each paper's dissection is browsable,
searchable and copyable — the same content the PDF carries, rendered in-theme. It
upserts one `repro_sweeps` header row + one `repro_analyses` row per paper (both
anon-readable) and stores the source PDF in the public `repro-analyses` bucket.

One-time (creates the tables + bucket): apply the schema once —
`SUPABASE_ACCESS_TOKEN=... python3 tools/run_viewer/setup_db.py`.

Per sweep (needs the **service key**, not the PAT):

```bash
source <(grep -E 'SUPABASE_SERVICE_KEY' ~/.bashrc)
python3 .claude/skills/analyze-sweep/upload.py \
  --slug hard-2672018 --title "Qwen3.6-27B Hard-Tier Dissection" \
  --subtitle "sweep 2672018 · post-freeze" --tier Hard --frozen \
  --batch-id slurm-2672018 \
  --runs "$OUT/runs.json" --analyses "$OUT/analyses.json" \
  --pdf "notes/Analysis/Repro-Agent Runs/<report>.pdf"
```

- `--frozen` marks a post-freeze (paper-eligible) sweep; omit for pre-freeze
  process-validation runs — the report page shows the right caveat banner either way.
- Aggregates (per-band means, verdict + failure-mode counts, self-claim gap,
  compute) are computed from `runs.json` + `analyses.json`; nothing to precompute.
- Idempotent: re-runs upsert on `slug` / `run_id` and the PDF overwrites. Add
  `--dry-run` to preview without writing.
- The viewer reads live (anon), so a new sweep needs **no redeploy**. Only redeploy
  when you change the front-end itself: `cd tools/run_viewer/public && vercel --prod`.

## Gotchas

- `run_id` prefixes are **not** the batch id — a requeued sbatch keeps the old
  job id in run_ids (e.g. `2666353-*` rows belong to batch `slurm-2672018`).
  Always select by `batch_id`, never by run_id prefix.
- `audit_score` is the **capped** score: a high cheat flag zeroes it and sets
  `verdict=disqualified`; the pre-cap value is in `audit_reported_score`
  (often NULL when the cap didn't fire). Report both.
- Budget bands differ **within** one sweep (hard tier mixes 8/32/96 H100-h);
  never average spend or score without grouping by `budget`.
- `spent_h100` includes allocation-hold, not just productive compute — per-call
  `cost_h100` in events sums to less than `spent_h100`.
- The login-node DNS is flaky on DeltaAI; this driver is meant to run on the
  local workstation, not the cluster.

## Troubleshooting

- `SUPABASE_SERVICE_KEY not set` → run the `source <(grep ...)` line above.
- Empty result for a batch → wrong id; run `--list` (batch_id is `slurm-<jobid>`
  of the *original* submission, see Gotchas).
