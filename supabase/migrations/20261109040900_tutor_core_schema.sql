-- Applied to the Supabase project "Misconception-Tutor" (elqvhkhtoucovwdnjylp) on 2026-11-09.
-- Misconception Tutor: per-learner data. Every table is private to its owner (Row Level Security).

create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  full_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.tutor_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  question text not null check (char_length(question) <= 4000),
  subject text not null default 'Mathematics',
  misconception text,
  result jsonb,
  sample_id text,
  created_at timestamptz not null default now()
);

create table public.practice_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  session_id uuid references public.tutor_sessions (id) on delete cascade,
  practice_id text not null,
  set_id text,
  misconception text,
  answer text check (char_length(answer) <= 4000),
  correct boolean not null,
  created_at timestamptz not null default now()
);

create table public.feedback (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  session_id uuid references public.tutor_sessions (id) on delete cascade,
  rating text not null check (rating in ('helpful', 'unhelpful')),
  created_at timestamptz not null default now()
);

create index tutor_sessions_user_created_idx on public.tutor_sessions (user_id, created_at desc);
create index practice_attempts_user_created_idx on public.practice_attempts (user_id, created_at desc);
create index practice_attempts_session_idx on public.practice_attempts (session_id);
create index feedback_user_idx on public.feedback (user_id);
create index feedback_session_idx on public.feedback (session_id);

alter table public.profiles enable row level security;
alter table public.tutor_sessions enable row level security;
alter table public.practice_attempts enable row level security;
alter table public.feedback enable row level security;

create policy "profiles: read own" on public.profiles
  for select to authenticated using ((select auth.uid()) = id);
create policy "profiles: update own" on public.profiles
  for update to authenticated using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

create policy "tutor_sessions: read own" on public.tutor_sessions
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "tutor_sessions: insert own" on public.tutor_sessions
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "tutor_sessions: update own" on public.tutor_sessions
  for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "tutor_sessions: delete own" on public.tutor_sessions
  for delete to authenticated using ((select auth.uid()) = user_id);

create policy "practice_attempts: read own" on public.practice_attempts
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "practice_attempts: insert own" on public.practice_attempts
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "practice_attempts: delete own" on public.practice_attempts
  for delete to authenticated using ((select auth.uid()) = user_id);

create policy "feedback: read own" on public.feedback
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "feedback: insert own" on public.feedback
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "feedback: delete own" on public.feedback
  for delete to authenticated using ((select auth.uid()) = user_id);

create function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, full_name)
  values (new.id, nullif(trim(new.raw_user_meta_data ->> 'full_name'), ''));
  return new;
end;
$$;

revoke execute on function public.handle_new_user() from public, anon, authenticated;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
