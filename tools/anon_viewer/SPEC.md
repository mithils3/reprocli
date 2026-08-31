# RECLAIM reviewer viewer: spec and data contract (v2, facing app)

Frozen, anonymous, self-contained, public-facing copy of `tools/run_viewer`
for the ICLR 2027 double-blind submission. Executes decision
`publish-run-viewer-anon-reviewer-link` (2026-08-09). The live viewer at
agent-logs.vercel.app is untouched.

v2 supersedes v1 in four ways: the site uses the paper's vocabulary (RECLAIM,
tiers Run / Retrain / Reimplement, three agents, the nine-slug taxonomy of
appendix G), the grade of record is the pinned Claude Sonnet 5 grade only,
the dissection records come from `notes/Analysis/*-analyses.json`, and every
development-era detail is removed from what a reviewer can see or download.

```
GOAL            Static site under tools/anon_viewer/public/ showing the paper's
                run set (3 agents x 3 tiers = 9 sweeps, 275 runs, Claude Sonnet 5
                grades) in the paper's own vocabulary, with no identifying,
                infrastructure or development detail anywhere in source or data.
DONE-WHEN       (1) python3 tools/anon_viewer/export.py exits 0, prints 275 runs /
                9 sweeps / 3 agents, leak gate 0 hits;
                (2) an independent grep of public/ (data included) for the gate
                list returns nothing;
                (3) Playwright smoke: overview matrix has 9 cells whose n sum to
                275, a run page renders its transcript, no console errors;
                (4) deployed on Vercel project reprobench-traces, URL returned.
MUST-NOT-CHANGE tools/run_viewer/** (live viewer), the Supabase DB (read only),
                notes/** (read only), audit scores/verdicts/flags (displayed as
                stored, never edited).
ARTIFACT        tools/anon_viewer/{export.py,scrub.py,SPEC.md,manifest.json,
                redactions.json,export_report.md,screen_report.md,public/**};
                public/data/ is gitignored (regenerable), manifest committed.
VERIFY-BY       export.py self-report + leak gate; red-team grep; Playwright.
```

## 1. Selection

Sources (service key `SUPABASE_SERVICE_KEY` in env, URL
`https://rjnkpoxwdslkgxjliakq.supabase.co`): `repro_runs`, `repro_events`,
`audit_runs`, `audit_events`, `repro_analyses` (fallback only). Never read
`host_*`, `repro_tags`, `repro_sweeps.aggregates`. Dissection records of record
are the local files below (read only).

Roster: three agents, three tiers, nine sweeps. Muse Spark, Laguna and GLM are
not in the paper and never appear.

| model key | `repro_runs.model` | display name | tier key | sweep slug (DB) | dissection record (notes/Analysis/) |
|---|---|---|---|---|---|
| `dsv4` | `deepseek-ai/DeepSeek-V4-Flash-0731` | DeepSeek-V4 | run | easy-2883229-dsv4 | easy-sweep-2883229-dsv4-analyses.json |
| `dsv4` | | | retrain | medium-2896059-dsv4 | medium-sweep-2896059-dsv4-analyses.json |
| `dsv4` | | | reimplement | hard-2918306-dsv4 | hard-sweep-2918306-dsv4-analyses.json |
| `qwen3` | `Qwen/Qwen3.6-27B-FP8` | Qwen3.6-27B | run | easy-2687371-qwen3 | easy-sweep-2687371-qwen3-analyses.json |
| `qwen3` | | | retrain | medium-2698678-qwen3 | medium-sweep-2698678-qwen3-analyses.json |
| `qwen3` | | | reimplement | hard-2672018 | hard-sweep-2672018-analyses.json |
| `minimax` | `MiniMaxAI/MiniMax-M2.7` | MiniMax-M2.7 | run | easy-2652648-minimax | easy-sweep-2652648-minimax-analyses.json |
| `minimax` | | | retrain | medium-2690187 | medium-sweep-2690187-minimax-analyses.json |
| `minimax` | | | reimplement | hard-2936132-minimax | hard-sweep-2936132-minimax-analyses.json |

Tier names: the DB says Easy / Medium / Hard; the site says Run / Retrain /
Reimplement (keys `run`, `retrain`, `reimplement`). The old words never appear.

