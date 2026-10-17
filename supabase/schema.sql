-- Apply to your local/self-hosted Supabase SQL editor.
-- Only the Python server service key can read/write these rows.
create table if not exists public.analysis_jobs (
  id uuid primary key,
  status text not null check (status in ('processing','done','failed')),
  result jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
alter table public.analysis_jobs enable row level security;
revoke all on public.analysis_jobs from anon, authenticated;
grant select, insert, update, delete on public.analysis_jobs to service_role;
-- No public policies: results are served only through the authenticated Python API.
