# Repro Run Viewer — setup & deploy

A web viewer for the reproduction agent's transcript logs, plus **live upload** so
you can watch in-flight runs from a browser. Two ways to use it:

- **Local file** — drop an `agent.log` / `agent.full.log` / `first_try.log` onto the
  page; it's parsed in your browser. No backend needed. Works today.
- **Live runs** — the harness streams each round to Supabase as a run executes; the
  deployed app lists runs and updates them in real time.

It reuses the design system of the `verify_app` data-labelling app (warm Claude/
Anthropic look, light/dark) and the same Supabase project.

```
tools/run_viewer/
  public/              # <-- the website you deploy (static, no build step)
    index.html
    config.js          # SUPABASE_URL / anon key (read-only) / FULL_LOG_BASE_URL
    parser.js          # transcript text -> normalized rounds[]
    render.js          # rounds[] -> round cards (shared by local + live)
    supabase-data.js   # Supabase read + Realtime -> rounds[]; tag read/write
    tags.js            # user-authored run tags (repro_tags) store + editor
    charts.js          # Stats-tab bar charts (tokens / compute by model)
    app.js             # boot, tabs, drag/drop, run list, live append
    styles.css viewer.css theme.css
  supabase_schema.sql  # the three tables + RLS + Realtime + Storage bucket
  setup_db.py          # create the tables for you (Management API / psql)
  SETUP.md
```

## 1. Preview the local viewer right now (no backend)

```bash
cd tools/run_viewer/public
python3 -m http.server 8800
# open http://127.0.0.1:8800 -> "Local file" tab -> drop outputs/agents/first_try.log
```

## 2. Create the Supabase tables (for live runs)

Reuses the existing project (ref `rjnkpoxwdslkgxjliakq`, shared with verify_app).
Add two new tables — they don't collide with verify_app's.

**Option A — let the script do it (recommended):**

```bash
# token from https://supabase.com/dashboard/account/tokens
export SUPABASE_ACCESS_TOKEN=sbp_xxx
python3 tools/run_viewer/setup_db.py
```

**Option B — DB connection string:**

```bash
export SUPABASE_DB_URL='postgresql://postgres:PASSWORD@db.rjnkpoxwdslkgxjliakq.supabase.co:5432/postgres'
python3 tools/run_viewer/setup_db.py      # needs psycopg installed
```

**Option C — manual:** open Supabase → SQL Editor → paste all of
`supabase_schema.sql` → Run.

This creates `repro_runs`, `repro_events` (anon read-only; Realtime on),
`repro_tags` (anon read **and write**, so the browser can label runs directly —
same trust model as verify_app), the `updated_at` trigger, and the public
`repro-logs` Storage bucket. Re-running it is safe; it adds `repro_tags` to an
existing deployment without touching the other tables.

## 3. Configure `public/config.js`

Already filled for the shared project. The anon key is read-only (gated by the
RLS policies) and is safe to ship to the browser. Set `FULL_LOG_BASE_URL` to the
`repro-logs` bucket's public path (already set).

## 4. Deploy to Vercel (a NEW, standalone project)

```bash
npm i -g vercel
cd tools/run_viewer/public
vercel            # first run: create a new project, e.g. "repro-run-viewer"
vercel --prod
```

Or git-based: Vercel → Add New Project → Framework **Other**, **Root Directory**
`tools/run_viewer/public`, empty build command. (Keep this separate from the
`data_label` project, which serves verify_app.)

## 5. Turn on live upload from the harness (opt-in)

The uploader is **off** unless these env vars are set, so default runs are
unchanged. The `service_role` key (Settings → API) bypasses RLS and must live
**only** on the cluster — never in `config.js` or the repo.

```bash
export SUPABASE_URL="https://rjnkpoxwdslkgxjliakq.supabase.co"
export SUPABASE_SERVICE_KEY="<service-role-key>"
export REPRO_UPLOAD_FULL_LOG=1            # optional: upload agent.full.log at run end
export REPRO_BATCH_ID="slurm-123456"     # optional: group one sbatch launch's runs (auto-falls back to SLURM_JOB_ID)
export REPRO_BATCH_LABEL="dev15 #123456" # optional: human-readable label for that batch in the viewer
python -m reprocli_repro --vllm-server-url ... --paper-id 2506.09045 --budget-h100-hours 8
```

Each round now streams to `repro_events` and the run's meters to `repro_runs`;
open the Vercel app's **Live runs** tab to watch. If the cluster can't reach
Supabase, the run is unaffected — `agent.full.log` on disk stays the complete
record, and you can always view it via the **Local file** tab.

### Host telemetry (optional)

Two more tables (created by the same `supabase_schema.sql` / `setup_db.py` run)
feed a live host panel: `host_metrics` — append-only samples (cpu / mem / load /
per-GPU util, one row per beacon cycle) — and `host_status` — one upserted row
per host with the latest snapshot plus the master's slurm/vLLM log tail. The
beacons are enabled by the **same** `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` env
vars as the run uploader (unset means off; never an error). The reproduce sbatch
scripts start the master beacon on the brain node once `/health` is green:

```bash
python -m reprocli_repro.metrics_beacon --role master --log-file slurm-<job>.out --interval 15 &
```

and each held GPU allocation gets a per-run beacon spawned **automatically** by
the harness (`gpu_session` → `run_beacon`) inside the allocation:

```bash
srun --jobid=<jobid> --overlap ... python -m reprocli_repro.metrics_beacon --role run --run-id <run_id> --interval 20
```

A host counts as live while `host_status.updated_at` is under 10 minutes old;
the master beacon prunes its own `host_metrics` rows older than 24 h.

## How it works (one shape, two sources)

`parser.js` (local text) and `supabase-data.js` (`rowsToRounds` over `repro_events`)
both emit the **same** `Round`/`Call` objects, so `render.js` draws either source
identically. The harness feeds the uploader from the existing `live_log` seam
(`src/reprocli_repro/live_log.py` → `supabase_sink.py`), so what you see live is
exactly what lands in `agent.log`.

## Notes / limits

- **Trust model:** the service-role key can write/delete anything — keep it in the
  cluster env only. The browser uses the anon key: read-only on `repro_runs` /
  `repro_events`, read+write on `repro_tags` only (so anyone with the URL can edit
  tags — fine for a personal tool; tighten the RLS if that ever changes).
- **Truncation:** per-event stdout/stderr is capped (full text in `agent.full.log`,
  optionally uploaded to Storage). The viewer flags truncated output.
- **Realtime volume:** the viewer subscribes to one open run at a time; the run
  list watches the low-volume `repro_runs` table.