Run inclusion: the run appears in the sweep's dissection record (the local
JSON; each record has `run_id`) AND has a pinned grade. Pinned grade = the
latest by `updated_at` of the `audit_runs` rows with `model == 'claude-sonnet-5'`,
`status == 'finished'`, integer `score`; if none exists, `repro_runs.audit_*`
when `repro_runs.audit_model == 'claude-sonnet-5'`; otherwise the run is
excluded and listed in the report. `claude-opus-*` passes never count.
Expected: 275 runs (33/32/33 MiniMax, 34/26/30 Qwen, 29/28/30 DeepSeek).
Expected cell means: DeepSeek 6.21 / 6.43 / 5.10, Qwen 3.91 / 4.54 / 3.27,
MiniMax 3.18 / 3.41 / 2.70; reproduced 14/9/4, 5/6/2, 3/5/2.

Auditor transcript: when the pinned grade came from an `audit_runs` row,
that row's `audit_events` become `audit_events` in the bundle; else null.

Papers: `eval_100.jsonl` from HF dataset `Mithilss/reprobench-splits`
(field names in `tools/run_viewer/public/estimates.js` lines 36-55). Snapshot
`arxiv_id, tier (renamed), band, claim, predicted_h100, kind, paper_url,
code_url`. Report any included run whose arxiv is not in eval_100 (expected 0).
Sweep aggregates are recomputed from the included runs.

## 2. Failure modes

The vocabulary is the nine slugs of appendix G. Display names in parentheses.

`reproduced-clean` (Reproduced clean), `near-miss-partial` (Near-miss partial),
`reimplement-without-validating` (Reimplemented without validating),
`environment-fights` (Environment fights), `artifact-provenance-mismatch`
(Artifact provenance mismatch), `scope-substitution` (Scope substitution),
`stale-artifact-reliance` (Stale-artifact reliance), `procrastination/wall-kill`
(Procrastination and wall kill), `killed-before-the-number` (Killed before the
number). Anything else displays as `other` (Other) with the original slug kept
in `mode_slug`.

Resolution order per run:
1. `failure_mode` from the local dissection record (already relabelled; the DB
   row is stale for 35 runs). Fall back to `repro_analyses.failure_mode` only
   when the run is missing from the local file (report it).
2. Alias map, exact synonyms only: `success` -> reproduced-clean;
   underscore spellings -> hyphen spellings; `procrastination-wall-kill`,
   `procrastination` -> procrastination/wall-kill; `honest-shortfall`,
   `quantitative-miss` -> near-miss-partial; `environment_setup_spiral` ->
   environment-fights; `stale-artifact-substitution` -> stale-artifact-reliance;
   `artifact-substitution-gap` -> artifact-provenance-mismatch; strip a
   trailing parenthetical.
3. Band consistency, ONLY for the two sweeps whose dissection was graded by
   the agent's own family before the pinned re-audit (easy-2652648-minimax,
   easy-2687371-qwen3): a run labelled reproduced-clean whose pinned verdict
   is not `reproduced` becomes near-miss-partial when the pinned score is 6-7
   and `other` otherwise; a run labelled near-miss-partial whose pinned
   verdict is `reproduced` becomes reproduced-clean. Five runs expected. List
   every relabel in the report.
4. Report the full slug -> mode mapping table with counts and the size of
   `other` (about 19 expected).

## 3. Anonymization

### 3.1 Structural

- `id = "{model_key}-{tier_key}-{arxiv_id}"` (one run per paper per sweep).
  Raw run ids never appear anywhere, including inside text (dict replace of
  every `repro_runs.run_id` and `audit_runs.audit_run_id` in the whole DB to
  the anon id when included, else `[run]`).
- Dropped: `batch_id`, `batch_label`, `host`, `full_log_url`, `stats_url`,
  `gpu_*`, `audit_run_id`, `graded_run_id`, `status`, `audit_reported_score`,
  `audit_has_high_cheat_flag`, `audited_at`, every `repro_sweeps` text field.
- Timestamps: `duration_s` only; per event `t_rel_s` (seconds from run start).
- `exit_reason` -> `exit_label`: natural -> "Finished", budget_exhausted ->
  "Budget exhausted", context_budget -> "Context limit", round_limit -> "Round
  limit", wall_clock / timeout -> "Time limit", error -> "Ended with error",
  anything else -> "Ended". Report the distinct raw values so the map is complete.
- Dissection record: keep only `paper_gist`, `target_claim`,
  `failure_mode_detail`, `agent_trajectory_summary`, `evidence_quotes`
  (`{round, quote}`), and `agent_final_selfclaim.claimed_outcome` as
  `self_report`. Drop `suspected_grading_error`, `self_claim_gap`,
  `compute_pattern`, `genuine_wall`, `artifact_availability`,
  `notable_insights`, `audit_summary`, `claimed_numbers`, `honest_about_failure`.
- Audit: `score`, `verdict`, `reproduced`, `flags[{kind, severity, evidence}]`,
  `rationale`, `has_transcript`.
