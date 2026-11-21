-- Dev Productivity AI: weekly history.
-- Run once in the Supabase SQL editor. Safe to run again.
--
-- Only the backend touches these tables, with the secret key. Row level security is
-- on with no policies, so the public (publishable/anon) key can't read or write them.

create table if not exists public.tracked_repos (
  repo             text primary key,          -- "owner/name", lowercase
  display_name     text not null,             -- as GitHub spells it, e.g. "tailwindlabs/tailwindcss"
  added_at         timestamptz not null default now(),
  last_snapshot_at timestamptz,
  last_error       text
);

create table if not exists public.daily_snapshots (
  repo               text not null references public.tracked_repos(repo) on delete cascade,
  day                date not null,           -- UTC date the snapshot was taken
  health_score       int  not null,
  status             text not null,           -- healthy / watch / at_risk / quiet
  median_merge_hours real,                    -- six-week median, open to merge
  latest_week_hours  real,                    -- median wait in the most recent week
  top_review_share   int,                     -- % of reviews by the busiest reviewer
  top_reviewer       text,
  open_prs           int,
  stale_open_prs     int,                     -- open more than 3 days
  merged_prs         int,
  commits            int,
  people             int,
  signals            jsonb not null default '[]',
  created_at         timestamptz not null default now(),
  primary key (repo, day)
);

create index if not exists daily_snapshots_repo_day on public.daily_snapshots (repo, day desc);

alter table public.tracked_repos   enable row level security;
alter table public.daily_snapshots enable row level security;

-- Newer Supabase projects don't grant table access to roles automatically.
-- service_role is what the backend's secret key acts as; nobody else gets access.
grant usage on schema public to service_role;
grant select, insert, update, delete on public.tracked_repos, public.daily_snapshots to service_role;

-- Weekly email reports. Subscriptions are made from a team space (its private link),
-- so reports go to the team the project belongs to, not to anyone watching a stranger's repo.
-- Every subscription must be confirmed from the email it was made for (double opt-in).
create table if not exists public.subscriptions (
  id            uuid primary key default gen_random_uuid(),
  email         text not null,
  repo          text not null,                -- "owner/name", lowercase
  display_name  text not null,
  team          text not null,                -- team space id; its documents ground the report
  timezone      text not null default 'UTC',
  token         text not null unique,         -- secret for the confirm and unsubscribe links
  confirmed     boolean not null default false,
  created_at    timestamptz not null default now(),
  confirmed_at  timestamptz,
  last_sent_at  timestamptz,
  unique (email, repo, team)
);

alter table public.subscriptions enable row level security;
grant select, insert, update, delete on public.subscriptions to service_role;
