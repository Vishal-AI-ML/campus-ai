-- ============================================================================
-- Phase 4 RLS fix: dedicated NON-bypass application role (app_user)
-- ----------------------------------------------------------------------------
-- WHY: Supabase's default `postgres` role has BYPASSRLS = true, so it ignores
-- every Row-Level Security policy. The app MUST connect as a role WITHOUT
-- bypass for RLS to actually filter rows. Migrations keep using `postgres`
-- (the table owner) because they run DDL.
--
-- NOTE: We do NOT write NOSUPERUSER / NOBYPASSRLS explicitly, because only a
-- real superuser may set those attributes and Supabase's `postgres` is not
-- one. A freshly created role already DEFAULTS to NOSUPERUSER + NOBYPASSRLS
-- + NOCREATEDB + NOCREATEROLE, which is exactly what we want. The final SELECT
-- proves bypassrls = false.
--
-- HOW TO RUN: paste into the Supabase SQL editor (runs as `postgres`).
-- Replace the password placeholder first. Safe to re-run (idempotent).
-- ============================================================================

-- 1) Create the role (only if missing). Pick a STRONG password.
--    Defaults give us NOSUPERUSER + NOBYPASSRLS automatically.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user LOGIN PASSWORD 'Vishal0703050607@';
    END IF;
END$$;

-- Make sure it can log in (LOGIN is not a privileged attribute).
-- To rotate the password later: ALTER ROLE app_user PASSWORD '...';
ALTER ROLE app_user LOGIN;

-- 2) Let it connect to the database (Supabase db name is `postgres`).
GRANT CONNECT ON DATABASE postgres TO app_user;

-- 3) Schema usage (public = your tables, app = the RLS helper fn).
GRANT USAGE ON SCHEMA public TO app_user;
GRANT USAGE ON SCHEMA app TO app_user;

-- 4) Read/write on all current tables + sequences (for serial PKs).
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- 5) Execute the RLS helper the policies call.
GRANT EXECUTE ON FUNCTION app.current_tenant_id() TO app_user;

-- 6) Future tables/sequences created by `postgres` are auto-granted too.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_user;

-- 7) Sanity check: MUST show bypassrls = f (false).
SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'app_user';