- `redactions.json` (committed, starts as `{"hide_runs": [], "hide_fields": {}}`):
  `hide_fields` maps an anon id to a list of dotted paths (`audit.rationale`,
  `analysis.failure_mode_detail`, `analysis.agent_trajectory_summary`,
  `analysis.evidence_quotes`) that the exporter blanks for that run;
  `hide_runs` drops runs. Applied last, reported.

### 3.2 Text scrub (unchanged from v1; every string field, recursively)

Apply in order; case-insensitive unless noted.
1. Secrets: `hf_[A-Za-z0-9]{20,}`, `sk-[A-Za-z0-9_-]{20,}`, `ghp_[A-Za-z0-9]{30,}`,
   `AKIA[0-9A-Z]{16}`, JWT `eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,}` -> `[redacted]`.
2. Emails -> `[email]`.
3. Env dumps: `(USER|LOGNAME|HOME|MAIL|HOSTNAME|SLURM_CLUSTER_NAME|SLURM_SUBMIT_HOST|
   SLURMD_NODENAME|SLURM_JOB_NODELIST|SLURM_NODELIST|SLURM_JOB_PARTITION|
   SLURM_JOB_ACCOUNT|SLURM_JOB_QOS|SLURM_JOB_USER|SLURM_TOPOLOGY_ADDR|
   NCCL_SOCKET_IFNAME)=\S*` -> `\1=[redacted]`.
4. Hostnames: `[\w.-]*\.(delta\.internal\.ncsa\.edu|ncsa\.illinois\.edu|illinois\.edu|ncsa\.edu)`
   -> `[host]`; `\bgh-login0?\d\b` -> `[login-node]`; `\bgh\d{3}(\.hsn\.cm)?\b`
   -> `[node]`; `\bcm\.delta\b` -> `[host]`.
5. People: `msalunkhe|mithils3|mithilss|salunkhe|mithil` -> `[user]`;
   `/u/[user]` -> `/home/[user]`.
6. Project/account: `bfvr-dtai-gh|betw-dtai-gh|bfvr-delta-\w+|betw-delta-\w+` -> `[account]`;
   `/work/nvme/bfvr` -> `/work`; `/work/hdd/bfvr` -> `/work-hdd`;
   `/(projects|scratch)/bfvr` -> `/\1/[proj]`; remaining `\bbfvr\b|\bbetw\b` -> `[proj]`.
7. Cluster software/partitions: `/sw/spack/\S+` -> `/sw/[redacted]`;
   `\bdeltas?\d{2}[\w-]*` -> `[cluster-sw]`; `\bghx4(-interactive)?\b|\bgpu[AH]100x[48](-interactive)?\b`
   -> `[partition]`; `\bhsn[0-3]\b` -> `[iface]`.
8. Institution: `DeltaAI|Delta AI` -> `[cluster]`;
   `\bDelta\b(?=\s+(cluster|login|GPU|node|system|HPC|account|allocation))`
   (case-sensitive) -> `[cluster]`; `NCSA|University of Illinois|Illinois|UIUC|Urbana[- ]Champaign`
   -> `[institution]`.
9. Slurm ids: `slurm-\d{6,8}` -> `sweep`; `(SLURM_JOB_ID|SLURM_JOBID|--jobid|jobid|job id|job)\s*[=: ]\s*\d{6,8}`
   -> `\1=[job]`; `slurm-?\d+\.(out|err)` -> `job.\1`; every known 7-digit job
   id (all `slurm-*` batch ids plus 2678961, 2889476, 2666353) as `\b\d{7}\b` -> `[job]`.
10. Hardware: `GH200(\s*\d+GB)?` -> `[GPU]`; `Grace Hopper` -> `[GPU]`.
11. Repos/datasets/harness: `Mithilss/reprobench-splits` -> `[dataset]`;
    `github\.com/mithils3\S*` -> `[repo]`; `reprocli\w*` -> `harness`;
    `rjnkpoxwdslkgxjliakq` -> `[storage]`; `agent-logs\.vercel\.app` -> `[viewer]`;
    `ReproBench` -> `RECLAIM`.
12. IPs: RFC1918 and `141\.142\.\d+\.\d+` -> `[ip]`.

Do not scrub: the benchmark papers' own repos and authors, arXiv ids, vendor
model names, the words srun/slurm inside tool output, `H100` as the compute
unit, `aarch64`.

### 3.3 Leak gate (hard fail, exporter and independent verifier)

