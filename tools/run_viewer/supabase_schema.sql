-- ============================================================================
-- Repro Run Viewer schema  (run via tools/run_viewer/setup_db.py, or paste this
-- whole file into Supabase > SQL Editor and hit Run). Safe to run twice.
--
--   repro_runs    -- one row per run_id: lifecycle + compute meters
--   repro_events  -- append-only transcript events (round_open / call_* / final)
--
-- Auth model: anon (the browser) is READ ONLY. Writes come from the harness with
-- the service_role key, which bypasses RLS. (verify_app, by contrast, is anon
-- read+write because reviewers type into it directly.) No FK from events->runs:
-- the uploader streams best-effort and out of order, so we don't want an insert
-- to fail just because the run row hasn't landed yet — the viewer joins by run_id.
-- ============================================================================

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- repro_runs
-- ---------------------------------------------------------------------------
create table if not exists public.repro_runs (
  run_id            text primary key,            -- <UTCstamp>-<hex> (inputs.new_run_id)
  arxiv_id          text not null,
  budget            numeric,                      -- total H100-equiv hours (the <budget>h dir)
  model             text,
  status            text not null default 'running',  -- 'running' | 'finished' | 'error'
  exit_reason       text,
  host              text,                         -- login-node hostname
  tool_rounds_used  int     default 0,
  spent_h100        numeric default 0,
  remaining_h100    numeric,
  total_h100        numeric,                      -- = budget, denormalized for the meter
  full_log_url      text,                         -- Storage public URL (set at run end)
  started_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  finished_at       timestamptz
);

create index if not exists repro_runs_status_idx  on public.repro_runs (status);
create index if not exists repro_runs_updated_idx on public.repro_runs (updated_at desc);
create index if not exists repro_runs_arxiv_idx   on public.repro_runs (arxiv_id);

-- real per-run token usage (summed over rounds by the harness) + the detailed
-- stats.json URL. Added after the first deploy; safe to run twice.
alter table public.repro_runs add column if not exists prompt_tokens     bigint;
alter table public.repro_runs add column if not exists completion_tokens bigint;
alter table public.repro_runs add column if not exists total_tokens      bigint;
alter table public.repro_runs add column if not exists cached_tokens     bigint;
alter table public.repro_runs add column if not exists reasoning_tokens  bigint;
alter table public.repro_runs add column if not exists tool_calls        int;
alter table public.repro_runs add column if not exists stats_url         text;

-- Stage-7 auditor verdict for this run's bundle, pushed by
-- `python -m reprocli_repro.audit_upload` after `reprocli_vllm --mode audit`.
-- audit_verdict / audit_reproduced drive the viewer's reproduced status; the
-- hand-applied `success` tag is the fallback for runs that were never graded.
-- Safe to run twice.
alter table public.repro_runs add column if not exists audit_score               int;
alter table public.repro_runs add column if not exists audit_reported_score      int;   -- pre-cap score when a high cheat flag zeroed it
alter table public.repro_runs add column if not exists audit_verdict             text;  -- reproduced|partial|not_reproduced|unverifiable
alter table public.repro_runs add column if not exists audit_reproduced          boolean;
alter table public.repro_runs add column if not exists audit_has_high_cheat_flag boolean;
alter table public.repro_runs add column if not exists audit_flags               jsonb; -- cheat_flags[]: {kind,severity,evidence}
alter table public.repro_runs add column if not exists audit_rationale           text;
alter table public.repro_runs add column if not exists audit_model               text;  -- grader model id
alter table public.repro_runs add column if not exists audited_at                timestamptz;

-- Sweep grouping: set by the harness from REPRO_BATCH_ID/REPRO_BATCH_LABEL
-- (falling back to the sbatch job id) so one sweep's runs group in the viewer.
-- Safe to run twice.
alter table public.repro_runs add column if not exists batch_id    text;
alter table public.repro_runs add column if not exists batch_label text;
create index if not exists repro_runs_batch_idx on public.repro_runs (batch_id);

