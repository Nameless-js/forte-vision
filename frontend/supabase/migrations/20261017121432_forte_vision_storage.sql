-- Local Supabase. Server-only access; videos remain on local disk.
create table if not exists public.analysis_jobs (
  id uuid primary key,
  status text not null check (status in ('processing','done','failed')),
  mode text not null default 'model' check (mode in ('model','demo')),
  filename text check (char_length(filename) <= 255),
  file_size bigint check (file_size >= 0),
  duration_sec double precision check (duration_sec > 0),
  result jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists analysis_jobs_created_idx on public.analysis_jobs (created_at desc);
create index if not exists analysis_jobs_processing_idx on public.analysis_jobs (status) where status='processing';
alter table public.analysis_jobs enable row level security;
revoke all on public.analysis_jobs from anon, authenticated;
grant select, insert, update, delete on public.analysis_jobs to service_role;
create table if not exists public.normative_rules (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  title text not null,
  document_title text not null,
  section text,
  source_url text check (source_url ~ '^https://'),
  description text,
  verified boolean not null default false,
  created_at timestamptz not null default now()
);
alter table public.normative_rules enable row level security;
revoke all on public.normative_rules from anon, authenticated;
grant select, insert, update, delete on public.normative_rules to service_role;

-- One atomic job row holds events, proof frames and their rules.
create or replace view public.analysis_events with (security_invoker=true) as
select j.id as job_id, j.mode, (e.ordinality-1)::integer as event_index,
       e.value->>'type' as type,
       (e.value->>'timecode_sec')::double precision as timecode_sec,
       e.value->>'description' as description,
       e.value->'rule' as rule,
       e.value->'evidence_frames' as evidence_frames
from public.analysis_jobs j
cross join lateral jsonb_array_elements(coalesce(j.result->'violations','[]'::jsonb))
  with ordinality as e(value,ordinality);
revoke all on public.analysis_events from anon, authenticated;
grant select on public.analysis_events to service_role;