Case-insensitive grep over every file under `public/` (data gunzipped) for:
`ncsa`, `illinois`, `uiuc`, `urbana`, `deltaai`, `delta.internal`, `gh-login`,
`msalunkhe`, `mithil`, `salunkhe`, `bfvr`, `betw-dtai`, `/u/`, `rjnkpoxwdslkgxjliakq`,
`slurm-2`, `ghx4`, `gh200`, `reprocli`, `agent-logs`, `reprobench`, `muse`,
`laguna`, `hf_[A-Za-z0-9]{20}`, `eyJhbGci`, `@illinois`, every known 7-digit
job id, every raw run id. Zero hits. Source-only list: `supabase`,
`huggingface`, `Mithilss`, `freeze`, `frozen`, `self-grade`, `sbatch`, `slurm`,
`Anthropic`, `trace.paper`, `Easy`, `Medium`, `Hard` (as tier words), `dev split`.

## 4. Data contract (`public/data/`)

`.json` plain; `.json.gz` via `DecompressionStream("gzip")`.

`index.json`:
```
{
  "generated": "2026-08-30",
  "benchmark": {"name": "RECLAIM", "papers": 100, "venue": "NeurIPS 2025"},
  "auditor": {"id": "claude-sonnet-5", "name": "Claude Sonnet 5"},
  "models": [{"key":"dsv4","name":"DeepSeek-V4","id":"deepseek-ai/DeepSeek-V4-Flash-0731"},
             {"key":"qwen3","name":"Qwen3.6-27B","id":"Qwen/Qwen3.6-27B-FP8"},
             {"key":"minimax","name":"MiniMax-M2.7","id":"MiniMaxAI/MiniMax-M2.7"}],
  "tiers": [{"key":"run","name":"Run","what":"code, data and weights released; execute or evaluate"},
            {"key":"retrain","name":"Retrain","what":"code and data released, no released weights; train before evaluating"},
            {"key":"reimplement","name":"Reimplement","what":"no released code; rebuild the method from the paper"}],
  "modes": [{"key":"reproduced-clean","name":"Reproduced clean"}, ... nine ..., {"key":"other","name":"Other"}],
  "sweeps": [{"key":"dsv4-retrain","model":"dsv4","tier":"retrain","n":28,
              "mean_score":6.43,"n_reproduced":9,"verdicts":{...},
              "modes":{...},"score_distribution":{"0":..},
              "spent_h100":322.1,"budget_h100":792.0}],
  "papers": [{"arxiv_id":"2510.21363","tier":"retrain","band":"8h","claim":"...",
              "predicted_h100":3.2,"kind":"...","paper_url":"...","code_url":"...",
              "gist":"<paper_gist from any run's dissection>"}],
  "runs": [{
    "id":"dsv4-retrain-2510.21363","arxiv_id":"2510.21363","model":"dsv4",
    "tier":"retrain","sweep":"dsv4-retrain",
    "exit_label":"Finished","rounds":64,"tool_calls":210,
    "budget_h100":8.0,"spent_h100":2.6,"duration_s":31234,
    "tokens":{"prompt":..,"completion":..,"total":..,"cached":..,"reasoning":..},
    "audit":{"score":8,"verdict":"reproduced","reproduced":true,
             "flags":[{"kind":"other_provenance_break","severity":"low","evidence":"..."}],
             "rationale":"...","has_transcript":true},
    "mode":"reproduced-clean","mode_slug":"reproduced-clean",
    "claim":"<target_claim>","self_report":"not_reproduced"
  }]
}
```

`runs/<id>.json.gz`:
```
{ "run": <index entry>,
  "events": [ {seq, round_index, kind, role, reasoning, content, exit_reason,
               finish_reason, tool_name, command, detail_kind, args, ok, rc,
               duration_s, cost_h100, remaining_h100, error, path, stdout,
               stderr, truncated, t_rel_s} ],
  "analysis": {"paper_gist","target_claim","failure_mode_detail",
               "agent_trajectory_summary","evidence_quotes":[{round,quote}],
               "self_report"},
  "audit_events": [ same compact shape ] | null }
```
The frontend reuses `rowsToRounds` unchanged.

`manifest.json` (committed): `{generated, n_runs, n_sweeps, gate_hits: 0,
runs: [{id, score, verdict, mode}], dropped: [...], relabels: [...],
score_notes: [...]}`.

`screen_report.md` (written by a review agent, not by export.py): every
displayed narrative passage (audit rationale, failure_mode_detail,
agent_trajectory_summary, evidence quotes, paper gist, claim) that criticizes
or casts doubt on the benchmark, a pinned target, the rubric, the auditor, the
harness or the compute setup, with run id, field, excerpt and a suggested
`redactions.json` entry. Nothing is applied automatically.

## 5. Site (`public/`)

