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

-- tell PostgREST to pick up the new columns immediately (Supabase also auto-reloads)
notify pgrst, 'reload schema';
