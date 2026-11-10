-- Dedicated heartbeat row used by GitHub Actions.
-- Keep this table separate from application/user data.
create table if not exists public.ops_heartbeat (
    key text primary key check (key = 'github-actions'),
    checked_at timestamptz not null,
    workflow_run_id text not null,
    check_type text not null check (check_type in ('scheduled', 'monday_weekly'))
);

alter table public.ops_heartbeat enable row level security;

-- Only the server-side service role may access this operational table.
revoke all on table public.ops_heartbeat from anon, authenticated;
grant all on table public.ops_heartbeat to service_role;