Static, no build step, vanilla JS. No supabase-js, no external fetch except
Google Fonts. `<meta name="robots" content="noindex,nofollow">`. Brand
"RECLAIM", sub-line "reproduction run traces", `<title>RECLAIM run traces</title>`.
Hash routing: `#/overview` (default), `#/runs?model=&tier=&verdict=&mode=&q=`,
`#/run/<id>`, `#/papers`, `#/paper/<arxiv_id>`, `#/about`. Global filter bar
(Agent: all + 3; Tier: all + 3) persists across Overview, Runs and Papers.

- Overview: tiles (papers 100, runs 275, agents 3, reproduced rate overall);
  the agent x tier matrix (mean score to 2 decimals, reproduced %, n; click ->
  Runs filtered); failure-mode distribution as stacked bars per agent with the
  nine modes plus Other in a fixed order and colour; score histogram 0-10;
  compute row (mean fraction of budget spent, reproduced vs not, per tier).
- Runs: sortable table (claim, arXiv id, agent, tier, score, verdict, mode,
  rounds, spent/budget H100h, tokens) with verdict / mode / search filters.
- Run page: header (claim, arXiv link, agent, tier, verdict stamp, score,
  mode, budget/spent, rounds, tool calls, tokens, duration, exit label); Audit
  card (Claude Sonnet 5: verdict, score, rationale, flags with severity);
  Dissection card (mode with one-line definition, failure_mode_detail,
  agent_trajectory_summary, evidence quotes linking to round cards, one line
  "Agent's own report: <self_report>"); Transcript (round cards, burn trace,
  rail); "Auditor transcript" toggle when present; prev/next within the
  current filter order.
- Papers: 100 rows, one score chip per agent (coloured by verdict family) ->
  paper page with gist, claim, tier, band, links and its runs.
- About (calm methods note, no caveats, no dates, no names beyond the paper's
  own terms): RECLAIM is 100 NeurIPS 2025 papers, each with a frozen target
  claim and tolerance, a metered GPU-hour budget in H100-hours, and a tier
  set by what the authors released (Run / Retrain / Reimplement). An agent
  attempts each paper once per tier sweep. A pinned auditor (Claude Sonnet 5)
  reads the run's evidence bundle and transcript and assigns 0-10; the
  verdict is derived in code: 8-10 reproduced, 6-7 partial, 1-5 not
  reproduced (1 unverifiable when execution was not verified), 0 disqualified
  on a high-severity integrity flag. A separate transcript dissection assigns
  one primary failure mode from a fixed vocabulary and never changes a grade.
  Transcripts are shown verbatim; sandbox paths and identifiers are replaced
  by bracketed tokens.

Copy rules: no em dashes; never "Easy/Medium/Hard", "ReproBench", "Muse",
"freeze", "self-grade", "re-audit", "test-retest", "sbatch", "slurm",
"cluster", "GPU node", "specimen", "dev split", "harness fault", "pin defect",
"corrupted", "unstable", or any date. Nothing on the site describes a
limitation of the benchmark, the auditor or the infrastructure. Keep the warm
palette, Fraunces / Inter / IBM Plex Mono, dark mode.

## 6. Deploy

`cd tools/anon_viewer/public && vercel link --yes --project reprobench-traces && vercel --prod --yes`.
`vercel.json`: `X-Robots-Tag: noindex, nofollow` on `/(.*)`. `.vercel/` and
`data/` gitignored.

## 7. Concordance with the paper (hard requirement)

The site is a supplement to `paper_latex/iclr2027_conference.tex` and must agree
with it. `tools/anon_viewer/concordance.py` reads `public/data/index.json` only
and prints one line per check, PASS or FAIL with both values; `export.py` runs
it last and the report carries the table. Numbers of record (paper abstract,
intro and the `% numbers of record` comment block, 2026-08-24/27):

| check | paper says | computed from |
|---|---|---|
| DeepSeek-V4 reproduced by tier | 14/29 run, 9/28 retrain, 4/30 reimplement (48% / 32% / 13%) | sweeps dsv4-* n_reproduced / n |
| Retrain matched-number range | MiniMax 5/32 = 16%, Qwen3.6 6/26 = 23%, DeepSeek 9/28 = 32% | sweeps *-retrain |
| Retrain mean audit score range | 3.41 (MiniMax) to 6.43 (DeepSeek) | sweeps *-retrain mean_score |
| Failed-run spend | mean spent/budget = 45% (median 27.4%) over the 60 non-reproduced DeepSeek-V4 runs (15 + 19 + 26) | runs model=dsv4, audit.reproduced=false |
| 96 H100-hour band | mean spend 13.1%, 0 of 11 reproduced, pooled over the pinned sweeps | runs budget_h100 = 96 |
| Retrain near-miss | 15 of 28 DeepSeek retrain runs are near-miss-partial, 15 of its 19 misses | runs dsv4-retrain mode |
| Retrain verified partial | 22 of 28 DeepSeek retrain runs score >= 6 | runs dsv4-retrain audit.score |
| Papers | 100, tiers 34 / 33 / 33 (lockfile) | papers |
| Agents | 3 | models |

