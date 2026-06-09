-- ============================================================================
-- Verification app schema  (paste this whole file into Supabase > SQL Editor)
-- ============================================================================
-- Two tables:
--   verifications  -- one row per (paper, reviewer); the source of truth
--   activity       -- append-only event log that powers the live dashboard feed
--
-- Auth model: name-only. There are no Supabase user accounts; the reviewer's
-- typed name is stored in the `reviewer` column. RLS is therefore permissive
-- (anyone with the anon key can read/write). This is intended for a small,
-- trusted internal team. If you later want real logins, switch to Supabase
-- email auth and tighten the policies to `auth.uid()`.
-- ============================================================================

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- verifications
-- ---------------------------------------------------------------------------
create table if not exists public.verifications (
  id            uuid primary key default gen_random_uuid(),
  paper_id      text not null,            -- arxiv id / custom_id
  reviewer      text not null,            -- typed display name

  -- per-signal verdicts: 'agree' | 'disagree' | 'unsure' | null (not yet done)
  code_verdict             text,
  code_note                text,
  dataset_verdict          text,
  dataset_note             text,
  weights_verdict          text,
  weights_note             text,
  dataset_standard_verdict text,
  dataset_standard_note    text,

  -- score review
  score_verdict   text,                   -- 'agree' | 'disagree' | 'unsure'
  score_suggested int,                    -- reviewer's own score, if disagree
  score_note      text,

  -- reviewer-found links (so you can collect ground-truth artifact urls)
  found_code_url    text,
  found_dataset_url text,
  found_weights_url text,

  status      text not null default 'in_progress',   -- 'in_progress' | 'completed'
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),

  unique (paper_id, reviewer)
);

create index if not exists verifications_reviewer_idx on public.verifications (reviewer);
create index if not exists verifications_paper_idx    on public.verifications (paper_id);
create index if not exists verifications_updated_idx  on public.verifications (updated_at desc);

-- keep updated_at fresh on every upsert/update
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists verifications_touch on public.verifications;
create trigger verifications_touch
  before update on public.verifications
  for each row execute function public.touch_updated_at();

-- ---------------------------------------------------------------------------
-- activity feed (lightweight; powers "who is doing what right now")
-- ---------------------------------------------------------------------------
create table if not exists public.activity (
  id         bigint generated always as identity primary key,
  reviewer   text not null,
  paper_id   text,
  action     text not null,              -- 'opened' | 'saved' | 'completed' | 'login'
  detail     text,
  created_at timestamptz not null default now()
);

create index if not exists activity_created_idx on public.activity (created_at desc);

-- ---------------------------------------------------------------------------
-- Row Level Security: permissive for the anon key (trusted-team model)
-- ---------------------------------------------------------------------------
alter table public.verifications enable row level security;
alter table public.activity      enable row level security;

drop policy if exists verifications_all on public.verifications;
create policy verifications_all on public.verifications
  for all to anon, authenticated using (true) with check (true);

drop policy if exists activity_all on public.activity;
create policy activity_all on public.activity
  for all to anon, authenticated using (true) with check (true);

-- Optional: let the dashboard get live updates without polling.
-- (Supabase Realtime) -- safe to run twice.
alter publication supabase_realtime add table public.verifications;
alter publication supabase_realtime add table public.activity;
