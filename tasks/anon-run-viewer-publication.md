# Task: Anonymous paper-ready build of the run viewer (ICLR 2027 supplementary link)

> **Runbook / durable spec.** Saved so it survives context compaction. Re-read this
> before resuming. Status: **PLANNED 2026-08-09** — nothing built yet. Blocked on the
> final pinned-auditor sweeps existing; the tooling below can be built before then.
> Decision of record: `m-decide` key `publish-run-viewer-anon-reviewer-link` (2026-08-09).

## Goal

Ship a frozen, anonymous, self-contained build of `tools/run_viewer` at a URL that can go
into the ICLR 2027 submission as a supplementary link, showing **only the runs the paper
reports**. Reviewers get to inspect the actual agent trajectories and audit records behind
every number. Nobody gets to write to our database, learn which cluster we use, or watch
the data change under them mid-review.

## Why this shape

Three properties of the current deployment make it unfit as-is, and all three dissolve if
the paper build is **static** rather than a live mirror:

1. **`repro_tags` is world-writable.** `supabase_schema.sql` grants anon
   `insert`/`update`/`delete` with `using (true)`, and the anon key ships in
   `public/config.js` by design. A public URL is therefore a public write endpoint.
2. **`host_status` publishes cluster internals.** `log_tail` is ~120 lines of the master's
   slurm/vLLM log and `host` is the login-node hostname. Measured on the existing dumps:
   `notes/Analysis/easy-sweep-2687371-qwen3-runs.json` contains 34 `ncsa` and 35 `delta`
   hits, and the analyses dump has a `/u/` path. That is institution-identifying under
   double-blind.
3. **Live data drifts.** A reviewer who checks a number in week 1 and again in week 4 must
   see the same thing, or the link damages the paper instead of supporting it.

A static build has no database, so 1 and 2 cannot happen and 3 is free.

## Selection rule: which runs appear

Only runs whose numbers the paper reports **(assumed — confirm when the final sweeps land)**:

- `split` is the frozen eval-100 or dev-14 set, and the run is post-dataset-freeze
  (2026-07-13, the `--frozen` eligibility gate).
- Audited by the **pinned auditor**, not self-graded. Self-graded sweeps are a comparability
  confound and are excluded, per `reprobench-cross-model-comparability`.
- Every sweep listed in the paper's tables, and nothing else. Exploratory, pre-freeze, and
  repair sweeps stay out. The viewer's existing "Exclude non-frozen" toggle is the wrong
  instrument here: filtering must happen at **export time**, not in the client, or the
  excluded runs still ship in the payload.

Record the exact sweep IDs in this file when chosen, so the build is reproducible.

## Steps

### 1. Exporter (`tools/run_viewer/export_static.py`)

New script. Reads Supabase with the service key, writes a static bundle:

- `data/runs.json`, `data/events/<run_id>.json`, `data/audits.json`,
  `data/analyses.json`, `data/manifest.json` (build date, sweep IDs, counts, scrub version).
- Takes an explicit `--sweep` allowlist. No "everything since date X" default: an allowlist
  is auditable, a date filter silently picks up whatever else ran.
- Drops the `host_metrics` / `host_status` tables entirely. They have no reviewer value.
- Drops `repro_tags` (internal annotations, not evidence).
- Rewrites `full_log_url` to a bundled relative path, or drops the field if the full log is
  not shipped. A live Storage URL defeats the point of freezing.

### 2. Scrubber (same script, `--scrub` pass, applied to every string field)

Runs over **event payloads**, not just metadata. The transcripts are where the cluster
paths live.

| Pattern | Replacement |
|---|---|
| `/u/<netid>`, `/work/...`, `/scratch/...`, `$HOME` expansions | `/home/agent` |
| login/compute hostnames (`*.delta.ncsa.illinois.edu`, `dt-*`, `gh*`) | `login-node`, `gpu-node-N` |
| slurm account strings (`bfvr`, `betw`), job IDs | `acct`, `job-N` (stable per-run alias) |
| `ncsa`, `delta`, `illinois`, `Mithilss`, `mithils3`, personal emails | `REDACTED` / neutral term |
| Supabase project ref, service keys, tokens | removed |

