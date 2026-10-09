create table if not exists public.pw_errors(id uuid primary key, created_at timestamptz not null, code text not null);
create table if not exists public.pw_limits(bucket text primary key, count integer not null, expires_at timestamptz not null);
alter table public.pw_errors enable row level security;
alter table public.pw_limits enable row level security;
revoke all on public.pw_errors,public.pw_limits from public,anon,authenticated;
grant select,insert,update,delete on public.pw_errors,public.pw_limits to service_role;
create index if not exists pw_errors_created_at_idx on public.pw_errors(created_at);
create index if not exists pw_limits_expires_at_idx on public.pw_limits(expires_at);
create or replace function public.pw_take_limit(p_bucket text,p_maximum integer,p_seconds integer)
returns boolean language plpgsql security invoker set search_path='' as $$
declare accepted integer;
begin
 if p_maximum<1 or p_seconds<1 or length(p_bucket)>200 then return false; end if;
 insert into public.pw_limits(bucket,count,expires_at) values(p_bucket,1,now()+make_interval(secs=>p_seconds))
 on conflict(bucket) do update set
 count=case when public.pw_limits.expires_at<=now() then 1 else public.pw_limits.count+1 end,
 expires_at=case when public.pw_limits.expires_at<=now() then now()+make_interval(secs=>p_seconds) else public.pw_limits.expires_at end
 where public.pw_limits.expires_at<=now() or public.pw_limits.count<p_maximum
 returning count into accepted;
 return accepted is not null;
end $$;
create or replace function public.pw_cleanup(p_days integer default 30)
returns void language plpgsql security invoker set search_path='' as $$
begin
 delete from public.pw_events where created_at<now()-make_interval(days=>greatest(p_days,1));
 delete from public.pw_errors where created_at<now()-make_interval(days=>greatest(p_days,1));
 delete from public.pw_limits where expires_at<now();
end $$;
create or replace function public.pw_dashboard()
returns jsonb language sql security invoker set search_path='' as $$
select jsonb_build_object(
'chats',(select count(distinct session_id) from public.pw_events),
'questions',(select count(*) from public.pw_events),
'outcomes',coalesce((select jsonb_agg(x) from(select outcome,count(*) as count from public.pw_events group by outcome)x),'[]'::jsonb),
'popular',coalesce((select jsonb_agg(x) from(select question,count(*) as count from public.pw_events group by question order by count(*) desc limit 15)x),'[]'::jsonb),
'gaps',coalesce((select jsonb_agg(x) from(select topic,question,count(*) as count from public.pw_events where outcome in('unknown','clarify','unavailable') group by topic,question order by count(*) desc limit 100)x),'[]'::jsonb),
'errors',coalesce((select jsonb_agg(x) from(select created_at,code from public.pw_errors order by created_at desc limit 15)x),'[]'::jsonb));
$$;
revoke execute on function public.pw_take_limit(text,integer,integer),public.pw_cleanup(integer),public.pw_dashboard() from public,anon,authenticated;
grant execute on function public.pw_take_limit(text,integer,integer),public.pw_cleanup(integer),public.pw_dashboard() to service_role;
