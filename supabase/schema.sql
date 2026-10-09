-- Dedicated assessment project only. Run with an administrative connection.
-- No public/browser access. The FastAPI server uses the secret key.
create table if not exists public.pw_events (
 id uuid primary key,
 created_at timestamptz not null,
 session_id text not null,
 question text not null,
 topic text not null,
 outcome text not null,
 latency_ms integer not null
);
create table if not exists public.pw_knowledge (
 id text primary key,
 created_at timestamptz not null default now(),
 snapshot jsonb not null
);
alter table public.pw_events enable row level security;
alter table public.pw_knowledge enable row level security;
revoke all on public.pw_events, public.pw_knowledge from public, anon, authenticated;
grant select,insert,update,delete on public.pw_events, public.pw_knowledge to service_role;
create index if not exists pw_events_created_at_idx on public.pw_events(created_at);
-- Supabase's automatic-RLS helper is an event trigger, not a public RPC.
do $$
begin
 if to_regprocedure('public.rls_auto_enable()') is not null then
  revoke execute on function public.rls_auto_enable() from public, anon, authenticated;
 end if;
end $$;