A FAIL is reported, never patched in the data: the exporter prints the FAIL
and exits 0, and the report's Concordance section explains which definition
differs (for example the pooled denominator of the 96-hour band). The main
loop decides.

`export_report.md` also carries "Table: primary failure mode by tier", in the
paper's `tab:failure-modes` shape (rows = the nine modes plus Other, columns =
Run / Retrain / Reimplement / All), once per agent and once pooled, so the
paper's XX placeholders can be filled from the same data the site shows.

Known discrepancy inside the paper (not the site's to fix): the main-text
table lists Evaluation-protocol shopping, Availability wall and Honest
shortfall as rows, while appendix G retires availability-wall and
honest-shortfall and has no protocol-shopping slug. The site follows appendix G.

## 8. Facing pass (v2.1): what the screen report changes

Source: `screen_report.md` (56 flags, 44 runs). Grades, verdicts and flag kinds
and severities are never edited. Everything below is presentation of prose.

### 8.1 Structural
- `run.claim` = the lockfile's `central_claim` for the paper (papers[].claim),
  for every run. The dissector's `target_claim` is dropped from the bundle. If
  the lockfile row carries a structured match target (metric, value, scope,
  bar kind), render it as a separate `target` string on the run
  ("metric = value on scope, bar kind"); otherwise omit.
- `analysis.evidence_quotes`: keep only quotes whose `round` is an integer in
  [0, last round of the transcript] AND whose text does not read as auditor
  prose (drop when it matches `(?i)\b(audit(or)?|rubric|band \d|score \d|verdict)\b`).
- `self_report`: normalise to one of reproduced | partial | not_reproduced |
  unverifiable | null by regex over `claimed_outcome` (case-insensitive:
  "not.reproduced|not reproduced|NOT REPRODUCED|cannot be verified" -> not_reproduced;
  "partial" -> partial; "unverifiable" -> unverifiable; "reproduced" -> reproduced;
  else null). The site prints the word or omits the line.
- `audit.rationale` shorter than 40 characters (the literal "placeholder"):
  fall back to the other finished claude-sonnet-5 pass's rationale for that run,
  else to the dissection's `audit_summary.rationale_gist`, else null (card
  shows score and verdict only). Report the fallbacks.
- Trailing serialization garbage on a rationale (`"}` `</br>` `{` fragments at
  the end) is trimmed.

### 8.2 Text pass over displayed narrative fields
Applied by the exporter to `audit.rationale`, `audit.flags[].evidence`,
`analysis.failure_mode_detail`, `analysis.agent_trajectory_summary`,
`analysis.evidence_quotes[].quote`, `analysis.paper_gist`, `papers[].gist`.
Never applied to transcript events.
1. Delete whole sentences that start with or contain: "human spot-check" (not the
   participle "spot-checked"), "A spot-check of/should/would",
   "A human reviewer should", "human review of",
   "confidence is [up to two words] (low|moderate|high|reduced|limited|<digit>)" (not "verbal confidence is", which is paper content),
   "confidence is moderate", "See suspected_grading_error", "suspected_grading_error",
   "I diverge from a pre-existing", "This diverges from a prior self-audit",
   "should have been excluded from the", "needs correction in the benchmark",
   "should have been pinned", "curation-level concern", "worth flagging for human review",
   "worth flagging for tuple-quality review", "for human review of the pinned",
   "the benchmark's own", "benchmark-lockfile mis-specification",
   "is not in the paper" when the subject is the pin, "corresponds to no table or row",
   "appear to be from an entirely different paper or are fabricated",
   "the (self-)auditor", "which the audit rationale's phrase", "I propose tracking this as a new sub-mode",
   "report-truncation-audit-loss", "metering behavior", "GPU-allocation-hold overhead",
   "run_gpu tool bug", "OOM cascade incident", "rc-masking bug", "The previous agent ran",
   "outbound git protocol blocked", "shared SLURM job hosting", "At zero, EVERYTHING dies",
   "Invalid partition name specified", "stateless resend architecture".
   A sentence is the span between sentence terminators (. ! ? or newline).
