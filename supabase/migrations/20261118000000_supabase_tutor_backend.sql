-- Supabase migration: Bayesian Knowledge Tracing (BKT) states and Learner Notifications
-- Extends core tutor schema for complete cloud-native persistence with Row Level Security (RLS).
-- Follows Supabase Postgres Best Practices: cached (select auth.uid()), indexed foreign keys, RLS enabled.

-- 1. Bayesian Knowledge Tracing (BKT) States
create table if not exists public.bkt_states (
  learner_id text not null,
  user_id uuid references auth.users (id) on delete cascade,
  misc_id text not null,
  p_mastery double precision not null default 0.50,
  last_updated timestamptz not null default now(),
  primary key (learner_id, misc_id)
);

create index if not exists bkt_states_learner_idx on public.bkt_states (learner_id);
create index if not exists bkt_states_user_idx on public.bkt_states (user_id);

alter table public.bkt_states enable row level security;

create policy "bkt_states: read own" on public.bkt_states
  for select to authenticated
  using (
    (select auth.uid())::text = learner_id
    or (user_id is not null and (select auth.uid()) = user_id)
  );

create policy "bkt_states: insert own" on public.bkt_states
  for insert to authenticated
  with check (
    (select auth.uid())::text = learner_id
    or (user_id is not null and (select auth.uid()) = user_id)
  );

create policy "bkt_states: update own" on public.bkt_states
  for update to authenticated
  using (
    (select auth.uid())::text = learner_id
    or (user_id is not null and (select auth.uid()) = user_id)
  )
  with check (
    (select auth.uid())::text = learner_id
    or (user_id is not null and (select auth.uid()) = user_id)
  );

create policy "bkt_states: delete own" on public.bkt_states
  for delete to authenticated
  using (
    (select auth.uid())::text = learner_id
    or (user_id is not null and (select auth.uid()) = user_id)
  );

-- 2. Learner Notifications & Study Recommendations
create table if not exists public.learner_notifications (
  id text primary key,
  learner_id text not null,
  user_id uuid references auth.users (id) on delete cascade,
  title text not null,
  message text not null,
  icon text,
  category text default 'general',
  read_status boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists learner_notifs_learner_idx on public.learner_notifications (learner_id, created_at desc);
create index if not exists learner_notifs_user_idx on public.learner_notifications (user_id, created_at desc);

alter table public.learner_notifications enable row level security;

create policy "notifications: read own" on public.learner_notifications
  for select to authenticated
  using (
    (select auth.uid())::text = learner_id
    or (user_id is not null and (select auth.uid()) = user_id)
  );

create policy "notifications: insert own" on public.learner_notifications
  for insert to authenticated
  with check (
    (select auth.uid())::text = learner_id
    or (user_id is not null and (select auth.uid()) = user_id)
  );

create policy "notifications: update own" on public.learner_notifications
  for update to authenticated
  using (
    (select auth.uid())::text = learner_id
    or (user_id is not null and (select auth.uid()) = user_id)
  )
  with check (
    (select auth.uid())::text = learner_id
    or (user_id is not null and (select auth.uid()) = user_id)
  );

create policy "notifications: delete own" on public.learner_notifications
  for delete to authenticated
  using (
    (select auth.uid())::text = learner_id
    or (user_id is not null and (select auth.uid()) = user_id)
  );

-- 3. Tutor sessions & Practice compatibility updates
alter table public.tutor_sessions add column if not exists learner_id text;
alter table public.practice_attempts add column if not exists learner_id text;
alter table public.practice_attempts add column if not exists subject text;

create index if not exists tutor_sessions_learner_created_idx on public.tutor_sessions (learner_id, created_at desc);
create index if not exists practice_attempts_learner_idx on public.practice_attempts (learner_id, created_at desc);
