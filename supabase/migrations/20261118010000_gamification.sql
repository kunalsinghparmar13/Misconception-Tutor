-- Supabase migration: Gamification (XP, Levels, Streaks, Daily Challenges, Explain-It-Back)
-- Extends tutor schema with engagement & habit-forming mechanics under Row Level Security (RLS).

-- 1. Learner XP & Leveling
create table if not exists public.learner_xp (
  learner_id text primary key,
  user_id uuid references auth.users (id) on delete cascade,
  total_xp integer not null default 0,
  combo_count integer not null default 0,
  total_actions integer not null default 0,
  updated_at timestamptz not null default now()
);

create index if not exists learner_xp_user_idx on public.learner_xp (user_id);
alter table public.learner_xp enable row level security;

create policy "learner_xp: read own" on public.learner_xp
  for select to authenticated
  using ((select auth.uid())::text = learner_id or (user_id is not null and (select auth.uid()) = user_id));

create policy "learner_xp: upsert own" on public.learner_xp
  for all to authenticated
  using ((select auth.uid())::text = learner_id or (user_id is not null and (select auth.uid()) = user_id))
  with check ((select auth.uid())::text = learner_id or (user_id is not null and (select auth.uid()) = user_id));

-- 2. Streaks & Freeze Mechanism
create table if not exists public.streak_data (
  learner_id text primary key,
  user_id uuid references auth.users (id) on delete cascade,
  current_streak integer not null default 0,
  longest_streak integer not null default 0,
  last_active_date date,
  freezes_available integer not null default 1,
  freezes_used_total integer not null default 0,
  total_active_days integer not null default 0,
  updated_at timestamptz not null default now()
);

alter table public.streak_data enable row level security;

create policy "streak_data: manage own" on public.streak_data
  for all to authenticated
  using ((select auth.uid())::text = learner_id or (user_id is not null and (select auth.uid()) = user_id))
  with check ((select auth.uid())::text = learner_id or (user_id is not null and (select auth.uid()) = user_id));

-- 3. Daily Challenges
create table if not exists public.daily_challenges (
  learner_id text not null,
  challenge_date date not null,
  user_id uuid references auth.users (id) on delete cascade,
  target_misc text,
  problem_json jsonb,
  completed boolean not null default false,
  correct boolean,
  xp_earned integer not null default 0,
  created_at timestamptz not null default now(),
  primary key (learner_id, challenge_date)
);

create index if not exists daily_challenges_date_idx on public.daily_challenges (challenge_date desc);
alter table public.daily_challenges enable row level security;

create policy "daily_challenges: manage own" on public.daily_challenges
  for all to authenticated
  using ((select auth.uid())::text = learner_id or (user_id is not null and (select auth.uid()) = user_id))
  with check ((select auth.uid())::text = learner_id or (user_id is not null and (select auth.uid()) = user_id));

-- 4. Explain-It-Back Submissions
create table if not exists public.explain_back (
  id uuid primary key default gen_random_uuid(),
  learner_id text not null,
  user_id uuid references auth.users (id) on delete cascade,
  session_id text,
  misconception text,
  learner_explanation text not null,
  stars integer not null default 0 check (stars between 0 and 3),
  feedback text,
  xp_earned integer not null default 0,
  created_at timestamptz not null default now()
);

create index if not exists explain_back_learner_idx on public.explain_back (learner_id, created_at desc);
alter table public.explain_back enable row level security;

create policy "explain_back: manage own" on public.explain_back
  for all to authenticated
  using ((select auth.uid())::text = learner_id or (user_id is not null and (select auth.uid()) = user_id))
  with check ((select auth.uid())::text = learner_id or (user_id is not null and (select auth.uid()) = user_id));