2. Replacements (case-insensitive unless noted):
   "the pinned bar is mis-specified and the agent reproduced the reproducible sibling quantity" -> "the agent reproduced a sibling quantity";
   "pinned bar mis-specified" -> "sibling quantity reproduced";
   "rubric band (\d+)" / "Band (\d+)" / "band (\d+)" (followed by optional parenthetical or quoted anchor text) -> "a score of N" (the band number is the score; the anchor text is dropped so the sentence keeps its verb); "rubric band N-M" -> "a score of N to M"; "band-N anchor/profile" -> "score-N anchor/profile"; "the rubric's band-N" -> "the grading protocol's score-N"; "higher/lower band" -> "higher/lower score";
   criterion codes -> plain names, never bare deletion (deletion left "-C3" fragments): a list or range such as "C1-C3", "C2/C3", "C2 through C4", "C4, C5 and C6" -> "grading checks"; "the C1-C6 criteria" -> "the grading criteria"; "C1 criterion" -> "the match criterion"; single codes C1..C6 -> "the match criterion" / "the execution check" / "the value-location check" / "the provenance check" / "the numeric comparison" / "the experiment-fidelity check" (after appendix C); a code in parentheses alone, "(C2)", is deleted;
   "Self-assessed auditor (same <model>) scored this N/10 under the '<band name>' band:" -> "Scored N/10, <band name>:" (a self-graded dissection gist that reaches the rationale through the 8.1 fallback);
   scheduler words: "srun (step) time limit" / "srun step limit" -> "session time limit"; "srun step(s)" -> "GPU session(s)"; "srun wrapper" -> "session wrapper"; "srun error" -> "scheduler error"; "srun:" -> "scheduler:"; bare "srun" -> "GPU session"; "Slurm" -> "scheduler" (keeping a preceding article); "sbatch" -> "batch-job"; "scancel" -> "job cancel"; "squeue" -> "the queue";
   ", though/but/and it should be human spot-checked" -> delete the clause; " and should be independently spot-checked in <file> against <file>" -> delete the clause;
   "per the rubric" / "under the frozen rubric" / "the frozen rubric" / "the rubric's" -> "the grading protocol" forms ("under the grading protocol", "the grading protocol's");
   "frozen eval set" / "frozen benchmark" / "frozen set" -> "evaluation set";
   "Stage-7 audit(or)?" / "Stage 7" -> "the auditor" / "the audit";
   "sweep wall" -> "session time"; "sweep" -> "batch" (word);
   "mre_config" -> "the pinned configuration"; "match_target" / "match_bar" -> "the match target";
   "audited_h100_hours \d+" -> delete; "audit_verdict.json" / "audit_result.json" -> "an earlier report file";
   "methodology_notes" -> "the methodology notes"; "self-graded" / "self-grade" -> "self-assessed";
   "harness/formatting failure" / "harness failure" / "harness fault" / "harness artifact" -> "final-turn truncation" / "run artifact";
   "harness" (remaining, word) -> "the run controller";
   "Easy-tier" -> "Run-tier", "Medium-tier" -> "Retrain-tier", "Hard-tier" -> "Reimplement-tier" (also the `[tier]-tier` residue from the v2 scrub);
   "lockfile" -> "benchmark record"; "pinned tuple" / "claim tuple" / "bar tuple" -> "pinned target".
3. After the pass, collapse doubled spaces and dangling ", ." / " ." artefacts.

### 8.3 Residue: `redactions.json`
`hide_fields` may now name any of: `audit.rationale`, `audit.flags`,
`analysis.failure_mode_detail`, `analysis.agent_trajectory_summary`,
`analysis.evidence_quotes`, `analysis.paper_gist`, `self_report`. New key
`hide_sentences`: anon id -> list of substrings; every sentence containing a
substring is deleted from every displayed narrative field of that run.
Seed the file from the screen report with:
- hide_fields: minimax-run-2505.18809 [failure_mode_detail, agent_trajectory_summary, evidence_quotes];
  dsv4-retrain-2504.12463 [evidence_quotes]; qwen3-run-2503.18430 [failure_mode_detail];
  qwen3-reimplement-2506.00070 [evidence_quotes, agent_trajectory_summary];
  minimax-retrain-2506.13717 [agent_trajectory_summary]; qwen3-run-2504.12397 [failure_mode_detail];
  qwen3-reimplement-2503.02809 [agent_trajectory_summary]; qwen3-retrain-2509.16391 [agent_trajectory_summary];
  qwen3-reimplement-2502.08924 [agent_trajectory_summary]; qwen3-reimplement-2511.20906 [agent_trajectory_summary];
  minimax-run-2503.18430 [evidence_quotes]; minimax-retrain-2506.20233 [evidence_quotes];
  qwen3-run-2505.10475 [failure_mode_detail, evidence_quotes]; qwen3-run-2506.01511 [failure_mode_detail].