Keep GPU model strings (`GH200`) **only if** the paper already states the hardware. If the
paper says "a GH200 cluster", the site may too; if it says nothing, redact it.

### 3. Client changes (`tools/run_viewer/public/`)

- Swap `supabase-data.js` for a static loader reading `data/*.json`. Same interface, so the
  rest of the app is untouched.
- **`estimates.js` hardcodes `https://huggingface.co/datasets/Mithilss/reprobench-splits/`.**
  That handle deanonymizes on sight. Bundle the needed rows into `data/estimates.json` and
  cut the remote fetch.
- Delete the Live tab and the host strip (`live.css`, `hoststrip.js`, `fleet.js`, `hosts.js`)
  from the paper build. They exist to watch a cluster we are not disclosing.
- Delete the tagging UI (`tags.js`, `tagfilter.js`) since there is no DB to write to.
- Keep the Local tab. "Parsed locally in your browser; nothing is uploaded" is a good look
  on a reproducibility artifact and it costs nothing.
- Title and footer must carry no author, institution, repo, or funding string.

### 4. Contamination control

The bundle is a complete set of solution traces for the eval-100 papers. That cost was
accepted deliberately (see the decision record), but reduce the passive part:

- `robots.txt` with `Disallow: /` plus `<meta name="robots" content="noindex,nofollow">`.
- No sitemap, no analytics, no third-party scripts.
- A one-paragraph note on the landing page stating the artifact is evaluation material and
  asking crawlers and dataset builders not to ingest it.

This does not stop a determined scraper. It does stop the default ones, and it is the same
move LiveCodeBench-style benchmarks make.

### 5. Deploy

- A **new** Vercel project, not `agent-logs`. Neutral name, no personal account branding in
  the URL. Static output, no env vars, no serverless functions.
- Leave the existing `agent-logs.vercel.app` as the working instance, but turn on Vercel
  deployment protection on it now, since it is currently live and unprotected.
- Separately, close the write hole on the live DB regardless of this build: drop
  `repro_tags_insert` / `repro_tags_update` / `repro_tags_delete`. Requires the PAT, not the
  service key (see `deltaai`-adjacent note in `supabase-run-viewer` memory).

### 6. Verify before linking (the gate)

```bash
# 1. no identity survives the scrub
grep -rniE 'ncsa|delta|illinois|mithil|/u/[a-z0-9]|bfvr|betw|@.*\.edu' dist/data/ dist/*.js dist/*.html
# expect: zero hits

# 2. no live network calls
grep -rniE 'supabase|huggingface\.co|fetch\(.*https?://' dist/*.js
# expect: zero hits

# 3. the run set matches the paper
python3 -c "import json;d=json.load(open('dist/data/runs.json'));print(len(d))"
# expect: exactly the N the paper reports

# 4. it renders with the network off
python3 -m http.server -d dist 8080   # then load in a browser with devtools offline mode
```

Then have one person who has never seen the site try to identify the institution from it.
That is the real test and the greps are just the pre-filter.

### 7. Link it in the paper

Footnote at the first mention of the audit protocol, not in a Reproducibility Statement at
the back. The point is that a reviewer reading "provenance-audited" can immediately go look
at a provenance audit. Wording should state what the site contains and that it is frozen at
submission.

## Must not change

- The live `agent-logs` instance keeps working for our own use. This is a second build, not
  a migration.
- No schema change that breaks the harness writer path.
- Do not alter run content to make it look better. Scrubbing removes identity, never
  evidence. If a transcript is embarrassing, it ships.

## Open questions

- Ship full logs (`full_log_url` targets) or only the structured event stream? Full logs are
  large and carry the most identity surface. Default to the event stream, and only add full
  logs for the handful of runs the paper discusses by name.
- Does the paper state the hardware? That decides whether `GH200` is redacted.