-- ---------------------------------------------------------------------------
-- repro_events  (append-only; grouped into rounds client-side by round_index)
-- ---------------------------------------------------------------------------
create table if not exists public.repro_events (
  id             bigint generated always as identity primary key,
  run_id         text not null,                  -- joins repro_runs.run_id (no FK on purpose)
  round_index    int,
  seq            int  not null,                  -- per-run monotonic ordering (sink-assigned)
  kind           text not null,                  -- 'round_open'|'call_start'|'call_result'|'final'
  role           text,
  reasoning      text,
  content        text,
  exit_reason    text,                           -- on 'final' events (mirrors the run's exit)
  finish_reason  text,                           -- model's finish_reason for the turn ('length' => cut off)
  tool_name      text,
  command        text,
  detail_kind    text,                           -- 'command'|'diff'|'path'|'json'
  args           jsonb,                           -- tool-call json args when detail_kind='json'
  ok             boolean,
  rc             int,
  duration_s     numeric,
  cost_h100      numeric,
  remaining_h100 numeric,
  error          text,
  path           text,
  stdout         text,                            -- capped by the sink (full text -> agent.full.log)
  stderr         text,
  truncated      boolean default false,
  created_at     timestamptz not null default now(),
  unique (run_id, seq)
);

create index if not exists repro_events_run_idx on public.repro_events (run_id, seq);

-- existing deployments: add columns introduced after first run (safe to run twice)
alter table public.repro_events add column if not exists exit_reason text;
alter table public.repro_events add column if not exists finish_reason text;

-- keep updated_at fresh on every PATCH
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;
drop trigger if exists repro_runs_touch on public.repro_runs;
create trigger repro_runs_touch before update on public.repro_runs
  for each row execute function public.touch_updated_at();

-- ---------------------------------------------------------------------------
-- Row Level Security: anon/authenticated READ ONLY; writes via service_role
-- ---------------------------------------------------------------------------
alter table public.repro_runs   enable row level security;
alter table public.repro_events enable row level security;

drop policy if exists repro_runs_read   on public.repro_runs;
create policy repro_runs_read   on public.repro_runs   for select to anon, authenticated using (true);
drop policy if exists repro_events_read on public.repro_events;
create policy repro_events_read on public.repro_events for select to anon, authenticated using (true);
-- (no insert/update/delete policies for anon => only service_role can write)

-- ---------------------------------------------------------------------------
-- Realtime: the viewer subscribes to both tables (idempotent adds)
-- ---------------------------------------------------------------------------
do $$ begin
  if not exists (select 1 from pg_publication_tables
                 where pubname='supabase_realtime' and schemaname='public' and tablename='repro_runs') then
    alter publication supabase_realtime add table public.repro_runs;
  end if;
  if not exists (select 1 from pg_publication_tables
                 where pubname='supabase_realtime' and schemaname='public' and tablename='repro_events') then
    alter publication supabase_realtime add table public.repro_events;
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- Storage: public 'repro-logs' bucket for the downloadable full log
-- ---------------------------------------------------------------------------
insert into storage.buckets (id, name, public)
  values ('repro-logs', 'repro-logs', true)
  on conflict (id) do update set public = true;

-- ---------------------------------------------------------------------------
-- audit_runs / audit_events  (the S7 auditor streamed live, mirroring repro_*).
-- One audit_runs row per graded paper; audit_events is the same shape as
-- repro_events so the viewer's rowsToRounds/render render an audit like a run.
-- graded_run_id links back to the repro_runs row it graded. Anon READ ONLY;
-- writes come from reprocli_vllm.runtime.audit_sink with the service_role key.
-- ---------------------------------------------------------------------------
create table if not exists public.audit_runs (
  audit_run_id      text primary key,             -- <graded_run_id>-<arxiv>-audit
  graded_run_id     text,                          -- joins repro_runs.run_id (no FK on purpose)
  arxiv_id          text not null,
  model             text,                          -- grader model id
  status            text not null default 'running',  -- 'running' | 'finished' | 'error'
  exit_reason       text,
  score             int,                           -- 0-5 (capped)
  verdict           text,                          -- reproduced|partial|not_reproduced|unverifiable
  reproduced        boolean,
  has_high_cheat_flag boolean,
  tool_rounds_used  int default 0,
  host              text,
  started_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  finished_at       timestamptz
);
create index if not exists audit_runs_updated_idx on public.audit_runs (updated_at desc);
create index if not exists audit_runs_graded_idx  on public.audit_runs (graded_run_id);

create table if not exists public.audit_events (
  id             bigint generated always as identity primary key,
  audit_run_id   text not null,                  -- joins audit_runs.audit_run_id (no FK on purpose)
  round_index    int,
  seq            int  not null,
  kind           text not null,                  -- 'round_open'|'call_start'|'call_result'|'final'
  role           text,
  reasoning      text,
  content        text,
  exit_reason    text,
  finish_reason  text,                           -- model's finish_reason for the turn ('length' => cut off)
  tool_name      text,
  command        text,
  detail_kind    text,                           -- 'command'|'path'|'json'
  args           jsonb,
  ok             boolean,
  rc             int,
  duration_s     numeric,
  error          text,
  path           text,
  stdout         text,
  stderr         text,
  truncated      boolean default false,
  created_at     timestamptz not null default now(),
  unique (audit_run_id, seq)
);
create index if not exists audit_events_run_idx on public.audit_events (audit_run_id, seq);

drop trigger if exists audit_runs_touch on public.audit_runs;
create trigger audit_runs_touch before update on public.audit_runs
  for each row execute function public.touch_updated_at();

alter table public.audit_runs   enable row level security;
alter table public.audit_events enable row level security;
drop policy if exists audit_runs_read   on public.audit_runs;
create policy audit_runs_read   on public.audit_runs   for select to anon, authenticated using (true);
drop policy if exists audit_events_read on public.audit_events;
create policy audit_events_read on public.audit_events for select to anon, authenticated using (true);

do $$ begin
  if not exists (select 1 from pg_publication_tables
                 where pubname='supabase_realtime' and schemaname='public' and tablename='audit_runs') then
    alter publication supabase_realtime add table public.audit_runs;
  end if;
  if not exists (select 1 from pg_publication_tables
                 where pubname='supabase_realtime' and schemaname='public' and tablename='audit_events') then
    alter publication supabase_realtime add table public.audit_events;
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- repro_tags  (user-authored run labels). Unlike repro_runs/repro_events, the
-- browser writes these directly, so anon is READ + WRITE here — same trust model
-- as verify_app, where reviewers type into the app. One row per run_id holds the
-- whole tag array; the viewer upserts it (and deletes the row when it empties).
-- ---------------------------------------------------------------------------
create table if not exists public.repro_tags (
  run_id     text primary key,             -- joins repro_runs.run_id (no FK on purpose)
  tags       text[] not null default '{}',
  updated_at timestamptz not null default now()
);

drop trigger if exists repro_tags_touch on public.repro_tags;
create trigger repro_tags_touch before update on public.repro_tags
  for each row execute function public.touch_updated_at();

alter table public.repro_tags enable row level security;
drop policy if exists repro_tags_read   on public.repro_tags;
create policy repro_tags_read   on public.repro_tags for select to anon, authenticated using (true);
drop policy if exists repro_tags_insert on public.repro_tags;
create policy repro_tags_insert on public.repro_tags for insert to anon, authenticated with check (true);
drop policy if exists repro_tags_update on public.repro_tags;
create policy repro_tags_update on public.repro_tags for update to anon, authenticated using (true) with check (true);
drop policy if exists repro_tags_delete on public.repro_tags;
create policy repro_tags_delete on public.repro_tags for delete to anon, authenticated using (true);

do $$ begin
  if not exists (select 1 from pg_publication_tables
                 where pubname='supabase_realtime' and schemaname='public' and tablename='repro_tags') then
    alter publication supabase_realtime add table public.repro_tags;
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- host_metrics / host_status  (host telemetry from reprocli_repro.metrics_beacon).
-- host_metrics is an append-only time series: one row per beacon cycle, per
-- host. host_status is one upserted row per host — the latest snapshot plus the
-- master's slurm/vLLM log tail. Anon READ ONLY; writes come from the beacons
-- with the service_role key. run_id joins repro_runs.run_id (no FK on purpose:
-- the beacon streams best-effort). The master beacon self-prunes its own
-- host_metrics rows older than 24 h, so the table stays a rolling window.
-- ---------------------------------------------------------------------------
create table if not exists public.host_metrics (
  id           bigint generated always as identity primary key,
  host         text not null,          -- short hostname
  role         text not null,          -- 'master' (brain/vLLM node) | 'run' (JIT GPU node)
  batch_id     text,                   -- REPRO_BATCH_ID (groups a sweep)
  run_id       text,                   -- set when role='run'; joins repro_runs.run_id (no FK)
  cpu_pct      numeric,                -- whole-node cpu busy %, 0-100
  mem_used_gb  numeric,
  mem_total_gb numeric,
  load1        numeric,                -- 1-min loadavg
  gpus         jsonb,                  -- [{"i":0,"util":93,"mem":72.1,"mem_total":97.8,"power":610,"temp":52}, ...] or null
  created_at   timestamptz not null default now()
);
create index if not exists host_metrics_run_idx  on public.host_metrics (run_id, created_at desc);
create index if not exists host_metrics_host_idx on public.host_metrics (host, created_at desc);

create table if not exists public.host_status (
  host         text primary key,
  role         text not null,
  batch_id     text,
  run_id       text,
  cpu_pct      numeric,
  mem_used_gb  numeric,
  mem_total_gb numeric,
  load1        numeric,
  gpus         jsonb,                  -- same shape as host_metrics.gpus
  log_tail     text,                   -- last ~120 lines of the master's slurm/vLLM log, <=16 KB
  updated_at   timestamptz not null default now()
);

drop trigger if exists host_status_touch on public.host_status;
create trigger host_status_touch before update on public.host_status
  for each row execute function public.touch_updated_at();

alter table public.host_metrics enable row level security;
alter table public.host_status  enable row level security;
drop policy if exists host_metrics_read on public.host_metrics;
create policy host_metrics_read on public.host_metrics for select to anon, authenticated using (true);
drop policy if exists host_status_read on public.host_status;
create policy host_status_read on public.host_status for select to anon, authenticated using (true);

do $$ begin
  if not exists (select 1 from pg_publication_tables
                 where pubname='supabase_realtime' and schemaname='public' and tablename='host_metrics') then
    alter publication supabase_realtime add table public.host_metrics;
  end if;
  if not exists (select 1 from pg_publication_tables
                 where pubname='supabase_realtime' and schemaname='public' and tablename='host_status') then
    alter publication supabase_realtime add table public.host_status;
  end if;
end $$;

-- Per-run GPU-efficiency rollup of that run's host_metrics series, written by the
-- sink at run finish (reprocli_repro.gpu_usage): how hard the held H100s were
-- actually driven. avg/max util %, % of samples above the active threshold, peak
-- and total single-GPU memory (GB), mean board power (W), and the sample count.
-- Safe to run twice.
alter table public.repro_runs add column if not exists gpu_util_avg_pct  numeric;
alter table public.repro_runs add column if not exists gpu_util_max_pct  numeric;
alter table public.repro_runs add column if not exists gpu_active_pct    numeric;
alter table public.repro_runs add column if not exists gpu_mem_peak_gb   numeric;
alter table public.repro_runs add column if not exists gpu_mem_total_gb  numeric;
alter table public.repro_runs add column if not exists gpu_power_avg_w   numeric;
alter table public.repro_runs add column if not exists gpu_samples       int;

-- tell PostgREST to pick up the new columns immediately (Supabase also auto-reloads)
notify pgrst, 'reload schema';