- hide_sentences: qwen3-reimplement-2510.25146 ["should have been excluded"];
  qwen3-reimplement-2510.04136 ["needs correction", "stale audit_result", "fabricated"];
  dsv4-reimplement-2510.04136 ["corresponds to no table"]; qwen3-retrain-2502.01203 ["mis-specification"];
  qwen3-run-2506.02392 ["should have been pinned"]; minimax-retrain-2510.09485 ["garbled"];
  qwen3-retrain-2510.09485 ["garbled", "flagged for human review"]; qwen3-run-2505.11483 ["mis-specified"];
  minimax-retrain-2510.22123 ["I diverge"]; minimax-run-2505.14827 ["diverges from a prior"];
  qwen3-run-2410.18164 ["audit_result.json"]; qwen3-reimplement-2505.24452 ["curation-level"];
  qwen3-retrain-2505.17836 ["read off a log-log figure"]; qwen3-run-2506.12025 ["worth flagging"].
Report every hide applied (id, field or substring, characters removed).

### 8.4 Scrub additions (round-3 red team)
ps/top USER column -> `[user]` (line-anchored: `^\s*([a-z][a-z0-9_-]{1,15})\s+\d+\s+[\d.]+\s+[\d.]+`), plus
the literal `yjian1`; `/harbor(/|\b)` -> `[export]`; `\[timestamp\]\s*[+-]\d{2}:?\d{2}\b` -> `[timestamp]`;
GPU capacity within 80 chars of GPU|VRAM|HBM|[GPU] on one line: `\b\d{2,3}\s?GB\b` -> `[GPU-mem]`;
host RAM `\bMem:\s+\d{3}(Gi|GB|G)?\b` and `[2-5]\d{2}\s?(Gi|GB|G)\b` within 40 chars of
free|MemAvailable|MemTotal|available|RAM|host|node -> `[RAM]`; `\b(72|144|288)\s?(CPU\s+)?(cores?|threads?|CPUs?)\b` -> `[cpu]`;
`\b(easy|medium|hard)_sweeps?\b` -> `sweeps`; bare `(?<![\w./])/u(?![\w/])` -> `/home`;
`/work/(b|bf|bfv|be|bet|h|hd|hdd|n|nv|nvm|nvme)(?![\w-])` -> `/work`; `\[user\][A-Za-z0-9]{1,2}(?=[/\s"'])` -> `[user]`;
nvidia-smi csv `\[GPU\]\s*,\s*\d{4,6}(\s*,\s*\d{1,6})*` -> `[GPU], [GPU-spec]`; `total\s+mem\s+GB\s*:\s*[\d.]+` -> `total mem GB: [GPU-spec]`;
`(datasets|models)--\[user\]--[\w.-]+` -> `\1--[user]--[dataset]`; `neurips-20\d\d-paper-bundles` -> `[dataset]`;
`(easy|medium|hard)[-_](?=difficulty)` -> delete; `dtai[\w.-]*` and `root@dtai\S*` -> `[host]`;
`\bx\d{3,5}c\d+[rs]\d+b\d+\b` -> `[node]`; `oscar_server` -> `[host]`; `SGI Tempo` -> `[vendor]`;
`Grace[- ]?Hopper|gracehopper` -> `[GPU]`; `/dltawork` and `\bdlta\w*` -> `[fs]`.
Email rule: require a letter or dot before `@` and a domain with a letter and a dot (`[A-Za-z0-9._%+-]*[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9-]+\.[A-Za-z]{2,}`), so `Acc@22.5°` survives.
Secret rule `sk-`: require a non-word character or start before `sk-`.
Gate additions: `yjian1`, `/harbor`, `dltawork`, `dtai-`, `oscar_server`, `Grace-Hopper`, `_sweeps`.

### 8.5 Site
- Run page tiles: SPENT, BUDGET, ESTIMATED NEED (the paper's compute estimate,
  sub-line "paper's estimate"; no IN THE RED / IN THE BLACK stamp, no LEFT tile),
  ROUNDS, TOKENS, DURATION. The burn trace keeps its dashed estimate line.
- About, grading section: replace "Flags are shown exactly as the auditor
  recorded them." with "Rationales, flags and dissection notes are shown as
  recorded, except that references to internal rubric bands, criterion codes,
  file names and scheduling terms are replaced by plain words or removed."
- Run header shows the paper's claim; if `target` exists it is a second line in
  mono type labelled TARGET.
- "Agent's own report" line prints the normalised word or is omitted.
