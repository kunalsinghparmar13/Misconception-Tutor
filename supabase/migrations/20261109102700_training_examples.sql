-- Applied to the Supabase project "Misconception-Tutor" (elqvhkhtoucovwdnjylp) on 2026-11-09.
-- Learner questions + reviewer-approved tutor answers, collected to continue fine-tuning the model.
-- Written only by the app server (secret key); browsers have no access, so examples can't be forged.

create table public.training_examples (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id) on delete set null,
  subject text not null,
  question text not null check (char_length(question) <= 4000),
  answer text not null check (char_length(answer) <= 20000),
  misconception text,
  grounding_kind text,
  student_correct boolean,
  approved boolean not null,
  verified boolean not null,
  rating text check (rating in ('helpful', 'unhelpful')),
  model text,
  exported_at timestamptz,
  created_at timestamptz not null default now()
);

create index training_examples_created_idx on public.training_examples (created_at);
create index training_examples_user_idx on public.training_examples (user_id);

alter table public.training_examples enable row level security;
-- No policies on purpose: only the server's secret key (which bypasses RLS) can read or write.
revoke all on public.training_examples from anon, authenticated;
